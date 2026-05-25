import os
import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout, redirect_stderr
from tqdm import tqdm
import comfy.utils
import math
import torch
import torchaudio
import folder_paths
import time
from safetensors.torch import save_file, load_file
import uuid
import subprocess
import re
from . import register_node

# Intento de carga de OpenCV para el Director de Fotografía

# Caché persistente para evitar re-escaneos pesados de vídeo
VIDEO_ANALYSIS_CACHE = {}

# 🎵 Helper para estandarizar audio a 44100Hz y 2 Canales (Estéreo)
def extract_and_standardize_audio(video_path, target_sr=44100):
    import torchaudio.transforms as T
    try:
        waveform, sample_rate = torchaudio.load(video_path)

        # 1. Resampling si la frecuencia es distinta
        if sample_rate != target_sr:
            resampler = T.Resample(orig_freq=sample_rate, new_freq=target_sr)
            waveform = resampler(waveform)
            sample_rate = target_sr

        # 2. Downmix / Upmix a Estéreo (2 canales) estrictamente
        channels = waveform.shape[0]
        if channels > 2:
            # Si tiene más de 2 canales (ej. 5.1), mezclamos a mono y duplicamos a estéreo
            mono = torch.mean(waveform, dim=0, keepdim=True)
            waveform = mono.repeat(2, 1)
        elif channels == 1:
            # Si es mono, duplicamos la pista para que sea estéreo
            waveform = waveform.repeat(2, 1)

        return {"waveform": waveform.unsqueeze(0), "sample_rate": sample_rate}
    except Exception as e:
        raise e

# 🎬 Helper para crear un Clon de Vídeo Físico Estandarizado (Soluciona el desvío VHS)
def standardize_video_file(video_path, _log):
    import folder_paths

    if "_std_audio.mp4" in video_path:
        return video_path

    filename = os.path.basename(video_path)
    name, _ = os.path.splitext(filename)
    out_filename = f"{name}_std_audio.mp4"
    out_path = os.path.join(folder_paths.get_temp_directory(), out_filename)

    if os.path.exists(out_path):
        _log(f"   -> ♻️ Usando clon de vídeo estandarizado existente en disco: {out_filename}")
        return out_path

    # Averiguar info original del audio
    target_sr = None
    target_ac = None
    try:
        info = torchaudio.info(video_path)
        # Solo aplicamos limitador si se superan los umbrales máximos de ComfyUI
        if info.sample_rate > 44100:
            target_sr = "44100"
        if info.num_channels > 2:
            target_ac = "2"
    except Exception as e:
        _log(f"   -> ⚠️ No se pudo leer metadata de audio con torchaudio. Forzando límites de seguridad. (Error: {e})")
        target_sr = "44100"
        target_ac = "2"

    # Si el audio ya es seguro, no gastamos recursos en clonar
    if target_sr is None and target_ac is None:
        _log(f"   -> ✅ El audio original ya está en parámetros seguros (<=44100Hz, <=2 Canales). Omitiendo FFmpeg.")
        return video_path

    _log(f"   -> ⚙️ Reestructurando contenedor físico con FFmpeg (Vídeo: Copy | Audio: Limitando a parámetros seguros)...")
    try:
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-c:v", "copy",
            "-c:a", "aac"
        ]

        # Añadimos los filtros solo si son necesarios
        if target_sr:
            cmd.extend(["-ar", target_sr])
        if target_ac:
            cmd.extend(["-ac", target_ac])

        cmd.extend(["-map", "0:v?", "-map", "0:a?", out_path])

        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        _log(f"   -> ✅ Contenedor clonado y blindado con éxito para los nodos de VHS.")
        return out_path
    except Exception as e:
        raise Exception(f"❌ [Secuencial Batcher] Error crítico: Falló la reestructuración del vídeo. Asegúrate de tener FFmpeg instalado y accesible en el PATH del sistema. Detalles: {e}")

try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

