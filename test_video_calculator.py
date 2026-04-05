import sys
import types
import os

# Create dummy modules for comfyui dependencies
comfy_module = types.ModuleType("comfy")
comfy_mm_module = types.ModuleType("comfy.model_management")
comfy_module.model_management = comfy_mm_module
sys.modules["comfy"] = comfy_module
sys.modules["comfy.model_management"] = comfy_mm_module

folder_paths_module = types.ModuleType("folder_paths")
sys.modules["folder_paths"] = folder_paths_module

nodes_module = types.ModuleType("nodes")
sys.modules["nodes"] = nodes_module

# Mock torchaudio and torch
sys.modules["torch"] = types.ModuleType("torch")
sys.modules["torchaudio"] = types.ModuleType("torchaudio")
sys.modules["cv2"] = types.ModuleType("cv2")
sys.modules["numpy"] = types.ModuleType("numpy")
sys.modules["tqdm"] = types.ModuleType("tqdm")
def mock_tqdm(iter_obj, *args, **kwargs):
    class DummyPbar:
        def update(self, *args, **kwargs): pass
        def close(self): pass
    if isinstance(iter_obj, int):
        return DummyPbar()
    return iter_obj
sys.modules["tqdm"].tqdm = mock_tqdm

# Mock parent package for relative imports
dummy_pkg = types.ModuleType("dummy_pkg")
def mock_register_node(cls):
    return cls
dummy_pkg.register_node = mock_register_node
sys.modules["dummy_pkg"] = dummy_pkg

# Overwrite sys.modules for testing so `from . import register_node` works
# We'll just load the file using importlib
import importlib.util
def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    # make it part of dummy_pkg
    module.__package__ = "dummy_pkg"
    spec.loader.exec_module(module)
    return module

load_module("dummy_pkg.loop", "loop.py")
video = load_module("dummy_pkg.video", "video.py")
loop_mod = sys.modules["dummy_pkg.loop"]

# Run tests
calc_base = video.AutoLoopCalculator()
calc_wan = video.AutoLoopCalculatorWan()
calc_ltx = loop_mod.AutoLoopCalculatorLTX()

print("Testing base calculator...")
calc_base.calculate(source_frame_count=876, target_frames_per_loop=50, select_every_nth=8, current_loop_index=0)

print("\nTesting WanVideo calculator...")
calc_wan.calculate(source_frame_count=876, target_frames_per_loop=48, select_every_nth=8, current_loop_index=0)

print("\nTesting LTX calculator...")
calc_ltx.calculate(source_frame_count=876, target_frames_per_loop=81, select_every_nth=8, current_loop_index=0)

print("\nTests passed!")
