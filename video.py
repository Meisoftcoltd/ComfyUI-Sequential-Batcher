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
        # Clonar los inputs dinámicamente si VHS está instalado
        vhs_class = nodes.NODE_CLASS_MAPPINGS.get("VHS_LoadVideo")
        if vhs_class:
            return vhs_class.INPUT_TYPES()
        else:
            raise Exception("❌ VHS_LoadVideo no encontrado. Instala VideoHelperSuite.")

    RETURN_TYPES = ("IMAGE", "INT", "AUDIO", "VHS_VIDEOINFO", "AUDIO")
    RETURN_NAMES = ("IMAGE", "frame_count", "audio", "video_info", "source_audio")
    FUNCTION = "load_video_with_audio"
    CATEGORY = "🔁 Sequential Batcher/Video"

    # Intentamos mantener el Display Name para la interfaz web a través del Custom Node mapping original de ComfyUI (opcional pero util para que se llame diferente a VHS)
    # Normalmente esto se hace en el NODE_DISPLAY_NAME_MAPPINGS global de __init__.py pero la clase será LoadVideoWithSourceAudio

    def load_video_with_audio(self, **kwargs):
        vhs_class = nodes.NODE_CLASS_MAPPINGS.get("VHS_LoadVideo")
        if not vhs_class:
            raise Exception("❌ VHS_LoadVideo no encontrado.")

        print(f"\n{'='*50}")
        print(f"🎥 [DEBUG] NODO: Load Video + Source Audio")

        # 1. Instanciar el nodo original y ejecutar su lógica
        print(f"   -> Ejecutando lógica original de VHS...")
        vhs_instance = vhs_class()
        vhs_result = vhs_instance.load_video(**kwargs)

        # vhs_result contiene: (IMAGE, frame_count, audio, video_info)

        # 2. Lógica nueva: Extraer el audio completo del archivo fuente
        video_filename = kwargs.get("video")
        # El nombre del archivo puede venir como una ruta completa desde input, o desde un subdirectorio.
        # En VHS y ComfyUI, usan get_annotated_filepath (esto lo traemos si hace falta, o simplemente path del input dir)
        # VHS lo carga así:
        video_path = folder_paths.get_annotated_filepath(video_filename)

        print(f"   -> 🎵 Extrayendo pista de audio completa (sin cortes) desde: {video_path}")
        try:
            waveform, sample_rate = torchaudio.load(video_path)
            # Retornamos el diccionario en el formato estándar AUDIO de ComfyUI
            source_audio = {"waveform": waveform.unsqueeze(0), "sample_rate": sample_rate}
            print(f"   -> ✅ Audio extraído con éxito. Muestreo: {sample_rate}Hz")
        except Exception as e:
            print(f"   -> ⚠️ Error cargando audio fuente: {e}")
            source_audio = None

        print(f"{'='*50}\n")
        # 3. Devolver el resultado original + nuestro audio completo en el 5º puerto
        return (vhs_result[0], vhs_result[1], vhs_result[2], vhs_result[3], source_audio)