@register_node
class VideoAnalyzerFaceDetector:
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
                "unload_detector": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "bbox_detector": ("BBOX_DETECTOR", ), # 💡 Puerto para YOLO/ONNX
                "current_loop_index": ("INT", {"default": 0, "forceInput": True}),
            }
        }

    RETURN_TYPES = ("*", "INT", "FLOAT", "AUDIO", "FACE_CUTS", "IMAGE", "STRING")
    RETURN_NAMES = ("video_path", "total_frames", "source_fps", "source_audio", "safe_faces_list", "reference_frame", "log")
    OUTPUT_NODE = True
    FUNCTION = "analyze"
    CATEGORY = "🔁 Sequential Batcher/Video"

    @classmethod
    def IS_CHANGED(cls, video, reference_frame_idx, use_face_detector, blur_threshold, **kwargs):
        if isinstance(video, list):
            video_str = "".join(video)
        else:
            video_str = str(video)
        return f"{video_str}_{reference_frame_idx}_{use_face_detector}_{blur_threshold}"

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        # Bypass para permitir conexiones dinámicas (como descargas en curso)
        return True

    def analyze(self, video, reference_frame_idx, use_face_detector, blur_threshold, unload_detector_after_analysis=True, bbox_detector=None, current_loop_index=0, **kwargs):
        log_output = []
        def _log(msg):
            print(msg)
            log_output.append(str(msg))
        # Resolución unificada de la ruta, tal como hace VHS
        if os.path.exists(video):
            video_path = video
        else:
            video_path = folder_paths.get_annotated_filepath(video)

        # 🚀 CLONACIÓN FÍSICA PARA VHS
        video_path = standardize_video_file(video_path, _log)

        _log(f"\n{'='*50}")
        _log(f"🕵️ [Secuencial Batcher] NODO: Video Analyzer (Explorador)")
        _log(f"   -> Archivo resuelto: {video_path}")

        cache_key = f"{video_path}_face"

        # --- LÓGICA DE CACHÉ / RECUPERACIÓN ---
        if current_loop_index > 0 and cache_key in VIDEO_ANALYSIS_CACHE:
            _log(f"♻️ [Face Detector] Ciclo {current_loop_index}: Recuperando análisis del caché.")
            cached = VIDEO_ANALYSIS_CACHE[cache_key]
            frame_count, source_fps, source_audio, safe_faces = cached
        else:
            # Análisis completo (Solo Ciclo 0 o primer arranque)
            _log(f"🎬 [Face Detector] Ciclo {current_loop_index}: Iniciando análisis profundo...")
            # 1. Extracción de Audio Íntegro (Estandarizado a 44100Hz Estéreo)
            source_audio = None
            try:
                source_audio = extract_and_standardize_audio(video_path)
                _log(f"   -> 🎵 Audio extraído y estandarizado correctamente (44100Hz, Estéreo)")
            except Exception as e:
                _log(f"   -> ⚠️ Sin audio o error al extraer: {e}")

            # 2. Escaneo de OpenCV (Frames, Rostros y Referencia)
            frame_count = 0
            source_fps = 0.0
            safe_faces = []

            if not HAS_OPENCV:
                _log("   -> ❌ ERROR: OpenCV no está instalado. Ejecuta: pip install opencv-python")
            else:
                cap = cv2.VideoCapture(video_path)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                source_fps = float(cap.get(cv2.CAP_PROP_FPS))
                _log(f"   -> 🎞️ Total Frames detectados: {frame_count}")
                _log(f"   -> ⏱️ FPS detectados: {source_fps}")

                # Escaneo de Rostros
                if bbox_detector is not None or use_face_detector:
                    _log(f"   -> 🤖 Iniciando escaneo de rostros (Umbral: {blur_threshold})...")
                    if bbox_detector is not None:
                        _log(f"   -> ⚡ Usando detector de rostros por GPU (YOLO/ONNX).")
                    else:
                        _log(f"   -> 🐢 Usando detector de rostros por CPU (OpenCV).")

                    if HAS_OPENCV:
                        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                        face_cascade = cv2.CascadeClassifier(cascade_path)

                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0) # Volver al inicio

                    _log(f"   -> 🤖 Iniciando escaneo de rostros por GPU...")

                    # Silenciamos el logger de ultralytics antes de empezar
                    logging.getLogger("ultralytics").setLevel(logging.ERROR)

                    # Barra de progreso profesional (desc=Descripción, unit=unidad, leave=True para que no desaparezca)
                    pbar = tqdm(total=frame_count, desc="🔍 Analizando Rostros", unit="frame", dynamic_ncols=True)
                    comfy_pbar = comfy.utils.ProgressBar(frame_count)

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
                                            res = bbox_detector.detect(img_tensor, 0.5, 10, 1.0, 10)
                                            if isinstance(res, tuple):
                                                segs = res[0]
                                            else:
                                                segs = res
                                            if isinstance(segs, tuple) and len(segs) > 1 and isinstance(segs[1], list):
                                                faces_found = len(segs[1]) > 0
                                            elif isinstance(segs, list):
                                                faces_found = len(segs) > 0
                                            elif hasattr(segs, '__len__'):
                                                faces_found = len(segs) > 0
                                except Exception as e:
                                    _log(f"      ❌ ERROR BBOX en frame {idx}: {e}")

                            else:
                                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
                                faces_found = len(faces) > 0

                        if faces_found:
                            safe_faces.append(idx)
                            # _log(f"      ✨ Rostro nítido detectado en frame [{idx}] (Varianza: {variance:.2f})")

                        pbar.update(1)
                        comfy_pbar.update(1)

                    pbar.close()
                    _log(f"   -> ✅ Encontrados {len(safe_faces)} frames válidos con rostros.")

                cap.release()

            # Guardar en caché
            VIDEO_ANALYSIS_CACHE[cache_key] = (frame_count, source_fps, source_audio, safe_faces)

        # --- EXTRACCIÓN DINÁMICA DEL FRAME DE REFERENCIA (Siempre se ejecuta) ---
        ui_result = {}
        if HAS_OPENCV:
            cap = cv2.VideoCapture(video_path)
            safe_ref_idx = min(reference_frame_idx, max(0, frame_count - 1))
            cap.set(cv2.CAP_PROP_POS_FRAMES, safe_ref_idx)
            ret, frame = cap.read()
            if ret:
                ref_frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                ref_tensor = torch.from_numpy(ref_frame_rgb).float() / 255.0
                ref_tensor = ref_tensor.unsqueeze(0)
                _log(f"   -> 🖼️ Frame de referencia extraído (Índice: {safe_ref_idx})")

                from PIL import Image
                preview_dir = folder_paths.get_temp_directory()
                preview_name = f"preview_ref_{uuid.uuid4().hex[:5]}.png"
                Image.fromarray(ref_frame_rgb).save(os.path.join(preview_dir, preview_name))
                ui_result = {"images": [{"filename": preview_name, "subfolder": "", "type": "temp"}]}
            else:
                ref_tensor = torch.zeros((1, 64, 64, 3), dtype=torch.float32)
            cap.release()
        else:
            ref_tensor = torch.zeros((1, 64, 64, 3), dtype=torch.float32)

        # Liberar el detector de VRAM si se solicita y si se usó
        if unload_detector_after_analysis and bbox_detector is not None and getattr(kwargs, 'unload_detector', True):
            _log(f"   -> 🧹 Limpiando BBOX_DETECTOR de la VRAM para ahorrar memoria...")
            import gc
            import comfy.model_management as mm
            # Romper referencias
            del bbox_detector
            bbox_detector = None
            gc.collect()
            torch.cuda.empty_cache()
            mm.soft_empty_cache()
        _log(f"{'='*50}\n")

        return {"ui": ui_result, "result": (video_path, frame_count, source_fps, source_audio, safe_faces, ref_tensor, "\n".join(log_output))}


