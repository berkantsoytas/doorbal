import cv2
import face_recognition
from pathlib import Path
from datetime import datetime
import re
import time

from encoder import load_known_faces

known_face_encodings, known_face_names = load_known_faces("known_faces")


def open_camera():
    # Linux'ta once V4L2, olmazsa varsayilan backend ile dene.
    camera = cv2.VideoCapture(0, cv2.CAP_V4L2)
    if camera.isOpened():
        return camera

    camera.release()
    camera = cv2.VideoCapture(0)
    if camera.isOpened():
        return camera

    raise RuntimeError("Kamera acilamadi. /dev/video0 izinlerini ve cihaz baglantisini kontrol et.")


cap = open_camera()
last_face_frame = None
last_face_box = None
last_face_name = None
brightness_beta = 35
contrast_alpha = 1.08
output_dir = Path("captured_faces")
known_faces_root = Path("known_faces")
output_dir.mkdir(parents=True, exist_ok=True)
known_faces_root.mkdir(parents=True, exist_ok=True)


def extract_expanded_face(frame, face_box, scale: float = 2.0):
    top, right, bottom, left = face_box
    height, width = frame.shape[:2]

    box_w = right - left
    box_h = bottom - top
    cx = left + box_w / 2.0
    cy = top + box_h / 2.0

    new_w = int(box_w * scale)
    new_h = int(box_h * scale)

    new_left = max(0, int(cx - new_w / 2.0))
    new_right = min(width, int(cx + new_w / 2.0))
    new_top = max(0, int(cy - new_h / 2.0))
    new_bottom = min(height, int(cy + new_h / 2.0))

    expanded = frame[new_top:new_bottom, new_left:new_right]
    if expanded.size == 0:
        return None
    return expanded


def save_face_snapshot(face_crop, save_dir: Path, suffix: str = ""):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    extra = f"_{suffix}" if suffix else ""
    filename = f"face_{timestamp}{extra}.jpg"
    output_path = save_dir / filename
    cv2.imwrite(str(output_path), face_crop)
    return output_path


def normalize_person_name(raw_name: str):
    cleaned = re.sub(r"\s+", "_", raw_name.strip())
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "", cleaned)
    return cleaned


def select_largest_face(face_locations):
    if not face_locations:
        return None
    return max(face_locations, key=lambda loc: (loc[2] - loc[0]) * (loc[1] - loc[3]))


def capture_face_burst(
    cap_obj,
    fallback_box,
    brightness_beta_value,
    contrast_alpha_value,
    count=5,
    countdown_seconds=2,
):
    collected_faces = []
    photo_index = 1
    window_name = "AI Doorbell - Face Recognition"

    while photo_index <= count:
        countdown_end = time.time() + countdown_seconds
        preview_frame = None
        preview_box = fallback_box

        while time.time() < countdown_end:
            ret_burst, frame_burst = cap_obj.read()
            if not ret_burst:
                continue

            frame_burst = cv2.convertScaleAbs(
                frame_burst, alpha=contrast_alpha_value, beta=brightness_beta_value
            )
            rgb_burst = cv2.cvtColor(frame_burst, cv2.COLOR_BGR2RGB)
            burst_locations = face_recognition.face_locations(rgb_burst)
            best_location = select_largest_face(burst_locations)
            if best_location is None:
                best_location = fallback_box

            preview_frame = frame_burst
            preview_box = best_location

            if preview_box is not None:
                top, right, bottom, left = preview_box
                cv2.rectangle(preview_frame, (left, top), (right, bottom), (0, 200, 255), 2)

            remaining = max(0.0, countdown_end - time.time())
            cv2.putText(
                preview_frame,
                f"{photo_index}/{count} cekiliyor - {remaining:.1f}s",
                (10, 65),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2
            )
            cv2.imshow(window_name, preview_frame)
            if cv2.waitKey(1) & 0xFF == 27:
                return collected_faces

        if preview_frame is None or preview_box is None:
            continue

        expanded = extract_expanded_face(preview_frame, preview_box, scale=2.0)
        if expanded is not None:
            collected_faces.append(expanded.copy())
            photo_index += 1

    return collected_faces

while True:
    ret, frame = cap.read()
    
    if not ret:
        break

    # Canli goruntu parlaklik/kontrast duzeltmesi.
    frame = cv2.convertScaleAbs(frame, alpha=contrast_alpha, beta=brightness_beta)

    # dlib/face_recognition icin contiguous RGB buffer gerekli.
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb)
    face_encodings = face_recognition.face_encodings(rgb, face_locations)

    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        name = "Yabanci"

        if known_face_encodings:
            matches = face_recognition.compare_faces(
                known_face_encodings, face_encoding, tolerance=0.5
            )
            face_distances = face_recognition.face_distance(
                known_face_encodings, face_encoding
            )

            if len(face_distances) > 0:
                best_match_index = face_distances.argmin()
                if matches[best_match_index]:
                    name = known_face_names[best_match_index]

        # kutu çiz
        cv2.rectangle(frame, (left, top), (right, bottom), (0,255,0), 2)

        # Son gorulen yuzun frame + kutu bilgisini sakla.
        last_face_frame = frame.copy()
        last_face_box = (top, right, bottom, left)
        last_face_name = name

        # isim yaz
        cv2.putText(
            frame,
            name,
            (left, top - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

    cv2.putText(
        frame,
        f"Brightness: {brightness_beta} (b:+ n:-)",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 255),
        2
    )

    cv2.imshow("AI Doorbell - Face Recognition", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord("s"):
        if last_face_frame is not None and last_face_box is not None:
            if last_face_name != "Yabanci":
                print("Bu yuz zaten taniniyor. Yeni kisi kaydi icin yabanci bir yuzde 's' kullan.")
                continue

            raw_name = input("Kisi adini gir (bos birakirsan encoder'a eklenmez): ")
            person_name = normalize_person_name(raw_name)
            if not person_name:
                print("Gecerli bir isim girilmedigi icin encoder'a ekleme yapilmadi.")
                continue

            person_dir = known_faces_root / person_name
            person_dir.mkdir(parents=True, exist_ok=True)
            burst_faces = capture_face_burst(
                cap_obj=cap,
                fallback_box=last_face_box,
                brightness_beta_value=brightness_beta,
                contrast_alpha_value=contrast_alpha,
                count=5,
                countdown_seconds=2,
            )
            saved_paths = []
            for idx, face_img in enumerate(burst_faces, start=1):
                captured_path = save_face_snapshot(face_img, output_dir, suffix=f"burst{idx}")
                known_path = save_face_snapshot(face_img, person_dir, suffix=f"burst{idx}")
                saved_paths.append((captured_path, known_path))

            known_face_encodings, known_face_names = load_known_faces("known_faces")
            print(f"{len(saved_paths)} adet farkli yuz snapshot kaydedildi.")
            print(f"Encoder guncellendi: known_faces/{person_name}")
        else:
            print("Snapshot icin algilanmis yuz yok.")
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