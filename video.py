import os
import math
import torch
import torchaudio
import folder_paths
import nodes
import time
from . import register_node

# Intento de carga de OpenCV para el Director de Fotografía
try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

@register_node
class VideoAnalyzerWithAudio:
    @classmethod
    def INPUT_TYPES(cls):
        # 💡 TRUCO: Robamos solo el widget de video (con su botón Upload) de VHS
        vhs_class = nodes.NODE_CLASS_MAPPINGS.get("VHS_LoadVideo")
        video_input = ("STRING", {"video_upload": True}) # Fallback por defecto
        if vhs_class:
            vhs_inputs = vhs_class.INPUT_TYPES()
            if "video" in vhs_inputs.get("required", {}):
                video_input = vhs_inputs["required"]["video"]

        return {
            "required": {
                "video": video_input,
                "reference_frame_idx": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
                "use_face_detector": ("BOOLEAN", {"default": True}),
                "blur_threshold": ("FLOAT", {"default": 100.0, "min": 0.0, "max": 1000.0, "step": 1.0}),
            },
            "optional": {
                "opt_video_path": ("STRING", {"forceInput": True}),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "FLOAT", "AUDIO", "FACE_CUTS", "IMAGE")
    RETURN_NAMES = ("video_name", "total_frames", "source_fps", "source_audio", "safe_faces_list", "reference_frame")
    OUTPUT_NODE = True  # Obligatorio para que ComfyUI renderice la preview
    FUNCTION = "analyze"
    CATEGORY = "🔁 Sequential Batcher/Video"

    @classmethod
    def IS_CHANGED(cls, video, **kwargs):
        # Usar entrada opcional si está disponible, sino usar video
        opt_video_path = kwargs.get("opt_video_path", None)
        if opt_video_path is not None:
            video_name = opt_video_path[0] if isinstance(opt_video_path, (list, tuple)) else opt_video_path
        else:
            video_name = video[0] if isinstance(video, (list, tuple)) else video

        if os.path.exists(video_name):
            video_path = video_name
        else:
            video_path = folder_paths.get_annotated_filepath(video_name)

        if os.path.exists(video_path):
            return os.path.getmtime(video_path)
        return time.time()

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        # 1. Bypass dinámico: Si el puerto opcional está conectado, delegamos la existencia al tiempo de ejecución
        if "opt_video_path" in kwargs and kwargs["opt_video_path"] is not None:
            return True

        # 2. Validación estricta UX: Si se usa el widget manual estándar, verificamos físicamente el archivo
        if "video" in kwargs:
            video_val = kwargs["video"]
            if isinstance(video_val, str):
                video_path = folder_paths.get_annotated_filepath(video_val)
                if not os.path.exists(video_path):
                    return f"❌ El archivo de video no existe en: {video_path}"

        return True

    def analyze(self, video, reference_frame_idx, use_face_detector, blur_threshold, opt_video_path=None, **kwargs):
        if opt_video_path is not None:
            video_name = opt_video_path[0] if isinstance(opt_video_path, (list, tuple)) else opt_video_path
        else:
            video_name = video[0] if isinstance(video, (list, tuple)) else video

        if os.path.exists(video_name):
            video_path = video_name
        else:
            video_path = folder_paths.get_annotated_filepath(video_name)

        print(f"\n{'='*50}")
        print(f"🕵️ [DEBUG] NODO: Video Analyzer (Explorador)")
        print(f"   -> Archivo: {video_name}")

        # 1. Extracción de Audio Íntegro
        source_audio = None
        try:
            waveform, sample_rate = torchaudio.load(video_path)
            source_audio = {"waveform": waveform.unsqueeze(0), "sample_rate": sample_rate}
            print(f"   -> 🎵 Audio extraído correctamente ({sample_rate}Hz)")
        except:
            print(f"   -> ⚠️ Sin audio o error al extraer.")

        # 2. Escaneo de OpenCV (Frames, Rostros y Referencia)
        frame_count = 0
        source_fps = 0.0
        safe_faces = []
        ref_tensor = torch.zeros((1, 64, 64, 3), dtype=torch.float32) # Tensor negro de seguridad
        ui_result = {}

        if not HAS_OPENCV:
            print("   -> ❌ ERROR: OpenCV no está instalado. Ejecuta: pip install opencv-python")
        else:
            cap = cv2.VideoCapture(video_path)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            source_fps = float(cap.get(cv2.CAP_PROP_FPS))
            print(f"   -> 🎞️ Total Frames detectados: {frame_count}")
            print(f"   -> ⏱️ FPS detectados: {source_fps}")

            # Extraer el Frame de Referencia específico
            safe_ref_idx = min(reference_frame_idx, max(0, frame_count - 1))
            cap.set(cv2.CAP_PROP_POS_FRAMES, safe_ref_idx)
            ret, ref_frame = cap.read()

            if ret:
                # Convertir BGR a RGB para ComfyUI
                ref_frame_rgb = cv2.cvtColor(ref_frame, cv2.COLOR_BGR2RGB)
                # Convertir a Tensor (1, H, W, 3)
                ref_tensor = torch.from_numpy(ref_frame_rgb).float() / 255.0
                ref_tensor = ref_tensor.unsqueeze(0)
                print(f"   -> 🖼️ Frame de referencia extraído (Índice: {safe_ref_idx})")

                # Generar imagen temporal para el Preview de la UI
                import random
                from PIL import Image
                preview_dir = folder_paths.get_temp_directory()
                preview_name = f"preview_ref_{random.randint(1000, 9999)}.png"
                Image.fromarray(ref_frame_rgb).save(os.path.join(preview_dir, preview_name))
                ui_result = {"images": [{"filename": preview_name, "subfolder": "", "type": "temp"}]}

            # Escaneo de Rostros
            if use_face_detector:
                print(f"   -> 🤖 Iniciando escaneo de rostros (Umbral: {blur_threshold})...")
                cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                face_cascade = cv2.CascadeClassifier(cascade_path)

                cap.set(cv2.CAP_PROP_POS_FRAMES, 0) # Volver al inicio
                idx = 0
                while True:
                    ret, frame = cap.read()
                    if not ret: break

                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    variance = cv2.Laplacian(gray, cv2.CV_64F).var()

                    if variance > blur_threshold:
                        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
                        if len(faces) > 0:
                            safe_faces.append(idx)
                    idx += 1
                print(f"   -> ✅ Encontrados {len(safe_faces)} frames nítidos con rostros.")
            else:
                print(f"   -> 🤖 Escaneo de rostros DESACTIVADO.")

            cap.release()

        print(f"{'='*50}\n")

        # 💡 EL BYPASS A VHS: Pasamos video_path (Ruta Absoluta) en lugar de video_name
        return {"ui": ui_result, "result": (video_path, frame_count, source_fps, source_audio, safe_faces, ref_tensor)}

@register_node
class AutoLoopCalculator:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "source_frame_count": ("INT", {"forceInput": True}),
                "target_frames_per_loop": ("INT", {"default": 50, "min": 1, "max": 10000}),
                "select_every_nth": ("INT", {"default": 1, "min": 1, "max": 100}),
                "current_loop_index": ("INT", {"forceInput": True}),
            },
            "optional": {
                "safe_faces_list": ("FACE_CUTS", {"forceInput": True}),
            }
        }

    RETURN_TYPES = ("INT", "INT", "INT")
    RETURN_NAMES = ("chunk_frames", "skip_frames", "select_every_nth")
    FUNCTION = "calculate"
    CATEGORY = "🔁 Sequential Batcher/Video"

    def calculate(self, source_frame_count, target_frames_per_loop, select_every_nth, current_loop_index, safe_faces_list=None):
        import math
        from . import loop

        loop.global_source_frame_count = source_frame_count
        loop.global_select_every_nth = select_every_nth

        current_pos = loop.global_accumulated_frames

        print(f"\n{'='*50}")
        print(f"📊 [DEBUG] NODO: Auto Loop Calculator (Motor Dinámico)")
        print(f"   -> Posición en el timeline original: {current_pos} / {source_frame_count}")

        if current_pos >= source_frame_count:
            return (1, current_pos, select_every_nth)

        frames_left = source_frame_count - current_pos

        total_loops = math.ceil(source_frame_count / (target_frames_per_loop * select_every_nth))
        equitable_target = math.floor(source_frame_count / total_loops)

        ideal_cut = current_pos + equitable_target

        if frames_left <= equitable_target:
            best_cut = source_frame_count
            print(f"   -> 🧮 Absorbiendo resto final: meta fijada en frame {best_cut}")
        else:
            best_cut = ideal_cut
            if safe_faces_list and len(safe_faces_list) > 0:
                # Find the safe face closest to the equitable target
                closest_face = min(safe_faces_list, key=lambda x: abs(x - ideal_cut))
                best_cut = closest_face
                print(f"   -> ✂️ Corte Inteligente proyectado: {best_cut} (Meta equitativa: {ideal_cut})")
            else:
                print(f"   -> ⚖️ Sin caras detectadas. Forzando corte equitativo: {ideal_cut}")

        effective_chunk_frames = math.ceil((best_cut - current_pos) / select_every_nth)
        skip_frames = current_pos

        print(f"   -> 🚀 Ciclo {current_loop_index}: Solicitando {effective_chunk_frames} frames efectivos (Saltando {skip_frames})")
        print(f"{'='*50}\n")

        return (effective_chunk_frames, skip_frames, select_every_nth)

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
        import os, folder_paths, torch

        cache_dir = os.path.join(folder_paths.get_temp_directory(), "wan_stitcher_cache")
        os.makedirs(cache_dir, exist_ok=True)

        path = os.path.join(cache_dir, f"batch_{current_loop_index:04d}.pt")
        torch.save(images.cpu(), path)
        print(f"🎞️ [Stitcher] Lote {current_loop_index} guardado en disco ({images.shape[0]} frames).")

        is_final = loop.global_accumulated_frames >= loop.global_source_frame_count

        if not is_final:
            preview_frame = images[0:1]
            return (preview_frame, None)

        print(f"📦 [Stitcher] Ensamblando todos los lotes de vídeo...")
        all_tensors = []
        for i in range(current_loop_index + 1):
            p = os.path.join(cache_dir, f"batch_{i:04d}.pt")
            if os.path.exists(p):
                all_tensors.append(torch.load(p))
                try: os.remove(p)
                except: pass

        final_images = torch.cat(all_tensors, dim=0)
        print(f"✅ [Stitcher] Vídeo completado: {final_images.shape[0]} frames ensamblados.")

        return (final_images, audio)

