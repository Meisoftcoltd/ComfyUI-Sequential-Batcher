import os
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
        print(f"🛡️ [Wan Validator] Fotogramas ajustados: {corrected_frames}")
        return (max(1, corrected_frames), )

# 1. Obtenemos la clase original de VHS para heredar de ella
vhs_load_video_class = nodes.NODE_CLASS_MAPPINGS.get("VHS_LoadVideo")

if vhs_load_video_class:
    @register_node
    class LoadVideoWithSourceAudio(vhs_load_video_class):
        # Heredamos todo de VHS, solo añadimos nuestra salida extra
        RETURN_TYPES = vhs_load_video_class.RETURN_TYPES + ("AUDIO",)

        # Intentamos heredar los nombres si existen, si no, usamos los por defecto + el nuestro
        _base_names = getattr(vhs_load_video_class, "RETURN_NAMES", ("IMAGE", "frame_count", "audio", "video_info"))
        RETURN_NAMES = _base_names + ("source_audio",)

        FUNCTION = "load_video_with_source_audio"
        CATEGORY = "🔁 Sequential Batcher/Video"

        def load_video_with_source_audio(self, **kwargs):
            # 1. Ejecutamos la función original del padre (VHS) tal cual
            vhs_func_name = vhs_load_video_class.FUNCTION
            vhs_func = getattr(self, vhs_func_name)
            vhs_output = vhs_func(**kwargs)

            # 2. Gestionamos si VHS devolvió la interfaz de vista previa o solo resultados
            if isinstance(vhs_output, dict):
                res = list(vhs_output["result"])
                ui = vhs_output.get("ui", {})
            else:
                res = list(vhs_output)
                ui = {}

            # 3. Nuestra lógica añadida: Extraer audio fuente de forma segura
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

            # 4. Añadimos el audio al final de la lista original de salidas
            res.append(source_audio)

            # 5. Devolvemos el paquete exactamente en el formato que espera ComfyUI
            if isinstance(vhs_output, dict):
                return {"ui": ui, "result": tuple(res)}
            else:
                return tuple(res)
else:
    print("⚠️ [Advertencia] VideoHelperSuite no encontrado. LoadVideoWithSourceAudio no funcionará.")


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
            # Micro-tensor (8x8) para mantener cables activos sin petar la memoria
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
