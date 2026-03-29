import random
import time
import urllib.request
import json
from . import register_node

global_loop_index = 0
global_total_loops = 1  # 🌍 NUEVA MEMORIA GLOBAL PARA LOS CICLOS
global_source_frame_count = 0  # NUEVO: Memoria del total de frames
global_target_frames = 50      # NUEVO: Memoria del target del usuario
global_stride = 1              # NUEVO: Memoria del salto

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
        global global_total_loops
        global global_source_frame_count

        print(f"\n{'='*50}")
        print(f"🚀 [DEBUG] NODO: Loop Start")
        print(f"   -> Input loop_idx: {loop_idx} (Total Esperado: {global_total_loops})")
        print(f"   -> Input reset_loop: {reset_loop}")

        is_reset = str(reset_loop).lower() in ['true', '1', 't', 'y']
        if is_reset:
            global_loop_index = 0
            global_total_loops = 1 # Reinicio de seguridad limpia la memoria fantasma
            global_source_frame_count = 0 # Reinicio limpio
            print("   -> 🔄 Bucle reiniciado a 0 manualmente.")
        else:
            global_loop_index = loop_idx

        print(f"   -> 📤 OUTPUT current_loop_index: {global_loop_index}")
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
        if trigger_dependency is None:
            raise ValueError("❌ ERROR CRÍTICO: El nodo 'Loop Trigger' no tiene nada conectado en 'trigger_dependency'. Debes conectar la salida del Stitcher para que el bucle pueda continuar.")

        global global_loop_index
        global global_total_loops

        target_loops = global_total_loops
        next_loop = global_loop_index + 1

        print(f"\n{'='*50}")
        print(f"🎯 [DEBUG] NODO: Loop Trigger")
        print(f"   -> Ciclo terminado: {global_loop_index} | Target: {target_loops}")

        if next_loop < target_loops:
            print(f"   -> ⚙️ Preparando Ciclo {next_loop}...")
            if prompt is not None:
                m_seeds = 0
                for node_id, node_data in prompt.items():
                    inputs = node_data.get("inputs", {})
                    # Mutar Semillas
                    for key in ["seed", "noise_seed"]:
                        if key in inputs and isinstance(inputs[key], (int, float)):
                            inputs[key] = random.randint(1, 0xffffffff)
                            m_seeds += 1
                    # 💥 INYECCIÓN ANTI-CACHÉ: Forzar a Loop Start a leer el nuevo índice
                    if node_data.get("class_type") == "SequentialLoopStart":
                        inputs["loop_idx"] = next_loop
                        inputs["reset_loop"] = False
                        print(f"   -> 💉 Inyectado loop_idx={next_loop} en LoopStart (Nodo {node_id})")
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
            print(f"   -> 🏁 ¡Generación finalizada! ({target_loops} ciclos)")
            global_loop_index = 0

        print(f"{'='*50}\n")
        return ()
