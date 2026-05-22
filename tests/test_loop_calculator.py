import sys
import types
import unittest
from unittest.mock import MagicMock
import os

# Mock required modules (as per memory)
mock_torch = types.ModuleType("torch")
mock_torch.Tensor = type("Tensor", (), {})
mock_torch.nn = type("nn", (), {"functional": type("functional", (), {}), "Module": type("Module", (), {})})
mock_torch.int64 = MagicMock()
mock_torch.float32 = MagicMock()
mock_torch.from_numpy = MagicMock()
mock_torch.int32 = MagicMock()
mock_torch.bfloat16 = MagicMock()
mock_torch.float16 = MagicMock()
mock_torch.cat = MagicMock()
mock_torch.zeros = MagicMock()
mock_torch.ones = MagicMock()
mock_torch.tensor = MagicMock()
mock_torch.int16 = MagicMock()
mock_torch.int8 = MagicMock()
mock_torch.float64 = MagicMock()
mock_torch.save = MagicMock()
mock_torch.load = MagicMock()
mock_torch.device = MagicMock()
mock_torch.uint8 = MagicMock()
mock_torch.Size = MagicMock()
mock_torch.autocast = MagicMock()
mock_torch.bool = MagicMock()
mock_torch.no_grad = MagicMock()
mock_torch.complex64 = MagicMock()
mock_torch.complex128 = MagicMock()
mock_torch.qint8 = MagicMock()
mock_torch.quint8 = MagicMock()
mock_torch.__version__ = "2.0.0"
mock_torch.dtype = type("dtype", (), {})
mock_torch.empty = MagicMock()
mock_torch.randn = MagicMock()
mock_torch.dtype = type("dtype", (), {})
mock_torch.empty = MagicMock()
mock_torch.randn = MagicMock()
mock_torch.cuda = MagicMock()
mock_torch.cuda.is_available.return_value = False
sys.modules["torch"] = mock_torch

sys.modules["comfy"] = types.ModuleType("comfy")
sys.modules["comfy.model_management"] = types.ModuleType("comfy.model_management")
sys.modules["comfy.utils"] = types.ModuleType("comfy.utils")
sys.modules["torchaudio"] = types.ModuleType("torchaudio")
sys.modules["folder_paths"] = types.ModuleType("folder_paths")



# Mock the loop module since it will be imported in video.py
mock_loop = types.ModuleType("loop")
mock_loop.global_step_by_chunk = False
mock_loop.global_source_frame_count = 0
mock_loop.global_select_every_nth = 1
mock_loop.global_is_final_chunk = False
mock_loop.global_accumulated_frames = 0
sys.modules["loop"] = mock_loop

import sys
sys.modules["tqdm"] = types.ModuleType("tqdm")
sys.modules["tqdm"].tqdm = lambda x, **kwargs: x
sys.modules["cv2"] = types.ModuleType("cv2")


def get_node_class(file_name, class_name):
    # Read the file
    path = os.path.join(os.path.dirname(__file__), "..", file_name)
    with open(path, 'r') as f:
        code = f.read()

    # Mock 'from . import register_node'
    code = code.replace("from . import register_node", "def register_node(c, *args, **kwargs): return c")
    # In video.py, there are more relative imports
    code = code.replace("from . import loop", "import loop")

    # We create a new module
    module = types.ModuleType(file_name.replace(".py", ""))

    # We must patch sys.modules inside so it can import loop
    sys.modules[module.__name__] = module

    try:
        exec(code, module.__dict__)
    except Exception as e:
        print(f"Failed to execute {file_name}: {e}")
        pass

    return getattr(module, class_name, None)


class TestAutoLoopCalculators(unittest.TestCase):

    def setUp(self):
        LTXClass = get_node_class("loop.py", "AutoLoopCalculatorLTX")
        self.calc_ltx = LTXClass() if LTXClass else None

        BaseClass = get_node_class("video.py", "AutoLoopCalculator")
        self.calc_base = BaseClass() if BaseClass else None

        WanClass = get_node_class("video.py", "AutoLoopCalculatorWan")
        self.calc_wan = WanClass() if WanClass else None

    # LTX Calculator
    def test_ltx_guard_zero_source(self):
        res = self.calc_ltx.calculate(0, 100, 1, 0)
        self.assertEqual(res, (1, 0, 1))

    def test_ltx_guard_negative_source(self):
        res = self.calc_ltx.calculate(-5, 100, 1, 0)
        self.assertEqual(res, (1, 0, 1))

    def test_ltx_guard_zero_target(self):
        res = self.calc_ltx.calculate(100, 0, 1, 0)
        self.assertEqual(res, (1, 0, 1))

    def test_ltx_valid_input(self):
        res = self.calc_ltx.calculate(80, 81, 1, 0)
        self.assertEqual(res[0], 81)
        self.assertEqual(res[1], 0)
        self.assertEqual(res[2], 1)

    # Base Calculator
    def test_base_guard_zero_source(self):
        res = self.calc_base.calculate(0, 100, 1, 0)
        self.assertEqual(res[0], 1)
        self.assertEqual(res[1], 0)
        self.assertEqual(res[2], 1)
        self.assertIn("Invalid frame count", res[3])

    def test_base_guard_zero_target(self):
        res = self.calc_base.calculate(100, 0, 1, 0)
        self.assertEqual(res[0], 1)
        self.assertEqual(res[1], 0)
        self.assertEqual(res[2], 1)
        self.assertIn("Invalid frame count", res[3])

    def test_base_valid_input(self):
        res = self.calc_base.calculate(100, 50, 1, 0)
        self.assertEqual(res[0], 50)
        self.assertEqual(res[1], 0)
        self.assertEqual(res[2], 1)

    # Wan Calculator
    def test_wan_guard_zero_source(self):
        res = self.calc_wan.calculate(0, 100, 1, 0)
        self.assertEqual(res[0], 1)
        self.assertEqual(res[1], 0)
        self.assertEqual(res[2], 1)
        self.assertIn("Invalid frame count", res[3])

    def test_wan_guard_zero_target(self):
        res = self.calc_wan.calculate(100, 0, 1, 0)
        self.assertEqual(res[0], 1)
        self.assertEqual(res[1], 0)
        self.assertEqual(res[2], 1)
        self.assertIn("Invalid frame count", res[3])

    def test_wan_valid_input(self):
        res = self.calc_wan.calculate(80, 81, 1, 0)
        self.assertEqual(res[0], 81)
        self.assertEqual(res[1], 0)
        self.assertEqual(res[2], 1)

if __name__ == "__main__":
    unittest.main()
