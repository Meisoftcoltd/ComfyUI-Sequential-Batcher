import random
import time
import urllib.request
import json
import gc
import torch
import comfy.model_management as mm
from . import register_node

global_loop_index = 0
global_accumulated_frames = 0
global_source_frame_count = 1
global_select_every_nth = 1
global_server_port = 8188  # 💡 NUEVO: Única fuente de la verdad para el puerto
global_ltx_mode = False
global_step_by_chunk = False
global_batch_index = 0
global_has_more_batches = False
global_is_batch_advancing = False

@register_node
class SequentialLoopStart:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "reset_loop": ("BOOLEAN", {"default": False}),
                "loop_idx": ("INT", {"default": 0, "min": 0, "max": 10000}),
                "port": ("INT", {"default": 8188, "min": 1, "max": 65535}), # 💡 FAIL-FAST: Pedimos el puerto aquí
            }
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("current_loop_index",)
    FUNCTION = "get_index"
    CATEGORY = "🔁 Sequential Batcher/Loop"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time()

    def get_index(self, reset_loop, loop_idx, port):
        global global_loop_index
        global global_accumulated_frames
        global global_server_port
        global global_ltx_mode
        global global_batch_index
        global global_is_batch_advancing
        import sys
        import argparse

        print(f"\n{'='*50}")
        print(f"🚀 [DEBUG] NODO: Loop Start (Motor Dinámico)")

        # --- PRE-FLIGHT CHECK (SECURITY SSRF FIX) ---
        parser = argparse.ArgumentParser()
        parser.add_argument("--port", type=int, default=8188)
        try:
            args, _ = parser.parse_known_args(sys.argv[1:])
            system_port = args.port
        except:
            system_port = 8188

        safe_port = system_port
        if port != safe_port:
            print(f"   -> ⚠️ ATENCIÓN: El puerto de entrada ({port}) no coincide con el puerto del sistema ({safe_port}).")
            print(f"   -> 🔒 Por motivos de seguridad (Prevención SSRF), se forzará el puerto real del sistema: {safe_port}.")

        print(f"   -> 📡 Verificando conexión con ComfyUI en el puerto seguro {safe_port}...")
        max_retries = 3
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{safe_port}/system_stats")
                urllib.request.urlopen(req, timeout=10)
                global_server_port = safe_port
                print(f"   -> ✅ Conexión establecida. Puerto blindado y seguro.")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"   -> ⏳ Reintentando conexión ({attempt + 1}/{max_retries}) por alta carga del servidor...")
                    time.sleep(1)

                    error_msg = f"🚨 FATAL ERROR: EL PUERTO {safe_port} NO RESPONDE TRAS VARIOS INTENTOS. El servidor ComfyUI podría estar bloqueado o apagado. (Error original: {e})"
                    print(f"   -> ❌ {error_msg}")
                    raise RuntimeError(error_msg)
        # ------------------------------------

        is_reset = str(reset_loop).lower() in ['true', '1', 't', 'y']

        if is_reset or loop_idx == 0:
            global_loop_index = 0
            global_accumulated_frames = 0
            global_ltx_mode = False
            print("   -> 🔄 Bucle y Acumulador reiniciados a 0.")
        else:
            global_loop_index = loop_idx
            global_is_batch_advancing = False

        print(f"   -> 📍 Índice actual de bucle: {global_loop_index}")
        print(f"{'='*50}\n")
        return (global_loop_index,)

