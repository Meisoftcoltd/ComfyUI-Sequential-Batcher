import random
import time
import urllib.request
import json
import gc
import torch
import comfy.model_management as mm
from . import register_node

global_loop_index = 0
global_accumulated_frames = 0
global_source_frame_count = 1
global_select_every_nth = 1

@register_node
class SequentialLoopStart:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "reset_loop": ("BOOLEAN", {"default": False}),
                "loop_idx": ("INT", {"default": 0, "min": 0, "max": 10000}),
            }
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("current_loop_index",)
    FUNCTION = "get_index"
    CATEGORY = "🔁 Sequential Batcher/Loop"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time()

    def get_index(self, reset_loop, loop_idx):
        global global_loop_index
        global global_accumulated_frames

        print(f"\n{'='*50}")
        print(f"🚀 [DEBUG] NODO: Loop Start (Motor Dinámico)")

        is_reset = str(reset_loop).lower() in ['true', '1', 't', 'y']
        if is_reset or loop_idx == 0:
            global_loop_index = 0
            global_accumulated_frames = 0
            print("   -> 🔄 Bucle y Acumulador reiniciados a 0.")
        else:
            global_loop_index = loop_idx

        print(f"   -> 📤 OUTPUT current_loop_index: {global_loop_index}")
        print(f"   -> 📈 Frames acumulados históricamente: {global_accumulated_frames}")
        print(f"{'='*50}\n")

        return (global_loop_index,)

@register_node
class SequentialLoopTrigger:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "trigger_dependency": ("*", ),
                "port": ("INT", {"default": 8188, "min": 1000, "max": 9999}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"}
        }

    RETURN_TYPES = ()
    RETURN_NAMES = ()
    OUTPUT_NODE = True
    FUNCTION = "trigger_next"
    CATEGORY = "🔁 Sequential Batcher/Loop"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time()

    def trigger_next(self, trigger_dependency, port, prompt=None, extra_pnginfo=None):
        global global_loop_index
        global global_accumulated_frames
        global global_source_frame_count

        next_loop = global_loop_index + 1
        is_final = global_accumulated_frames >= global_source_frame_count

        print(f"\n{'='*50}")
        print(f"🎯 [DEBUG] NODO: Loop Trigger")
        print(f"   -> Progreso del vídeo: {global_accumulated_frames} / {global_source_frame_count} frames.")

        if not is_final:
            print(f"   -> ⚙️ Preparando Ciclo {next_loop}...")
            if prompt is not None:
                m_seeds = 0
                for node_id, node_data in prompt.items():
                    inputs = node_data.get("inputs", {})
                    for key in ["seed", "noise_seed"]:
                        if key in inputs and isinstance(inputs[key], (int, float)):
                            inputs[key] = random.randint(1, 0xffffffff)
                            m_seeds += 1
                    if node_data.get("class_type") == "SequentialLoopStart":
                        inputs["loop_idx"] = next_loop
                        inputs["reset_loop"] = False
                print(f"   -> 🎲 Semillas mutadas: {m_seeds}")

            p = {"prompt": prompt}
            if extra_pnginfo:
                p["extra_data"] = {"extra_pnginfo": extra_pnginfo}
            data = json.dumps(p).encode('utf-8')
            req = urllib.request.Request(f"http://127.0.0.1:{port}/prompt", data=data, headers={'Content-Type': 'application/json'})
            try:
                urllib.request.urlopen(req, timeout=5)
                print(f"   -> ✅ Ciclo {next_loop} inyectado en la cola.")
            except Exception as e:
                print(f"   -> ❌ Error HTTP: {e}")
        else:
            print(f"   -> 🏁 ¡Generación Finalizada! Todos los frames ensamblados.")
            global_loop_index = 0
            global_accumulated_frames = 0

            # --- LIMPIEZA EXTREMA DE VRAM AUTOMÁTICA (Multi-Plataforma) ---
            print(f"   -> 🧹 Iniciando vaciado automático de VRAM...")
            try:
                # 1. Obligamos al motor interno de ComfyUI a soltar los modelos
                mm.unload_all_models()
                mm.soft_empty_cache()
            except Exception as e:
                print(f"   -> ⚠️ Aviso: No se pudo usar model_management: {e}")

            # 2. Forzamos al recolector de basura de Python
            gc.collect()

            # 3. Le arrancamos a PyTorch la memoria reservada (CUDA, ROCm y Mac MPS)
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                torch.mps.empty_cache()

            print(f"   -> ✨ VRAM liberada con éxito. Gráfica lista para nuevos flujos.")

        print(f"{'='*50}\n")
        return ()
