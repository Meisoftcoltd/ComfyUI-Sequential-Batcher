import math
import time
import torch
from . import register_node
from .switch_node import any_type

@register_node
class PrimitiveDelay:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "delay_seconds": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 3600.0, "step": 0.1, "tooltip": "Tiempo de pausa en segundos"}),
            },
            "optional": {
                "any_in": (any_type, {"tooltip": "Conecta aquí el cable que quieres retrasar"}),
            }
        }

    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("* (passthrough)",)
    FUNCTION = "execute_delay"
    CATEGORY = "🔁 Sequential Batcher/Tools"

    def execute_delay(self, delay_seconds, any_in=None):
        log_output = []
        def _log(msg):
            print(msg)
            log_output.append(str(msg))

        _log(f"\n{'='*50}")
        _log(f"⏱️ [Secuencial Batcher] NODO: Primitive Delay")
        _log(f"   -> Congelando la ejecución durante {delay_seconds} segundos...")

        time.sleep(delay_seconds)

        _log(f"   -> ✅ Pausa terminada. Reanudando flujo.")
        _log(f"{'='*50}\n")

        return (any_in,)

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

    RETURN_TYPES = ("INT", "INT", "STRING", "STRING")
    RETURN_NAMES = ("width", "height", "debug_info", "log")
    FUNCTION = "get_resolution"
    CATEGORY = "🔁 Sequential Batcher/Tools"

    def get_resolution(self, aspect_ratio, base_resolution):
        log_output = []
        def _log(msg):
            print(msg)
            log_output.append(str(msg))
        div = self.DIVISOR
        min_pixels = getattr(self, "MIN_PIXELS", 0)
        longest_side = int(base_resolution) # Mantenemos el casting por seguridad

        w_str, h_str = aspect_ratio.split(':')
        w_ratio = float(w_str)
        h_ratio = float(h_str)
        ratio = w_ratio / h_ratio

        _log(f"\n{'='*50}")
        _log(f"🛠️ [Secuencial Batcher] NODO: Resolution Tool {div}x")
        _log(f"   -> Petición Original: Lado mayor {longest_side}px | Ratio {aspect_ratio}")

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
            _log(f"   -> ⚠️ ALERTA: La resolución pedida ({int(current_pixels)} píxeles) es inferior al mínimo vital del modelo ({min_pixels} píxeles).")
            _log(f"   -> 🛡️ Escalando proporcionalmente para evitar artefactos...")
            # Factor de escala basado en área
            scale_factor = math.sqrt(min_pixels / current_pixels)
            ideal_w *= scale_factor
            ideal_h *= scale_factor

        # 3. Ajuste final de divisibilidad estricta
        # Usamos round para asegurar que nos quedamos lo más cerca posible del área ideal
        width = max(div, round(ideal_w / div) * div)
        height = max(div, round(ideal_h / div) * div)

        debug_msg = f"{width}x{height} (Div {div})"

        _log(f"   -> 🎯 Resultado Final Seguro: Ancho {width} | Alto {height} | Píxeles totales: {width*height}")
        _log(f"{'='*50}\n")

        return (width, height, debug_msg, "\n".join(log_output))

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

    RETURN_TYPES = ("INT", "FLOAT", "STRING")
    RETURN_NAMES = ("select_every_nth", "new_fps", "log")
    FUNCTION = "calculate_fps"
    CATEGORY = "🔁 Sequential Batcher/Tools"

    def calculate_fps(self, source_fps, target_max_fps):
        log_output = []
        def _log(msg):
            print(msg)
            log_output.append(str(msg))
        import math
        _log(f"\n{'='*50}")
        _log(f"⏱️ [Secuencial Batcher] NODO: Auto FPS Limiter")
        _log(f"   -> FPS Originales: {source_fps:.2f} | Meta Máxima: {target_max_fps:.2f}")

        if source_fps <= target_max_fps:
            nth = 1
            new_fps = source_fps
            _log(f"   -> ✅ Los FPS originales ya están dentro del límite.")
        else:
            # Calculamos el salto matemático (hacia arriba) para garantizar no superar la meta
            nth = math.ceil(source_fps / target_max_fps)
            new_fps = source_fps / nth
            _log(f"   -> ✂️ Reducción necesaria. Procesando 1 de cada {nth} frames.")

        _log(f"   -> 🎯 Resultado: {new_fps:.2f} FPS finales (Nth: {nth})")
        _log(f"{'='*50}\n")

        return (nth, new_fps, "\n".join(log_output))

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

    RETURN_TYPES = ("AUDIO", "STRING")
    RETURN_NAMES = ("routed_audio", "log")
    FUNCTION = "route"
    CATEGORY = "🔁 Sequential Batcher/Tools"

    def route(self, audio, is_final_cycle):
        log_output = []
        def _log(msg):
            print(msg)
            log_output.append(str(msg))
        if is_final_cycle:
            _log("   -> 🔊 [Audio Router] Ciclo Final: Enviando pista de audio completa al Lip Sync.")
            return (audio, "\n".join(log_output))
        else:
            _log("   -> 🔇 [Audio Router] Ciclo Intermedio: Generando micro-silencio para bypasear el Lip Sync...")

            # Detectar el sample rate del audio original (estándar de ComfyUI es un dict)
            sample_rate = 44100
            if isinstance(audio, dict) and "sample_rate" in audio:
                sample_rate = audio["sample_rate"]

            # Creamos 0.1 segundos de silencio absoluto (1 canal, mínimos samples)
            samples = int(sample_rate * 0.1)
            dummy_waveform = torch.zeros((1, 1, samples), dtype=torch.float32)
            dummy_audio = {"waveform": dummy_waveform, "sample_rate": sample_rate}

            return (dummy_audio, "\n".join(log_output))

