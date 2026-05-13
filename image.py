import os
import time
import random
import numpy as np
import torch
from PIL import Image
import folder_paths
from . import register_node

global_session_image = None

def tensor_to_temp_image(tensor_image, prefix="session_img"):
    temp_dir = folder_paths.get_temp_directory()
    filename = f"{prefix}_{random.randint(10000, 99999)}.png"
    filepath = os.path.join(temp_dir, filename)
    img_array = 255. * tensor_image[0].cpu().numpy()
    img = Image.fromarray(np.clip(img_array, 0, 255).astype(np.uint8))
    img.save(filepath)
    return {"filename": filename, "subfolder": "", "type": "temp"}

@register_node
class SessionImageReceiver:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "initial_image": ("IMAGE",),
                "current_loop_index": ("INT", {"default": 0, "min": 0, "max": 10000}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("current_image", "log")
    OUTPUT_NODE = True
    FUNCTION = "get_image"
    CATEGORY = "🔁 Sequential Batcher/Image"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time()

    def get_image(self, initial_image, current_loop_index):
        log_output = []
        def _log(msg):
            print(msg)
            log_output.append(str(msg))
        from . import loop
        global global_session_image

        loop_idx = current_loop_index[0] if isinstance(current_loop_index, list) else current_loop_index
        is_first = (loop_idx == 0)

        # Usamos getattr para evitar errores si el bucle aún no ha inicializado las variables
        accumulated = getattr(loop, 'global_accumulated_frames', 0)
        source_total = getattr(loop, 'global_source_frame_count', 1)

        _log(f"\n{'='*50}")
        _log(f"📥 [Secuencial Batcher] NODO: Image Receiver")
        _log(f"   -> Ciclo actual: {loop_idx} | Progreso global: {accumulated} / {source_total} frames")

        if is_first or global_session_image is None:
            global_session_image = initial_image.clone().cpu()
            _log(f"   -> 🆕 Iniciando sesión con la imagen ORIGINAL.")
            selected = initial_image
        else:
            _log(f"   -> ♻️ Usando el Keyframe validado y rescatado de la RAM.")
            selected = global_session_image

        _log(f"   -> 🖼️ Tensor shape: {selected.shape}")
        _log(f"{'='*50}\n")

        ui_image = tensor_to_temp_image(selected, "receiver")
        return {"ui": {"images": [ui_image]}, "result": (selected, "\n".join(log_output))}

@register_node
class SessionImageSender:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "generated_images": ("IMAGE",),
                "current_loop_index": ("INT", {"default": 0, "min": 0, "max": 10000}),
                "detect_faces": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("VALIDATED_IMAGES", "log")
    OUTPUT_NODE = True
    FUNCTION = "set_image"
    CATEGORY = "🔁 Sequential Batcher/Image"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time()

    def set_image(self, generated_images, current_loop_index, detect_faces):
        log_output = []
        def _log(msg):
            print(msg)
            log_output.append(str(msg))
        from . import loop
        import cv2
        import numpy as np
        import os, folder_paths, torch
        from PIL import Image

        if generated_images is None:
            raise ValueError("❌ ERROR CRÍTICO: No se recibieron imágenes en el Sender.")

        global global_session_image
        loop_idx = current_loop_index[0] if isinstance(current_loop_index, list) else current_loop_index
        batch_size = generated_images.shape[0]
        best_idx = batch_size - 1

        accumulated = getattr(loop, 'global_accumulated_frames', 0)
        source_total = getattr(loop, 'global_source_frame_count', 1)
        stride = getattr(loop, 'global_select_every_nth', 1)
        ltx_mode_active = getattr(loop, 'global_ltx_mode', False)

        _log(f"\n{'='*50}")
        _log(f"📤 [Secuencial Batcher] NODO: Image Sender (Filtro Dinámico)")
        _log(f"   -> Frames recibidos de la IA: {batch_size}")

        # 🧠 BYPASS IMPLACABLE: Si al sumar este lote llegamos al final del video, NO RECORTAMOS
        advance_check = (batch_size - 1) * stride if ltx_mode_active else batch_size * stride
        if (accumulated + advance_check) >= source_total:
            _log(f"   -> 🏁 LOTE FINAL ABSOLUTO DETECTADO. Desactivando recorte de rostros para forzar la salida de TODOS los frames.")
            detect_faces = False

        if detect_faces:
            try:
                cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                face_cascade = cv2.CascadeClassifier(cascade_path)

                _log(f"   -> 🕵️ Buscando el último rostro frontal en reversa (Desde frame {batch_size - 1} hasta 0)...")

                found = False
                for i in range(batch_size - 1, -1, -1):
                    img_np = (generated_images[i].cpu().numpy() * 255.0).astype(np.uint8)
                    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
                    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))

                    if len(faces) > 0:
                        best_idx = i
                        found = True
                        _log(f"   -> ✅ Rostro detectado en el frame [{i}].")
                        break

                if not found:
                    _log(f"   -> ⚠️ ALERTA: No se detectó rostro frontal en NINGÚN frame. Aceptando todo el lote para evitar bucles infinitos.")
                    best_idx = batch_size - 1
            except Exception as e:
                _log(f"   -> ⚠️ Error en OpenCV al validar: {e}")
        else:
            _log(f"   -> ⏩ Detección de rostros desactivada. Usando el último frame absoluto del lote ({batch_size - 1}).")
            best_idx = batch_size - 1

        # 1. TRUNCAR EL TENSOR
        valid_images = generated_images[:best_idx + 1]
        frames_accepted = best_idx + 1

        # 2. AVANZAR LA MÁQUINA
        stride = getattr(loop, 'global_select_every_nth', 1)
        advanced_original_frames = frames_accepted * stride

        if not hasattr(loop, 'global_accumulated_frames'):
            loop.global_accumulated_frames = 0

        # LTX Mode Fix: Avoid counting the overlap frame in the progression
        ltx_mode_active = getattr(loop, 'global_ltx_mode', False)
        if ltx_mode_active:
            # We subtract 1 from frames_accepted to account for the anchor frame
            # The overlap frame shouldn't advance the global accumulated frames count
            # since it will be reused as the start of the next chunk.
            advanced_original_frames = max(1, (frames_accepted - 1) * stride)

        source_total = getattr(loop, 'global_source_frame_count', 1)
        is_final_chunk = getattr(loop, 'global_is_final_chunk', False)

        # 🚀 FIX: Compensar los frames destruidos por el VAE en el ciclo final
        is_chunk_mode = getattr(loop, 'global_step_by_chunk', False)

        if is_chunk_mode:
            # En modo TTS (Texto), el progreso se mide estrictamente en frases/chunks, no en frames de video.
            is_final_cycle = is_final_chunk
            _log(f"   -> 🧩 Modo Texto activo: Progreso gestionado por frases ({loop.global_accumulated_frames} / {source_total}).")
        else:
            # Lógica original por frames de video
            if is_final_chunk:
                _log(f"   -> 🏁 LOTE FINAL ABSOLUTO DETECTADO. Compensando mermas del VAE (Timeline forzado al 100%).")
                loop.global_accumulated_frames = source_total
            else:
                loop.global_accumulated_frames += advanced_original_frames

            is_final_cycle = loop.global_accumulated_frames >= source_total
            _log(f"   -> 📈 Timeline avanzado a {loop.global_accumulated_frames} / {source_total} frames")

        _log(f"   -> ✂️ Tensor truncado a {frames_accepted} frames válidos.")

        last_frame = valid_images[-1:].clone().cpu()
        global_session_image = last_frame

        # 🛡️ Solo guardamos el keyframe si habrá un próximo ciclo
        if not is_final_cycle:
            out_dir = folder_paths.get_output_directory()
            filename = f"keyframe_{loop_idx:03d}.png"
            filepath = os.path.join(out_dir, filename)

            img_array = 255. * last_frame[0].numpy()
            img = Image.fromarray(np.clip(img_array, 0, 255).astype(np.uint8))
            img.save(filepath)

            _log(f"   -> 💾 Keyframe seguro guardado: {filename}")
        else:
            _log(f"   -> 🚀 Ciclo final/único detectado. Omitiendo guardado de keyframe.")

        _log(f"{'='*50}\n")

        ui_image = tensor_to_temp_image(last_frame, "sender")
        return {"ui": {"images": [ui_image]}, "result": (valid_images, "\n".join(log_output))}
