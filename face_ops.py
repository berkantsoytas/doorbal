from datetime import datetime
from pathlib import Path
import re
import time

import cv2
import face_recognition


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
    window_name="AI Doorbell - Face Recognition",
):
    collected_faces = []
    photo_index = 1

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
                2,
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