@register_node
class VAESafeFramePadder:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "rule": (["WanVideo (Regla 4n+1)", "LTX (Regla 8n+1)"],),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT", "STRING")
    RETURN_NAMES = ("PADDED_IMAGES", "frames_added", "log")
    FUNCTION = "pad"
    CATEGORY = "🔁 Sequential Batcher/Tools"

    def pad(self, images, rule):
        log_output = []
        def _log(msg):
            print(msg)
            log_output.append(str(msg))

        if not isinstance(images, torch.Tensor):
            raise ValueError("[VAESafeFramePadder] Input is not a valid tensor.")

        n_frames = images.shape[0]
        target_frames = n_frames

        if "WanVideo" in rule:
            # 🚀 FIX: Regla 4n+1 para WanVideo (Evita la pérdida de 3 frames en el VAE)
            if n_frames < 5:
                target_frames = 5
            else:
                target_frames = ((n_frames + 2) // 4) * 4 + 1
        elif "LTX" in rule:
            if n_frames < 9:
                target_frames = 9
            else:
                target_frames = ((n_frames + 6) // 8) * 8 + 1

        diff = target_frames - n_frames

        _log(f"\n{'='*50}")
        _log(f"🛡️ [Secuencial Batcher] NODO: VAE Safe Frame Padder")
        _log(f"   -> Frames recibidos: {n_frames}")
        _log(f"   -> Regla aplicada: {rule}")

        if diff > 0:
            _log(f"   -> 🧱 Tensor incompleto. Clonando el último frame {diff} vez/veces...")
            last_frame = images[-1:] # Extraemos el último frame
            padding = last_frame.repeat(diff, 1, 1, 1) # Lo multiplicamos
            images = torch.cat([images, padding], dim=0) # Lo fusionamos al final
            _log(f"   -> ✅ Tensor final acolchado a: {target_frames} frames.")
        else:
            _log(f"   -> ✅ Tensor perfecto. No requiere acolchado.")

        _log(f"{'='*50}\n")
        return (images, diff, "\n".join(log_output))

@register_node
class VHS_Path_Selector:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "vhs_filenames": ("VHS_FILENAMES",),
                "select_file": (["video_with_audio", "video_muted", "png_thumbnail"],),
            }
        }

    # 🔄 Ahora devuelve la cadena y el objeto VHS reordenado
    RETURN_TYPES = ("STRING", "VHS_FILENAMES", "STRING")
    RETURN_NAMES = ("file_path", "vhs_filenames", "log")
    FUNCTION = "select"
    CATEGORY = "🔁 Sequential Batcher/Tools" # 📍 Ubicación corregida

    def select(self, vhs_filenames, select_file):
        log_output = []
        def _log(msg):
            print(msg)
            log_output.append(str(msg))
        try:
            if vhs_filenames is None or not isinstance(vhs_filenames, (list, tuple)) or len(vhs_filenames) < 2:
                _log("⚠️ [Path Selector] Entrada vhs_filenames vacía o inválida.")
                return ("", vhs_filenames, "\n".join(log_output))

            paths = vhs_filenames[1]
            if not isinstance(paths, list) or not paths:
                return ("", vhs_filenames, "\n".join(log_output))

            # Identificación de archivos
            audio_path = next((s for s in paths if isinstance(s, str) and s.endswith("-audio.mp4")), None)
            muted_path = next((s for s in paths if isinstance(s, str) and s.endswith(".mp4") and not s.endswith("-audio.mp4")), None)
            png_path = next((s for s in paths if isinstance(s, str) and s.endswith(".png")), None)

            # Selección del archivo principal (result)
            if select_file == "video_with_audio":
                result = audio_path if audio_path else (muted_path if muted_path else paths[0])
            elif select_file == "video_muted":
                result = muted_path if muted_path else (audio_path if audio_path else paths[0])
            else: # png_thumbnail
                result = png_path if png_path else paths[0]

            # 🪄 REORDENADO: Ponemos el elegido en la posición 0
            new_paths = list(paths)
            if result in new_paths:
                new_paths.remove(result)
            new_paths.insert(0, result)

            # Creamos el nuevo paquete VHS [bool, [lista_reordenada]]
            reordered_vhs = [vhs_filenames[0], new_paths]

            _log(f"📂 [Path Selector] Selección: {select_file} -> {result}")
            return (str(result), reordered_vhs, "\n".join(log_output))

        except Exception as e:
            _log(f"❌ [Path Selector] Error crítico: {e}")
            return ("", vhs_filenames, "\n".join(log_output))

