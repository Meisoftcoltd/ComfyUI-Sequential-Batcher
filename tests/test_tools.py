import sys
import types
import pytest
from unittest.mock import MagicMock
import os

# Mock dependencies
mock_torch = types.ModuleType("torch")
class MockTensor:
    pass
mock_torch.Tensor = MockTensor
mock_torch.Tensor.__module__ = "torch"
sys.modules["torch"] = mock_torch

def get_VAESafeFramePadder():
    tools_path = os.path.join(os.path.dirname(__file__), "..", "tools.py")
    with open(tools_path, 'r') as f:
        code = f.read()

    # Mock 'from . import register_node' and other potential relative imports
    code = code.replace("from . import register_node", "def register_node(c, *args, **kwargs): return c")
    code = code.replace("from .switch_node import any_type", "any_type = '*'")

    tools_module = types.ModuleType("tools")
    # Provide torch to the module's namespace
    tools_module.__dict__["torch"] = mock_torch

    try:
        exec(code, tools_module.__dict__)
    except Exception as e:
        print(f"Error executing tools.py code: {e}")
        raise e

    return tools_module.VAESafeFramePadder

@pytest.fixture
def VAESafeFramePadder():
    return get_VAESafeFramePadder()

def test_pad_non_tensor_input_raises_value_error(VAESafeFramePadder):
    padder = VAESafeFramePadder()

    with pytest.raises(ValueError, match=r"\[VAESafeFramePadder\] Input is not a valid tensor\."):
        padder.pad(None, "WanVideo")

    with pytest.raises(ValueError, match=r"\[VAESafeFramePadder\] Input is not a valid tensor\."):
        padder.pad("not a tensor", "WanVideo")

if __name__ == "__main__":
    pytest.main([__file__])
