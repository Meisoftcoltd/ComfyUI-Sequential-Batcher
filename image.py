import torch
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import register_node


@register_node
class JoinImageBatch:
    """Turns an image batch into one big image."""
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "mode": (("horizontal", "vertical"), {"default": "horizontal"}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    INPUT_IS_LIST = True
    FUNCTION = "join"
    CATEGORY = "🔁 Sequential Batcher/Image"

    def join(self, images, mode):
        # mode will be a list of strings, e.g. ["horizontal", "horizontal", ...]
        mode = mode[0]
        if isinstance(images, list):
            # images is a list of [1, H, W, C] tensors or similar
            images = torch.cat(images, dim=0)
        n, h, w, c = images.shape
        image = None
        if mode == "vertical":
            # for vertical we can just reshape
            image = images.reshape(1, n * h, w, c)
        elif mode == "horizontal":
            # for horizontal we have to swap axes
            image = torch.transpose(torch.transpose(images, 1, 2).reshape(1, n * w, h, c), 1, 2)
        return (image,)


@register_node
class JoinImages:
    """Turns joins two images into one big image."""
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image_a": ("IMAGE",),
                "image_b": ("IMAGE",),
                "mode": (("horizontal", "vertical"), {"default": "horizontal"}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "join"
    CATEGORY = "🔁 Sequential Batcher/Image"

    def join(self, image_a, image_b, mode):
        dim = {'horizontal': 2, 'vertical': 1}[mode]
        return (torch.concat((image_a, image_b), dim), )


@register_node
class SelectImageBatch:
    """Selects one image from an image batch."""
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "select": ("INT", {"default": 0, "min": 0, "max": 99999, "step": 1}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "select"
    CATEGORY = "🔁 Sequential Batcher/Image"

    def select(self, images, select):
        n, h, w, c = images.shape
        if select >= n:
            select = n - 1
        return (images[select].reshape(1, h, w, c),)


@register_node
class SelectImageList:
    """Selects one image from an image list."""
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "select": ("INT", {"default": 0, "min": 0, "max": 99999, "step": 1}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    INPUT_IS_LIST = True
    FUNCTION = "select"
    CATEGORY = "🔁 Sequential Batcher/Image"

    def select(self, images, select):
        select = select[0]
        n = len(images)
        if select >= n:
            select = n - 1
        return (images[select],)


@register_node
class GetImageSize:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("INT", "INT", "INT")
    RETURN_NAMES = ("width", "height", "batch_size")
    FUNCTION = "go"
    CATEGORY = "🔁 Sequential Batcher/Image"

    def go(self, images):
        return (images.shape[2], images.shape[1], images.shape[0])


@register_node
class StringToImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"default": "Hello world!"}),
                "width": ("INT", {"default": 384}),
                "height": ("INT", {"default": 16}),
                "colour": ("COLOR", {"default": "white"}),
                "background": ("COLOR", {"default": "black"}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "render"
    CATEGORY = "🔁 Sequential Batcher/Image"

    def render(self, text, width, height, colour, background):
        font = ImageFont.load_default()
        img = Image.new("RGB", (width, height), background)
        draw = ImageDraw.Draw(img)
        _, _, w, h = draw.textbbox((0, 0), text, font=font)
        draw.text(((width - w) / 2, ((height - h) / 2) - 1), text, font=font, fill=colour)
        tensor = torch.from_numpy(np.array(img).astype(np.float32) / 255.0).unsqueeze(0)
        return (tensor,)


@register_node
class ProgressBar:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "progress": ("FLOAT", {'default': 0, 'forceInput': True}),
                "padding": ("INT", {'default': 3}),
                "width": ("INT", {"default": 384}),
                "height": ("INT", {"default": 16}),
                "colour": ("COLOR", {"default": "white"}),
                "background": ("COLOR", {"default": "black"}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "render"
    CATEGORY = "🔁 Sequential Batcher/Image"

    def render(self, progress, padding, width, height, colour, background):
        img = Image.new("RGB", (width, height), background)
        draw = ImageDraw.Draw(img)
        draw.rectangle((padding, padding, width - padding - 1, height - padding - 1), outline=colour)
        if progress > 0:
            ip = padding + 2
            draw.rectangle((ip, ip, max(ip+1, (width - ip - 1) * progress), height - ip - 1), outline=colour, fill=colour)
        tensor = torch.from_numpy(np.array(img).astype(np.float32) / 255.0).unsqueeze(0)
        return (tensor,)


@register_node
class ImageBatchToList:
    """Splits an image batch into a list for iteration."""
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"images": ("IMAGE",)}}
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "go"
    CATEGORY = "🔁 Sequential Batcher/Image"

    def go(self, images):
        return (list(torch.split(images, 1, dim=0)),)


@register_node
class ImageListToBatch:
    """Gathers an iterated list of images into a single batch."""
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"images": ("IMAGE",)}}
    INPUT_IS_LIST = True
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "go"
    CATEGORY = "🔁 Sequential Batcher/Image"

    def go(self, images):
        return (torch.cat(images, dim=0),)


