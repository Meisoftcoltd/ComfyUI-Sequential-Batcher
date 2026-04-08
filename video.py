import os
import sys
import logging
from contextlib import redirect_stdout, redirect_stderr
from tqdm import tqdm
import math
import torch
import torchaudio
import folder_paths
import nodes
import time
from . import register_node

# Aseguramos que torch esté disponible globalmente para los bloques de limpieza
import torch

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
        # 1. Obtenemos los archivos locales igual que VHS
        input_dir = folder_paths.get_input_directory()
        files = []
        video_extensions = ['webm', 'mp4', 'mkv', 'gif', 'mov'] # Mismos que VHS
        if os.path.exists(input_dir):
            for f in os.listdir(input_dir):
                if os.path.isfile(os.path.join(input_dir, f)):
                    file_parts = f.split('.')
                    if len(file_parts) > 1 and (file_parts[-1].lower() in video_extensions):
                        files.append(f)

        # 2. El truco VHS: Una tupla con (lista_de_archivos,) pero configurado como STRING y con forceInput=False
        return {
            "required": {
                "video": (sorted(files), {"forceInput": False, "video_upload": True}),
                "reference_frame_idx": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
                "use_face_detector": ("BOOLEAN", {"default": True}),
                "blur_threshold": ("FLOAT", {"default": 100.0, "min": 0.0, "max": 1000.0, "step": 1.0}),
                "unload_detector_after_analysis": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "bbox_detector": ("BBOX_DETECTOR", ), # 💡 Puerto para YOLO/ONNX
            }
        }

    RETURN_TYPES = ("*", "INT", "FLOAT", "AUDIO", "FACE_CUTS", "IMAGE")
    RETURN_NAMES = ("video_path", "total_frames", "source_fps", "source_audio", "safe_faces_list", "reference_frame")
    OUTPUT_NODE = True
    FUNCTION = "analyze"
    CATEGORY = "🔁 Sequential Batcher/Video"

    @classmethod
    def IS_CHANGED(cls, video, **kwargs):
        # VHS procesa las rutas dinámicas resolviéndolas directamente
        if os.path.exists(video):
            video_path = video
        else:
            video_path = folder_paths.get_annotated_filepath(video)

        if os.path.exists(video_path):
            return os.path.getmtime(video_path)
        return time.time()

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        # Bypass para permitir conexiones dinámicas (como descargas en curso)
        return True

    def analyze(self, video, reference_frame_idx, use_face_detector, blur_threshold, unload_detector_after_analysis=True, bbox_detector=None, **kwargs):
        # Resolución unificada de la ruta, tal como hace VHS
        if os.path.exists(video):
            video_path = video
        else:
            video_path = folder_paths.get_annotated_filepath(video)

        print(f"\n{'='*50}")
        print(f"🕵️ [DEBUG] NODO: Video Analyzer (Explorador)")
        print(f"   -> Archivo resuelto: {video_path}")

        # 1. Extracción de Audio Íntegro
        source_audio = None
        try:
            waveform, sample_rate = torchaudio.load(video_path)
            source_audio = {"waveform": waveform.unsqueeze(0), "sample_rate": sample_rate}
            print(f"   -> 🎵 Audio extraído correctamente ({sample_rate}Hz)")
        except Exception as e:
            print(f"   -> ⚠️ Sin audio o error al extraer: {e}")

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
            if bbox_detector is not None or use_face_detector:
                print(f"   -> 🤖 Iniciando escaneo de rostros (Umbral: {blur_threshold})...")
                if bbox_detector is not None:
                    print(f"   -> ⚡ Usando detector de rostros por GPU (YOLO/ONNX).")
                else:
                    print(f"   -> 🐢 Usando detector de rostros por CPU (OpenCV).")

                if HAS_OPENCV:
                    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                    face_cascade = cv2.CascadeClassifier(cascade_path)

                cap.set(cv2.CAP_PROP_POS_FRAMES, 0) # Volver al inicio

                print(f"   -> 🤖 Iniciando escaneo de rostros por GPU...")

                # Silenciamos el logger de ultralytics antes de empezar
                logging.getLogger("ultralytics").setLevel(logging.ERROR)

                # Barra de progreso profesional (desc=Descripción, unit=unidad, leave=True para que no desaparezca)
                pbar = tqdm(total=frame_count, desc="🔍 Analizando Rostros", unit="frame", dynamic_ncols=True)

                for idx in range(frame_count):
                    ret, frame = cap.read()
                    if not ret: break

                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    variance = cv2.Laplacian(gray, cv2.CV_64F).var()

                    faces_found = False
                    if variance > blur_threshold:

                        if bbox_detector is not None:
                            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            img_tensor = torch.from_numpy(frame_rgb.astype(np.float32) / 255.0).unsqueeze(0).cpu()

                            try:
                                # 🤐 CÁPSULA DE VACÍO: Silenciamos TODO el ruido de la consola
                                with open(os.devnull, 'w') as fnull:
                                    with redirect_stdout(fnull), redirect_stderr(fnull):
                                        # Inferencia
                                        segs = bbox_detector.detect(img_tensor, 0.5, 0, 1.0, 10)

                                if segs is not None:
                                    # Formato ImpactPack: (shape, [lista_de_segs])
                                    if isinstance(segs, tuple) and len(segs) == 2 and isinstance(segs[1], list):
                                        if len(segs[1]) > 0:
                                            faces_found = True
                                    # Otros formatos directos
                                    elif isinstance(segs, list) and len(segs) > 0:
                                        faces_found = True
                            except Exception:
                                pass # Fallback silencioso si el detector falla

                        elif HAS_OPENCV and use_face_detector:
                            # Fallback silencioso a OpenCV si el usuario no conectó el cable ONNX
                            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
                            if len(faces) > 0:
                                faces_found = True

                        if faces_found:
                            safe_faces.append(idx)

                    # Actualizamos la barra una sola vez por frame
                    pbar.update(1)

                pbar.close() # Cerramos la barra al terminar
                print(f"   -> ✅ Encontrados {len(safe_faces)} frames nítidos con rostros.")

                # Descarga de VRAM
                if unload_detector_after_analysis:
                    print(f"   -> 🧹 Descargando detector de rostros de la VRAM...")
                    import gc
                    import comfy.model_management as mm
                    mm.unload_all_models()
                    gc.collect()
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
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
        # --- Ajuste Proporcional Base (Sin restricciones VAE) ---
        import math
        from . import loop

        potential_effective_frames = source_frame_count // select_every_nth
        safe_effective_frames = potential_effective_frames # Sin restricciones

        safe_source_frame_count = safe_effective_frames * select_every_nth
        loop.global_source_frame_count = safe_source_frame_count
        effective_loss = potential_effective_frames - safe_effective_frames

        estimated_loops = math.ceil(safe_effective_frames / target_frames_per_loop)
        if estimated_loops > 0:
            target_frames_per_loop = math.ceil(safe_effective_frames / estimated_loops)
            print(f"   -> ⚖️ Ajuste Proporcional: Target recalculado a {target_frames_per_loop} frames por ciclo.")

        # --- LOGS MEJORADOS Y TRANSPARENTES ---
        print(f"   -> 🎞️ Capacidad del video: {potential_effective_frames} frames procesables (Nth: {select_every_nth})")
        if effective_loss > 0:
            print(f"   -> 🛡️ Ajuste VAE: Se usarán {safe_effective_frames} frames (Descarte técnico: {effective_loss} frame/s de proceso)")
        else:
            print(f"   -> ✅ Ajuste VAE: Perfecto. Múltiplo de 4 detectado.") # Manteniendo el mismo string por ahora o podemos omitirlo, lo adapto a que es genérico

        print(f"   -> 📊 Timeline final: 0 a {safe_source_frame_count} (de {source_frame_count} totales)")
        # -------------------------------------------------------------

        loop.global_select_every_nth = select_every_nth

        current_pos = loop.global_accumulated_frames

        print(f"\n{'='*50}")
        print(f"📊 [DEBUG] NODO: Auto Loop Calculator (Motor Dinámico)")
        print(f"   -> Posición en el timeline original: {current_pos} / {source_frame_count}")

        if current_pos >= safe_source_frame_count:
            return (1, current_pos, select_every_nth)

        frames_left = safe_source_frame_count - current_pos

        equitable_target = target_frames_per_loop * select_every_nth

        ideal_cut = current_pos + equitable_target

        if frames_left <= equitable_target:
            best_cut = safe_source_frame_count
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
        if current_pos + (effective_chunk_frames * select_every_nth) > safe_source_frame_count:
            effective_chunk_frames = (safe_source_frame_count - current_pos) // select_every_nth

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

    RETURN_TYPES = ("IMAGE", "AUDIO", "BOOLEAN")
    RETURN_NAMES = ("ALL_IMAGES", "AUDIO_OUT", "IS_FINAL_CYCLE")
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

        source_total = getattr(loop, 'global_source_frame_count', 1)
        is_final_cycle = loop.global_accumulated_frames >= source_total

        if is_final_cycle:
            print(f"   -> 🏁 Generación completa. Liberando tensor total al flujo para procesos finales.")
            print(f"📦 [Stitcher] Ensamblando todos los lotes de vídeo...")
            all_tensors = []
            for i in range(current_loop_index + 1):
                p = os.path.join(cache_dir, f"batch_{i:04d}.pt")
                if os.path.exists(p):
                    all_tensors.append(torch.load(p))
                    try: os.remove(p)
                    except: pass

            final_tensor = torch.cat(all_tensors, dim=0)
            print(f"✅ [Stitcher] Vídeo completado: {final_tensor.shape[0]} frames ensamblados.")

            # 🚀 Retornamos True al final
            return (final_tensor, audio, True)
        else:
            print(f"   -> ⏳ Ciclo intermedio. Soltando 1 frame dummy...")
            dummy_frame = images[-1:].clone()

            # 🚀 Retornamos False al final
            return (dummy_frame, None, False)

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

        # --- MEISOFT PATCH: Sincronización Matemática y Ajuste Proporcional ---
        # 1. Truncado a múltiplo de 4 (Desechamos los 2-3 frames residuales)
        potential_effective_frames = source_frame_count // select_every_nth
        safe_effective_frames = (potential_effective_frames // 4) * 4

        safe_source_frame_count = safe_effective_frames * select_every_nth
        loop.global_source_frame_count = safe_source_frame_count
        effective_loss = potential_effective_frames - safe_effective_frames

        loop.global_select_every_nth = select_every_nth

        # 2. Ajuste Proporcional Real (Evitar micro-ciclos al final)
        estimated_loops = math.ceil(safe_effective_frames / target_frames_per_loop)
        if estimated_loops > 0:
            # Repartir los frames equitativamente
            optimal_target = math.ceil(safe_effective_frames / estimated_loops)
            # Asegurar que el nuevo target sea múltiplo de 4 (redondeando hacia arriba por seguridad)
            adjusted_target = ((optimal_target + 3) // 4) * 4

            print(f"   -> ⚖️ Ajuste Proporcional: Target recalculado de {target_frames_per_loop} a {adjusted_target} frames por ciclo (para {estimated_loops} ciclos)")
            target_frames_per_loop = adjusted_target

        # --- LOGS MEJORADOS Y TRANSPARENTES ---
        print(f"   -> 🎞️ Capacidad del video: {potential_effective_frames} frames procesables (Nth: {select_every_nth})")
        if effective_loss > 0:
            print(f"   -> 🛡️ Ajuste VAE: Se usarán {safe_effective_frames} frames (Descarte técnico: {effective_loss} frame/s de proceso)")
        else:
            print(f"   -> ✅ Ajuste VAE: Perfecto. Múltiplo de 4 detectado.")

        print(f"   -> 📊 Timeline final: 0 a {safe_source_frame_count} (de {source_frame_count} totales)")
        # -------------------------------------------------------------

        current_pos = getattr(loop, 'global_accumulated_frames', 0)

        print(f"\n{'='*50}")
        print(f"📊 [DEBUG] NODO: Auto Loop Calculator (WanVideo 3D VAE)")
        print(f"   -> Timeline seguro ajustado a múltiplos de 4: {current_pos} / {safe_source_frame_count} (Original: {source_frame_count})")

        # Prevención de desbordamiento de bucle
        if current_pos >= safe_source_frame_count:
            return (4, current_pos, select_every_nth)

        frames_left = safe_source_frame_count - current_pos

        equitable_target = target_frames_per_loop * select_every_nth

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

        # 4. Cálculo final del chunk consolidado
        effective_chunk_frames = math.ceil((best_cut - current_pos) / select_every_nth)
        effective_chunk_frames = (effective_chunk_frames // 4) * 4

        if effective_chunk_frames < 4:
            effective_chunk_frames = 4

        if current_pos + (effective_chunk_frames * select_every_nth) > safe_source_frame_count:
            effective_chunk_frames = (safe_source_frame_count - current_pos) // select_every_nth

        skip_frames = current_pos

        print(f"   -> 🚀 Ciclo {current_loop_index}: Solicitando {effective_chunk_frames} frames efectivos a VHS (Saltando {skip_frames})")
        print(f"{'='*50}\n")

        return (effective_chunk_frames, skip_frames, select_every_nth)
