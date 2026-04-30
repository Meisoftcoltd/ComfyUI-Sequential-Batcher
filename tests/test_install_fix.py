import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Mock sys.platform to linux for testing check_and_install_ffmpeg
@patch("sys.platform", "linux")
@patch("shutil.which", return_value=None)
class TestInstall(unittest.TestCase):

    @patch("subprocess.check_call")
    def test_check_and_install_ffmpeg_linux(self, mock_check_call, mock_which):
        from install import check_and_install_ffmpeg

        check_and_install_ffmpeg()

        # Verify that subprocess.check_call was called twice with the correct lists
        self.assertEqual(mock_check_call.call_count, 2)

        expected_calls = [
            unittest.mock.call(["sudo", "apt-get", "update"]),
            unittest.mock.call(["sudo", "DEBIAN_FRONTEND=noninteractive", "apt-get", "install", "-y", "ffmpeg"])
        ]
        mock_check_call.assert_has_calls(expected_calls)

        # Verify shell=True was NOT used
        for call in mock_check_call.call_args_list:
            args, kwargs = call
            if "shell" in kwargs:
                self.assertFalse(kwargs["shell"], "shell should be False if explicitly provided")
            # If not in kwargs, it defaults to False for subprocess.check_call

if __name__ == "__main__":
    unittest.main()