@register_node
class VideoAnalyzerSceneDetector:
    @classmethod
    def INPUT_TYPES(cls):
        input_dir = folder_paths.get_input_directory()
        files = []
        if os.path.exists(input_dir):
            files = [f for f in os.listdir(input_dir) if f.split('.')[-1].lower() in ['webm', 'mp4', 'mkv', 'gif', 'mov']]
        return {
            "required": {
                "video": (sorted(files), {"forceInput": False, "video_upload": True}),
                "reference_frame_idx": ("INT", {"default": 0, "min": 0, "max": 100000}),
                "scene_threshold": ("FLOAT", {"default": 25.0, "min": 5.0, "max": 150.0}),
            },
            "optional": {
                "current_loop_index": ("INT", {"default": 0, "forceInput": True}),
            }
        }

    RETURN_TYPES = ("*", "INT", "FLOAT", "AUDIO", "SCENE_CUTS", "IMAGE", "STRING")
    RETURN_NAMES = ("video_path", "total_frames", "source_fps", "source_audio", "scene_cuts_list", "reference_frame", "log")
    OUTPUT_NODE = True
    FUNCTION = "analyze"
    CATEGORY = "🔁 Sequential Batcher/Video"

    @classmethod
    def IS_CHANGED(cls, video, reference_frame_idx, scene_threshold, **kwargs):
        if isinstance(video, list):
            video_str = "".join(video)
        else:
            video_str = str(video)
        return f"{video_str}_{reference_frame_idx}_{scene_threshold}"

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        return True

    def analyze(self, video, reference_frame_idx, scene_threshold, current_loop_index=0, **kwargs):
        log_output = []
        def _log(msg):
            print(msg)
            log_output.append(str(msg))

        video_path = video if os.path.exists(video) else folder_paths.get_annotated_filepath(video)

        # 🚀 CLONACIÓN FÍSICA PARA VHS
        video_path = standardize_video_file(video_path, _log)

        cache_key = f"{video_path}_scene"

        # --- LÓGICA DE CACHÉ / RECUPERACIÓN ---
        if current_loop_index > 0 and cache_key in VIDEO_ANALYSIS_CACHE:
            _log(f"♻️ [Scene Detector] Ciclo {current_loop_index}: Recuperando análisis del caché.")
            cached = VIDEO_ANALYSIS_CACHE[cache_key]
            frame_count, source_fps, source_audio, scene_cuts = cached
        else:
            # Análisis completo (Solo Ciclo 0 o primer arranque)
            _log(f"🎬 [Scene Detector] Ciclo {current_loop_index}: Iniciando análisis profundo...")

            frame_count = 0
            source_fps = 0.0
            source_audio = None
            scene_cuts = []

            if HAS_OPENCV:
                cap = cv2.VideoCapture(video_path)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                source_fps = float(cap.get(cv2.CAP_PROP_FPS))

                # 1. Extracción de Audio Íntegro (Estandarizado a 44100Hz Estéreo)
                source_audio = None
                try:
                    source_audio = extract_and_standardize_audio(video_path)
                    _log(f"   -> 🎵 Audio extraído y estandarizado correctamente (44100Hz, Estéreo)")
                except Exception as e:
                    _log(f"   -> ⚠️ Sin audio o error al extraer: {e}")

                # Detección de cortes
                _log(f"   -> 🎬 Iniciando escaneo de escenas (Umbral Diferencia: {scene_threshold})...")
                prev_gray = None
                pbar = tqdm(total=frame_count, desc="🎬 Analizando Escenas")
                comfy_pbar = comfy.utils.ProgressBar(frame_count)

                for idx in range(frame_count):
                    ret, frame = cap.read()
                    if not ret: break
                    small = cv2.resize(frame, (128, 128))
                    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
                    if prev_gray is not None:
                        score = np.mean(cv2.absdiff(gray, prev_gray))
                        if score > scene_threshold:
                            scene_cuts.append(idx)
                            # _log(f"      🎞️ Corte de escena detectado en frame [{idx}] (Puntuación: {score:.2f})")
                    prev_gray = gray
                    pbar.update(1)
                    comfy_pbar.update(1)
                pbar.close()
                cap.release()
                _log(f"   -> ✅ Encontrados {len(scene_cuts)} cambios de escena fuertes.")
            else:
                _log("   -> ❌ ERROR: OpenCV no está instalado. Ejecuta: pip install opencv-python")

            # Guardar en caché
            VIDEO_ANALYSIS_CACHE[cache_key] = (frame_count, source_fps, source_audio, scene_cuts)

        # --- EXTRACCIÓN DINÁMICA DEL FRAME DE REFERENCIA (Siempre se ejecuta) ---
        ui_result = {}
        if HAS_OPENCV:
            cap = cv2.VideoCapture(video_path)
            safe_ref_idx = min(reference_frame_idx, max(0, frame_count - 1)) if frame_count > 0 else 0
            cap.set(cv2.CAP_PROP_POS_FRAMES, safe_ref_idx)
            ret, frame = cap.read()
            if ret:
                ref_frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                ref_tensor = torch.from_numpy(ref_frame_rgb).float() / 255.0
                ref_tensor = ref_tensor.unsqueeze(0)

                from PIL import Image
                preview_name = f"preview_scene_{uuid.uuid4().hex[:5]}.png"
                Image.fromarray(ref_frame_rgb).save(os.path.join(folder_paths.get_temp_directory(), preview_name))
                ui_result = {"images": [{"filename": preview_name, "subfolder": "", "type": "temp"}]}
            else:
                ref_tensor = torch.zeros((1, 64, 64, 3))
            cap.release()
        else:
            ref_tensor = torch.zeros((1, 64, 64, 3))

        _log(f"{'='*50}\n")
        return {"ui": ui_result, "result": (video_path, frame_count, source_fps, source_audio, scene_cuts, ref_tensor, "\n".join(log_output))}



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
                "scene_cuts_list": ("SCENE_CUTS", {"forceInput": True}),
            }
        }

    RETURN_TYPES = ("INT", "INT", "INT", "STRING")
    RETURN_NAMES = ("chunk_frames", "skip_frames", "select_every_nth", "log")
    FUNCTION = "calculate"
    CATEGORY = "🔁 Sequential Batcher/Video"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()

    def calculate(self, source_frame_count, target_frames_per_loop, select_every_nth, current_loop_index, safe_faces_list=None, scene_cuts_list=None):
        log_output = []
        def _log(msg):
            print(msg)
            log_output.append(str(msg))

        if source_frame_count <= 0 or target_frames_per_loop <= 0:
            _log("⚠️ [WARNING] Invalid frame count or target frames per loop.")
            return (1, 0, select_every_nth, "\n".join(log_output))

        source_frame_count = min(source_frame_count, 10000)
        select_every_nth = max(1, select_every_nth)

        # --- Ajuste Proporcional Base (Sin restricciones VAE) ---
        import math
        from . import loop

        loop.global_step_by_chunk = False

        potential_effective_frames = source_frame_count // select_every_nth
        safe_effective_frames = potential_effective_frames # Sin restricciones

        safe_source_frame_count = safe_effective_frames * select_every_nth
        loop.global_source_frame_count = safe_source_frame_count
        effective_loss = potential_effective_frames - safe_effective_frames

        estimated_loops = math.ceil(safe_effective_frames / target_frames_per_loop)
        if estimated_loops > 0:
            target_frames_per_loop = math.ceil(safe_effective_frames / estimated_loops)
            _log(f"   -> ⚖️ Ajuste Proporcional: Target recalculado a {target_frames_per_loop} frames por ciclo.")

        # --- LOGS MEJORADOS Y TRANSPARENTES ---
        _log(f"   -> 🎞️ Capacidad del video: {potential_effective_frames} frames procesables (Nth: {select_every_nth})")
        if effective_loss > 0:
            _log(f"   -> 🛡️ Ajuste VAE: Se usarán {safe_effective_frames} frames (Descarte técnico: {effective_loss} frame/s de proceso)")
        else:
            _log(f"   -> ✅ Ajuste VAE: Perfecto. Múltiplo de 4 detectado.") # Manteniendo el mismo string por ahora o podemos omitirlo, lo adapto a que es genérico

        _log(f"   -> 📊 Timeline final: 0 a {safe_source_frame_count} (de {source_frame_count} totales)")
        # -------------------------------------------------------------

        loop.global_select_every_nth = select_every_nth

        current_pos = loop.global_accumulated_frames

        _log(f"\n{'='*50}")
        _log(f"📊 [Secuencial Batcher] NODO: Auto Loop Calculator (Motor Dinámico)")
        _log(f"   -> Posición en el timeline original: {current_pos} / {source_frame_count}")

        if current_pos >= safe_source_frame_count:
            return (1, current_pos, select_every_nth, "\n".join(log_output))

        frames_left = safe_source_frame_count - current_pos

        equitable_target = target_frames_per_loop * select_every_nth

        ideal_cut = current_pos + equitable_target

        if frames_left <= equitable_target:
            best_cut = safe_source_frame_count
            _log(f"   -> 🧮 Absorbiendo resto final: meta fijada en frame {best_cut}")
        else:
            if scene_cuts_list and len(scene_cuts_list) > 0:
                # 🎬 LÓGICA DE ESCENAS ESTRICTA (1 Escena = 1 Bucle)
                # Buscar el PRIMER corte que venga inmediatamente después de la posición actual
                future_cuts = [c for c in scene_cuts_list if c > current_pos]

                if future_cuts:
                    next_cut = min(future_cuts)

                    # Verificamos si esta escena entera cabe en la VRAM
                    if next_cut <= ideal_cut:
                        best_cut = next_cut
                        _log(f"   -> 🎬 Bucle aislado por escena. Cortando exacto en el frame: {best_cut}")
                    else:
                        best_cut = ideal_cut
                        _log(f"   -> ⚠️ Toma demasiado larga para la VRAM. Cortando por límite técnico en: {best_cut} (El plano real acaba en {next_cut})")
                else:
                    best_cut = ideal_cut
                    _log(f"   -> 🎬 No quedan cortes de cámara por delante. Forzando corte final por VRAM en: {ideal_cut}")

            elif safe_faces_list and len(safe_faces_list) > 0:
                # 👤 LÓGICA DE ROSTROS (Fallback si no hay escenas conectadas)
                closest_face = min(safe_faces_list, key=lambda x: abs(x - ideal_cut))
                best_cut = closest_face
                _log(f"   -> ✂️ Corte Facial Inteligente: {best_cut} (Meta: {ideal_cut})")

            else:
                best_cut = ideal_cut
                _log(f"   -> ⚖️ Sin detectores conectados. Forzando corte equitativo: {ideal_cut}")

        effective_chunk_frames = math.ceil((best_cut - current_pos) / select_every_nth)
        if current_pos + (effective_chunk_frames * select_every_nth) > safe_source_frame_count:
            effective_chunk_frames = (safe_source_frame_count - current_pos) // select_every_nth

        skip_frames = current_pos

        _log(f"   -> 🚀 Ciclo {current_loop_index}: Solicitando {effective_chunk_frames} frames efectivos (Saltando {skip_frames})")
        _log(f"{'='*50}\n")

        return (effective_chunk_frames, skip_frames, select_every_nth, "\n".join(log_output))

