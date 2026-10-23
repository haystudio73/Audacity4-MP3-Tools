import unittest
import tempfile
from pathlib import Path
from suno_importer.helper import parse_request, write_heartbeat

class ProtocolTests(unittest.TestCase):
    def test_open_dialog_request(self):
        self.assertIsNone(parse_request("SUNO-OPEN-1\nabc\nOPEN\nEND\n", "abc"))
        for data in ("SUNO-OPEN-1\nold\nOPEN\nEND\n", "SUNO-OPEN-1\nabc\nURL\nEND\n"):
            with self.assertRaises(ValueError):
                parse_request(data, "abc")

    def test_heartbeat_replaces_old_session_and_timestamp(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            write_heartbeat(directory, "old-session", 1700000000)
            write_heartbeat(directory, "new-session", 1800000000.75)
            self.assertEqual((directory / "heartbeat.txt").read_text(),
                             "new-session\n1800000000\n")
            self.assertFalse((directory / "heartbeat.tmp").exists())

    def test_complete_request(self):
        self.assertEqual(parse_request("SUNO-IMPORT-1\nabc\nhttps://suno.com/song/test\nEND\n", "abc"), "https://suno.com/song/test")

    def test_stale_truncated_and_injected_request(self):
        for data in ["SUNO-IMPORT-1\nold\nhttps://suno.com\nEND\n",
                     "SUNO-IMPORT-1\nabc\nhttps://suno.com\n",
                     "SUNO-IMPORT-1\nabc\nhttps://suno.com\nother\nEND\n"]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                parse_request(data, "abc")