@register_node
class AudioDurationCalculator:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "audio": ("AUDIO",),
            }
        }

    RETURN_TYPES = ("FLOAT", "STRING")
    RETURN_NAMES = ("duration_seconds", "log")
    FUNCTION = "calculate"
    CATEGORY = "🔁 Sequential Batcher/Tools"

    def calculate(self, audio):
        log_output = []
        def _log(msg):
            print(msg)
            log_output.append(str(msg))

        _log(f"\n{'='*50}")
        _log(f"⏱️ [Secuencial Batcher] NODO: Audio Duration Calculator")

        # 1. Validación de seguridad para evitar crashes
        if not isinstance(audio, dict):
            _log("   -> ⚠️ No se detectó un diccionario de audio válido. Devolviendo 0.0")
            _log(f"{'='*50}\n")
            return (0.0, "\n".join(log_output))

        waveform = audio.get("waveform")
        sample_rate = audio.get("sample_rate", 44100)

        if waveform is None:
            _log("   -> ⚠️ No se detectó 'waveform' en el audio. Devolviendo 0.0")
            _log(f"{'='*50}\n")
            return (0.0, "\n".join(log_output))

        # 2. Cálculo matemático
        samples = waveform.shape[-1]
        duration = float(samples) / float(sample_rate)

        _log(f"   -> ✅ Duración calculada: {duration:.3f} segundos ({samples} samples @ {sample_rate}Hz)")
        _log(f"{'='*50}\n")

        return (duration, "\n".join(log_output))