@register_node
class AutoLoopCalculatorTTS:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "dynamicPrompts": False}),
                "split_mode": (["Párrafos (Saltos de línea)", "Frases (Puntos)"], {"default": "Párrafos (Saltos de línea)"}),
                "current_loop_index": ("INT", {"forceInput": True}),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "INT", "STRING")
    RETURN_NAMES = ("current_text", "current_index", "total_chunks", "log")
    FUNCTION = "calculate"
    CATEGORY = "🔁 Sequential Batcher/Text"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()

    def calculate(self, text, split_mode, current_loop_index):
        log_output = []
        def _log(msg):
            print(msg)
            log_output.append(str(msg))

        from . import loop

        loop.global_step_by_chunk = True

        # 1. Separar el texto según el modo elegido
        if split_mode == "Frases (Puntos)":
            # PASO A: Separación cruda respetando todos los signos
            matches = re.findall(r'[^.!?\n]+[.!?\n]*', text)
            temp_chunks = [m.strip() for m in matches if m.strip()]

            # PASO B: Fusión inteligente (Evitar micro-frases y roturas por "...")
            MIN_WORDS = 5
            raw_chunks = []
            buffer_text = ""

            for chunk in temp_chunks:
                buffer_text = (buffer_text + " " + chunk).strip()
                # Contamos las palabras reales acumuladas en el buffer
                word_count = len(buffer_text.split())

                # Si el bloque ya tiene suficiente "cuerpo", lo cerramos
                if word_count >= MIN_WORDS:
                    raw_chunks.append(buffer_text)
                    buffer_text = ""

            # PASO C: Si quedó texto corto huérfano al final, lo unimos al bloque anterior
            if buffer_text:
                if raw_chunks:
                    raw_chunks[-1] += " " + buffer_text
                else:
                    raw_chunks.append(buffer_text)

            chunk_type_name = "Frases Optimizadas"
        else:
            # Comportamiento original: Dividir por párrafos
            raw_chunks = [p.strip() for p in text.split('\n') if p.strip()]
            chunk_type_name = "Párrafos"

        total_chunks = len(raw_chunks)

        if total_chunks == 0:
            raw_chunks = [""]
            total_chunks = 1

        # 2. Seguridad de índice
        safe_index = min(current_loop_index, total_chunks - 1)
        current_text = raw_chunks[safe_index]

        # 3. 🧠 HACK CORE: Inyectamos los bloques como si fueran frames
        loop.global_source_frame_count = total_chunks
        loop.global_accumulated_frames = safe_index + 1
        loop.global_is_final_chunk = (safe_index + 1) >= total_chunks

        _log(f"\n{'='*50}")
        _log(f"🗣️ [Secuencial Batcher] NODO: Auto Loop Calculator (TTS)")
        _log(f"   -> Modo de división: {split_mode}")
        _log(f"   -> {chunk_type_name} detectados: {total_chunks}")
        _log(f"   -> Timeline: Bloque {safe_index + 1} de {total_chunks}")
        _log(f"   -> 📜 Texto a procesar: {current_text[:75]}...")
        _log(f"{'='*50}\n")

        return (current_text, safe_index, total_chunks, "\n".join(log_output))

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

    RETURN_TYPES = ("IMAGE", "AUDIO", "BOOLEAN", "STRING")
    RETURN_NAMES = ("ALL_IMAGES", "AUDIO_OUT", "IS_FINAL_CYCLE", "log")
    FUNCTION = "stitch"
    CATEGORY = "🔁 Sequential Batcher/Video"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()

    def stitch(self, images, audio, current_loop_index):
        log_output = []
        def _log(msg):
            print(msg)
            log_output.append(str(msg))
        from . import loop
        import os, folder_paths, torch, shutil, time
        from PIL import Image
        import numpy as np
        from concurrent.futures import ThreadPoolExecutor

        cache_dir = os.path.join(folder_paths.get_temp_directory(), "meisoft_video_cache")

        if current_loop_index == 0:
            if os.path.exists(cache_dir):
                try: shutil.rmtree(cache_dir)
                except Exception as e: pass
            os.makedirs(cache_dir, exist_ok=True)
            _log(f"\n🧹 [Stitcher] Ciclo 0 detectado. Subcarpeta temporal limpiada.")
        else:
            os.makedirs(cache_dir, exist_ok=True)

        timestamp = int(time.time() * 1000)

        # 🖼️ GUARDAR IMÁGENES (PNG)
        _log(f"📦 [Stitcher] Guardando {images.shape[0]} frames como PNGs de alta calidad...")
        for i in range(images.shape[0]):
            filename = f"frame_{current_loop_index:04d}_{timestamp}_{i:04d}.png"
            path = os.path.join(cache_dir, filename)
            img_array = 255. * images[i].cpu().numpy()
            img = Image.fromarray(np.clip(img_array, 0, 255).astype(np.uint8))
            img.save(path, format="PNG")

        # 🎵 GUARDAR AUDIO EN CACHÉ (.safetensors)
        if audio is not None:
            audio_path = os.path.join(cache_dir, f"audio_{current_loop_index:04d}_{timestamp}.safetensors")
            # Convert sample_rate to tensor for safetensors compatibility
            audio_data = {
                "waveform": audio["waveform"],
                "sample_rate": torch.tensor(audio["sample_rate"], dtype=torch.int32)
            }
            save_file(audio_data, audio_path)

        source_total = getattr(loop, 'global_source_frame_count', 1)
        is_final_chunk = getattr(loop, 'global_is_final_chunk', False)

        if is_final_chunk or loop.global_accumulated_frames >= source_total:
            _log(f"   -> 🏁 ¡Último ciclo detectado! Ensamblando recursos desde la caché temporal...")

            # 1. ENSAMBLAR VÍDEO
            png_files = sorted([f for f in os.listdir(cache_dir) if f.endswith('.png')])
            if not png_files:
                _log("   -> ❌ ERROR: No se encontraron frames en la subcarpeta.")
                return (images, audio, True, "\n".join(log_output))

            total_frames = len(png_files)
            _log(f"   -> 🧩 Extrayendo {total_frames} frames en paralelo...")

            # Función pura que devuelve el tensor directamente (Sin in-place updates)
            def load_and_process(filename):
                img = Image.open(os.path.join(cache_dir, filename)).convert("RGB")
                img_np = np.array(img).astype(np.float32) / 255.0
                return torch.from_numpy(img_np).unsqueeze(0) # Añadimos batch dimension

            # Usamos map para garantizar el orden secuencial de los resultados
            with ThreadPoolExecutor() as executor:
                tensors_list = list(executor.map(load_and_process, png_files))

            # Concatenamos de forma segura y nativa
            final_tensor = torch.cat(tensors_list, dim=0)

            # 2. ENSAMBLAR AUDIO
            audio_files = sorted([f for f in os.listdir(cache_dir) if f.startswith('audio_') and f.endswith('.safetensors')])
            final_audio = None
            if audio_files:
                _log(f"   -> 🎵 Ensamblando {len(audio_files)} fragmentos de audio...")
                waveforms = []
                sample_rate = 44100
                for af in audio_files:
                    chunk_audio = load_file(os.path.join(cache_dir, af))
                    waveforms.append(chunk_audio["waveform"])
                    sample_rate = chunk_audio["sample_rate"].item()

                # Concatenamos los audios en el eje del tiempo (dimensión -1)
                final_waveform = torch.cat(waveforms, dim=-1)
                final_audio = {"waveform": final_waveform, "sample_rate": sample_rate}
                _log(f"   -> ✅ Audio unificado. Duración total: {final_waveform.shape[-1] / sample_rate:.2f} segundos.")
            else:
                final_audio = audio

            _log(f"✅ [Stitcher] VÍDEO COMPLETADO: {final_tensor.shape[0]} frames ensamblados con éxito.")

            try:
                shutil.rmtree(cache_dir)
                _log(f"🧹 [Stitcher] Subcarpeta temporal destruida.")
            except:
                pass

            return (final_tensor, final_audio, True, "\n".join(log_output))
        else:
            _log(f"   -> ⏳ Ciclo intermedio. Recursos almacenados de forma segura. Pasando frames dummy...")
            dummy_frame = images[-1:].clone()
            return (dummy_frame, None, False, "\n".join(log_output))

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
                "scene_cuts_list": ("SCENE_CUTS", {"forceInput": True}),
            }
        }

    RETURN_TYPES = ("INT", "INT", "INT", "STRING")
    RETURN_NAMES = ("chunk_frames", "skip_frames", "select_every_nth", "log")
    FUNCTION = "calculate"
    CATEGORY = "🔁 Sequential Batcher/Video"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()

    def calculate(self, source_frame_count, target_frames_per_loop, select_every_nth, current_loop_index, safe_faces_list=None, scene_cuts_list=None):
        log_output = []
        def _log(msg):
            print(msg)
            log_output.append(str(msg))

        if source_frame_count <= 0 or target_frames_per_loop <= 0:
            _log("⚠️ [WARNING] Invalid frame count or target frames per loop.")
            return (1, 0, select_every_nth, "\n".join(log_output))

        source_frame_count = min(source_frame_count, 10000)
        select_every_nth = max(1, select_every_nth)

        import math
        from . import loop

        loop.global_step_by_chunk = False

        # --- MEISOFT PATCH: Sincronización Matemática (Hold Last Frame) ---
        # 1. Redondear hacia ARRIBA a la regla 4n+1 (Acolchado WanVideo)
        potential_effective_frames = source_frame_count // select_every_nth

        if potential_effective_frames < 5:
            safe_effective_frames = 5
        else:
            safe_effective_frames = ((potential_effective_frames + 2) // 4) * 4 + 1

        # 🚀 FIX: Conservamos el límite FÍSICO real del vídeo para el timeline global
        physical_source_frame_count = potential_effective_frames * select_every_nth
        loop.global_source_frame_count = physical_source_frame_count
        effective_padding = safe_effective_frames - potential_effective_frames

        loop.global_select_every_nth = select_every_nth

        # 2. Ajuste Proporcional Real (Evitar micro-ciclos al final)
        estimated_loops = math.ceil(safe_effective_frames / target_frames_per_loop)
        if estimated_loops > 0:
            optimal_target = math.ceil(safe_effective_frames / estimated_loops)
            adjusted_target = ((optimal_target + 2) // 4) * 4 + 1
            _log(f"   -> ⚖️ Ajuste Proporcional: Target recalculado de {target_frames_per_loop} a {adjusted_target} frames por ciclo (para {estimated_loops} ciclos)")
            target_frames_per_loop = adjusted_target

        _log(f"   -> 🎞️ Capacidad del video original: {potential_effective_frames} frames (Nth: {select_every_nth})")
        if effective_padding > 0:
            _log(f"   -> 🛡️ Ajuste VAE: Se pedirán {safe_effective_frames} frames (Acolchado técnico: Se rellenarán {effective_padding} frames)")
        else:
            _log(f"   -> ✅ Ajuste VAE: Perfecto. Regla 4n+1 detectada.")

        _log(f"   -> 📊 Timeline final: 0 a {physical_source_frame_count} (Límite Físico Real)")

        current_pos = getattr(loop, 'global_accumulated_frames', 0)

        _log(f"\n{'='*50}")
        _log(f"📊 [Secuencial Batcher] NODO: Auto Loop Calculator (WanVideo 3D VAE)")
        _log(f"   -> Timeline físico ajustado: {current_pos} / {physical_source_frame_count} (Original: {source_frame_count})")

        # Prevención de desbordamiento de bucle (Usando límite físico)
        if current_pos >= physical_source_frame_count:
            return (4, current_pos, select_every_nth, "\n".join(log_output))

        frames_left = physical_source_frame_count - current_pos

        equitable_target = target_frames_per_loop * select_every_nth
        ideal_cut = current_pos + equitable_target

        if frames_left <= equitable_target:
            best_cut = physical_source_frame_count
            _log(f"   -> 🧮 Absorbiendo resto final seguro: meta fijada en frame {best_cut}")
        else:
            if scene_cuts_list and len(scene_cuts_list) > 0:
                future_cuts = [c for c in scene_cuts_list if c > current_pos]
                if future_cuts:
                    next_cut = min(future_cuts)
                    if next_cut <= ideal_cut:
                        chunk_from_scene = math.ceil((next_cut - current_pos) / select_every_nth)
                        safe_chunk_from_scene = (chunk_from_scene // 4) * 4
                        if safe_chunk_from_scene < 4: safe_chunk_from_scene = 4
                        best_cut = current_pos + (safe_chunk_from_scene * select_every_nth)
                        _log(f"   -> 🎬 Bucle aislado por escena (Ajustado x4). Cortando en el frame: {best_cut} (Corte real: {next_cut})")
                    else:
                        best_cut = ideal_cut
                        _log(f"   -> ⚠️ Toma demasiado larga para la VRAM. Cortando por límite técnico en: {best_cut} (El plano real acaba en {next_cut})")
                else:
                    best_cut = ideal_cut
                    _log(f"   -> 🎬 No quedan cortes de cámara por delante. Forzando corte final por VRAM en: {ideal_cut}")
            elif safe_faces_list and len(safe_faces_list) > 0:
                closest_face = min(safe_faces_list, key=lambda x: abs(x - ideal_cut))
                chunk_from_face = math.ceil((closest_face - current_pos) / select_every_nth)
                safe_chunk_from_face = (chunk_from_face // 4) * 4
                if safe_chunk_from_face < 4: safe_chunk_from_face = 4

                best_cut = current_pos + (safe_chunk_from_face * select_every_nth)
                _log(f"   -> ✂️ Corte Facial Inteligente (Ajustado x4): {best_cut} (Cara original detectada: {closest_face})")
            else:
                best_cut = ideal_cut
                _log(f"   -> ⚖️ Sin detectores conectados. Forzando corte equitativo x4: {ideal_cut}")

        # 4. Cálculo final del chunk consolidado a regla 4n+1
        effective_chunk_frames = math.ceil((best_cut - current_pos) / select_every_nth)

        effective_chunk_frames = ((effective_chunk_frames + 2) // 4) * 4 + 1

        if effective_chunk_frames < 5:
            effective_chunk_frames = 5

        # Comprobación contra el límite físico para evitar pedir más allá del final
        if current_pos + (effective_chunk_frames * select_every_nth) >= physical_source_frame_count:
            _log(f"   -> 🏁 Chunk final detectado. Ajustando a {effective_chunk_frames} frames para mantener regla 4n+1.")
            loop.global_is_final_chunk = True
        else:
            loop.global_is_final_chunk = False

        skip_frames = current_pos

        _log(f"   -> 🚀 Ciclo {current_loop_index}: Solicitando {effective_chunk_frames} frames efectivos a VHS (Saltando {skip_frames})")
        _log(f"{'='*50}\n")

        return (effective_chunk_frames, skip_frames, select_every_nth, "\n".join(log_output))
