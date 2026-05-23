import sys
import unittest.mock

# Mocking missing dependencies for syntax check
sys.modules['torch'] = unittest.mock.MagicMock()
sys.modules['comfy'] = unittest.mock.MagicMock()
sys.modules['comfy.model_management'] = unittest.mock.MagicMock()
sys.modules['folder_paths'] = unittest.mock.MagicMock()

# Mock internal import to prevent syntax error on register_node
class DummyRegister:
    def __call__(self, cls):
        return cls

sys.modules['__main__'].register_node = DummyRegister()

try:
    import loop
    print("Syntax is OK")
except Exception as e:
    import traceback
    traceback.print_exc()
