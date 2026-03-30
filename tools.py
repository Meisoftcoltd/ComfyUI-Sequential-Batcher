import math
from . import register_node

# 🧠 Clase Base Invisible (El molde matemático por Megapíxeles)
class BaseResolutionTool:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "aspect_ratio": (["16:9", "9:16", "1:1", "4:3", "3:4", "21:9", "3:2", "2:3"],),
                "base_resolution": (["256", "360", "480", "512", "720", "768", "1024", "1080", "1280", "1440", "1920", "2048", "2160"], {"default": "1024"}),
            }
        }

    RETURN_TYPES = ("INT", "INT", "STRING")
    RETURN_NAMES = ("width", "height", "debug_info")
    FUNCTION = "get_resolution"
    CATEGORY = "🔁 Sequential Batcher/Tools"

    def get_resolution(self, aspect_ratio, base_resolution):
        div = self.DIVISOR
        min_pixels = getattr(self, "MIN_PIXELS", 0)
        longest_side = int(base_resolution)

        w_str, h_str = aspect_ratio.split(':')
        w_ratio = float(w_str)
        h_ratio = float(h_str)
        ratio = w_ratio / h_ratio

        print(f"\n{'='*50}")
        print(f"🛠️ [DEBUG] NODO: Resolution Tool {div}x")
        print(f"   -> Petición Original: Lado mayor {longest_side}px | Ratio {aspect_ratio}")

        # 1. Calcular resolución inicial teórica
        if w_ratio >= h_ratio:
            ideal_w = longest_side
            ideal_h = ideal_w / ratio
        else:
            ideal_h = longest_side
            ideal_w = ideal_h * ratio

        current_pixels = ideal_w * ideal_h

        # 2. 🛡️ Protección de Suelo por ÁREA TOTAL (Training Floor)
        if current_pixels < min_pixels:
            print(f"   -> ⚠️ ALERTA: La resolución pedida ({int(current_pixels)} píxeles) es inferior al mínimo vital del modelo ({min_pixels} píxeles).")
            print(f"   -> 🛡️ Escalando proporcionalmente para evitar artefactos...")
            # Factor de escala basado en área
            scale_factor = math.sqrt(min_pixels / current_pixels)
            ideal_w *= scale_factor
            ideal_h *= scale_factor

        # 3. Ajuste final de divisibilidad estricta
        # Usamos round para asegurar que nos quedamos lo más cerca posible del área ideal
        width = max(div, round(ideal_w / div) * div)
        height = max(div, round(ideal_h / div) * div)

        debug_msg = f"{width}x{height} (Div {div})"

        print(f"   -> 🎯 Resultado Final Seguro: Ancho {width} | Alto {height} | Píxeles totales: {width*height}")
        print(f"{'='*50}\n")

        return (width, height, debug_msg)

# 📦 Nodos Específicos Blindados por Píxeles
@register_node
class ResTool8x(BaseResolutionTool):
    DIVISOR = 8
    MIN_PIXELS = 262144  # SD1.5 (Equivale a 512x512)

@register_node
class ResTool16x(BaseResolutionTool):
    DIVISOR = 16
    MIN_PIXELS = 1048576 # SDXL (Equivale a 1024x1024)

@register_node
class ResTool32x(BaseResolutionTool):
    DIVISOR = 32
    MIN_PIXELS = 399360  # WanVideo (Equivale a 832x480)

@register_node
class ResTool64x(BaseResolutionTool):
    DIVISOR = 64
    MIN_PIXELS = 921600  # Hunyuan (Equivale a 1280x720)