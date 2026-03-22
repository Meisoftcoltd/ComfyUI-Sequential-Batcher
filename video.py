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
                "current_loop_index": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1}),
            },
        }

    RETURN_TYPES = ("STRING", )
    RETURN_NAMES = ("final_video_path", )
    OUTPUT_NODE = True
    INPUT_IS_LIST = True
    FUNCTION = "stitch_incremental"
    CATEGORY = "🔁 Sequential Batcher/Video"

    def stitch_incremental(self, trigger, output_filename, current_loop_index):
        global session_video_list

        if not shutil.which("ffmpeg"):
            print("[Sequential Batcher] Error de FFmpeg: No está instalado.")
            return ("", )

        out_dir = folder_paths.get_output_directory()
        out_name = output_filename[0] if isinstance(output_filename, list) else output_filename

        # Extracción segura obligatoria por INPUT_IS_LIST = True
        loop_idx = current_loop_index[0] if isinstance(current_loop_index, list) else current_loop_index

        # LÓGICA NATIVA: Si es el primer ciclo, vaciamos la lista
        is_first_cycle = (loop_idx == 0)

        if is_first_cycle:
            print(f"[Sequential Batcher] Auto-Stitcher: Ciclo {loop_idx}. Vaciando memoria de la sesión.")
            session_video_list.clear()

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