@register_node
class AutoLoopCalculatorTTSBatch:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text_list": ("STRING", {"forceInput": True}),
                "file_names": ("STRING", {"forceInput": True}),
                "split_mode": (["Párrafos (Saltos de línea)", "Frases (Puntos)"], {"default": "Párrafos (Saltos de línea)"}),
                "current_loop_index": ("INT", {"forceInput": True}),
            }
        }

    # 💡 FIX: Mantenemos INPUT_IS_LIST para absorber el batch, pero ELIMINAMOS OUTPUT_IS_LIST
    # para que ComfyUI desempaquete las salidas automáticamente.
    INPUT_IS_LIST = True

    RETURN_TYPES = ("STRING", "INT", "INT", "STRING", "STRING")
    RETURN_NAMES = ("current_text", "current_index", "total_chunks", "current_file_name", "log")
    FUNCTION = "calculate"
    CATEGORY = "🔁 Sequential Batcher/Text"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()

    def calculate(self, text_list, file_names, split_mode, current_loop_index):
        log_output = []
        def _log(msg):
            print(msg); log_output.append(str(msg))

        from . import loop
        import re

        loop.global_step_by_chunk = True

        texts = text_list[0] if (isinstance(text_list, list) and len(text_list) > 0 and isinstance(text_list[0], list)) else (text_list if isinstance(text_list, list) else [text_list])
        names = file_names[0] if (isinstance(file_names, list) and len(file_names) > 0 and isinstance(file_names[0], list)) else (file_names if isinstance(file_names, list) else [file_names])

        mode = split_mode[0] if isinstance(split_mode, list) else split_mode
        idx = current_loop_index[0] if isinstance(current_loop_index, list) else current_loop_index

        # El batch index es extraído directamente de idx para evitar bloqueos
        current_batch_idx = idx

        if current_batch_idx >= len(texts):
            current_batch_idx = len(texts) - 1

        current_file_text = texts[current_batch_idx]
        current_name = names[current_batch_idx] if current_batch_idx < len(names) else "unknown"

        if mode == "Frases (Puntos)":
            matches = re.findall(r'[^.!?\n]+[.!?\n]*', current_file_text)
            temp_chunks = [m.strip() for m in matches if m.strip()]
            MIN_WORDS = 5
            raw_chunks = []
            buffer_text = ""
            for chunk in temp_chunks:
                buffer_text = (buffer_text + " " + chunk).strip()
                if len(buffer_text.split()) >= MIN_WORDS:
                    raw_chunks.append(buffer_text)
                    buffer_text = ""
            if buffer_text:
                if raw_chunks: raw_chunks[-1] += " " + buffer_text
                else: raw_chunks.append(buffer_text)
            chunk_type_name = "Frases Optimizadas"

            raw_chunks = [p.strip() for p in current_file_text.split('\n') if p.strip()]
            chunk_type_name = "Párrafos"

        total_chunks = len(raw_chunks)
        if total_chunks == 0:
            raw_chunks = [""]
            total_chunks = 1

        safe_index = min(idx, total_chunks - 1)
        current_chunk_text = raw_chunks[safe_index]

        loop.global_source_frame_count = total_chunks
        loop.global_accumulated_frames = safe_index + 1
        loop.global_is_final_chunk = (safe_index + 1) >= total_chunks
        loop.global_has_more_batches = (current_batch_idx < len(texts) - 1)

        _log(f"\n{'='*50}")
        _log(f"🗣️ [Secuencial Batcher] NODO: Auto Loop Calculator (TTS Batch)")
        _log(f"   -> Archivo {current_batch_idx + 1} de {len(texts)}: {current_name}")
        _log(f"   -> Modo de división: {mode}")
        _log(f"   -> {chunk_type_name} detectados: {total_chunks}")
        _log(f"   -> Timeline: Bloque {safe_index + 1} de {total_chunks}")
        _log(f"   -> 📜 Texto a procesar: {current_chunk_text[:75]}...")
        _log(f"{'='*50}\n")

        return (current_chunk_text, safe_index, total_chunks, current_name, "\n".join(log_output))

