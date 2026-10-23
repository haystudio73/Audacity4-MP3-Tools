import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from suno_importer.downloader import (
    DownloadError, SafeRedirect, audio_from_page, download, safe_name, validate_url,
)
from urllib.request import Request

ID = "ab39a04d-b2e6-463b-9b8e-ddea725422f5"
URL = f"https://cdn1.suno.ai/{ID}.mp3"
MP3 = b"ID3" + bytes(1000)


class Response(io.BytesIO):
    def __init__(self, data, url=URL, length=None):
        super().__init__(data)
        self.url = url
        self.headers = {"Content-Length": str(len(data) if length is None else length)}

    def geturl(self):
        return self.url


class Opener:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.urls = []

    def open(self, request, timeout):
        self.urls.append(request.full_url)
        return next(self.responses)


class DownloaderTests(unittest.TestCase):
    def test_url_allowlist(self):
        self.assertEqual(validate_url(URL + "#fragment"), URL)
        for value in ["file:///C:/x", "http://suno.com/x", "https://suno.com.evil.org/x",
                      "https://evil.suno.ai/x", "https://localhost/x", "https://user@suno.com/x",
                      "https://suno.com:444/x", "https://suno.com:bad/x", "https://suno.com/x\nY"]:
            with self.subTest(value=value), self.assertRaises(DownloadError):
                validate_url(value)

    def test_redirect_to_other_host_rejected(self):
        with self.assertRaises(DownloadError):
            SafeRedirect().redirect_request(Request(URL), None, 302, "", {}, "https://example.com/x")

    def test_html_metadata_with_escaped_query(self):
        page = f'<meta content="{URL}?a=1&amp;b=2" property="og:audio"><meta property="og:title" content="Bài hát">'
        self.assertEqual(audio_from_page(page, f"https://suno.com/song/{ID}"), (URL+"?a=1&b=2", "Bài hát"))

    def test_silence_placeholder_not_downloaded(self):
        self.assertEqual(audio_from_page('<meta property="og:audio" content="https://cdn1.suno.ai/silence.mp3">', f"https://suno.com/song/{ID}")[0], URL)

    def test_unrecognized_page_and_external_audio_rejected(self):
        for page in ["<html>login</html>", '<meta property="og:audio" content="https://example.com/x.mp3">']:
            with self.assertRaises(DownloadError):
                audio_from_page(page, "https://suno.com/s/abc")

    def test_safe_windows_names(self):
        self.assertEqual(safe_name("../Bài: hát?"), "_Bài_ hát_")
        self.assertEqual(safe_name("CON"), "Suno_CON")

    def test_download_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            first = download(URL, Path(folder), opener=Opener(Response(MP3)))
            second = download(URL, Path(folder), opener=Opener(Response(MP3)))
            self.assertNotEqual(first, second)
            self.assertEqual(first.read_bytes(), MP3)
            self.assertFalse(list(Path(folder).glob("*.part")))

    def test_share_redirect_uses_final_song(self):
        opener = Opener(Response(b"<html></html>", f"https://suno.com/song/{ID}"), Response(MP3))
        with tempfile.TemporaryDirectory() as folder:
            download("https://suno.com/s/abc", Path(folder), opener=opener)
        self.assertEqual(opener.urls[-1], URL)

    def test_invalid_truncated_oversized_cleaned(self):
        for payload, length in [(b"<html>Access denied</html>"*20, None), (MP3, 9000), (MP3, 300*1024*1024)]:
            with self.subTest(length=length), tempfile.TemporaryDirectory() as folder:
                with self.assertRaises(DownloadError):
                    download(URL, Path(folder), opener=Opener(Response(payload, length=length)))
                self.assertEqual(list(Path(folder).iterdir()), [])

    def test_actual_stream_limit(self):
        with tempfile.TemporaryDirectory() as folder, patch("suno_importer.downloader.MAX_AUDIO", 512):
            response = Response(MP3)
            response.headers = {}
            with self.assertRaises(DownloadError):
                download(URL, Path(folder), opener=Opener(response))
            self.assertEqual(list(Path(folder).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
