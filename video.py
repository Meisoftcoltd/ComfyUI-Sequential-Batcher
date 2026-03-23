import os
import glob
import shutil
import subprocess
import torchaudio
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
            "optional": {
                "audio": ("AUDIO", ), # Nueva entrada de audio opcional
            }
        }

    RETURN_TYPES = ("STRING", )
    RETURN_NAMES = ("final_video_path", )
    OUTPUT_NODE = True
    INPUT_IS_LIST = True
    FUNCTION = "stitch_incremental"
    CATEGORY = "🔁 Sequential Batcher/Video"

    def stitch_incremental(self, trigger, output_prefix, current_loop_index, audio=None):
        if not trigger or trigger[0] is None:
            raise ValueError("❌ ERROR CRÍTICO: El nodo 'Incremental Auto-Stitcher' no recibe archivos de vídeo. Conecta la salida 'filenames' de tu Video Combine.")

        if not current_loop_index or current_loop_index[0] is None:
            raise ValueError("❌ ERROR CRÍTICO: El nodo 'Incremental Auto-Stitcher' necesita el cable de 'current_loop_index' para gestionar la sesión.")

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
        temp_concat = os.path.join(out_dir, f"temp_concat_video_{loop_idx:04d}.mp4")
        final_output = os.path.join(out_dir, out_name)

        try:
            with open(list_file_path, 'w', encoding='utf-8') as f:
                for video in session_video_list: f.write(f"file '{video}'\n")

            # Paso 1: Ensamblar los vídeos de forma silenciosa
            ffmpeg_cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file_path, "-c", "copy", temp_concat]
            subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Paso 2: Procesar e inyectar el Audio (si existe)
            has_audio = audio is not None and isinstance(audio, list) and len(audio) > 0 and audio[0] is not None
            if has_audio:
                print(f"   -> 🎵 Audio detectado. Sincronizando y multiplexando...")

                audio_data = audio[0]
                waveform = audio_data.get("waveform")
                sample_rate = audio_data.get("sample_rate", 44100)

                if waveform is not None:
                    # ComfyUI a veces envía el tensor como [Batch, Canales, Muestras]. Lo pasamos a [Canales, Muestras]
                    if waveform.dim() == 3:
                        waveform = waveform.squeeze(0)

                    temp_audio_path = os.path.join(out_dir, f"temp_audio_{loop_idx:04d}.wav")
                    torchaudio.save(temp_audio_path, waveform, sample_rate)

                    # Multiplexamos usando -shortest para que el audio se corte donde termina el vídeo
                    ffmpeg_mux_cmd = [
                        "ffmpeg", "-y",
                        "-i", temp_concat,
                        "-i", temp_audio_path,
                        "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "192k",
                        "-shortest", final_output
                    ]
                    subprocess.run(ffmpeg_mux_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                    if os.path.exists(temp_audio_path): os.remove(temp_audio_path)
                    if os.path.exists(temp_concat): os.remove(temp_concat)
                    print(f"   -> ✅ Ensamblaje progresivo CON AUDIO exitoso: {out_name}")
                else:
                    shutil.move(temp_concat, final_output)
                    print(f"   -> ⚠️ Audio detectado pero sin waveform. Ensamblaje sin audio: {out_name}")
            else:
                # Si no hay audio conectado, simplemente renombramos el archivo temporal
                shutil.move(temp_concat, final_output)
                print(f"   -> ✅ Ensamblaje progresivo exitoso (Mudo): {out_name}")

        except Exception as e:
            print(f"   -> ❌ Error FFmpeg: {e}")
        finally:
            if os.path.exists(list_file_path): os.remove(list_file_path)

        print(f"{'='*50}\n")
        return (final_output, )