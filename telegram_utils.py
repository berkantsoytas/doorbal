from urllib import error, parse, request


def _build_multipart_form_data(fields, files, boundary: str):
    body = bytearray()

    for key, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8")
        )
        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")

    for key, file_info in files.items():
        filename = file_info["filename"]
        content = file_info["content"]
        content_type = file_info.get("content_type", "application/octet-stream")

        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            (
                f'Content-Disposition: form-data; name="{key}"; '
                f'filename="{filename}"\r\n'
            ).encode("utf-8")
        )
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.extend(content)
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    return bytes(body)


def send_telegram_message(bot_token: str, chat_id: str, message: str, timeout: int = 6) -> bool:
    if not bot_token or not chat_id:
        return False

    endpoint = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = parse.urlencode({"chat_id": chat_id, "text": message}).encode("utf-8")
    req = request.Request(endpoint, data=payload, method="POST")

    try:
        with request.urlopen(req, timeout=timeout) as response:
            return 200 <= response.status < 300
    except (error.URLError, TimeoutError):
        return False


def send_telegram_photo(
    bot_token: str,
    chat_id: str,
    photo_bytes: bytes,
    caption: str = "",
    filename: str = "alert.jpg",
    timeout: int = 10,
) -> bool:
    if not bot_token or not chat_id or not photo_bytes:
        return False

    boundary = "----AIDoorballTelegramBoundary"
    payload = _build_multipart_form_data(
        fields={"chat_id": chat_id, "caption": caption},
        files={
            "photo": {
                "filename": filename,
                "content": photo_bytes,
                "content_type": "image/jpeg",
            }
        },
        boundary=boundary,
    )
    endpoint = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    req = request.Request(endpoint, data=payload, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

    try:
        with request.urlopen(req, timeout=timeout) as response:
            return 200 <= response.status < 300
    except (error.URLError, TimeoutError):
        return False