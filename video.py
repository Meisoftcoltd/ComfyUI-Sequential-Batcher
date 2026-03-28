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

import gc
import torch

@register_node
class IncrementalVideoStitcher:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", ),
                "output_prefix": ("STRING", {"default": "SCAIL_Final"}),
                "current_loop_index": ("INT", {"default": 0, "min": 0, "max": 10000}),
                "total_loops": ("INT", {"default": 1, "min": 1, "max": 10000}),
            },
            "optional": {
                "audio": ("AUDIO", ),
            }
        }

    INPUT_IS_LIST = False
    RETURN_TYPES = ("IMAGE", "AUDIO")
    RETURN_NAMES = ("ALL_IMAGES", "AUDIO_OUT")
    OUTPUT_NODE = True
    FUNCTION = "stitch_incremental"
    CATEGORY = "🔁 Sequential Batcher/Video"

    def stitch_incremental(self, images, output_prefix, current_loop_index, total_loops, audio=None):
        if images is None:
            raise ValueError("❌ ERROR CRÍTICO: El nodo 'Incremental Auto-Stitcher' necesita el cable de 'images' con los tensores.")

        if current_loop_index is None or total_loops is None:
            raise ValueError("❌ ERROR CRÍTICO: El nodo 'Incremental Auto-Stitcher' necesita 'current_loop_index' y 'total_loops'.")

        # Barrera de seguridad para evitar que un string vacío borre el directorio principal
        if not output_prefix or not output_prefix.strip():
            output_prefix = "SCAIL_Final"

        out_dir = folder_paths.get_output_directory()
        # Creamos una subcarpeta usando el output_prefix
        stitch_dir = os.path.join(out_dir, output_prefix)
        os.makedirs(stitch_dir, exist_ok=True)

        print(f"\n{'='*50}")
        print(f"🎞️ [DEBUG] NODO: Incremental Auto-Stitcher")
        print(f"   -> Ciclo actual: {current_loop_index} / Total: {total_loops} | Prefix: {output_prefix}")

        # Ciclo 0: Limpieza
        if current_loop_index == 0:
            print(f"   -> 🧹 Limpiando archivos de tensores de sesiones anteriores en: {stitch_dir}")
            pt_files = glob.glob(os.path.join(stitch_dir, "*.pt"))
            for pt_file in pt_files:
                try:
                    os.remove(pt_file)
                except Exception as e:
                    print(f"   -> ❌ Error borrando {pt_file}: {e}")

        # Guardar tensor a disco para liberar RAM/VRAM
        pt_filename = f"batch_{current_loop_index:04d}.pt"
        pt_path = os.path.join(stitch_dir, pt_filename)

        print(f"   -> 💾 Descargando tensores a la CPU y guardando en: {pt_filename}")
        cpu_images = images.cpu()
        torch.save(cpu_images, pt_path)

        # Limpieza manual de memoria
        del images
        del cpu_images
        gc.collect()

        # Comprobamos si es el último ciclo
        if current_loop_index < (total_loops - 1):
            print(f"   -> ⏳ Bucle en proceso. Retornando tensor vacío para ahorrar RAM.")
            print(f"{'='*50}\n")
            # Devolvemos un tensor vacío y None para el audio
            dummy_tensor = torch.zeros((1, 16, 16, 3))
            return (dummy_tensor, None)

        elif current_loop_index == (total_loops - 1):
            print(f"   -> 🏁 Último ciclo alcanzado. Ensamblando tensores finales...")
            pt_files = sorted(glob.glob(os.path.join(stitch_dir, "*.pt")))
            tensor_list = []

            for pt_file in pt_files:
                try:
                    loaded_tensor = torch.load(pt_file)
                    tensor_list.append(loaded_tensor)
                    print(f"   -> 📦 Cargado: {os.path.basename(pt_file)}")
                except Exception as e:
                    print(f"   -> ❌ Error cargando {pt_file}: {e}")

            if not tensor_list:
                print(f"   -> ⚠️ No se encontraron tensores guardados para ensamblar.")
                print(f"{'='*50}\n")
                dummy_tensor = torch.zeros((1, 16, 16, 3))
                return (dummy_tensor, audio)

            # Unir todos los tensores
            print(f"   -> 🧩 Concatenando {len(tensor_list)} tensores...")
            final_images = torch.cat(tensor_list, dim=0)

            # (Opcional) Borrar la subcarpeta para ahorrar espacio
            print(f"   -> 🧹 Limpiando subcarpeta temporal: {stitch_dir}")
            try:
                shutil.rmtree(stitch_dir)
            except Exception as e:
                print(f"   -> ❌ Error borrando subcarpeta: {e}")

            print(f"   -> ✅ Ensamblaje exitoso. Retornando tensor gigante: {list(final_images.shape)}")
            if audio is not None:
                print(f"   -> 🎵 Retornando audio ('passthrough').")
            else:
                print(f"   -> 🔇 No se detectó audio ('passthrough' vacío).")
            print(f"{'='*50}\n")

            return (final_images, audio)

