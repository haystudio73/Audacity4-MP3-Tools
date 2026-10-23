from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from suno_importer.downloader import download, song_id, convert_video, DownloadError

ID = "3603f35f-f31c-4930-adcb-f05e58b4239b"
URL = "https://suno.com/song/" + ID

class FallbackTests(unittest.TestCase):
    def test_403_uses_same_song_public_video(self):
        with patch("suno_importer.downloader._download_mp3", side_effect=HTTPError(URL,403,"Forbidden",{},None)), patch("suno_importer.downloader.download_public_video", return_value=Path("song.mp3")) as fallback:
            self.assertEqual(download(URL, Path("downloads")), Path("song.mp3"))
            self.assertEqual(fallback.call_args.args[0], ID)

    def test_rate_limit_is_not_retried(self):
        with patch("suno_importer.downloader._download_mp3", side_effect=HTTPError(URL,429,"Rate limited",{},None)), patch("suno_importer.downloader.download_public_video") as fallback:
            with self.assertRaises(HTTPError):
                download(URL, Path("downloads"))
            fallback.assert_not_called()

    def test_short_link_redirect_failure_uses_final_song(self):
        with patch("suno_importer.downloader._download_mp3", side_effect=HTTPError(URL,403,"Forbidden",{},None)), patch("suno_importer.downloader.download_public_video", return_value=Path("song.mp3")) as fallback:
            download("https://suno.com/s/test", Path("downloads"))
            self.assertEqual(fallback.call_args.args[0], ID)

    def test_arbitrary_query_is_not_a_song(self):
        self.assertIsNone(song_id("https://suno.com/?id="+ID))
        self.assertIsNone(song_id("https://suno.com/playlist/"+ID))

    def test_broken_media_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)/"bad.mp4"
            source.write_bytes(b"not audio")
            with self.assertRaises(DownloadError):
                convert_video(source, Path(folder)/"result.mp3", "Test")