@register_node
class AutoLoopCalculatorWan:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "source_frame_count": ("INT", {"forceInput": True}),
                "target_frames_per_loop": ("INT", {"default": 48, "min": 4, "max": 10000, "step": 4}),
                "select_every_nth": ("INT", {"default": 1, "min": 1, "max": 100}),
                "current_loop_index": ("INT", {"forceInput": True}),
            },
            "optional": {
                "safe_faces_list": ("FACE_CUTS", {"forceInput": True}),
            }
        }

    RETURN_TYPES = ("INT", "INT", "INT")
    RETURN_NAMES = ("chunk_frames", "skip_frames", "select_every_nth")
    FUNCTION = "calculate"
    CATEGORY = "🔁 Sequential Batcher/Video"

    def calculate(self, source_frame_count, target_frames_per_loop, select_every_nth, current_loop_index, safe_faces_list=None):
        import math
        from . import loop

        # 1. TRUNCADO GLOBAL PARA WANVIDEO (Múltiplo de 4)
        # Ignoramos el remanente asimétrico del video original para no estrellar el VAE en el ciclo final
        safe_source_frame_count = (source_frame_count // 4) * 4

        loop.global_source_frame_count = safe_source_frame_count
        loop.global_select_every_nth = select_every_nth

        current_pos = getattr(loop, 'global_accumulated_frames', 0)

        print(f"\n{'='*50}")
        print(f"📊 [DEBUG] NODO: Auto Loop Calculator (WanVideo 3D VAE)")
        print(f"   -> Timeline seguro ajustado a múltiplos de 4: {current_pos} / {safe_source_frame_count} (Original: {source_frame_count})")

        # Prevención de desbordamiento de bucle
        if current_pos >= safe_source_frame_count:
            return (4, current_pos, select_every_nth)

        frames_left = safe_source_frame_count - current_pos

        # 2. Asegurar que el target per loop es múltiplo de 4 estricto
        safe_target = (target_frames_per_loop // 4) * 4
        if safe_target < 4: safe_target = 4

        total_loops = math.ceil(safe_source_frame_count / (safe_target * select_every_nth))
        if total_loops <= 0: total_loops = 1

        equitable_target = math.floor(safe_source_frame_count / total_loops)

        # 3. Múltiplo de 4 para la meta equitativa
        equitable_target = (equitable_target // 4) * 4
        if equitable_target < 4: equitable_target = 4

        ideal_cut = current_pos + equitable_target

        if frames_left <= equitable_target:
            best_cut = safe_source_frame_count
            print(f"   -> 🧮 Absorbiendo resto final seguro: meta fijada en frame {best_cut}")
        else:
            best_cut = ideal_cut
            if safe_faces_list and len(safe_faces_list) > 0:
                closest_face = min(safe_faces_list, key=lambda x: abs(x - ideal_cut))
                # Distancia al corte de cara
                chunk_from_face = math.ceil((closest_face - current_pos) / select_every_nth)
                # Blindaje matemático x4 para el corte de cara
                safe_chunk_from_face = (chunk_from_face // 4) * 4
                if safe_chunk_from_face < 4: safe_chunk_from_face = 4

                best_cut = current_pos + (safe_chunk_from_face * select_every_nth)
                print(f"   -> ✂️ Corte Inteligente (Ajustado x4): {best_cut} (Cara original detectada: {closest_face})")
            else:
                print(f"   -> ⚖️ Sin caras. Forzando corte equitativo x4: {ideal_cut}")

        # 4. Cálculo final del chunk con blindaje absoluto hacia VHS
        effective_chunk_frames = math.ceil((best_cut - current_pos) / select_every_nth)
        effective_chunk_frames = (effective_chunk_frames // 4) * 4

        # Regla de oro de WanVideo: mínimo 4 frames para que el VAE no colapse
        if effective_chunk_frames < 4:
            effective_chunk_frames = 4

        # Control de límites: Si este chunk x4 nos hace pasarnos del total seguro, ajustar al resto exacto
        if current_pos + (effective_chunk_frames * select_every_nth) > safe_source_frame_count:
            remaining = safe_source_frame_count - current_pos
            effective_chunk_frames = (remaining // 4) * 4
            if effective_chunk_frames < 4: effective_chunk_frames = 4

        skip_frames = current_pos

        print(f"   -> 🚀 Ciclo {current_loop_index}: Solicitando {effective_chunk_frames} frames efectivos a VHS (Saltando {skip_frames})")
        print(f"{'='*50}\n")

        return (effective_chunk_frames, skip_frames, select_every_nth)