@register_node
class PreciseAudioSlicer:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "audio": ("AUDIO",),
                "skip_frames": ("INT", {"forceInput": True, "tooltip": "Frames que ya han pasado"}),
                "chunk_frames": ("INT", {"forceInput": True, "tooltip": "Frames de este bloque"}),
                "fps": ("FLOAT", {"default": 12.0, "min": 1.0, "max": 120.0, "step": 1.0}),
            }
        }

    RETURN_TYPES = ("AUDIO", "STRING")
    RETURN_NAMES = ("sliced_audio", "log")
    FUNCTION = "slice_audio"
    CATEGORY = "🔁 Sequential Batcher/Tools"

    def slice_audio(self, audio, skip_frames, chunk_frames, fps):
        log_output = []
        def _log(msg):
            print(msg)
            log_output.append(str(msg))

        _log(f"\n{'='*50}")
        _log(f"✂️ [Secuencial Batcher] NODO: Precise Audio Slicer")

        # 1. Programación Defensiva (Fallback a Silencio)
        if not isinstance(audio, dict) or "waveform" not in audio:
            _log("   -> ⚠️ ALERTA: Audio no válido o no conectado. Generando silencio de seguridad...")
            sample_rate = 44100
            duration_sec = chunk_frames / fps
            chunk_samples = int(duration_sec * sample_rate)
            # Creamos un tensor de silencio estéreo
            silent_waveform = torch.zeros((1, 2, chunk_samples), dtype=torch.float32)
            _log(f"{'='*50}\n")
            return ({"waveform": silent_waveform, "sample_rate": sample_rate}, "\n".join(log_output))

        waveform = audio["waveform"]
        sample_rate = audio.get("sample_rate", 44100)

        # 2. Convertir frames a tiempo absoluto
        start_sec = skip_frames / fps
        duration_sec = chunk_frames / fps

        # 3. Convertir tiempo a samples de audio exactos
        start_sample = int(start_sec * sample_rate)
        chunk_samples = int(duration_sec * sample_rate)
        end_sample = start_sample + chunk_samples

        total_samples = waveform.shape[-1]

        _log(f"   -> Sincronizando audio ({chunk_frames} frames a {fps} FPS)")
        _log(f"   -> Tramo de tiempo: {start_sec:.3f}s hasta {start_sec + duration_sec:.3f}s")

        # 4. Cortar el tensor de audio con precisión matemática
        if start_sample >= total_samples:
            _log(f"   -> ⚠️ El tiempo de inicio supera el audio original. Generando silencio perfecto.")
            sliced_waveform = torch.zeros((*waveform.shape[:-1], chunk_samples), dtype=waveform.dtype, device=waveform.device)
        elif end_sample > total_samples:
            _log(f"   -> ⚠️ El bloque excede el final del audio. Rellenando con silencio para mantener la sincronía...")
            valid_audio = waveform[..., start_sample:total_samples]
            padding_needed = end_sample - total_samples
            pad_tensor = torch.zeros((*waveform.shape[:-1], padding_needed), dtype=waveform.dtype, device=waveform.device)
            sliced_waveform = torch.cat([valid_audio, pad_tensor], dim=-1)
        else:
            _log(f"   -> ✅ Corte extraído con éxito ({chunk_samples} samples).")
            sliced_waveform = waveform[..., start_sample:end_sample]

        _log(f"{'='*50}\n")

        return ({"waveform": sliced_waveform, "sample_rate": sample_rate}, "\n".join(log_output))

