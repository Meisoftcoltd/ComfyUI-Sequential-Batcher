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
        return {"required": {"target_frames": ("INT", {"default": 49, "min": 1, "max": 10000})}}
    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("valid_frames",)
    FUNCTION = "validate"
    CATEGORY = "🔁 Sequential Batcher/Video"

    def validate(self, target_frames):
        k = (target_frames - 1) // 4
        corrected_frames = (4 * k) + 1
        print(f"🛡️ [Wan Validator] Fotogramas ajustados: {corrected_frames}")
        return (max(1, corrected_frames), )

@register_node
class LoadVideoWithSourceAudio:
    @classmethod
    def INPUT_TYPES(cls):
        # 1. Obtenemos los inputs de VHS dinámicamente en tiempo de ejecución de la UI
        vhs_class = nodes.NODE_CLASS_MAPPINGS.get("VHS_LoadVideo")
        if vhs_class:
            inputs = vhs_class.INPUT_TYPES()
            if "video" in inputs.get("required", {}):
                video_in = inputs["required"]["video"]
                # Desempaquetado seguro
                if isinstance(video_in, (tuple, list)) and len(video_in) >= 2:
                    v_type, v_params = video_in[0], video_in[1]
                else:
                    v_type = video_in if isinstance(video_in, str) else "VIDEO"
                    v_params = {}

                v_params["video_upload"] = True
                inputs["required"]["video"] = (v_type, v_params)
            return inputs
        return {"required": {"video": ("VIDEO", {"video_upload": True})}}

    RETURN_TYPES = ("IMAGE", "INT", "AUDIO", "VHS_VIDEOINFO", "AUDIO")
    RETURN_NAMES = ("IMAGE", "frame_count", "audio", "video_info", "source_audio")
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
            raise Exception("❌ VideoHelperSuite no está instalado o cargado.")

        vhs_instance = vhs_class()

        # 2. EL TRUCO MÁGICO: Preguntamos a VHS qué parámetros exactos acepta en esta versión
        vhs_inputs = vhs_class.INPUT_TYPES()
        allowed_keys = set()
        for cat in ["required", "optional", "hidden"]:
            if cat in vhs_inputs:
                allowed_keys.update(vhs_inputs[cat].keys())

        # 3. Filtramos los kwargs estrictamente por lo que VHS nos acaba de decir
        vhs_kwargs = {k: v for k, v in kwargs.items() if k in allowed_keys}

        # 4. Ejecutamos VHS de forma segura
        vhs_output = vhs_instance.load_video(**vhs_kwargs)

        # Extraemos retornos
        if isinstance(vhs_output, dict):
            res = list(vhs_output.get("result", []))
            ui = vhs_output.get("ui", {})
        else:
            res = list(vhs_output)
            ui = {}

        # 5. Extraer audio original
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

        # Añadimos la quinta salida (el source audio)
        if len(res) >= 4:
            res = [res[0], res[1], res[2], res[3], source_audio]
        else:
            res.append(source_audio)

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
