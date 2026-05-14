import sys
import unittest
import types

class TestSSRF(unittest.TestCase):
    def test_ssrf_fix(self):
        # We want to load loop.py and simulate the port logic.
        import os
        import urllib.request
        from unittest.mock import patch, MagicMock

        # Load loop.py dynamically
        REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        loop_path = os.path.join(REPO_ROOT, "loop.py")
        with open(loop_path, 'r') as f:
            code = f.read()

        # Mock register_node by replacing the import
        code = code.replace("from . import register_node", "def register_node(c, *args, **kwargs): return c")

        # Mock comfy modules
        sys.modules["comfy"] = MagicMock()
        sys.modules["comfy.model_management"] = MagicMock()
        sys.modules["torch"] = MagicMock()

        module = types.ModuleType("loop")
        exec(code, module.__dict__)

        SequentialLoopStart = module.SequentialLoopStart()

        # Scenario 1: Malicious port input, should fallback to sys.argv or default
        sys.argv = ["main.py", "--port", "8188"]
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_urlopen.return_value = MagicMock()
            idx = SequentialLoopStart.get_index(reset_loop=True, loop_idx=0, port=9999)

            # The safe port should be 8188 since sys.argv overrides the malicious port
            self.assertEqual(module.global_server_port, 8188)

            # Scenario 2: sys.argv contains a different valid port
            sys.argv = ["main.py", "--port", "8189"]
            idx = SequentialLoopStart.get_index(reset_loop=True, loop_idx=0, port=9999)
            self.assertEqual(module.global_server_port, 8189)

if __name__ == "__main__":
    unittest.main()
