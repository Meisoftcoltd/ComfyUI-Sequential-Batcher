import unittest
from unittest.mock import patch, MagicMock
import sys
import types

# Create mock torch and comfy modules before importing loop.py
sys.modules['torch'] = MagicMock()
sys.modules['comfy.model_management'] = MagicMock()
sys.modules['comfy'] = MagicMock()

# Mock out the relative import of register_node from .
sys.modules['.'] = MagicMock()

# Read loop.py and execute it into a module to test it in isolation
module_name = 'loop'
module = types.ModuleType(module_name)
sys.modules[module_name] = module

with open('../loop.py', 'r') as f:
    source = f.read()

# Remove the relative import for testing purposes
source = source.replace("from . import register_node", "def register_node(cls):\n    return cls")

exec(source, module.__dict__)

class TestSSRFFix(unittest.TestCase):
    @patch('urllib.request.urlopen')
    def test_valid_port(self, mock_urlopen):
        # Should not raise a value error for valid ports
        node = module.SequentialLoopStart()
        # It will try to connect and mock_urlopen will return a success
        # The method might raise ValueError if urlopen fails, so we don't configure mock_urlopen to throw

        # Test valid port execution
        node.get_index(reset_loop=True, loop_idx=0, port=8188)
        self.assertEqual(module.global_server_port, 8188)

    def test_invalid_port_string(self):
        node = module.SequentialLoopStart()

        # SSRF payload string
        malicious_payload = "8188/../../admin"

        # This should raise a ValueError due to the strict integer check
        with self.assertRaises(ValueError) as context:
            node.get_index(reset_loop=True, loop_idx=0, port=malicious_payload)

        self.assertIn("INVÁLIDO", str(context.exception))

    def test_invalid_port_range(self):
        node = module.SequentialLoopStart()

        # Test port out of bounds (0 or > 65535)
        with self.assertRaises(ValueError):
            node.get_index(reset_loop=True, loop_idx=0, port=0)

        with self.assertRaises(ValueError):
            node.get_index(reset_loop=True, loop_idx=0, port=99999)

if __name__ == '__main__':
    unittest.main()
