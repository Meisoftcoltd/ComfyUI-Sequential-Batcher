import os
import torch
import torchaudio
import folder_paths
import nodes
import time
from . import register_node

@register_node
class AutoLoopCalculator:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "source_frame_count": ("INT", {"forceInput": True}),
                "target_frames_per_loop": ("INT", {"default": 50, "min": 1, "max": 10000}),
                "select_every_nth": ("INT", {"default": 1, "min": 1, "max": 100}), # NUEVO PARÁMETRO
                "current_loop_index": ("INT", {"forceInput": True}),
            }
        }

    # Ahora devolvemos 3 valores para el cargador de vídeo
    RETURN_TYPES = ("INT", "INT", "INT")
    RETURN_NAMES = ("chunk_frames", "skip_frames", "select_every_nth")
    FUNCTION = "calculate"
    CATEGORY = "🔁 Sequential Batcher/Video"

    def calculate(self, source_frame_count, target_frames_per_loop, select_every_nth, current_loop_index):
        import math
        from . import loop

        if source_frame_count <= 0 or target_frames_per_loop <= 0:
            loop.global_total_loops = 1
            return (max(1, source_frame_count), 0, select_every_nth)

        # 1. Calcular los frames efectivos reales que vamos a procesar
        effective_source_frames = math.ceil(source_frame_count / select_every_nth)

        # 2. La matemática proporcional del usuario SOBRE LOS FRAMES EFECTIVOS
        total_loops = math.ceil(effective_source_frames / target_frames_per_loop)
        base_frames = effective_source_frames // total_loops
        remainder = effective_source_frames % total_loops

        plan = []
        for i in range(total_loops):
            plan.append(base_frames + (1 if i < remainder else 0))

        safe_index = min(current_loop_index, total_loops - 1)
        chunk_frames = plan[safe_index]

        # 3. Calcular el salto de frames originales
        # Sumamos los frames efectivos de ciclos anteriores y los multiplicamos por el salto
        effective_skip = sum(plan[:safe_index])
        skip_frames = effective_skip * select_every_nth

        # Guardamos en la memoria fantasma
        loop.global_total_loops = total_loops

        print(f"\n📊 [Auto Calculator] Video Original: {source_frame_count} frames | Stride: {select_every_nth}")
        print(f"   -> Frames efectivos a procesar: {effective_source_frames}")
        print(f"   -> Planificando {total_loops} ciclos: {plan}")
        print(f"   -> 🚀 Ciclo {current_loop_index}: Cargando {chunk_frames} frames (Saltando {skip_frames} frames de origen)")

        return (chunk_frames, skip_frames, select_every_nth)

@register_node
class LoadVideoWithSourceAudio:
    @classmethod
    def INPUT_TYPES(cls):
        vhs_class = nodes.NODE_CLASS_MAPPINGS.get("VHS_LoadVideo")
        if vhs_class:
            return vhs_class.INPUT_TYPES()
        return {"required": {"video": ("STRING", {"image_upload": True})}}

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

        first_frame = None
        if len(res) > 0 and res[0] is not None:
            first_frame = res[0][0:1]

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
            }
        }

    RETURN_TYPES = ("IMAGE", "AUDIO")
    RETURN_NAMES = ("ALL_IMAGES", "AUDIO_OUT")
    FUNCTION = "stitch"
    CATEGORY = "🔁 Sequential Batcher/Video"

    def stitch(self, images, audio, current_loop_index):
        from . import loop
        total_loops = loop.global_total_loops # Leemos la variable global

        cache_dir = os.path.join(folder_paths.get_temp_directory(), "wan_stitcher_cache")
        os.makedirs(cache_dir, exist_ok=True)

        # 1. Guardar el lote completo actual en disco
        path = os.path.join(cache_dir, f"batch_{current_loop_index:04d}.pt")
        torch.save(images.cpu(), path)
        print(f"🎞️ [Stitcher] Lote {current_loop_index} guardado en disco.")

        if current_loop_index < total_loops - 1:
            # 🛠️ TRUCO MAESTRO: En lugar de un frame negro, enviamos el primer frame real del lote.
            # Mantiene los cables vivos y establece la resolución correcta para RIFE/Upscale.
            preview_frame = images[0:1]
            return (preview_frame, None)

        # 2. Ciclo final: Ensamblar todos los lotes
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
