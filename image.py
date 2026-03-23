import os
import time
import random
import numpy as np
import torch
from PIL import Image
import folder_paths
from . import register_node

global_session_image = None

def tensor_to_temp_image(tensor_image, prefix="session_img"):
    temp_dir = folder_paths.get_temp_directory()
    filename = f"{prefix}_{random.randint(10000, 99999)}.png"
    filepath = os.path.join(temp_dir, filename)
    img_array = 255. * tensor_image[0].cpu().numpy()
    img = Image.fromarray(np.clip(img_array, 0, 255).astype(np.uint8))
    img.save(filepath)
    return {"filename": filename, "subfolder": "", "type": "temp"}

@register_node
class SessionImageReceiver:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "initial_image": ("IMAGE",),
                "current_loop_index": ("INT", {"default": 0, "min": 0, "max": 10000}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("current_image",)
    OUTPUT_NODE = True
    FUNCTION = "get_image"
    CATEGORY = "🔁 Sequential Batcher/Image"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time()

    def get_image(self, initial_image, current_loop_index):
        global global_session_image
        loop_idx = current_loop_index[0] if isinstance(current_loop_index, list) else current_loop_index
        is_first = (loop_idx == 0)

        print(f"\n{'='*50}")
        print(f"📥 [DEBUG] NODO: Image Receiver")
        print(f"   -> Ciclo actual detectado: {loop_idx}")

        if is_first or global_session_image is None:
            global_session_image = initial_image.clone().cpu()
            print(f"   -> 🆕 Iniciando sesión con la imagen ORIGINAL.")
            selected = initial_image
        else:
            print(f"   -> ♻️ Usando el fotograma rescatado de la RAM.")
            selected = global_session_image

        print(f"   -> 🖼️ Tensor shape: {selected.shape}")
        print(f"{'='*50}\n")

        ui_image = tensor_to_temp_image(selected, "receiver")
        return {"ui": {"images": [ui_image]}, "result": (selected, )}

@register_node
class SessionImageSender:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "generated_images": ("IMAGE",),
                "current_loop_index": ("INT", {"default": 0, "min": 0, "max": 10000}),
            },
        }

    RETURN_TYPES = ()
    RETURN_NAMES = ()
    OUTPUT_NODE = True
    FUNCTION = "set_image"
    CATEGORY = "🔁 Sequential Batcher/Image"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time()

    def set_image(self, generated_images, current_loop_index):
        if generated_images is None:
            raise ValueError("❌ ERROR CRÍTICO: El nodo 'Session Image Sender' no está recibiendo imágenes. Conecta la salida de tu VAE Decode o Sampler.")

        if current_loop_index is None:
            raise ValueError("❌ ERROR CRÍTICO: El nodo 'Session Image Sender' necesita el cable de 'current_loop_index' desde el Loop Start para nombrar los archivos.")

        global global_session_image
        loop_idx = current_loop_index[0] if isinstance(current_loop_index, list) else current_loop_index

        print(f"\n{'='*50}")
        print(f"📤 [DEBUG] NODO: Image Sender")
        print(f"   -> Ciclo actual: {loop_idx} | Frames recibidos: {generated_images.shape[0]}")

        last_frame = generated_images[-1:].clone().cpu()
        global_session_image = last_frame

        # Guardar disco progresivo
        out_dir = folder_paths.get_output_directory()
        filename = f"keyframe_{loop_idx:03d}.png"
        filepath = os.path.join(out_dir, filename)

        img_array = 255. * last_frame[0].numpy()
        img = Image.fromarray(np.clip(img_array, 0, 255).astype(np.uint8))
        img.save(filepath)

        print(f"   -> 💾 Keyframe guardado físicamente: {filename}")
        print(f"   -> 🧠 RAM asegurada para el próximo ciclo.")
        print(f"{'='*50}\n")

        ui_image = tensor_to_temp_image(last_frame, "sender")
        return {"ui": {"images": [ui_image]}}