@register_node
class SaveSceneKeyframe:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE",),
                "file_path": ("STRING", {"forceInput": True, "tooltip": "Ruta desde el Scene Director"})
            }
        }
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("file_path",)
    OUTPUT_NODE = True
    FUNCTION = "save"
    CATEGORY = "🔁 Sequential Batcher/Tools"

    def save(self, image, file_path):
        import os
        import numpy as np
        from PIL import Image

        img_array = 255. * image[0].cpu().numpy()
        img = Image.fromarray(np.clip(img_array, 0, 255).astype(np.uint8))

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        img.save(file_path)
        print(f"💾 [Keyframe Saver] Guardado con éxito en: {file_path}")
        return (file_path,)

@register_node
class LoadSceneKeyframe:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "file_path": ("STRING", {"forceInput": True})
            }
        }
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("IMAGE",)
    FUNCTION = "load"
    CATEGORY = "🔁 Sequential Batcher/Tools"

    def load(self, file_path):
        import os
        import torch
        import numpy as np
        from PIL import Image, ImageOps

        if not os.path.exists(file_path):
            print(f"⚠️ [Keyframe Loader] Archivo no encontrado: {file_path}. Generando tensor negro de seguridad.")
            return (torch.zeros((1, 512, 512, 3), dtype=torch.float32),)

        img = Image.open(file_path)
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        img_tensor = torch.from_numpy(np.array(img).astype(np.float32) / 255.0).unsqueeze(0)
        print(f"📥 [Keyframe Loader] Imagen cargada desde: {file_path}")
        return (img_tensor,)

@register_node
class LTXVSingleFrameInjector:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "vae": ("VAE",),
                "latent": ("LATENT",),
                "image": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("LATENT",)
    RETURN_NAMES = ("latent",)
    FUNCTION = "inject"
    CATEGORY = "🔁 Sequential Batcher/Tools"

    def inject(self, vae, latent, image):
        import torch
        import comfy.utils

        print(f"\n{'='*50}")
        print(f"💉 [Secuencial Batcher] NODO: LTXV Single Frame Injector")

        samples = latent["samples"].clone()

        # Extraer factores de escala del VAE (Típicamente 8x32x32 para LTXV)
        scale_factors = getattr(vae, "downscale_index_formula", (8, 32, 32))
        height_scale_factor = scale_factors[1]
        width_scale_factor = scale_factors[2]

        batch, channels, latent_frames, latent_height, latent_width = samples.shape
        width = latent_width * width_scale_factor
        height = latent_height * height_scale_factor

        if "noise_mask" in latent:
            mask = latent["noise_mask"].clone()
        else:
            mask = torch.ones((batch, 1, latent_frames, 1, 1), dtype=torch.float32, device=samples.device)

        print(f"   -> 📐 Adaptando resolución de la imagen ({image.shape[2]}x{image.shape[1]}) a la del Latent ({width}x{height})")

        # Ajustar resolución de la imagen si no coincide con el latent
        if image.shape[1] != height or image.shape[2] != width:
            pixels = comfy.utils.common_upscale(image.movedim(-1, 1), width, height, "bilinear", "center").movedim(1, -1)
        else:
            pixels = image

        encode_pixels = pixels[:, :, :, :3]

        # Codificar imagen usando el VAE de LTX
        t = vae.encode(encode_pixels)

        # Compatibilidad 4D a 5D (Si el VAE devuelve [B, C, H, W] lo pasamos a [B, C, T, H, W])
        if len(t.shape) == 4:
            t = t.unsqueeze(2)

        latent_idx = 0
        end_index = min(latent_idx + t.shape[2], latent_frames)

        # Inyección directa
        samples[:, :, latent_idx:end_index] = t[:, :, :end_index - latent_idx]
        mask[:, :, latent_idx:end_index] = 0.0  # 0.0 significa "Proteger este frame del ruido"

        print(f"   -> ✅ Imagen inyectada y sellada en el Frame 0 (Índice Latente {latent_idx}).")
        print(f"{'='*50}\n")

        return ({"samples": samples, "noise_mask": mask},)
