import sys
import unittest.mock

# Mocking missing dependencies for syntax check
sys.modules['torch'] = unittest.mock.MagicMock()
sys.modules['comfy'] = unittest.mock.MagicMock()
sys.modules['comfy.model_management'] = unittest.mock.MagicMock()
sys.modules['folder_paths'] = unittest.mock.MagicMock()

# Mock internal import to prevent syntax error on register_node
import types
dummy_module = types.ModuleType("dummy")
dummy_module.register_node = lambda c: c
sys.modules[__package__ or '.'] = dummy_module

try:
    with open('loop.py') as f:
        code = f.read()
    code = code.replace('from . import register_node', 'def register_node(c): return c')
    exec(code)
    print("Syntax is OK")
except Exception as e:
    import traceback
    traceback.print_exc()
