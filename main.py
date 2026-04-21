from pathlib import Path
from datetime import datetime
import os
import time

import cv2
import face_recognition

from camera_utils import open_camera
from env_utils import load_dotenv_file
from encoder import load_known_faces
from face_ops import capture_face_burst, extract_expanded_face, normalize_person_name, save_face_snapshot
from sound_utils import play_doorbell_sound_async
from telegram_utils import send_telegram_photo


WINDOW_NAME = "AI Doorbell - Face Recognition"
UNKNOWN_NAME = "Yabanci"
TELEGRAM_ALERT_COOLDOWN_SECONDS = 30
DOORBELL_COOLDOWN_SECONDS = 45
DOORBELL_RING_DURATION_SECONDS = 10


def build_telegram_caption(detections, event_time: str):
    known_names = sorted({name for _, name in detections if name != UNKNOWN_NAME})
    has_unknown = any(name == UNKNOWN_NAME for _, name in detections)

    if known_names and not has_unknown:
        if len(known_names) == 1:
            return f"Kapi onunde {known_names[0]} var. Zaman: {event_time}"
        joined_names = ", ".join(known_names)
        return f"Kapi onunde tanidik kisiler var: {joined_names}. Zaman: {event_time}"

    return f"Kapi onunde yabanci birisi var. Zaman: {event_time}"


def detect_and_annotate_faces(frame, known_face_encodings, known_face_names):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb)
    face_encodings = face_recognition.face_encodings(rgb, face_locations)

    detections = []
    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        name = UNKNOWN_NAME

        if known_face_encodings:
            matches = face_recognition.compare_faces(
                known_face_encodings, face_encoding, tolerance=0.5
            )
            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            if len(face_distances) > 0:
                best_match_index = face_distances.argmin()
                if matches[best_match_index]:
                    name = known_face_names[best_match_index]

        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        cv2.putText(
            frame,
            name,
            (left, top - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
        )
        detections.append(((top, right, bottom, left), name))

    return frame, detections


def save_new_person_faces(
    cap,
    last_face_box,
    brightness_beta,
    contrast_alpha,
    output_dir,
    known_faces_root,
):
    raw_name = input("Kisi adini gir (bos birakirsan encoder'a eklenmez): ")
    person_name = normalize_person_name(raw_name)
    if not person_name:
        print("Gecerli bir isim girilmedigi icin encoder'a ekleme yapilmadi.")
        return

    person_dir = known_faces_root / person_name
    person_dir.mkdir(parents=True, exist_ok=True)
    burst_faces = capture_face_burst(
        cap_obj=cap,
        fallback_box=last_face_box,
        brightness_beta_value=brightness_beta,
        contrast_alpha_value=contrast_alpha,
        count=5,
        countdown_seconds=2,
        window_name=WINDOW_NAME,
    )

    saved_paths = []
    for idx, face_img in enumerate(burst_faces, start=1):
        captured_path = save_face_snapshot(face_img, output_dir, suffix=f"burst{idx}")
        known_path = save_face_snapshot(face_img, person_dir, suffix=f"burst{idx}")
        saved_paths.append((captured_path, known_path))

    known_face_encodings, known_face_names = load_known_faces("known_faces")
    print(f"{len(saved_paths)} adet farkli yuz snapshot kaydedildi.")
    print(f"Encoder guncellendi: known_faces/{person_name}")
    return known_face_encodings, known_face_names


def main():
    load_dotenv_file()

    known_face_encodings, known_face_names = load_known_faces("known_faces")
    cap = open_camera()

    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    telegram_config_warning_printed = False

    last_face_frame = None
    last_face_box = None
    last_face_name = None
    last_telegram_alert_sent_at = 0.0
    last_known_ring_at = 0.0
    face_present_previous_frame = False
    known_present_previous_frame = False
    brightness_beta = 35
    contrast_alpha = 1.08

    output_dir = Path("captured_faces")
    known_faces_root = Path("known_faces")
    output_dir.mkdir(parents=True, exist_ok=True)
    known_faces_root.mkdir(parents=True, exist_ok=True)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.convertScaleAbs(frame, alpha=contrast_alpha, beta=brightness_beta)
        frame_for_alert = frame.copy()
        frame, detections = detect_and_annotate_faces(frame, known_face_encodings, known_face_names)
        face_detected_this_frame = len(detections) > 0
        known_detected_this_frame = any(name != UNKNOWN_NAME for _, name in detections)

        if detections:
            last_face_box, last_face_name = detections[-1]
            last_face_frame = frame.copy()

        now_ts = time.time()
        should_notify_telegram = (
            face_detected_this_frame
            and not face_present_previous_frame
            and (now_ts - last_telegram_alert_sent_at) >= TELEGRAM_ALERT_COOLDOWN_SECONDS
        )
        should_ring_known = (
            known_detected_this_frame
            and not known_present_previous_frame
            and (now_ts - last_known_ring_at) >= DOORBELL_COOLDOWN_SECONDS
        )

        if should_notify_telegram:
            if not telegram_bot_token or not telegram_chat_id:
                if not telegram_config_warning_printed:
                    print(
                        "Telegram ayarlari eksik. TELEGRAM_BOT_TOKEN ve TELEGRAM_CHAT_ID tanimlayin."
                    )
                    telegram_config_warning_printed = True
            else:
                event_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                alert_boxes = [box for box, _ in detections]
                alert_image = None
                if alert_boxes:
                    alert_image = extract_expanded_face(frame_for_alert, alert_boxes[0], scale=2.0)

                caption = build_telegram_caption(detections, event_time)
                encoded_ok = False
                photo_bytes = b""
                if alert_image is not None:
                    encoded_ok, encoded_image = cv2.imencode(".jpg", alert_image)
                    if encoded_ok:
                        photo_bytes = encoded_image.tobytes()

                if encoded_ok and send_telegram_photo(
                    telegram_bot_token,
                    telegram_chat_id,
                    photo_bytes,
                    caption=caption,
                ):
                    last_telegram_alert_sent_at = now_ts
                    print("Telegram fotograf bildirimi gonderildi.")
                else:
                    print("Telegram fotograf bildirimi gonderilemedi.")

        if should_ring_known:
            if play_doorbell_sound_async(duration_seconds=DOORBELL_RING_DURATION_SECONDS):
                last_known_ring_at = now_ts
                print("Tanidik kisi algilandi, zil sesi calindi.")

        face_present_previous_frame = face_detected_this_frame
        known_present_previous_frame = known_detected_this_frame

        cv2.putText(
            frame,
            f"Brightness: {brightness_beta} (b:+ n:-)",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 255),
            2,
        )
        cv2.imshow(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("s"):
            if last_face_frame is None or last_face_box is None:
                print("Snapshot icin algilanmis yuz yok.")
                continue
            if last_face_name != UNKNOWN_NAME:
                print("Bu yuz zaten taniniyor. Yeni kisi kaydi icin yabanci bir yuzde 's' kullan.")
                continue

            updated_known = save_new_person_faces(
                cap=cap,
                last_face_box=last_face_box,
                brightness_beta=brightness_beta,
                contrast_alpha=contrast_alpha,
                output_dir=output_dir,
                known_faces_root=known_faces_root,
            )
            if updated_known:
                known_face_encodings, known_face_names = updated_known
        elif key == 27:
            break
        elif key == ord("b"):
            brightness_beta = min(120, brightness_beta + 5)
            print(f"Parlaklik arttirildi: {brightness_beta}")
        elif key == ord("n"):
            brightness_beta = max(0, brightness_beta - 5)
            print(f"Parlaklik azaltildi: {brightness_beta}")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()