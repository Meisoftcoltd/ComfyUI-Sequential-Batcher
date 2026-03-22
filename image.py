import os
import random
import numpy as np
import torch
from PIL import Image
import folder_paths
from . import register_node

# Variable global para almacenar el último fotograma en la memoria del sistema (RAM)
global_session_image = None

def tensor_to_temp_image(tensor_image, prefix="session_img"):
    """Convierte un tensor de ComfyUI [1, H, W, C] a PNG temporal para la UI."""
    temp_dir = folder_paths.get_temp_directory()
    filename = f"{prefix}_{random.randint(10000, 99999)}.png"
    filepath = os.path.join(temp_dir, filename)

    # Extraemos el primer (y único) frame del tensor y lo convertimos
    img_array = 255. * tensor_image[0].cpu().numpy()
    img = Image.fromarray(np.clip(img_array, 0, 255).astype(np.uint8))
    img.save(filepath)

    return {"filename": filename, "subfolder": "", "type": "temp"}


@register_node
class SessionImageReceiver:
    """Proporciona la imagen inicial o la última generada, leyendo de la memoria RAM."""
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "initial_image": ("IMAGE",),
                "current_loop_index": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("current_image",)
    OUTPUT_NODE = True
    FUNCTION = "get_image"
    CATEGORY = "🔁 Sequential Batcher/Image"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    def get_image(self, initial_image, current_loop_index):
        global global_session_image

        # Extracción segura obligatoria por si hay listas
        loop_idx = current_loop_index[0] if isinstance(current_loop_index, list) else current_loop_index
        is_first_cycle = (loop_idx == 0)

        if is_first_cycle or global_session_image is None:
            global_session_image = initial_image.clone().cpu() # Guardamos en CPU por seguridad
            print(f"[Sequential Batcher] Receiver: Ciclo {loop_idx}. Iniciando sesión con la imagen original.")
            selected = initial_image
        else:
            print(f"[Sequential Batcher] Receiver: Ciclo {loop_idx}. Usando el fotograma rescatado de la RAM.")
            # Movemos de vuelta a la GPU (o dejamos que ComfyUI lo asigne)
            selected = global_session_image

        ui_image = tensor_to_temp_image(selected, "receiver")
        return {"ui": {"images": [ui_image]}, "result": (selected, )}


@register_node
class SessionImageSender:
    """Extrae, guarda en memoria del sistema (CPU) y muestra el último fotograma."""
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "generated_images": ("IMAGE",),
            },
        }

    RETURN_TYPES = ()
    RETURN_NAMES = ()
    OUTPUT_NODE = True
    FUNCTION = "set_image"
    CATEGORY = "🔁 Sequential Batcher/Image"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    def set_image(self, generated_images):
        global global_session_image

        # CRÍTICO: .cpu() asegura que ComfyUI no destruya el tensor al vaciar la VRAM de la gráfica
        last_frame = generated_images[-1:].clone().cpu()
        global_session_image = last_frame

        print(f"[Sequential Batcher] Sender: Último fotograma capturado y asegurado en la RAM del sistema.")

        ui_image = tensor_to_temp_image(last_frame, "sender")
        return {"ui": {"images": [ui_image]}}
