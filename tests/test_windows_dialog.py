import os
import unittest
from unittest.mock import Mock, patch

if os.name == "nt":
    from suno_importer import windows


@unittest.skipUnless(os.name == "nt", "Windows dialog ownership")
class DialogOwnershipTests(unittest.TestCase):
    def test_closed_project_does_not_modify_any_window(self):
        target = Mock(hwnd=100)
        target.validate.side_effect = RuntimeError("closed")
        with patch.object(windows, "set_window_long") as change:
            with self.assertRaisesRegex(RuntimeError, "closed"):
                windows.own_url_dialog(200, target)
            change.assert_not_called()

    def test_foreign_window_is_rejected_before_mutation(self):
        target = Mock(hwnd=100)
        with patch.object(windows, "ancestor", return_value=200), \
             patch.object(windows, "pid", return_value=-1), \
             patch.object(windows, "set_window_long") as change:
            with self.assertRaises(RuntimeError):
                windows.own_url_dialog(201, target)
            change.assert_not_called()

    def test_failure_to_establish_owner_is_reported(self):
        target = Mock(hwnd=100)
        with patch.object(windows, "ancestor", return_value=200), \
             patch.object(windows, "pid", return_value=os.getpid()), \
             patch.object(windows, "set_window_long", return_value=300), \
             patch.object(windows, "get_window", return_value=300), \
             patch.object(windows, "set_window_pos") as show:
            with self.assertRaises(RuntimeError):
                windows.own_url_dialog(201, target)
            show.assert_not_called()
