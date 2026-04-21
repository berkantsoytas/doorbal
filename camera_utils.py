from pathlib import Path
import shutil
import subprocess

import cv2


def _is_capture_device(source) -> bool | None:
    if not isinstance(source, str) or not source.startswith("/dev/video"):
        return None
    if shutil.which("v4l2-ctl") is None:
        return None

    try:
        result = subprocess.run(
            ["v4l2-ctl", "-d", source, "--all"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if result.returncode != 0:
        return False

    details = (result.stdout + result.stderr).lower()
    if "video capture" in details or "video capture mplane" in details:
        return True
    return False


def _candidate_camera_sources(max_index: int = 10):
    linux_devices = sorted(Path("/dev").glob("video*"))
    seen_sources = set()

    for device_path in linux_devices:
        device_str = str(device_path)
        capture_device = _is_capture_device(device_str)
        if capture_device is False:
            continue
        if device_str not in seen_sources:
            seen_sources.add(device_str)
            yield device_str

    for camera_index in range(max_index):
        if camera_index not in seen_sources:
            yield camera_index


def _open_and_validate(source, backend):
    camera = cv2.VideoCapture(source, backend) if backend is not None else cv2.VideoCapture(source)
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

    for camera_source in _candidate_camera_sources():
        for backend in backends:
            camera = _open_and_validate(camera_source, backend)
            if camera is not None:
                backend_name = "V4L2" if backend == cv2.CAP_V4L2 else "default"
                print(f"Kamera bulundu: {camera_source} ({backend_name})")
                return camera

    raise RuntimeError(
        "Kamera acilamadi. /dev/video* cihazlarini, kamera baglantisini ve kullanici izinlerini kontrol et."
    )