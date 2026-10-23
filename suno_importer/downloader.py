"""Public Suno audio downloader. Python standard library only; no account or API key."""
from __future__ import annotations

import html
from html.parser import HTMLParser
import os
from pathlib import Path
import re
import time
import json
import shutil
import subprocess
import tempfile
from urllib.parse import urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.error import HTTPError

MAX_AUDIO = 200 * 1024 * 1024
MAX_PAGE = 4 * 1024 * 1024
UUID = r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}"


class DownloadError(ValueError):
    pass


def validate_url(value: str) -> str:
    value = value.strip()
    if len(value) > 4096 or any(ord(c) < 32 for c in value):
        raise DownloadError("URL qua dai hoac co ky tu khong hop le.")
    try:
        p = urlsplit(value)
        port = p.port
    except ValueError as exc:
        raise DownloadError("URL khong hop le.") from exc
    host = (p.hostname or "").lower()
    if (p.scheme != "https" or p.username or p.password or port not in (None, 443)
            or not (host in {"suno.com", "www.suno.com", "suno.ai", "www.suno.ai"}
                    or re.fullmatch(r"cdn\d*\.suno\.(?:ai|com)", host))):
        raise DownloadError("Chi chap nhan URL HTTPS cong khai cua Suno hoac CDN Suno.")
    return urlunsplit((p.scheme, p.netloc, p.path, p.query, ""))


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, code, msg, headers, validate_url(newurl))


class PageMetadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.audio = None
        self.title = None

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "meta":
            return
        values = dict(attrs)
        key = values.get("property", values.get("name", ""))
        value = values.get("content", "")
        if key in {"og:audio", "og:audio:url", "og:audio:secure_url"} and value:
            self.audio = value
        if key == "og:title" and value:
            self.title = value


def audio_from_page(page: str, final_url: str) -> tuple[str, str]:
    meta = PageMetadata()
    meta.feed(page)
    if meta.audio and not urlsplit(meta.audio).path.endswith("/silence.mp3"):
        return validate_url(meta.audio), meta.title or "Suno"
    match = re.fullmatch(r"/song/(" + UUID + r")/?", urlsplit(final_url).path)
    if match:
        return f"https://cdn1.suno.ai/{match[1]}.mp3", meta.title or match[1]
    raise DownloadError("Khong tim thay MP3. Hay dung link /song/... hoac link CDN .mp3.")


def safe_name(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", html.unescape(value))
    value = value.strip(" .")[:100] or "Suno"
    if value.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(10)], *[f"LPT{i}" for i in range(10)]}:
        value = "Suno_" + value
    return value


def looks_like_mp3(data: bytes) -> bool:
    # ID3 tag or an MPEG Layer III frame header, excluding reserved fields.
    if data.startswith(b"ID3"):
        return True
    return any(data[i] == 255 and data[i+1] & 0xE0 == 0xE0
               and (data[i+1] >> 3) & 3 != 1 and (data[i+1] >> 1) & 3 == 1
               and (data[i+2] >> 4) not in (0, 15) and (data[i+2] >> 2) & 3 != 3
               for i in range(min(len(data)-2, 4096)))


def _download_mp3(url: str, directory: Path, progress=None, opener=None) -> Path:
    """Download atomically; never overwrite a previous download. Return local MP3."""
    url = validate_url(url)
    opener = opener or build_opener(SafeRedirect())
    deadline = time.monotonic() + 180

    def open_url(address):
        return opener.open(Request(validate_url(address), headers={
            "User-Agent": "SunoAudacityImporter/0.1", "Accept-Encoding": "identity"}), timeout=20)

    if urlsplit(url).path.lower().endswith(".mp3"):
        audio_url, title = url, Path(urlsplit(url).path).stem
    else:
        try:
            with open_url(url) as response:
                validate_url(response.geturl())
                page = response.read(MAX_PAGE + 1)
                if len(page) > MAX_PAGE:
                    raise DownloadError("Trang Suno vuot gioi han kich thuoc.")
                decoded = page.decode("utf-8", errors="replace")
                audio_url, title = audio_from_page(decoded, response.geturl())
        except HTTPError as exc:
            # Public MP3 CDN may still be accessible when the HTML frontend denies bots.
            if exc.code != 403 or not re.fullmatch(r"/song/(" + UUID + r")/?", urlsplit(url).path):
                raise
            audio_url, title = audio_from_page("", url)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    import uuid
    suffix = uuid.uuid4().hex[:10]
    target = directory / f"{safe_name(title)}-{suffix}.mp3"
    temporary = target.with_suffix(".part")
    try:
        with open_url(audio_url) as response, temporary.open("xb") as output:
            validate_url(response.geturl())
            length = response.headers.get("Content-Length")
            total = int(length) if length and length.isdigit() else None
            if total is not None and total > MAX_AUDIO:
                raise DownloadError("MP3 vuot gioi han 200 MB.")
            count = 0
            head = bytearray()
            while True:
                if time.monotonic() > deadline:
                    raise DownloadError("Tai MP3 qua 180 giay. Hay thu lai.")
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                count += len(chunk)
                if count > MAX_AUDIO:
                    raise DownloadError("MP3 vuot gioi han 200 MB.")
                if len(head) < 4096:
                    head.extend(chunk[:4096-len(head)])
                output.write(chunk)
                if progress:
                    progress(count, total)
            if count < 128 or not looks_like_mp3(bytes(head)):
                raise DownloadError("Phan hoi khong phai MP3 (co the la trang loi hoac bai rieng tu).")
            if total is not None and count != total:
                raise DownloadError("MP3 tai chua du. Hay thu lai.")
        os.replace(temporary, target)
        return target
    finally:
        temporary.unlink(missing_ok=True)


