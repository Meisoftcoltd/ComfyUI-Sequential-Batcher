import sys
from unittest.mock import MagicMock

sys.modules['torch'] = MagicMock()
sys.modules['comfy'] = MagicMock()
sys.modules['comfy.model_management'] = MagicMock()

# Mocking relative import
class MockRegisterNode:
    def __call__(self, cls):
        return cls

import builtins
real_import = builtins.__import__

def mocked_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name == '' and level > 0 and 'register_node' in fromlist:
        mock_module = MagicMock()
        mock_module.register_node = MockRegisterNode()
        return mock_module
    return real_import(name, globals, locals, fromlist, level)

builtins.__import__ = mocked_import

import loop
print("Sintaxis de loop.py verificada correctamente.")