@register_node
class AutoLoopCalculatorLTX:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "source_frame_count": ("INT", {"forceInput": True}),
                "target_frames_per_loop": ("INT", {"default": 81, "min": 9, "max": 257, "step": 8}),
                "select_every_nth": ("INT", {"default": 1, "min": 1, "max": 100}),
                "current_loop_index": ("INT", {"forceInput": True}),
            },
            "optional": {
                "safe_faces_list": ("FACE_CUTS", {"forceInput": True}),
                "scene_cuts_list": ("SCENE_CUTS", {"forceInput": True}),
            }
        }

    RETURN_TYPES = ("INT", "INT", "INT")
    RETURN_NAMES = ("chunk_frames", "skip_frames", "select_every_nth")
    FUNCTION = "calculate"
    CATEGORY = "🔁 Sequential Batcher/Loop"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()

    def calculate(self, source_frame_count, target_frames_per_loop, select_every_nth, current_loop_index, safe_faces_list=None, scene_cuts_list=None):
        if source_frame_count <= 0 or target_frames_per_loop <= 0:
            return (1, 0, select_every_nth)

        source_frame_count = min(source_frame_count, 10000)
        select_every_nth = max(1, select_every_nth)

        # --- Ajuste Proporcional LTX (Regla DiT 8n + 1) ---
        import math
        from . import loop

        loop.global_step_by_chunk = False

        potential_effective_frames = source_frame_count // select_every_nth

        if potential_effective_frames < 9:
            safe_effective_frames = 9

            safe_effective_frames = ((potential_effective_frames + 6) // 8) * 8 + 1

        # 🚀 FIX: Conservamos el límite FÍSICO real del vídeo para el timeline global
        physical_source_frame_count = potential_effective_frames * select_every_nth
        loop.global_source_frame_count = physical_source_frame_count
        effective_padding = safe_effective_frames - potential_effective_frames

        # Ajuste proporcional
        estimated_loops = math.ceil(safe_effective_frames / target_frames_per_loop)
        if estimated_loops > 0:
            optimal_target = math.ceil(safe_effective_frames / estimated_loops)
            adjusted_target = ((optimal_target - 1 + 7) // 8) * 8 + 1
            target_frames_per_loop = adjusted_target
            print(f"   -> ⚖️ Ajuste Proporcional LTX: Target recalculado a {adjusted_target} frames por ciclo.")

        print(f"   -> 🎞️ Capacidad del video original: {potential_effective_frames} frames (Nth: {select_every_nth})")
        if effective_padding > 0:
            print(f"   -> 🛡️ Ajuste VAE: Se pedirán {safe_effective_frames} frames (Acolchado técnico: Se rellenarán {effective_padding} frames)")

            print(f"   -> ✅ Ajuste VAE: Perfecto. Regla 8n+1 detectada.")

        print(f"   -> 📊 Timeline final: 0 a {physical_source_frame_count} (Límite Físico Real)")

        loop.global_select_every_nth = select_every_nth
        global global_ltx_mode
        global_ltx_mode = True

        current_pos = loop.global_accumulated_frames

        print(f"\n{'='*50}")
        print(f"📊 [DEBUG] NODO: Auto Loop Calculator (LTX 2.3)")
        print(f"   -> Timeline físico ajustado a LTX: {current_pos} / {physical_source_frame_count} (Original: {source_frame_count})")

        if current_pos >= physical_source_frame_count:
            return (1, current_pos, select_every_nth)

        frames_left = physical_source_frame_count - current_pos

        equitable_target = target_frames_per_loop * select_every_nth
        ideal_cut = current_pos + equitable_target

        if frames_left <= equitable_target:
            best_cut = physical_source_frame_count
            print(f"   -> 🧮 Absorbiendo resto final: meta fijada en frame {best_cut}")

            if scene_cuts_list and len(scene_cuts_list) > 0:
                future_cuts = [c for c in scene_cuts_list if c > current_pos]
                if future_cuts:
                    next_cut = min(future_cuts)
                    if next_cut <= ideal_cut:
                        chunk_from_scene = math.ceil((next_cut - current_pos) / select_every_nth)
                        safe_chunk_from_scene = ((chunk_from_scene + 6) // 8) * 8 + 1
                        if safe_chunk_from_scene < 9: safe_chunk_from_scene = 9
                        best_cut = current_pos + (safe_chunk_from_scene * select_every_nth)
                        print(f"   -> 🎬 Bucle aislado por escena (Ajustado x8). Cortando en el frame: {best_cut} (Corte real: {next_cut})")

                        best_cut = ideal_cut
                        print(f"   -> ⚠️ Toma demasiado larga para la VRAM. Cortando por límite técnico en: {best_cut} (El plano real acaba en {next_cut})")

                    best_cut = ideal_cut
                    print(f"   -> 🎬 No quedan cortes de cámara por delante. Forzando corte final por VRAM en: {ideal_cut}")
            elif safe_faces_list and len(safe_faces_list) > 0:
                closest_face = min(safe_faces_list, key=lambda x: abs(x - ideal_cut))
                chunk_from_face = math.ceil((closest_face - current_pos) / select_every_nth)
                safe_chunk_from_face = ((chunk_from_face + 6) // 8) * 8 + 1
                if safe_chunk_from_face < 9: safe_chunk_from_face = 9
                best_cut = current_pos + (safe_chunk_from_face * select_every_nth)
                print(f"   -> ✂️ Corte Facial Inteligente (Ajustado x8): {best_cut} (Meta equitativa: {ideal_cut})")

                best_cut = ideal_cut
                print(f"   -> ⚖️ Sin detectores conectados. Forzando corte equitativo x8: {ideal_cut}")

        effective_chunk_frames = math.ceil((best_cut - current_pos) / select_every_nth)
        effective_chunk_frames = ((effective_chunk_frames + 6) // 8) * 8 + 1

        if effective_chunk_frames < 9:
            effective_chunk_frames = 9

        if current_pos + (effective_chunk_frames * select_every_nth) >= physical_source_frame_count:
            print(f"   -> 🏁 Chunk final LTX detectado. Ajustando a {effective_chunk_frames} frames para mantener regla 8n+1.")
            loop.global_is_final_chunk = True

            loop.global_is_final_chunk = False

        skip_frames = current_pos

        print(f"   -> 🚀 Ciclo {current_loop_index}: Solicitando {effective_chunk_frames} frames efectivos (Saltando {skip_frames})")
        print(f"{'='*50}\n")

        return (effective_chunk_frames, skip_frames, select_every_nth)

@register_node
class SequentialLoopTrigger:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "trigger_dependency": ("*", ),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"}
        }

    RETURN_TYPES = ()
    RETURN_NAMES = ()
    OUTPUT_NODE = True
    FUNCTION = "trigger_next"
    CATEGORY = "🔁 Sequential Batcher/Loop"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time()

    def trigger_next(self, trigger_dependency, prompt=None, extra_pnginfo=None):
        global global_loop_index
        global global_accumulated_frames
        global global_source_frame_count
        global global_server_port

        next_loop = global_loop_index + 1
        is_final_chunk = global_accumulated_frames >= global_source_frame_count

        from . import loop
        has_more_batches = getattr(loop, 'global_has_more_batches', False)

        print(f"\n{'='*50}")
        print(f"🎯 [DEBUG] NODO: Loop Trigger")
        print(f"   -> Progreso: {global_accumulated_frames} / {global_source_frame_count} chunks/frames.")

        # 💡 FIX: Reencolar si NO es el final del chunk, O si es el final pero hay más archivos
        if not is_final_chunk or has_more_batches:
            if prompt is not None:
                estimated_chunk = 50
                found_calculator = False
                m_seeds = 0
                master_switches = []

                for node_id, node_data in prompt.items():
                    class_type = node_data.get("class_type", "")
                    inputs = node_data.get("inputs", {})

                    if not found_calculator and "AutoLoopCalculator" in class_type:
                        if "TTS" in class_type:
                            estimated_chunk = 1

                            estimated_chunk = inputs.get("target_frames_per_loop", 50)
                        found_calculator = True

                    for key in ["seed", "noise_seed"]:
                        if key in inputs and isinstance(inputs[key], (int, float)):
                            inputs[key] = random.randint(1, 0x7fffffff)
                            m_seeds += 1

                    if class_type == "SequentialLoopStart":
                        if is_final_chunk and has_more_batches:
                            inputs["loop_idx"] = 0
                            inputs["reset_loop"] = True
                        else:
                            inputs["loop_idx"] = next_loop
                            inputs["reset_loop"] = False

                    if class_type == "MasterSwitch":
                        master_switches.append(inputs)

                # 🛡️ Desempaquetado defensivo universal (Unwrapping de listas de ComfyUI)
                _acc_frames = global_accumulated_frames[0] if isinstance(global_accumulated_frames, list) else global_accumulated_frames
                _src_frames = global_source_frame_count[0] if isinstance(global_source_frame_count, list) else global_source_frame_count
                _est_chunk = estimated_chunk[0] if isinstance(estimated_chunk, list) else estimated_chunk

                # Asegurar casteo a enteros puros para evitar colisiones matemáticas en cualquier flujo
                _acc_frames = int(_acc_frames) if _acc_frames is not None else 0
                _src_frames = int(_src_frames) if _src_frames is not None else 0
                _est_chunk = int(_est_chunk) if _est_chunk is not None else 0

                is_next_final = (_acc_frames + _est_chunk) >= _src_frames
                if is_final_chunk and has_more_batches:
                    is_next_final = False

                for inputs in master_switches:
                    inputs["is_final_cycle"] = is_next_final

                if is_final_chunk and has_more_batches:
                    print(f"   -> 📦 Archivo finalizado. Iniciando siguiente archivo del lote...")
                else:
                    print(f"   -> ⚙️ Preparando Ciclo {next_loop}...")

            p = {"prompt": prompt}
            if extra_pnginfo: p["extra_data"] = {"extra_pnginfo": extra_pnginfo}
            data = json.dumps(p).encode('utf-8')
            req = urllib.request.Request(f"http://127.0.0.1:{global_server_port}/prompt", data=data, headers={'Content-Type': 'application/json'})
            try:
                urllib.request.urlopen(req, timeout=5)
                print(f"   -> ✅ Siguiente ciclo inyectado en la cola.")
            except Exception as e:
                print(f"   -> ❌ Error HTTP: {e}")

        else:
            print(f"   -> 🏁 ¡Generación Finalizada! Todos los archivos del lote completados.")

        print(f"{'='*50}\n")
        return ()

@register_node
class BatchAudioFolderLoader:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "folder_path": ("STRING", {"forceInput": True, "tooltip": "Conectar al output folder_path de Telegram WaitForMultipleFiles"}),
            }
        }

    RETURN_TYPES = ("AUDIO_LIST", "STRING_LIST", "INT", "STRING")
    RETURN_NAMES = ("audio_list", "file_names", "file_count", "log")
    FUNCTION = "load_audios"
    CATEGORY = "🔁 Sequential Batcher/Audio"

    def load_audios(self, folder_path):
        log_output = []
        def _log(msg):
            print(msg); log_output.append(str(msg))

        import os
        import torch
        from .video import extract_and_standardize_audio

        _log(f"\n📂 [Batch Audio Loader] Escaneando lote en: {folder_path}")

        if not folder_path or not os.path.exists(folder_path):
            _log("   -> ❌ ERROR: Directorio nulo o inexistente. Devolviendo silencio.")
            silent = {"waveform": torch.zeros((1, 2, int(0.1 * 44100)), dtype=torch.float32), "sample_rate": 44100}
            return ([silent], ["error_silence.ogg"], 0, "\n".join(log_output))

        valid_extensions = ('.mp3', '.wav', '.ogg', '.flac', '.m4a')
        files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(valid_extensions)])

        if not files:
            _log("   -> ⚠️ No se encontraron archivos de audio en el lote.")
            silent = {"waveform": torch.zeros((1, 2, int(0.1 * 44100)), dtype=torch.float32), "sample_rate": 44100}
            return ([silent], ["empty_silence.ogg"], 0, "\n".join(log_output))

        audio_list = []
        file_names = []

        for f in files:
            path = os.path.join(folder_path, f)
            try:
                _log(f"   -> 🎵 Cargando y estandarizando: {f}")
                audio_dict = extract_and_standardize_audio(path)
                audio_list.append(audio_dict)
                file_names.append(f)
            except Exception as e:
                _log(f"   -> ❌ Error procesando {f}: {e}")

        if not audio_list:
            silent = {"waveform": torch.zeros((1, 2, int(0.1 * 44100)), dtype=torch.float32), "sample_rate": 44100}
            return ([silent], ["error_silence.ogg"], 0, "\n".join(log_output))

        _log(f"   -> ✅ Lote procesado: {len(audio_list)} audios listos en RAM.")
        return (audio_list, file_names, len(audio_list), "\n".join(log_output))

