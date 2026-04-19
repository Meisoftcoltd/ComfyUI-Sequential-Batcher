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

    RETURN_TYPES = (any_type, "STRING")
    RETURN_NAMES = ("anything", "log")
    FUNCTION = "defragment"
    CATEGORY = "🔁 Sequential Batcher/Tools"

    def defragment(self, anything, force_model_unload):
        log_output = []
        def _log(msg):
            print(msg)
            log_output.append(str(msg))
        _log(f"\n{'='*65}")
        _log(f"🧹 [Secuencial Batcher] NODO: VRAM Defragmenter (Modo Arquitectura Profunda)")

        # --- ESTADÍSTICAS ANTES ---
        alloc_before = 0
        res_before = 0
        if torch.cuda.is_available():
            alloc_before = torch.cuda.memory_allocated()
            res_before = torch.cuda.memory_reserved()
            _log(f"   -> 📊 Estado Inicial  | Asignada: {format_bytes(alloc_before)} | Reservada (Caché): {format_bytes(res_before)}")

            # --- FASE 1: CONFIGURACIÓN DINÁMICA DEL ALLOCATOR ---
            try:
                # Permite que la reserva de VRAM crezca en bloque elástico
                torch.cuda.memory._set_allocator_settings("expandable_segments:True")
                _log("   -> ⚙️ PyTorch Allocator ajustado a expandable_segments:True")
            except Exception as e:
                _log(f"   -> ⚠️ Aviso: No se pudo ajustar expandable_segments: {e}")

        # --- FASE 2: EVACUACIÓN (Opcional) ---
        if force_model_unload:
            _log("   -> 📦 Trasladando modelos inactivos a la RAM (unload_all_models)...")
            mm.unload_all_models()

        # --- FASE 3: LIMPIEZA INTERNA DE COMFYUI (LA CLAVE) ---
        _log("   -> 🧹 Destruyendo referencias ocultas en el gestor de ComfyUI...")
        if hasattr(mm, "cleanup_models"):
            mm.cleanup_models()
        if hasattr(mm, "cleanup_models_gc"):
            mm.cleanup_models_gc()

        # --- FASE 4: ROMPER REFERENCIAS PYTHON ---
        _log("   -> 🗑️ Forzando Garbage Collector de Python (Doble pasada)...")
        gc.collect()
        gc.collect() # Doble pasada para romper referencias circulares rebeldes

        # --- FASE 5: EVACUACIÓN SUAVE ---
        mm.soft_empty_cache()

        # --- FASE 6: PURGADO PROFUNDO DE PYTORCH ---
        if torch.cuda.is_available():
            _log("   -> 🧱 Desfragmentando Caching Allocator de CUDA...")
            torch.cuda.ipc_collect()
            torch.cuda.synchronize() # 🚀 OPTIMIZACIÓN: Esperar a que terminen los kernels pendientes PRIMERO
            torch.cuda.empty_cache() # 🚀 Luego vaciamos la caché de forma segura

        # --- FASE 7: LIBERACIÓN DE MEMORIA DEL SISTEMA (Multi-Plataforma) ---
        import platform
        try:
            import ctypes
            if platform.system() == "Windows":
                # API de Windows: Reduce el 'Working Set' del proceso actual al mínimo
                kernel32 = ctypes.windll.kernel32
                current_process = kernel32.GetCurrentProcess()
                kernel32.SetProcessWorkingSetSize(current_process, -1, -1)
                _log("   -> 💻 Working Set reducido (RAM del sistema purgada en Windows).")
            else:
                # API de Linux/WSL: Libera la memoria de la librería C
                ctypes.CDLL('libc.so.6').malloc_trim(0)
                _log("   -> 💻 Malloc Trim ejecutado (RAM del sistema purgada en Linux/WSL).")
        except Exception as e:
            # Si algo falla a nivel de SO, fallamos silenciosamente sin romper el nodo
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

            _log(f"   -> 📈 Estado Final    | Asignada: {format_bytes(alloc_after)} | Reservada (Caché): {format_bytes(res_after)}")
            _log(f"   -> ✨ TOTAL LIBERADO  | {sign_alloc}{abs(freed_alloc)/(1024**3):.2f} GB (Asignada) | {sign_res}{abs(freed_res)/(1024**3):.2f} GB (Reservada purgada)")
        else:
            _log("   -> ✨ Limpieza completada (Modo CPU/Otra arquitectura).")

        _log(f"{'='*65}\n")
        return (anything, "\n".join(log_output))
