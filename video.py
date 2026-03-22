import os
import glob
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

# Variable global en memoria. Se vacía automáticamente al reiniciar ComfyUI.
session_video_list = []

@register_node
class IncrementalVideoStitcher:
    """Une los vídeos de la sesión actual extrayéndolos estrictamente del JSON del VHS."""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                # Recibe la lista/JSON de VHS_VideoCombine
                "trigger": ("VHS_FILENAMES", ),
                "output_filename": ("STRING", {"default": "Pelicula_Final_Sesion.mp4"}),
                "reset_list": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("STRING", )
    RETURN_NAMES = ("final_video_path", )
    OUTPUT_NODE = True
    INPUT_IS_LIST = True
    FUNCTION = "stitch_incremental"
    CATEGORY = "🔁 Sequential Batcher/Video"

    def stitch_incremental(self, trigger, output_filename, reset_list):
        global session_video_list

        # Extraer variables si llegan en lista por INPUT_IS_LIST=True
        do_reset = reset_list[0] if isinstance(reset_list, list) else reset_list

        if do_reset:
            session_video_list.clear()
            print("[Sequential Batcher] Memoria de sesión vaciada (reset_list=True).")

        if not shutil.which("ffmpeg"):
            print("[Sequential Batcher] Error: FFmpeg no está instalado en el sistema.")
            return ("", )

        out_dir = folder_paths.get_output_directory()
        out_name = output_filename[0] if isinstance(output_filename, list) else output_filename

        # 1. Extracción recursiva: buscar cualquier archivo .mp4 dentro del JSON/lista recibido
        current_mp4s = []
        def extract_mp4s(data):
            if isinstance(data, str) and data.endswith(".mp4"):
                current_mp4s.append(data)
            elif isinstance(data, list) or isinstance(data, tuple):
                for item in data:
                    extract_mp4s(item)
            elif isinstance(data, dict):
                for item in data.values():
                    extract_mp4s(item)

        extract_mp4s(trigger)

        # 2. Añadir los vídeos detectados a la memoria de la sesión (evitando duplicados)
        for video_path in current_mp4s:
            # Asegurar ruta absoluta dentro del directorio de salida si es relativa
            if not os.path.isabs(video_path):
                abs_video_path = os.path.join(out_dir, video_path)
            else:
                abs_video_path = video_path

            # Evitamos añadir el propio archivo de salida a la lista si se cuela, y comprobamos existencia
            if not abs_video_path.endswith(out_name) and abs_video_path not in session_video_list and os.path.exists(abs_video_path):
                session_video_list.append(abs_video_path)

        if not session_video_list:
            print("[Sequential Batcher] El JSON de entrada no contenía vídeos nuevos para unir, o la lista está vacía.")
            return ("", )

        # 3. Crear el listado para FFmpeg usando ESTRICTAMENTE la memoria de sesión
        list_file_path = os.path.join(out_dir, "batch_concat_exact_list.txt")
        try:
            with open(list_file_path, 'w', encoding='utf-8') as f:
                for video in session_video_list:
                    f.write(f"file '{video}'\n")

            final_output = os.path.join(out_dir, out_name)
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", list_file_path, "-c", "copy", final_output
            ]

            subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"[Sequential Batcher] Ensamblaje Exacto: {len(session_video_list)} vídeos unidos de la sesión actual.")
        except subprocess.CalledProcessError as e:
            print(f"[Sequential Batcher] Error de FFmpeg: {e.stderr.decode()}")
        finally:
            if os.path.exists(list_file_path):
                os.remove(list_file_path)

        return (final_output, )
