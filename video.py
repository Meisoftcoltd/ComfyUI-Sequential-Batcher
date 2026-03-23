import os
import glob
import shutil
import subprocess
import folder_paths
from . import register_node


@register_node
class WanFrameValidator:
    """Valida y corrige el número de fotogramas para que encaje en la fórmula 4k+1 de Wan."""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "target_frames": ("INT", {"default": 49, "min": 1, "max": 10000, "step": 1}),
            },
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("valid_frames",)
    FUNCTION = "validate"
    CATEGORY = "🔁 Sequential Batcher/Video"

    def validate(self, target_frames):
        # 1. Aplicamos la fórmula para redondear a la baja al 4k+1 más cercano
        k = (target_frames - 1) // 4
        corrected_frames = (4 * k) + 1

        # 2. Límite de seguridad por si ponen 0 o negativo
        if corrected_frames < 1:
            corrected_frames = 1

        # 3. Chivato por consola
        if corrected_frames != target_frames:
            print(f"🛡️ [Wan Validator] Aviso: {target_frames} no es válido para Wan. Redondeado a la baja a -> {corrected_frames}")
        else:
            print(f"🛡️ [Wan Validator] Fotogramas perfectos: {corrected_frames}")

        return (corrected_frames, )

session_video_list = []

@register_node
class IncrementalVideoStitcher:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "trigger": ("VHS_FILENAMES", ),
                "output_prefix": ("STRING", {"default": "SCAIL_Final"}),
                "current_loop_index": ("INT", {"default": 0, "min": 0, "max": 10000}),
            },
        }

    RETURN_TYPES = ("STRING", )
    RETURN_NAMES = ("final_video_path", )
    OUTPUT_NODE = True
    INPUT_IS_LIST = True
    FUNCTION = "stitch_incremental"
    CATEGORY = "🔁 Sequential Batcher/Video"

    def stitch_incremental(self, trigger, output_prefix, current_loop_index):
        global session_video_list

        out_dir = folder_paths.get_output_directory()
        prefix = output_prefix[0] if isinstance(output_prefix, list) else output_prefix
        loop_idx = current_loop_index[0] if isinstance(current_loop_index, list) else current_loop_index

        print(f"\n{'='*50}")
        print(f"🎞️ [DEBUG] NODO: Incremental Auto-Stitcher")
        print(f"   -> Ciclo actual: {loop_idx} | Prefix: {prefix}")

        if loop_idx == 0:
            print(f"   -> 🧹 Limpiando lista de vídeos de sesiones anteriores.")
            session_video_list.clear()

        current_mp4s = []
        def extract_mp4s(data):
            if isinstance(data, str) and data.endswith(".mp4"):
                current_mp4s.append(data)
            elif isinstance(data, (list, tuple)):
                for item in data: extract_mp4s(item)
            elif isinstance(data, dict):
                for item in data.values(): extract_mp4s(item)
        extract_mp4s(trigger)

        for v in current_mp4s:
            abs_path = v if os.path.isabs(v) else os.path.join(out_dir, v)
            if abs_path not in session_video_list and os.path.exists(abs_path):
                session_video_list.append(abs_path)
                print(f"   -> ➕ Añadido al ensamblaje: {os.path.basename(abs_path)}")

        print(f"   -> 📦 Total de vídeos a ensamblar: {len(session_video_list)}")

        if not session_video_list:
            print(f"{'='*50}\n")
            return ("", )

        list_file_path = os.path.join(out_dir, "batch_concat_list.txt")
        out_name = f"{prefix}_{loop_idx:04d}.mp4"
        final_output = os.path.join(out_dir, out_name)

        try:
            with open(list_file_path, 'w', encoding='utf-8') as f:
                for video in session_video_list: f.write(f"file '{video}'\n")

            ffmpeg_cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file_path, "-c", "copy", final_output]
            subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"   -> ✅ Ensamblaje progresivo exitoso: {out_name}")
        except Exception as e:
            print(f"   -> ❌ Error FFmpeg: {e}")
        finally:
            if os.path.exists(list_file_path): os.remove(list_file_path)

        print(f"{'='*50}\n")
        return (final_output, )