def song_id(url: str) -> str | None:
    """Only documented song/CDN paths, never an arbitrary UUID in a query."""
    parsed = urlsplit(validate_url(url))
    if parsed.hostname in {"suno.com", "www.suno.com", "suno.ai", "www.suno.ai"}:
        match = re.fullmatch(r"/song/(" + UUID + r")/?", parsed.path)
    else:
        match = re.fullmatch(r"/(" + UUID + r")\.(?:mp3|mp4)", parsed.path)
    return match[1] if match else None


def media_program(name: str) -> str:
    configured = os.environ.get("SUNO_" + name.upper())
    executable = configured or shutil.which(name)
    if not executable or not Path(executable).is_file():
        raise DownloadError(f"Can {name} de chuyen audio video public sang MP3. Them {name} vao PATH hoac dat SUNO_{name.upper()}.")
    return str(Path(executable).resolve())


def run_media(arguments: list[str], timeout=180):
    try:
        result = subprocess.run(arguments, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=timeout,
                                creationflags=0x08000000 if os.name == "nt" else 0)
    except subprocess.TimeoutExpired as exc:
        raise DownloadError("Chuyen doi audio qua thoi gian cho phep.") from exc
    if result.returncode:
        raise DownloadError("File audio khong giai ma duoc: " + result.stderr[-600:])
    return result.stdout


def convert_video(source: Path, destination: Path, title: str):
    ffmpeg, ffprobe = media_program("ffmpeg"), media_program("ffprobe")
    def probe(path):
        data = json.loads(run_media([ffprobe, "-v", "error", "-protocol_whitelist", "file,pipe",
                                    "-select_streams", "a:0", "-show_entries", "stream=codec_name,duration",
                                    "-of", "json", str(path)], 30))
        streams = data.get("streams", [])
        if not streams:
            raise DownloadError("Video khong co audio.")
        duration = float(streams[0].get("duration", 0))
        if not 0 < duration <= 7200:
            raise DownloadError("Thoi luong audio khong hop le (toi da 2 gio).")
        return duration
    original_duration = probe(source)
    run_media([ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-xerror", "-n",
               "-protocol_whitelist", "file,pipe", "-i", str(source), "-map", "0:a:0", "-vn",
               "-c:a", "libmp3lame", "-b:a", "256k", "-metadata", f"title={title}",
               "-f", "mp3", str(destination)])
    if abs(probe(destination) - original_duration) > 1.0:
        raise DownloadError("Thoi luong MP3 khong khop voi audio nguon.")


def download_public_video(clip_id: str, directory: Path, progress=None, opener=None) -> Path:
    """Use only the unencrypted public video CDN; no streaming keys or login."""
    media_program("ffmpeg")
    media_program("ffprobe")
    opener = opener or build_opener(SafeRedirect())
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    import uuid
    target = directory / f"Suno-{clip_id}-{uuid.uuid4().hex[:10]}.mp3"
    url = validate_url(f"https://cdn1.suno.ai/{clip_id}.mp4")
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="suno-convert-", dir=directory) as folder:
        source, output = Path(folder) / "public-video.mp4", Path(folder) / "audio.mp3"
        request = Request(url, headers={"User-Agent": "SunoAudacityImporter/0.2", "Accept-Encoding": "identity"})
        with opener.open(request, timeout=20) as response, source.open("xb") as stream:
            validate_url(response.geturl())
            length = response.headers.get("Content-Length")
            total = int(length) if length and length.isdigit() else None
            if total and total > MAX_AUDIO:
                raise DownloadError("Video public vuot gioi han 200 MB.")
            count = 0
            while True:
                if time.monotonic() - started > 180:
                    raise DownloadError("Tai video public qua 180 giay.")
                chunk = response.read(65536)
                if not chunk:
                    break
                count += len(chunk)
                if count > MAX_AUDIO:
                    raise DownloadError("Video public vuot gioi han 200 MB.")
                stream.write(chunk)
                if progress:
                    progress(count, total)
            if count < 128 or (total is not None and total != count):
                raise DownloadError("Video public tai chua du.")
        convert_video(source, output, f"Suno {clip_id}")
        output.replace(target)
    return target


def download(url: str, directory: Path, progress=None, opener=None) -> Path:
    """Direct MP3 first; on unavailable MP3, convert that song's public video."""
    url = validate_url(url)
    if urlsplit(url).path.lower().endswith(".mp4"):
        clip_id = song_id(url)
        if not clip_id:
            raise DownloadError("Can URL video Suno dang /UUID.mp4.")
        return download_public_video(clip_id, directory, progress, opener)
    try:
        return _download_mp3(url, directory, progress, opener)
    except HTTPError as exc:
        if exc.code not in (403, 404):
            raise
        clip_id = song_id(url) or song_id(exc.url)
        if not clip_id:
            raise
        return download_public_video(clip_id, directory, progress, opener)
