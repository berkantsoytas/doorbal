import cv2


def open_camera():
    # Try V4L2 first on Linux; fallback to default backend.
    camera = cv2.VideoCapture(0, cv2.CAP_V4L2)
    if camera.isOpened():
        return camera

    camera.release()
    camera = cv2.VideoCapture(0)
    if camera.isOpened():
        return camera

    raise RuntimeError("Kamera acilamadi. /dev/video0 izinlerini ve cihaz baglantisini kontrol et.")