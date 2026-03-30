from . import register_node

# 🧠 Clase Base Invisible (El molde matemático)
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
        longest_side = int(base_resolution)

        w_str, h_str = aspect_ratio.split(':')
        w_ratio = float(w_str)
        h_ratio = float(h_str)

        # Matemática segura hacia abajo (Strictly Down) simulando tabla memorizada
        actual_longest = max(div, (longest_side // div) * div)

        if w_ratio >= h_ratio:
            ideal_w = actual_longest
            ideal_h = ideal_w * (h_ratio / w_ratio)
            width = ideal_w
            height = max(div, (int(ideal_h) // div) * div)
        else:
            ideal_h = actual_longest
            ideal_w = ideal_h * (w_ratio / h_ratio)
            height = ideal_h
            width = max(div, (int(ideal_w) // div) * div)

        debug_msg = f"{width}x{height} (Div {div})"

        print(f"\n{'='*50}")
        print(f"🛠️ [DEBUG] NODO: Resolution Tool {div}x")
        print(f"   -> Petición: {base_resolution}p | Ratio {aspect_ratio}")
        print(f"   -> 🎯 Resultado Seguro: Ancho {width} | Alto {height}")
        print(f"{'='*50}\n")

        return (width, height, debug_msg)

# 📦 Los 4 Nodos Visibles para el Usuario
@register_node
class ResTool8x(BaseResolutionTool):
    DIVISOR = 8

@register_node
class ResTool16x(BaseResolutionTool):
    DIVISOR = 16

@register_node
class ResTool32x(BaseResolutionTool):
    DIVISOR = 32

@register_node
class ResTool64x(BaseResolutionTool):
    DIVISOR = 64
