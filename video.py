import os
import torch
import torchaudio
import folder_paths
import nodes
import time
from . import register_node

@register_node
class WanFrameValidator:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                # target_frames se queda como un campo numérico en el nodo
                "target_frames": ("INT", {"default": 49, "min": 1, "max": 10000}),
                # current_loop_index se fuerza como un punto de conexión de entrada (cable)
                "current_loop_index": ("INT", {"default": 0, "forceInput": True}),
            }
        }

    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("valid_frames", "skip_frames")
    FUNCTION = "validate"
    CATEGORY = "🔁 Sequential Batcher/Video"

    def validate(self, target_frames, current_loop_index):
        # 1. Validar la regla estricta de WanVideo (4k+1)
        k = (target_frames - 1) // 4
        corrected_frames = max(1, (4 * k) + 1)

        # 2. Calcular cuántos frames debe saltar el cargador en este ciclo
        skip_frames = current_loop_index * corrected_frames

        print(f"🛡️ [Wan Validator] Lote: {corrected_frames} frames | Saltar: {skip_frames} frames")

        return (corrected_frames, skip_frames)

@register_node
class LoadVideoWithSourceAudio:
    @classmethod
    def INPUT_TYPES(cls):
        vhs_class = nodes.NODE_CLASS_MAPPINGS.get("VHS_LoadVideo")
        if vhs_class:
            return vhs_class.INPUT_TYPES()
        return {"required": {"video": ("STRING", {"image_upload": True})}}

    # 1. Añadimos un nuevo "IMAGE" al final de las salidas
    RETURN_TYPES = ("IMAGE", "INT", "AUDIO", "VHS_VIDEOINFO", "AUDIO", "IMAGE")
    RETURN_NAMES = ("IMAGE", "frame_count", "audio", "video_info", "source_audio", "first_frame")
    FUNCTION = "load_video_with_audio"
    CATEGORY = "🔁 Sequential Batcher/Video"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time()

    @classmethod
    def VALIDATE_INPUTS(cls, video, **kwargs):
        path = folder_paths.get_annotated_filepath(video)
        return True if os.path.exists(path) else f"Archivo no encontrado: {path}"

    def load_video_with_audio(self, **kwargs):
        vhs_class = nodes.NODE_CLASS_MAPPINGS.get("VHS_LoadVideo")
        if not vhs_class:
            raise Exception("❌ VideoHelperSuite no está instalado.")

        vhs_instance = vhs_class()

        vhs_inputs = vhs_class.INPUT_TYPES()
        allowed_keys = set()
        for cat in ["required", "optional", "hidden"]:
            if cat in vhs_inputs:
                allowed_keys.update(vhs_inputs[cat].keys())

        vhs_kwargs = {k: v for k, v in kwargs.items() if k in allowed_keys}
        vhs_output = vhs_instance.load_video(**vhs_kwargs)

        if isinstance(vhs_output, dict):
            res = list(vhs_output.get("result", []))
            ui = vhs_output.get("ui", {})
        else:
            res = list(vhs_output)
            ui = {}

        # 2. Extraer audio original
        raw_video = kwargs.get("video")
        video_name = raw_video[0] if isinstance(raw_video, (list, tuple)) else raw_video
        video_path = folder_paths.get_annotated_filepath(video_name) if video_name else ""

        source_audio = None
        try:
            if os.path.exists(video_path):
                waveform, sample_rate = torchaudio.load(video_path)
                source_audio = {"waveform": waveform.unsqueeze(0), "sample_rate": sample_rate}
        except Exception as e:
            print(f"⚠️ [LoadVideo] Error extrayendo source_audio: {e}")

        # 3. Extraer el primer frame del tensor de vídeo
        first_frame = None
        if len(res) > 0 and res[0] is not None:
            # res[0] tiene forma (Lote, Alto, Ancho, Canales).
            # [0:1] coge el primer elemento pero mantiene el formato (1, Alto, Ancho, Canales)
            first_frame = res[0][0:1]

        # 4. Construimos el paquete final de 6 salidas
        if len(res) >= 4:
            res = [res[0], res[1], res[2], res[3], source_audio, first_frame]
        else:
            res.append(source_audio)
            res.append(first_frame)

        return {"ui": ui, "result": tuple(res)}

@register_node
class IncrementalVideoStitcher:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "audio": ("AUDIO",),
                "current_loop_index": ("INT", {"default": 0}),
                "total_loops": ("INT", {"default": 1}),
            }
        }

    RETURN_TYPES = ("IMAGE", "AUDIO")
    RETURN_NAMES = ("ALL_IMAGES", "AUDIO_OUT")
    FUNCTION = "stitch"
    CATEGORY = "🔁 Sequential Batcher/Video"

    def stitch(self, images, audio, current_loop_index, total_loops):
        cache_dir = os.path.join(folder_paths.get_temp_directory(), "wan_stitcher_cache")
        os.makedirs(cache_dir, exist_ok=True)

        path = os.path.join(cache_dir, f"batch_{current_loop_index:04d}.pt")
        torch.save(images.cpu(), path)
        print(f"🎞️ [Stitcher] Lote {current_loop_index} guardado en disco.")

        if current_loop_index < total_loops - 1:
            return (torch.zeros((1, 8, 8, 3)), None)

        print(f"📦 [Stitcher] Ensamblando todos los lotes de vídeo...")
        all_tensors = []
        for i in range(total_loops):
            p = os.path.join(cache_dir, f"batch_{i:04d}.pt")
            if os.path.exists(p):
                all_tensors.append(torch.load(p))
                try: os.remove(p)
                except: pass

        final_images = torch.cat(all_tensors, dim=0)
        print(f"✅ [Stitcher] Vídeo completado: {final_images.shape[0]} frames.")

        return (final_images, audio)
