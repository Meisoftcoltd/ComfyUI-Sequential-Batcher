import sys
import os

from types import ModuleType

class DummyModule(ModuleType):
    def __getattr__(self, name):
        if name == "__path__":
            return []
        if name == "__file__":
            return "dummy.py"
        return DummyModule(f"{self.__name__}.{name}")
    def __call__(self, *args, **kwargs):
        return self

comfy_module = DummyModule("comfy")
sys.modules["comfy"] = comfy_module
comfy_utils_module = DummyModule("comfy.utils")
sys.modules["comfy.utils"] = comfy_utils_module
comfy_mm_module = DummyModule("comfy.model_management")
sys.modules["comfy.model_management"] = comfy_mm_module

folder_paths_module = DummyModule("folder_paths")
folder_paths_module.get_output_directory = lambda: "."
folder_paths_module.get_filename_list = lambda x: []
sys.modules["folder_paths"] = folder_paths_module

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import importlib.util
spec = importlib.util.spec_from_file_location("ComfyUI_Sequential_Batcher", "__init__.py")
module = importlib.util.module_from_spec(spec)
sys.modules["ComfyUI_Sequential_Batcher"] = module
spec.loader.exec_module(module)
print("Import success!")
