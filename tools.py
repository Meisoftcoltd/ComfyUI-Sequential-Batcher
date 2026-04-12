import math
import torch
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

@register_node
class ConditionalAudioRouter:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "audio": ("AUDIO",),
                "is_final_cycle": ("BOOLEAN", {"forceInput": True}),
            }
        }

    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("routed_audio",)
    FUNCTION = "route"
    CATEGORY = "🔁 Sequential Batcher/Tools"

    def route(self, audio, is_final_cycle):
        if is_final_cycle:
            print("   -> 🔊 [Audio Router] Ciclo Final: Enviando pista de audio completa al Lip Sync.")
            return (audio,)
        else:
            print("   -> 🔇 [Audio Router] Ciclo Intermedio: Generando micro-silencio para bypasear el Lip Sync...")

            # Detectar el sample rate del audio original (estándar de ComfyUI es un dict)
            sample_rate = 44100
            if isinstance(audio, dict) and "sample_rate" in audio:
                sample_rate = audio["sample_rate"]

            # Creamos 0.1 segundos de silencio absoluto (1 canal, mínimos samples)
            samples = int(sample_rate * 0.1)
            dummy_waveform = torch.zeros((1, 1, samples), dtype=torch.float32)
            dummy_audio = {"waveform": dummy_waveform, "sample_rate": sample_rate}

            return (dummy_audio,)

@register_node
class VAESafeFramePadder:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "rule": (["WanVideo (Múltiplo de 4)", "LTX (Regla 8n+1)"],),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT")
    RETURN_NAMES = ("PADDED_IMAGES", "frames_added")
    FUNCTION = "pad"
    CATEGORY = "🔁 Sequential Batcher/Tools"

    def pad(self, images, rule):
        n_frames = images.shape[0]
        target_frames = n_frames

        if rule == "WanVideo (Múltiplo de 4)":
            target_frames = ((n_frames + 3) // 4) * 4
        elif rule == "LTX (Regla 8n+1)":
            if n_frames < 9:
                target_frames = 9
            else:
                target_frames = ((n_frames + 6) // 8) * 8 + 1

        diff = target_frames - n_frames

        print(f"\n{'='*50}")
        print(f"🛡️ [DEBUG] NODO: VAE Safe Frame Padder")
        print(f"   -> Frames recibidos: {n_frames}")
        print(f"   -> Regla aplicada: {rule}")

        if diff > 0:
            print(f"   -> 🧱 Tensor incompleto. Clonando el último frame {diff} vez/veces...")
            last_frame = images[-1:] # Extraemos el último frame
            padding = last_frame.repeat(diff, 1, 1, 1) # Lo multiplicamos
            images = torch.cat([images, padding], dim=0) # Lo fusionamos al final
            print(f"   -> ✅ Tensor final acolchado a: {target_frames} frames.")
        else:
            print(f"   -> ✅ Tensor perfecto. No requiere acolchado.")

        print(f"{'='*50}\n")
        return (images, diff)
