import os
import shutil
import subprocess
import folder_paths
from . import register_node

@register_node
class FFmpegVideoStitcher:
    """Toma una lista de rutas de vídeo generadas en un Batch secuencial, crea un TXT/CSV y los une con FFmpeg."""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                # VHS_FILENAMES proviene del nodo de guardado de vídeo
                "video_paths": ("VHS_FILENAMES", ),
                "output_filename": ("STRING", {"default": "Video_SCAIL_Completo.mp4"}),
            },
        }

    RETURN_TYPES = ("STRING", )
    RETURN_NAMES = ("final_video_path", )
    # Al ser INPUT_IS_LIST = True, ComfyUI acumulará los resultados de todos los
    # pasos del Batch y ejecutará esto al final del todo.
    INPUT_IS_LIST = True
    FUNCTION = "stitch_videos"
    CATEGORY = "🔁 Sequential Batcher/Video"

    def stitch_videos(self, video_paths, output_filename):
        # Aplanar la lista de rutas, ya que VHS_FILENAMES suele venir anidado
        flat_paths = []
        for path_group in video_paths:
            for p in path_group:
                if isinstance(p, str) and p.endswith(".mp4"):
                    flat_paths.append(p)

        # Como INPUT_IS_LIST es True, output_filename viene como lista, tomamos el primero
        out_name = output_filename[0] if isinstance(output_filename, list) else output_filename

        if not flat_paths:
            return ("Error: No se encontraron vídeos para unir en el Batch.", )

        if not shutil.which("ffmpeg"):
            raise FileNotFoundError("FFmpeg is not installed or not found in system PATH. Please install FFmpeg to stitch videos.")

        # 1. Crear el archivo de lista de concatenación en el directorio de salida estándar
        output_dir = folder_paths.get_output_directory()
        list_file_path = os.path.join(output_dir, "batch_concat_list.txt")

        with open(list_file_path, 'w', encoding='utf-8') as f:
            for video in sorted(flat_paths): # Mantener el orden de los chunks
                f.write(f"file '{os.path.abspath(video)}'\n")

        # 2. Definir ruta final
        final_output = os.path.join(output_dir, out_name)

        # 3. FFmpeg en modo copia (rápido y sin recodificar)
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", list_file_path, "-c", "copy", final_output
        ]

        try:
            subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"[Sequential Batcher] Vídeo final ensamblado exitosamente: {final_output}")
        except subprocess.CalledProcessError as e:
            print(f"[Sequential Batcher] Error de FFmpeg: {e.stderr.decode()}")
            raise e

        return (final_output, )
