import random
import time
import urllib.request
import json
from . import register_node

# Variable global para mantener el estado del bucle entre ejecuciones
global_loop_index = 0

@register_node
class SequentialLoopStart:
    """Inicia el bucle y provee el índice actual a los nodos de imagen y vídeo."""
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "reset_loop": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("current_loop_index",)
    FUNCTION = "get_index"
    CATEGORY = "🔁 Sequential Batcher/Loop"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time() # Garantiza 100% una ruptura de caché

    def get_index(self, reset_loop):
        global global_loop_index

        # Saneamiento de booleano por si viene de un text input
        is_reset = False
        if isinstance(reset_loop, str):
            is_reset = reset_loop.strip().lower() in ['true', '1', 't', 'y', 'yes']
        else:
            is_reset = bool(reset_loop)

        if is_reset:
            global_loop_index = 0
            print("🔄 [Sequential Batcher] Loop Start: Bucle reiniciado a 0 manualmente.")

        print(f"🔄 [Sequential Batcher] Loop Start: Ejecutando ciclo {global_loop_index}.")
        return (global_loop_index, )

@register_node
class SequentialLoopTrigger:
    """Se ejecuta al final del flujo. Incrementa el contador, muta las semillas y auto-encola el siguiente ciclo."""
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "trigger_dependency": ("*", ),
                "target_loops": ("INT", {"default": 4, "min": 1, "max": 1000, "step": 1}),
                "port": ("INT", {"default": 8188, "min": 1000, "max": 9999, "step": 1}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO"
            }
        }

    RETURN_TYPES = ()
    RETURN_NAMES = ()
    OUTPUT_NODE = True
    FUNCTION = "trigger_next"
    CATEGORY = "🔁 Sequential Batcher/Loop"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time() # Garantiza 100% una ruptura de caché en nuestro nodo

    def trigger_next(self, trigger_dependency, target_loops, port, prompt=None, extra_pnginfo=None):
        global global_loop_index

        global_loop_index += 1

        if global_loop_index < target_loops:
            print(f"🚀 [Sequential Batcher] Loop Trigger: Ciclo {global_loop_index}/{target_loops}. Encolando automáticamente el siguiente lote...")

            # 💥 MAGIA ANTI-CACHÉ: Muta todas las semillas en el lienzo para obligar al Sampler a renderizar
            if prompt is not None:
                for node_id, node_data in prompt.items():
                    inputs = node_data.get("inputs", {})
                    for key in ["seed", "noise_seed"]:
                        if key in inputs and isinstance(inputs[key], (int, float)):
                            # Generamos una semilla de 32 bits compatible con Samplers antiguos
                            inputs[key] = random.randint(1, 0xffffffff)

            p = {"prompt": prompt}
            if extra_pnginfo:
                p["extra_data"] = {"extra_pnginfo": extra_pnginfo}

            data = json.dumps(p).encode('utf-8')
            req = urllib.request.Request(f"http://127.0.0.1:{port}/prompt", data=data, headers={'Content-Type': 'application/json'})

            try:
                urllib.request.urlopen(req, timeout=5)
                print("✅ [Sequential Batcher] Loop Trigger: Siguiente lote mutado e inyectado con éxito.")
            except Exception as e:
                print(f"❌ [Sequential Batcher] Error al auto-encolar: {e}")
        else:
            print(f"🏁 [Sequential Batcher] Loop Trigger: ¡Generación finalizada! Se han completado los {target_loops} ciclos.")
            global_loop_index = 0

        return ()
