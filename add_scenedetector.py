import re

def update_node():
    with open('video.py', 'r') as f:
        content = f.read()

    scene_detector_code = """
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

    RETURN_TYPES = ("*", "INT", "FLOAT", "AUDIO", "FACE_CUTS", "IMAGE", "STRING")
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

                # Extracción de Audio
                try:
                    waveform, sample_rate = torchaudio.load(video_path)
                    source_audio = {"waveform": waveform.unsqueeze(0), "sample_rate": sample_rate}
                    _log(f"   -> 🎵 Audio extraído correctamente ({sample_rate}Hz)")
                except Exception as e:
                    source_audio = None
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

        _log(f"{'='*50}\\n")
        return {"ui": ui_result, "result": (video_path, frame_count, source_fps, source_audio, scene_cuts, ref_tensor, "\\n".join(log_output))}

"""

    # Insert after VideoAnalyzerFaceDetector class
    end_of_class = 'return {"ui": ui_result, "result": (video_path, frame_count, source_fps, source_audio, safe_faces, ref_tensor, "\\n".join(log_output))}'
    idx = content.find(end_of_class)
    if idx != -1:
        insert_idx = idx + len(end_of_class) + 1
        new_content = content[:insert_idx] + "\n" + scene_detector_code + "\n" + content[insert_idx:]
        with open('video.py', 'w') as f:
            f.write(new_content)
    else:
        print("Could not find the end of VideoAnalyzerFaceDetector")

if __name__ == '__main__':
    update_node()
