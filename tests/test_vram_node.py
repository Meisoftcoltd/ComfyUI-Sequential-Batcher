import sys
import types
import pytest
from unittest.mock import MagicMock
import os

# Mock dependencies before importing anything that might depend on them
mock_torch = types.ModuleType("torch")
mock_torch.cuda = MagicMock()
mock_torch.cuda.is_available.return_value = False
sys.modules["torch"] = mock_torch

sys.modules["comfy"] = types.ModuleType("comfy")
sys.modules["comfy.model_management"] = types.ModuleType("comfy.model_management")

def get_format_bytes():
    # Read the file
    vram_node_path = os.path.join(os.path.dirname(__file__), "..", "vram_node.py")
    with open(vram_node_path, 'r') as f:
        code = f.read()

    # Mock 'from . import register_node' by replacing it
    code = code.replace("from . import register_node", "def register_node(c, *args, **kwargs): return c")

    vram_module = types.ModuleType("vram_node")
    exec(code, vram_module.__dict__)

    return vram_module.format_bytes

@pytest.fixture
def format_bytes():
    return get_format_bytes()

def test_format_bytes_zero(format_bytes):
    assert format_bytes(0) == "0.00 GB"

def test_format_bytes_gigabyte(format_bytes):
    assert format_bytes(1024**3) == "1.00 GB"

def test_format_bytes_fractional(format_bytes):
    assert format_bytes(1024**3 * 0.5) == "0.50 GB"
    assert format_bytes(1024**3 * 2.5) == "2.50 GB"

def test_format_bytes_small_values(format_bytes):
    # 1 MB is 1/1024 GB ≈ 0.000976 GB -> 0.00 GB
    assert format_bytes(1024**2) == "0.00 GB"
    # 10 MB is 10/1024 GB ≈ 0.009765 GB -> 0.01 GB (due to rounding .2f)
    assert format_bytes(1024**2 * 10) == "0.01 GB"

def test_format_bytes_large_values(format_bytes):
    assert format_bytes(1024**3 * 1024) == "1024.00 GB"
    assert format_bytes(1024**3 * 123.456) == "123.46 GB"

if __name__ == "__main__":
    pytest.main([__file__])
