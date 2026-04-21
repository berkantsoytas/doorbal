from pathlib import Path

import face_recognition


SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def load_known_faces(known_faces_dir: str = "known_faces"):
    """
    known_faces klasorundeki gorsellerden yuz encoding listesi uretir.

    Klasor yapisi:
    - known_faces/
      - ali/
        - 1.jpg
      - ayse.jpg

    Donus:
    - known_face_encodings: [encoding, ...]
    - known_face_names: ["ali", "ayse", ...]
    """
    root = Path(known_faces_dir)
    known_face_encodings = []
    known_face_names = []

    if not root.exists():
        return known_face_encodings, known_face_names

    for image_path in root.rglob("*"):
        if not image_path.is_file():
            continue
        if image_path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
            continue

        image = face_recognition.load_image_file(str(image_path))
        encodings = face_recognition.face_encodings(image)

        if not encodings:
            continue

        known_face_encodings.append(encodings[0])

        if image_path.parent == root:
            person_name = image_path.stem
        else:
            person_name = image_path.parent.name
        known_face_names.append(person_name)

    return known_face_encodings, known_face_names