@register_node
class AudioBatchSelector:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "audio_list": ("AUDIO_LIST", {"forceInput": True}),
                "file_names": ("STRING_LIST", {"forceInput": True}),
                "current_loop_index": ("INT", {"forceInput": True}),
            }
        }

    # 💡 AÑADIDOS LOS PINES PARA EL ÍNDICE DEL LOTE
    RETURN_TYPES = ("AUDIO", "STRING", "INT", "INT", "STRING")
    RETURN_NAMES = ("current_audio", "current_file_name", "batch_index", "total_batches", "log")
    FUNCTION = "select"
    CATEGORY = "🔁 Sequential Batcher/Audio"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()

    def select(self, audio_list, file_names, current_loop_index):
        log_output = []
        def _log(msg):
            print(msg); log_output.append(str(msg))

        from . import loop

        # Normalización de listas
        audios = audio_list if isinstance(audio_list, list) else [audio_list]
        names = file_names if isinstance(file_names, list) else [file_names]

        if len(audios) == 1 and isinstance(audios[0], list): audios = audios[0]
        if len(names) == 1 and isinstance(names[0], list): names = names[0]

        idx = current_loop_index[0] if isinstance(current_loop_index, list) else current_loop_index

        # 🧠 FIX: El archivo lo dicta el índice de lote global, NO el índice de ciclo (que es para escenas)
        current_batch_idx = getattr(loop, 'global_batch_index', 0)

        if current_batch_idx >= len(audios):
            current_batch_idx = len(audios) - 1

        current_audio = audios[current_batch_idx]
        current_name = names[current_batch_idx]
        total_audios = len(audios)

        loop.global_has_more_batches = (current_batch_idx < total_audios - 1)

        _log(f"\n{'='*50}")
        _log(f"🎛️ [Secuencial Batcher] NODO: Audio Batch Selector")
        _log(f"   -> Lote (Batch) Actual: {current_batch_idx + 1} de {total_audios}")
        _log(f"   -> Archivo activo: {current_name}")
        _log(f"{'='*50}\n")

        return (current_audio, current_name, current_batch_idx, total_audios, "\n".join(log_output))

