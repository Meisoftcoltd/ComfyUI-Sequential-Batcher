import torch
import gc
import comfy.model_management as mm
import os
from . import register_node

class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False

any_type = AnyType("*")

def format_bytes(bytes_val):
    return f"{bytes_val / (1024 ** 3):.2f} GB"

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
        print(f"\n{'='*65}")
        print(f"🧹 [DEBUG] NODO: VRAM Defragmenter (Modo Arquitectura Profunda)")

        # --- ESTADÍSTICAS ANTES ---
        alloc_before = 0
        res_before = 0
        if torch.cuda.is_available():
            alloc_before = torch.cuda.memory_allocated()
            res_before = torch.cuda.memory_reserved()
            print(f"   -> 📊 Estado Inicial  | Asignada: {format_bytes(alloc_before)} | Reservada (Caché): {format_bytes(res_before)}")

            # --- FASE 1: CONFIGURACIÓN DINÁMICA DEL ALLOCATOR ---
            try:
                # Permite que la reserva de VRAM crezca en bloque elástico
                torch.cuda.memory._set_allocator_settings("expandable_segments:True")
                print("   -> ⚙️ PyTorch Allocator ajustado a expandable_segments:True")
            except Exception as e:
                print(f"   -> ⚠️ Aviso: No se pudo ajustar expandable_segments: {e}")

        # --- FASE 2: EVACUACIÓN (Opcional) ---
        if force_model_unload:
            print("   -> 📦 Trasladando modelos inactivos a la RAM (unload_all_models)...")
            mm.unload_all_models()

        # --- FASE 3: LIMPIEZA INTERNA DE COMFYUI (LA CLAVE) ---
        print("   -> 🧹 Destruyendo referencias ocultas en el gestor de ComfyUI...")
        if hasattr(mm, "cleanup_models"):
            mm.cleanup_models()
        if hasattr(mm, "cleanup_models_gc"):
            mm.cleanup_models_gc()

        # --- FASE 4: ROMPER REFERENCIAS PYTHON ---
        print("   -> 🗑️ Forzando Garbage Collector de Python (Doble pasada)...")
        gc.collect()
        gc.collect() # Doble pasada para romper referencias circulares rebeldes

        # --- FASE 5: EVACUACIÓN SUAVE ---
        mm.soft_empty_cache()

        # --- FASE 6: PURGADO PROFUNDO DE PYTORCH ---
        if torch.cuda.is_available():
            print("   -> 🧱 Desfragmentando Caching Allocator de CUDA...")
            torch.cuda.ipc_collect()
            torch.cuda.empty_cache()
            torch.cuda.synchronize() # Barrera contra race conditions

        # --- FASE 7: LIBERACIÓN DE MEMORIA DEL SISTEMA (Linux/WSL) ---
        try:
            import ctypes
            ctypes.CDLL('libc.so.6').malloc_trim(0)
            print("   -> 💻 Malloc Trim ejecutado (RAM del sistema purgada).")
        except Exception:
            pass

        # --- ESTADÍSTICAS DESPUÉS ---
        if torch.cuda.is_available():
            alloc_after = torch.cuda.memory_allocated()
            res_after = torch.cuda.memory_reserved()

            # Cálculos de liberación
            freed_alloc = alloc_before - alloc_after
            freed_res = res_before - res_after

            sign_alloc = "+" if freed_alloc < 0 else "-"
            sign_res = "+" if freed_res < 0 else "-"

            print(f"   -> 📈 Estado Final    | Asignada: {format_bytes(alloc_after)} | Reservada (Caché): {format_bytes(res_after)}")
            print(f"   -> ✨ TOTAL LIBERADO  | {sign_alloc}{abs(freed_alloc)/(1024**3):.2f} GB (Asignada) | {sign_res}{abs(freed_res)/(1024**3):.2f} GB (Reservada purgada)")
        else:
            print("   -> ✨ Limpieza completada (Modo CPU/Otra arquitectura).")

        print(f"{'='*65}\n")
        return (anything,)
