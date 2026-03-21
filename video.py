import os
import shutil
import subprocess
import folder_paths
from . import register_node

@register_node
class FFmpegVideoStitcher:
    """Nodo final: Espera a que termine todo el lote secuencial y une los vídeos con FFmpeg."""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "video_paths": ("VHS_FILENAMES", ),
                "output_filename": ("STRING", {"default": "SCAIL_Final_Completo.mp4"}),
            },
        }

    RETURN_TYPES = ("STRING", )
    RETURN_NAMES = ("final_video_path", )

    # CRÍTICO: Obliga a ComfyUI a recolectar todas las ejecuciones del loop antes de actuar.
    INPUT_IS_LIST = True
    FUNCTION = "stitch_videos"
    CATEGORY = "🔁 Sequential Batcher/Video"

    def stitch_videos(self, video_paths, output_filename):
        # 1. Comprobación estricta de dependencias
        if not shutil.which("ffmpeg"):
            raise Exception("FFmpeg no está instalado o no se encuentra en el PATH del sistema. Por favor, instálalo para unir los vídeos.")

        # Ensure video_paths is a valid list before iteration
        if not video_paths or not isinstance(video_paths, list):
            raise Exception("Error: 'video_paths' inválido. Se esperaba una lista.")

        # 2. Aplanar la lista de rutas generadas (VHS_FILENAMES genera listas anidadas)
        flat_paths = []
        for path_group in video_paths:
            if not isinstance(path_group, list):
                # Sometimes path_group might be a string directly depending on how it's passed
                if isinstance(path_group, str) and path_group.endswith(".mp4"):
                    flat_paths.append(path_group)
                continue

            for p in path_group:
                if isinstance(p, str) and p.endswith(".mp4"):
                    flat_paths.append(p)

        # Ensure output_filename is safe to read
        if isinstance(output_filename, list):
            if not output_filename:
                out_name = "SCAIL_Final_Completo.mp4"
            else:
                out_name = output_filename[0]
        else:
            out_name = output_filename

        if not isinstance(out_name, str) or not out_name.strip():
             out_name = "SCAIL_Final_Completo.mp4"

        # Add .mp4 extension if not present
        if not out_name.lower().endswith('.mp4'):
            out_name += '.mp4'

        if not flat_paths:
            return ("Error: No se encontraron vídeos .mp4 para unir.", )

        # 3. Preparar directorio de salida estándar
        out_dir = folder_paths.get_output_directory()
        list_file_path = os.path.join(out_dir, "batch_concat_list.txt")

        # 4. Crear archivo de concatenación seguro para FFmpeg
        with open(list_file_path, 'w', encoding='utf-8') as f:
            for video in sorted(flat_paths):
                # Usar rutas absolutas aseguradas
                f.write(f"file '{os.path.abspath(video)}'\n")

        # 5. Ejecutar unión sin recodificación (Copy codec)
        final_output = os.path.join(out_dir, out_name)
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", list_file_path, "-c", "copy", final_output
        ]

        try:
            subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"[Sequential Batcher] Vídeo ensamblado exitosamente en: {final_output}")
        except subprocess.CalledProcessError as e:
            raise Exception(f"Error crítico de FFmpeg al unir los fragmentos: {e.stderr.decode()}")

        return (final_output, )