import folder_paths
import math

@register_node
class DynamicSceneDirector:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "agent_json": ("STRING", {"multiline": True, "default": '{"scenes": [{"scene_id": 1, "duration_seconds": 5.0, "flux_prompt": "A cinematic wide shot...", "wan_prompt": "Camera pans..."}]}'}),
                "audio_filename": ("STRING", {"default": "audio_track"}),
                "current_loop_index": ("INT", {"default": 0, "min": 0, "max": 10000}),
                "fps": ("INT", {"default": 12, "min": 8, "max": 60}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "INT", "STRING", "STRING")
    RETURN_NAMES = ("flux_prompt", "wan_prompt", "chunk_frames", "image_load_path", "project_json_path")
    FUNCTION = "direct_scene"
    CATEGORY = "🔁 Sequential Batcher/Director"

    def direct_scene(self, agent_json, audio_filename, current_loop_index, fps):
        log_output = []
        def _log(msg): print(msg); log_output.append(str(msg))
        from . import loop
        import os, folder_paths, json, math, re

        idx = current_loop_index[0] if isinstance(current_loop_index, list) else current_loop_index

        _log(f"\n{'='*50}")
        _log(f"🎬 [Director] Evaluando Ciclo: {idx}")

        base_output = folder_paths.get_output_directory()
        safe_audio_name = "".join(c for c in audio_filename if c.isalnum() or c in " _-").strip() or "proyecto"
        plan_path = os.path.join(base_output, f"{safe_audio_name}_plan.json")

        # 1. 🛡️ GESTIÓN DEL JSON (Ignora a Ollama a partir del ciclo 1)
        if idx == 0:
            try:
                # Extracción robusta por si el LLM añade texto extra
                json_match = re.search(r'\{.*\}', agent_json, re.DOTALL)
                raw_json = json_match.group() if json_match else agent_json
                data = json.loads(raw_json)

                with open(plan_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                _log(f"   -> 💾 Plan maestro guardado en: {plan_path}")
            except Exception as e:
                raise ValueError(f"❌ Error al interpretar el JSON del Agente: {e}")
        else:
            try:
                with open(plan_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                _log(f"   -> ♻️ Plan recuperado del disco (Ignorando entrada del Agente).")
            except Exception as e:
                raise ValueError(f"❌ Error al leer el JSON guardado en {plan_path}: {e}")

        scenes = data.get("scenes", [])
        total_scenes = len(scenes)
        if total_scenes == 0: raise ValueError("❌ JSON sin escenas.")

        # 2. ⏱️ MÁQUINA DE ESTADOS (1 Ciclo = 1 Escena)
        # El director es un observador pasivo, scene_idx se deriva directamente de idx
        scene_idx = idx

        if scene_idx >= total_scenes:
            scene_idx = total_scenes - 1

        scene = scenes[scene_idx]

        # 🧠 REGLA APLICADA: Este nodo actúa como "Calculator" del flujo JSON
        loop.global_step_by_chunk = True
        loop.global_source_frame_count = total_scenes
        loop.global_accumulated_frames = scene_idx + 1
        loop.global_is_final_chunk = (scene_idx + 1) >= total_scenes
        loop.global_is_absolute_video_final = loop.global_is_final_chunk

        keyframes_dir = os.path.join(base_output, f"{safe_audio_name}_Keyframes")
        os.makedirs(keyframes_dir, exist_ok=True)

        image_path = os.path.join(keyframes_dir, f"scene_{scene.get('scene_id', scene_idx)}.png")

        flux_prompt = scene.get("flux_prompt", "")
        wan_prompt = scene.get("wan_prompt", "")
        duration = scene.get("duration_seconds", 5.0)
        chunk_frames = math.ceil(duration * fps)

        _log(f"   -> 🎬 Procesando Escena {scene_idx + 1}/{total_scenes} ({duration}s)")
        _log(f"{'='*50}\n")

        return (flux_prompt, wan_prompt, chunk_frames, image_path, plan_path)

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

    RETURN_TYPES = ("IMAGE", "AUDIO", "BOOLEAN", "BOOLEAN", "STRING")
    RETURN_NAMES = ("ALL_IMAGES", "AUDIO_OUT", "IS_FINAL_CYCLE", "IS_ABSOLUTE_FINAL", "log")
    FUNCTION = "stitch"
    CATEGORY = "🔁 Sequential Batcher/Video"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time; return time.time()

    def stitch(self, images, audio, current_loop_index):
        log_output = []
        def _log(msg): print(msg); log_output.append(str(msg))

        from . import loop
        import os, folder_paths, torch, shutil, time
        from PIL import Image
        import numpy as np
        from concurrent.futures import ThreadPoolExecutor

        idx = current_loop_index[0] if isinstance(current_loop_index, list) else current_loop_index
        cache_dir = os.path.join(folder_paths.get_temp_directory(), "meisoft_video_cache")

        if idx == 0:
            if os.path.exists(cache_dir): shutil.rmtree(cache_dir, ignore_errors=True)
            os.makedirs(cache_dir, exist_ok=True)
            _log(f"\n🧹 [Stitcher] Ciclo 0 detectado. Caché general limpiada.")
        else:
            os.makedirs(cache_dir, exist_ok=True)


        timestamp = int(time.time() * 1000)

        for i in range(images.shape[0]):
            filename = f"frame_{idx:04d}_{timestamp}_{i:04d}.png"
            path = os.path.join(cache_dir, filename)
            img_array = 255. * images[i].cpu().numpy()
            Image.fromarray(np.clip(img_array, 0, 255).astype(np.uint8)).save(path, format="PNG")

        if audio is not None:
            audio_path = os.path.join(cache_dir, f"audio_{idx:04d}_{timestamp}.safetensors")
            from safetensors.torch import save_file
            save_file({"waveform": audio["waveform"].contiguous(), "sample_rate": torch.tensor(audio["sample_rate"], dtype=torch.int32)}, audio_path)

        frames_accepted = images.shape[0]
        stride = getattr(loop, 'global_select_every_nth', 1)
        ltx_mode = getattr(loop, 'global_ltx_mode', False)
        advanced_frames = max(1, (frames_accepted - 1) * stride) if ltx_mode else frames_accepted * stride

        # 🧠 PROTECCIÓN: Solo el Stitcher suma frames si NO estamos en modo Chunk (Director/TTS)
        is_chunk_mode = getattr(loop, 'global_step_by_chunk', False)
        if not is_chunk_mode:
            loop.global_accumulated_frames += advanced_frames
            loop.global_is_final_chunk = loop.global_accumulated_frames >= getattr(loop, 'global_source_frame_count', 1)

        is_absolute_final = getattr(loop, 'global_is_absolute_video_final', False) and getattr(loop, 'global_is_final_chunk', False)
        has_more_batches = getattr(loop, 'global_has_more_batches', False)

        if is_absolute_final:
            _log(f"   -> 🏁 ¡Guion Completo! Ensamblando todas las escenas juntas...")
            png_files = sorted([f for f in os.listdir(cache_dir) if f.endswith('.png')])
            if not png_files: return (images, audio, True, True, "\n".join(log_output))

            def load_and_process(filename):
                img_np = np.array(Image.open(os.path.join(cache_dir, filename)).convert("RGB")).astype(np.float32) / 255.0
                return torch.from_numpy(img_np).unsqueeze(0)

            with ThreadPoolExecutor() as executor:
                tensors_list = list(executor.map(load_and_process, png_files))

            final_tensor = torch.cat(tensors_list, dim=0)

            audio_files = sorted([f for f in os.listdir(cache_dir) if f.startswith('audio_') and f.endswith('.safetensors')])
            final_audio = None
            if audio_files:
                waveforms = []
                sample_rate = 44100
                from safetensors.torch import load_file
                for af in audio_files:
                    chunk_audio = load_file(os.path.join(cache_dir, af))
                    waveforms.append(chunk_audio["waveform"])
                    sample_rate = chunk_audio["sample_rate"].item()
                final_audio = {"waveform": torch.cat(waveforms, dim=-1), "sample_rate": sample_rate}

                final_audio = audio

            try: shutil.rmtree(cache_dir)
            except: pass

            return (final_tensor, final_audio, True, not has_more_batches, "\n".join(log_output))

        # 💡 FIX: Retorno de seguridad para ciclos intermedios
        # Devolvemos el último frame procesado para que el flujo no rompa
        return (images[-1:].clone(), None, False, False, "\n".join(log_output))

@register_node
class ProjectPlanLoader:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "audio_filename": ("STRING", {"forceInput": True, "tooltip": "Conectar al 'current_file_name' del Audio Batch Selector"}),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "STRING")
    RETURN_NAMES = ("agent_json", "scene_count", "plan_path")
    FUNCTION = "load_plan"
    CATEGORY = "🔁 Sequential Batcher/Director"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Queremos que siempre lea el archivo más reciente del disco
        import time
        return time.time()

    def load_plan(self, audio_filename):
        log_output = []
        def _log(msg): print(msg); log_output.append(str(msg))

        import os
        import json
        import folder_paths

        _log(f"\n{'='*50}")
        _log(f"📂 [Plan Loader] Buscando proyecto para: {audio_filename}")

        # La misma lógica exacta del DynamicSceneDirector
        base_output = folder_paths.get_output_directory()
        safe_audio_name = "".join(c for c in audio_filename if c.isalnum() or c in " _-").strip() or "proyecto"
        plan_path = os.path.join(base_output, f"{safe_audio_name}_plan.json")

        if not os.path.exists(plan_path):
            raise ValueError(f"❌ Error: No se encontró el plan de proyecto en {plan_path}. Asegúrate de que el Flujo 1 lo haya generado.")

        with open(plan_path, 'r', encoding='utf-8') as f:
            raw_json = f.read()

        try:
            data = json.loads(raw_json)
            scenes = data.get("scenes", [])
            scene_count = len(scenes)
        except Exception as e:
            raise ValueError(f"❌ Error al interpretar el JSON guardado en {plan_path}: {e}")

        _log(f"   -> ✅ Plan cargado con éxito. Escenas detectadas: {scene_count}")
        _log(f"{'='*50}\n")

        return (raw_json, scene_count, plan_path)