import nodes

@register_node
class LoadVideoWithSourceAudio:
    @classmethod
    def INPUT_TYPES(s):
        vhs_class = nodes.NODE_CLASS_MAPPINGS.get("VHS_LoadVideo")
        if vhs_class:
            inputs = vhs_class.INPUT_TYPES()
            # Forzar la aparición del botón de subida ("Upload")
            if "video" in inputs["required"]:
                video_tuple = list(inputs["required"]["video"])
                if len(video_tuple) > 1 and isinstance(video_tuple[1], dict):
                    video_tuple[1]["video_upload"] = True
                else:
                    video_tuple = (video_tuple[0], {"video_upload": True})
                inputs["required"]["video"] = tuple(video_tuple)
            return inputs
        else:
            raise Exception("VHS_LoadVideo no encontrado. Instala VideoHelperSuite.")

    RETURN_TYPES = ("IMAGE", "INT", "AUDIO", "VHS_VIDEOINFO", "AUDIO")
    RETURN_NAMES = ("IMAGE", "frame_count", "audio", "video_info", "source_audio")
    CATEGORY = "🔁 Sequential Batcher/Video"
    FUNCTION = "load_video_with_audio"

    @classmethod
    def IS_CHANGED(s, video, **kwargs):
        # Lógica propia: Comprobamos si el vídeo ha cambiado usando su fecha de modificación en disco.
        # Es mucho más rápido que calcular el hash SHA256 de un archivo de vídeo gigante.
        video_path = folder_paths.get_annotated_filepath(video)
        if os.path.exists(video_path):
            return os.path.getmtime(video_path)
        return float("NaN")

    @classmethod
    def VALIDATE_INPUTS(s, video, **kwargs):
        # Lógica propia: Comprobamos directamente si la ruta del archivo existe.
        # Al aceptar **kwargs, absorbemos cualquier parámetro extra (como force_rate) sin que Python explote.
        video_path = folder_paths.get_annotated_filepath(video)
        if not os.path.exists(video_path):
            return f"❌ El archivo de vídeo no existe en la ruta: {video_path}"
        return True

    def load_video_with_audio(self, **kwargs):
        vhs_class = nodes.NODE_CLASS_MAPPINGS.get("VHS_LoadVideo")

        # 1. Ejecutar el nodo VHS original
        vhs_instance = vhs_class()
        vhs_output = vhs_instance.load_video(**kwargs)

        # 2. Recuperar la interfaz (Preview UI) y los resultados
        if isinstance(vhs_output, dict) and "result" in vhs_output:
            res = vhs_output["result"]
            ui = vhs_output.get("ui", {})
        else:
            res = vhs_output
            ui = {}

        # 3. Extraer el audio original completo
        video_name = kwargs.get("video")
        video_path = folder_paths.get_annotated_filepath(video_name)

        source_audio = None
        try:
            if os.path.exists(video_path):
                waveform, sample_rate = torchaudio.load(video_path)
                source_audio = {"waveform": waveform.unsqueeze(0), "sample_rate": sample_rate}
        except Exception as e:
            print(f"⚠️ [LoadVideo] Error cargando source_audio: {e}")

        # 4. Retornar el diccionario con la UI intacta (restaura el reproductor visual)
        return {
            "ui": ui,
            "result": (res[0], res[1], res[2], res[3], source_audio)
        }