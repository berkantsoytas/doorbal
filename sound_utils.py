import os
import shutil
import subprocess
import threading
import time


_doorbell_lock = threading.Lock()
_doorbell_thread = None


def _run_if_available(command):
    executable = command[0]
    if shutil.which(executable) is None:
        return False
    try:
        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except OSError:
        return False


def play_doorbell_sound(duration_seconds: int = 10) -> bool:
    end_time = time.time() + max(1, duration_seconds)

    while time.time() < end_time:
        # Try common Linux sound players first.
        if _run_if_available(["canberra-gtk-play", "-i", "bell", "-d", "ai-doorball"]):
            time.sleep(0.9)
            continue

        if _run_if_available(["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"]):
            time.sleep(0.9)
            continue

        if os.path.exists("/usr/share/sounds/alsa/Front_Center.wav"):
            if _run_if_available(["aplay", "/usr/share/sounds/alsa/Front_Center.wav"]):
                time.sleep(1.0)
                continue

        # Fallback to terminal bell.
        print("\a", end="", flush=True)
        time.sleep(0.7)

    return True


def _doorbell_worker(duration_seconds: int):
    try:
        play_doorbell_sound(duration_seconds=duration_seconds)
    finally:
        global _doorbell_thread
        with _doorbell_lock:
            _doorbell_thread = None


def play_doorbell_sound_async(duration_seconds: int = 10) -> bool:
    global _doorbell_thread
    with _doorbell_lock:
        if _doorbell_thread is not None and _doorbell_thread.is_alive():
            return False

        _doorbell_thread = threading.Thread(
            target=_doorbell_worker,
            args=(duration_seconds,),
            daemon=True,
        )
        _doorbell_thread.start()
        return True