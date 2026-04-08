import torch
import gc
import comfy.model_management as mm
from . import register_node

class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False

any_type = AnyType("*")

@register_node
class MeisoftVRAMDefragmenter:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "anything": (any_type,),
                "force_model_unload": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("anything",)
    FUNCTION = "defragment"
    CATEGORY = "🔁 Sequential Batcher/Tools"

    def defragment(self, anything, force_model_unload):
        print(f"\n{'='*50}")
        print(f"🧹 [DEBUG] NODO: VRAM Defragmenter (Pasarela)")

        # 1. Forzar descarga de modelos a la RAM si el usuario lo pide
        if force_model_unload:
            print("   -> 📦 Trasladando modelos inactivos a la memoria RAM (CPU)...")
            mm.unload_all_models()

        # 2. Recolector de basura de Python (elimina tensores huérfanos)
        print("   -> 🗑️ Eliminando tensores huérfanos de la memoria...")
        gc.collect()

        # 3. Desfragmentación agresiva del Caching Allocator de CUDA
        if torch.cuda.is_available():
            print("   -> 🧱 Desfragmentando bloques de memoria CUDA...")
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()

        print("   -> ✨ VRAM optimizada. Permitiendo el paso del flujo.")
        print(f"{'='*50}\n")

        # 4. Devolvemos el mismo dato sin alterarlo (Passthrough)
        return (anything,)
