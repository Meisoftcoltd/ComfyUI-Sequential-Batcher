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

        # Fase 1: Romper ciclos de referencia en Python
        gc.collect()

        # Fase 2: Evacuación suave nativa
        mm.soft_empty_cache()

        # Fase 3: Evacuación agresiva (Opcional)
        if force_model_unload:
            print("   -> 📦 Trasladando modelos inactivos a la RAM (unload_all_models)...")
            mm.unload_all_models()
            gc.collect() # Segunda barrida tras rotura de enlaces

        # Fases 4, 5 y 6: Limpieza IPC, Vaciado CUDA y Sincronización
        if torch.cuda.is_available():
            print("   -> 🧱 Purgando memoria IPC y desfragmentando Caching Allocator...")
            torch.cuda.ipc_collect()
            torch.cuda.empty_cache()
            torch.cuda.synchronize() # Barrera contra race conditions

        print("   -> ✨ VRAM hiper-optimizada. Permitiendo paso al Sampler.")
        print(f"{'='*50}\n")
        return (anything,)
