import re

def update_node():
    with open('video.py', 'r') as f:
        content = f.read()

    # Create the block to insert for caching
    cache_logic = """
        cache_key = f"{video_path}_face"

        # --- LÓGICA DE CACHÉ / RECUPERACIÓN ---
        if current_loop_index > 0 and cache_key in VIDEO_ANALYSIS_CACHE:
            _log(f"♻️ [Face Detector] Ciclo {current_loop_index}: Recuperando análisis del caché.")
            cached = VIDEO_ANALYSIS_CACHE[cache_key]
            frame_count, source_fps, source_audio, safe_faces = cached
        else:
            # Análisis completo (Solo Ciclo 0 o primer arranque)
            _log(f"🎬 [Face Detector] Ciclo {current_loop_index}: Iniciando análisis profundo...")
            # 1. Extracción de Audio Íntegro
            source_audio = None
            try:
                waveform, sample_rate = torchaudio.load(video_path)
                source_audio = {"waveform": waveform.unsqueeze(0), "sample_rate": sample_rate}
                _log(f"   -> 🎵 Audio extraído correctamente ({sample_rate}Hz)")
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
"""

    import ast
    # Instead of brittle regex, let's just find where to replace
    # we replace from "# 1. Extracción de Audio Íntegro" to "return {"ui": ui_result, "result": (video_path, frame_count, source_fps, source_audio, safe_faces, ref_tensor, "\n".join(log_output))}"

    start_idx = content.find('# 1. Extracción de Audio Íntegro')
    end_str = 'return {"ui": ui_result, "result": (video_path, frame_count, source_fps, source_audio, safe_faces, ref_tensor, "\\n".join(log_output))}'
    end_idx = content.find(end_str) + len(end_str)

    if start_idx != -1 and end_idx != -1:
        new_content = content[:start_idx] + cache_logic.strip() + '\n' + content[end_idx:]
        with open('video.py', 'w') as f:
            f.write(new_content)
    else:
        print("Could not find start/end markers")

if __name__ == '__main__':
    update_node()
