import math
from . import register_node

# 🧠 Clase Base Invisible (El molde matemático por Megapíxeles)
class BaseResolutionTool:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "aspect_ratio": (["16:9", "9:16", "1:1", "4:3", "3:4", "21:9", "3:2", "2:3"],),
                # 💡 Cambio clave: Dejamos de usar combo y pasamos a un campo INT libre
                "base_resolution": ("INT", {"default": 1024, "min": 128, "max": 8192, "step": 8}),
            }
        }

    RETURN_TYPES = ("INT", "INT", "STRING")
    RETURN_NAMES = ("width", "height", "debug_info")
    FUNCTION = "get_resolution"
    CATEGORY = "🔁 Sequential Batcher/Tools"

    def get_resolution(self, aspect_ratio, base_resolution):
        div = self.DIVISOR
        min_pixels = getattr(self, "MIN_PIXELS", 0)
        longest_side = int(base_resolution) # Mantenemos el casting por seguridad

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

@register_node
class ResTool64xLTX(BaseResolutionTool):
    DIVISOR = 64
    MIN_PIXELS = 393216  # LTX 2.3 (Equivale a 768x512)


@register_node
class AutoFPSLimiter:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "source_fps": ("FLOAT", {"forceInput": True}),
                "target_max_fps": ("FLOAT", {"default": 30.0, "min": 1.0, "max": 120.0, "step": 1.0}),
            }
        }

    RETURN_TYPES = ("INT", "FLOAT")
    RETURN_NAMES = ("select_every_nth", "new_fps")
    FUNCTION = "calculate_fps"
    CATEGORY = "🔁 Sequential Batcher/Tools"

    def calculate_fps(self, source_fps, target_max_fps):
        import math
        print(f"\n{'='*50}")
        print(f"⏱️ [DEBUG] NODO: Auto FPS Limiter")
        print(f"   -> FPS Originales: {source_fps:.2f} | Meta Máxima: {target_max_fps:.2f}")

        if source_fps <= target_max_fps:
            nth = 1
            new_fps = source_fps
            print(f"   -> ✅ Los FPS originales ya están dentro del límite.")
        else:
            # Calculamos el salto matemático (hacia arriba) para garantizar no superar la meta
            nth = math.ceil(source_fps / target_max_fps)
            new_fps = source_fps / nth
            print(f"   -> ✂️ Reducción necesaria. Procesando 1 de cada {nth} frames.")

        print(f"   -> 🎯 Resultado: {new_fps:.2f} FPS finales (Nth: {nth})")
        print(f"{'='*50}\n")

        return (nth, new_fps)
