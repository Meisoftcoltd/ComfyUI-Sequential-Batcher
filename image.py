import os
import random
import numpy as np
import torch
from PIL import Image
import folder_paths

from . import register_node


# Variable global para almacenar el último fotograma de la sesión
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
    """Proporciona la imagen inicial o la última generada, detectando el inicio automáticamente."""
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

        # Extracción segura por si en el futuro se usa INPUT_IS_LIST
        loop_idx = current_loop_index[0] if isinstance(current_loop_index, list) else current_loop_index

        # LÓGICA NATIVA: Si es el primer ciclo (index 0), reiniciamos
        is_first_cycle = (loop_idx == 0)

        if is_first_cycle or global_session_image is None:
            global_session_image = initial_image
            print(f"[Sequential Batcher] Receiver: Ciclo {loop_idx}. Iniciando sesión con la imagen original.")
        else:
            print(f"[Sequential Batcher] Receiver: Ciclo {loop_idx}. Usando el último fotograma del ciclo anterior.")

        ui_image = tensor_to_temp_image(global_session_image, "receiver")
        return {"ui": {"images": [ui_image]}, "result": (global_session_image, )}


@register_node
class SessionImageSender:
    """Extrae, guarda en memoria y MUESTRA el último fotograma de un lote de vídeo."""
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

        # Extraemos solo el último elemento preservando la dimensión del lote [1, H, W, C]
        last_frame = generated_images[-1:].clone()
        global_session_image = last_frame

        print(f"[Sequential Batcher] Sender: Último fotograma capturado con éxito.")

        # Generar vista previa para la UI
        ui_image = tensor_to_temp_image(last_frame, "sender")

        # Solo actualizamos la UI, no hay salida de cables ("result" no es necesario si RETURN_TYPES es vacío)
        return {"ui": {"images": [ui_image]}}