@register_node
class LatentBatchToList:
    """Splits a latent batch into a list for iteration."""
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"latents": ("LATENT",)}}
    RETURN_TYPES = ("LATENT",)
    RETURN_NAMES = ("latent",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "go"
    CATEGORY = "🔁 Sequential Batcher/Latent"

    def go(self, latents):
        samples = latents["samples"]
        return ([{"samples": samples[i:i+1]} for i in range(samples.shape[0])],)


@register_node
class LatentListToBatch:
    """Gathers an iterated list of latents into a single batch."""
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"latents": ("LATENT",)}}
    INPUT_IS_LIST = True
    RETURN_TYPES = ("LATENT",)
    RETURN_NAMES = ("latents",)
    FUNCTION = "go"
    CATEGORY = "🔁 Sequential Batcher/Latent"

    def go(self, latents):
        return ({"samples": torch.cat([l["samples"] for l in latents], dim=0)},)


# Variable global para almacenar el último fotograma de la sesión
global_session_image = None

@register_node
class SessionImageReceiver:
    """Proporciona la imagen inicial en el ciclo 1, y la última imagen generada en los ciclos siguientes."""
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "initial_image": ("IMAGE",),
                "reset_session": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("current_image",)
    FUNCTION = "get_image"
    CATEGORY = "🔁 Sequential Batcher/Image"

    # CRÍTICO: Obliga a ComfyUI a ejecutar este nodo en cada ciclo de Auto Queue
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    def get_image(self, initial_image, reset_session):
        global global_session_image

        # Si el usuario pide reiniciar, o es la primera vez que arranca ComfyUI
        if reset_session or global_session_image is None:
            global_session_image = initial_image
            print("[Sequential Batcher] Reference Image: Iniciando sesión con la imagen original.")
            return (initial_image, )

        print("[Sequential Batcher] Reference Image: Usando el último fotograma del ciclo anterior.")
        return (global_session_image, )

@register_node
class SessionImageSender:
    """Extrae el último fotograma de un lote de vídeo y lo guarda en memoria para el siguiente ciclo."""
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "generated_images": ("IMAGE",),
            },
        }

    RETURN_TYPES = ()
    OUTPUT_NODE = True
    FUNCTION = "set_image"
    CATEGORY = "🔁 Sequential Batcher/Image"

    # CRÍTICO: Obliga a ComfyUI a ejecutar este nodo siempre
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    def set_image(self, generated_images):
        global global_session_image

        # En ComfyUI, los lotes de imágenes son tensores de forma [B, H, W, C]
        # Extraemos solo el último elemento preservando la dimensión del lote [1, H, W, C] usando clone() para desligarlo del grafo actual
        last_frame = generated_images[-1:].clone()
        global_session_image = last_frame

        print(f"[Sequential Batcher] Reference Image: Último fotograma capturado con éxito.")
        return ()
