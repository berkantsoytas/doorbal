from pathlib import Path

import cv2


def _detect_camera_priority(device_path: Path):
    sysfs_device_dir = Path("/sys/class/video4linux") / device_path.name / "device"

    resolved_parts = []
    if sysfs_device_dir.exists():
        try:
            resolved_parts = [part.lower() for part in sysfs_device_dir.resolve().parts]
        except OSError:
            resolved_parts = []

    device_text = " ".join(resolved_parts)
    if "usb" in device_text:
        return 0
    if any(keyword in device_text for keyword in ["bcm2835", "csi", "unicam", "rp1-cfe"]):
        return 2
    return 1


def _candidate_camera_indices(max_index: int = 10):
    linux_devices = sorted(Path("/dev").glob("video*"))
    seen_indices = set()

    prioritized_devices = sorted(
        linux_devices,
        key=lambda device: (_detect_camera_priority(device), device.name),
    )

    for device_path in prioritized_devices:
        suffix = device_path.name.replace("video", "")
        if suffix.isdigit():
            camera_index = int(suffix)
            if camera_index not in seen_indices:
                seen_indices.add(camera_index)
                yield camera_index

    for camera_index in range(max_index):
        if camera_index not in seen_indices:
            yield camera_index


def _open_and_validate(index: int, backend):
    camera = cv2.VideoCapture(index, backend) if backend is not None else cv2.VideoCapture(index)
    if not camera.isOpened():
        camera.release()
        return None

    ok, _ = camera.read()
    if ok:
        return camera

    camera.release()
    return None


def open_camera():
    backends = [cv2.CAP_V4L2, None]

    for camera_index in _candidate_camera_indices():
        for backend in backends:
            camera = _open_and_validate(camera_index, backend)
            if camera is not None:
                backend_name = "V4L2" if backend == cv2.CAP_V4L2 else "default"
                print(f"Kamera bulundu: /dev/video{camera_index} ({backend_name})")
                return camera

    raise RuntimeError(
        "Kamera acilamadi. Raspberry Pi uzerinde USB webcam baglantisini, /dev/video* cihazlarini ve kullanici izinlerini kontrol et."
    )