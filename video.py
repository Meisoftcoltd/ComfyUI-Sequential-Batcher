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
                "target_frames_per_loop": ("INT", {"default": 50, "min": 1, "max": 10000}),
                "select_every_nth": ("INT", {"default": 1, "min": 1, "max": 100}),
                "current_loop_index": ("INT", {"forceInput": True}),
            }
        }

    RETURN_TYPES = ("INT", "INT", "INT")
    RETURN_NAMES = ("chunk_frames", "skip_frames", "select_every_nth")
    FUNCTION = "calculate"
    CATEGORY = "🔁 Sequential Batcher/Video"

    def calculate(self, target_frames_per_loop, select_every_nth, current_loop_index):
        import math
        from . import loop

        # Guardamos la config para que el Cargador la use luego en el Ciclo 0
        loop.global_target_frames = target_frames_per_loop
        loop.global_stride = select_every_nth

        source_frames = loop.global_source_frame_count

        # CICLO 0: Disparo a ciegas (El Explorador)
        if current_loop_index == 0 or source_frames == 0:
            print(f"\n📊 [Auto Calculator] Ciclo 0 (Explorador). Solicitando {target_frames_per_loop} frames a ciegas.")
            return (target_frames_per_loop, 0, select_every_nth)

        # CICLOS > 0: Matemática proporcional para el resto del vídeo
        effective_total = math.ceil(source_frames / select_every_nth)

        if effective_total <= target_frames_per_loop:
            return (target_frames_per_loop, 0, select_every_nth)

        remaining_effective = effective_total - target_frames_per_loop
        remaining_loops = math.ceil(remaining_effective / target_frames_per_loop)

        base_frames = remaining_effective // remaining_loops
        remainder = remaining_effective % remaining_loops

        plan = [target_frames_per_loop] # El Ciclo 0 ya se llevó su parte
        for i in range(remaining_loops):
            plan.append(base_frames + (1 if i < remainder else 0))

        safe_index = min(current_loop_index, len(plan) - 1)
        chunk_frames = plan[safe_index]

        effective_skip = sum(plan[:safe_index])
        skip_frames = effective_skip * select_every_nth

        print(f"\n📊 [Auto Calculator] Video Original: {source_frames} frames | Efectivos: {effective_total}")
        print(f"   -> Plan maestro: {plan}")
        print(f"   -> 🚀 Ciclo {current_loop_index}: Cargando {chunk_frames} frames (Saltando {skip_frames})")

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

        # 🎯 NUEVO: INTERCEPTACIÓN DEL TOTAL DE FRAMES
        video_info_dict = res[3] if len(res) > 3 else {}
        source_frame_count = video_info_dict.get("source_frame_count", 0) if isinstance(video_info_dict, dict) else 0

        if source_frame_count > 0:
            from . import loop
            import math
            loop.global_source_frame_count = source_frame_count

            # Solo fijamos el número total de ciclos durante el Ciclo 0
            if loop.global_loop_index == 0:
                target = loop.global_target_frames
                stride = loop.global_stride
                eff_total = math.ceil(source_frame_count / stride)

                if eff_total <= target:
                    loop.global_total_loops = 1
                else:
                    remaining = eff_total - target
                    rem_loops = math.ceil(remaining / target)
                    loop.global_total_loops = 1 + rem_loops

                print(f"🎥 [Video Loader] Interceptado: {source_frame_count} frames. Total Loops fijado en: {loop.global_total_loops}")

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
