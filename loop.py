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
global_server_port = 8188  # 💡 NUEVO: Única fuente de la verdad para el puerto
global_ltx_mode = False

@register_node
class SequentialLoopStart:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "reset_loop": ("BOOLEAN", {"default": False}),
                "loop_idx": ("INT", {"default": 0, "min": 0, "max": 10000}),
                "port": ("INT", {"default": 8188, "min": 1, "max": 65535}), # 💡 FAIL-FAST: Pedimos el puerto aquí
            }
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("current_loop_index",)
    FUNCTION = "get_index"
    CATEGORY = "🔁 Sequential Batcher/Loop"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time()

    def get_index(self, reset_loop, loop_idx, port):
        global global_loop_index
        global global_accumulated_frames
        global global_server_port
        global global_ltx_mode

        print(f"\n{'='*50}")
        print(f"🚀 [DEBUG] NODO: Loop Start (Motor Dinámico)")

        # --- PRE-FLIGHT CHECK (FAIL-FAST) ---
        print(f"   -> 📡 Verificando conexión con ComfyUI en el puerto {port}...")
        try:
            # Ping ultrarrápido a la API. Si falla, colapsa en 0.1 segundos.
            req = urllib.request.Request(f"http://127.0.0.1:{port}/system_stats")
            urllib.request.urlopen(req, timeout=2)
            global_server_port = port  # Guardamos el puerto correcto para el Trigger
            print(f"   -> ✅ Conexión establecida. Puerto blindado.")
        except Exception as e:
            print(f"   -> ❌ ERROR FATAL: No se pudo conectar al puerto {port}.")
            raise ValueError(f"🚨 EL PUERTO {port} ES INCORRECTO O COMFYUI NO RESPONDE. "
                             f"Cambia el puerto en el nodo 'Loop Start' antes de procesar. (Error: {e})")
        # ------------------------------------

        is_reset = str(reset_loop).lower() in ['true', '1', 't', 'y']
        if is_reset or loop_idx == 0:
            global_loop_index = 0
            global_accumulated_frames = 0
            global_ltx_mode = False # 💡 REINICIO DE SEGURIDAD PARA LTX
            print("   -> 🔄 Bucle y Acumulador reiniciados a 0.")
        else:
            global_loop_index = loop_idx

        print(f"   -> 📍 Índice actual de bucle: {global_loop_index}")
        print(f"{'='*50}\n")
        return (global_loop_index,)

@register_node
class AutoLoopCalculatorLTX:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "source_video_frames": ("INT", {"forceInput": True}),
                "target_chunk_frames": ("INT", {"default": 81, "min": 9, "max": 257, "step": 8}),
            }
        }

    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("ltx_chunk_size", "total_loops_estimated")
    FUNCTION = "calculate"
    CATEGORY = "🔁 Sequential Batcher/Loop"

    def calculate(self, source_video_frames, target_chunk_frames):
        import math

        # 1. Forzar el chunk a la regla estricta de LTX 2.3: 8n + 1
        n = max(1, round((target_chunk_frames - 1) / 8))
        ltx_chunk = (n * 8) + 1

        # 2. Calcular el avance real (Restamos el fotograma 'ancla' de solapamiento)
        advance_per_loop = ltx_chunk - 1
        total_loops = math.ceil(source_video_frames / advance_per_loop)

        # Indicador global para el Stitcher y Sender (LTX mode activo)
        global global_ltx_mode
        global_ltx_mode = True

        print(f"\n{'='*50}")
        print(f"📊 [DEBUG] NODO: Auto Loop Calculator (LTX 2.3)")
        print(f"   -> Frames Totales Origen: {source_video_frames}")
        print(f"   -> Chunk Solicitado: {target_chunk_frames} | Forzado a LTX (8n+1): {ltx_chunk}")
        print(f"   -> Avance Real por Bucle: {advance_per_loop} frames")
        print(f"   -> Total de Bucles Estimados: {total_loops}")
        print(f"{'='*50}\n")

        return (ltx_chunk, total_loops)

@register_node
class SequentialLoopTrigger:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "trigger_dependency": ("*", ),
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

    def trigger_next(self, trigger_dependency, prompt=None, extra_pnginfo=None):
        global global_loop_index
        global global_accumulated_frames
        global global_source_frame_count
        global global_server_port

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
            req = urllib.request.Request(f"http://127.0.0.1:{global_server_port}/prompt", data=data, headers={'Content-Type': 'application/json'})
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
