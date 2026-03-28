import os
import time
import torch
import torchaudio
import folder_paths
import nodes
from . import register_node

@register_node
class WanFrameValidator:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"target_frames": ("INT", {"default": 49, "min": 1, "max": 10000})}}
    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("valid_frames",)
    FUNCTION = "validate"
    CATEGORY = "🔁 Sequential Batcher/Video"

    def validate(self, target_frames):
        k = (target_frames - 1) // 4
        corrected_frames = (4 * k) + 1
        print(f"🛡️ [Wan Validator] Ajustado a: {corrected_frames}")
        return (max(1, corrected_frames), )

@register_node
class LoadVideoWithSourceAudio:
    @classmethod
    def INPUT_TYPES(s):
        vhs_class = nodes.NODE_CLASS_MAPPINGS.get("VHS_LoadVideo")
        if vhs_class:
            inputs = vhs_class.INPUT_TYPES()
            # Forzamos el botón de subida
            if "video" in inputs["required"]:
                v_type, v_params = inputs["required"]["video"]
                v_params["video_upload"] = True
                inputs["required"]["video"] = (v_type, v_params)
            return inputs
        return {"required": {"video": ("VIDEO", {"video_upload": True})}}

    RETURN_TYPES = ("IMAGE", "INT", "AUDIO", "VHS_VIDEOINFO", "AUDIO")
    RETURN_NAMES = ("IMAGE", "frame_count", "audio", "video_info", "source_audio")
    FUNCTION = "load_video_with_audio"
    CATEGORY = "🔁 Sequential Batcher/Video"

    @classmethod
    def IS_CHANGED(s, video, **kwargs):
        path = folder_paths.get_annotated_filepath(video)
        return os.path.getmtime(path) if os.path.exists(path) else time.time()

    @classmethod
    def VALIDATE_INPUTS(s, video, **kwargs):
        path = folder_paths.get_annotated_filepath(video)
        return True if os.path.exists(path) else f"Vídeo no encontrado: {path}"

    def load_video_with_audio(self, **kwargs):
        vhs_class = nodes.NODE_CLASS_MAPPINGS.get("VHS_LoadVideo")
        vhs_instance = vhs_class()

        # Filtro estricto de parámetros para evitar el error 'force_rate'
        vhs_keys = ["video", "force_rate", "frame_load_cap", "skip_first_frames",
                    "select_every_nth", "meta_batch", "vae", "format"]
        vhs_kwargs = {k: v for k, v in kwargs.items() if k in vhs_keys}

        vhs_output = vhs_instance.load_video(**vhs_kwargs)

        if isinstance(vhs_output, dict):
            res, ui = vhs_output["result"], vhs_output.get("ui", {})
        else:
            res, ui = vhs_output, {}

        # Extraer audio fuente completo
        video_path = folder_paths.get_annotated_filepath(kwargs.get("video"))
        source_audio = None
        try:
            waveform, sample_rate = torchaudio.load(video_path)
            source_audio = {"waveform": waveform.unsqueeze(0), "sample_rate": sample_rate}
        except Exception: pass

        return {"ui": ui, "result": (res[0], res[1], res[2], res[3], source_audio)}

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
        cache_dir = os.path.join(folder_paths.get_temp_directory(), "wan_stitcher")
        os.makedirs(cache_dir, exist_ok=True)

        # Guardar tensor actual en CPU para liberar VRAM
        path = os.path.join(cache_dir, f"b_{current_loop_index:04d}.pt")
        torch.save(images.cpu(), path)
        print(f"🎞️ [Stitcher] Lote {current_loop_index} guardado.")

        if current_loop_index < total_loops - 1:
            # Ciclos intermedios: Devolvemos micro-tensor para no romper validación
            return (torch.zeros((1, 8, 8, 3)), None)

        # Ciclo final: Concatenar todo
        print(f"🚀 [Stitcher] Ensamblando video final...")
        all_tensors = []
        for i in range(total_loops):
            p = os.path.join(cache_dir, f"b_{i:04d}.pt")
            if os.path.exists(p):
                all_tensors.append(torch.load(p))
                os.remove(p)

        return (torch.cat(all_tensors, dim=0), audio)
