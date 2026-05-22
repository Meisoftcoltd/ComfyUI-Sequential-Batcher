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

        if port != system_port:
            print(f"   -> ⚠️ ATENCIÓN: El puerto de entrada ({port}) no coincide con el puerto del sistema ({system_port}).")
            print(f"   -> 🔒 Por motivos de seguridad (Prevención SSRF), se forzará el puerto real del sistema: {system_port}.")
            safe_port = system_port
        else:
            safe_port = system_port

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
                else:
                    error_msg = f"🚨 FATAL ERROR: EL PUERTO {safe_port} NO RESPONDE TRAS VARIOS INTENTOS. El servidor ComfyUI podría estar bloqueado o apagado. (Error original: {e})"
                    print(f"   -> ❌ {error_msg}")
                    raise RuntimeError(error_msg)
        # ------------------------------------

        is_reset = str(reset_loop).lower() in ['true', '1', 't', 'y']
        if is_reset or loop_idx == 0:
            global_loop_index = 0
            global_accumulated_frames = 0
            global_ltx_mode = False # 💡 REINICIO DE SEGURIDAD PARA LTX
            print("   -> 🔄 Bucle y Acumulador reiniciados a 0.")

            # 💡 NUEVO: Control de lotes (Batch)
            global global_batch_index, global_is_batch_advancing
            if not global_is_batch_advancing:
                global_batch_index = 0
                print("   -> 🆕 Reinicio completo detectado. Lote (Batch) reiniciado a 0.")
            global_is_batch_advancing = False
        else:
            global_loop_index = loop_idx

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

    RETURN_TYPES = ("STRING", "INT", "INT", "STRING", "STRING")
    RETURN_NAMES = ("current_text", "current_index", "total_chunks", "current_file_name", "log")
    FUNCTION = "calculate"
    CATEGORY = "🔁 Sequential Batcher/Text"

    def calculate(self, text_list, file_names, split_mode, current_loop_index):
        log_output = []
        def _log(msg):
            print(msg); log_output.append(str(msg))

        from . import loop
        import re

        loop.global_step_by_chunk = True

        # Desempaquetado seguro para evitar dobles listas de ComfyUI
        texts = text_list[0] if (isinstance(text_list, list) and len(text_list) > 0 and isinstance(text_list[0], list)) else (text_list if isinstance(text_list, list) else [text_list])
        names = file_names[0] if (isinstance(file_names, list) and len(file_names) > 0 and isinstance(file_names[0], list)) else (file_names if isinstance(file_names, list) else [file_names])

        mode = split_mode
        idx = current_loop_index

        current_batch_idx = getattr(loop, 'global_batch_index', 0)
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
        else:
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
        else:
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
        else:
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
        else:
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
                    else:
                        best_cut = ideal_cut
                        print(f"   -> ⚠️ Toma demasiado larga para la VRAM. Cortando por límite técnico en: {best_cut} (El plano real acaba en {next_cut})")
                else:
                    best_cut = ideal_cut
                    print(f"   -> 🎬 No quedan cortes de cámara por delante. Forzando corte final por VRAM en: {ideal_cut}")
            elif safe_faces_list and len(safe_faces_list) > 0:
                closest_face = min(safe_faces_list, key=lambda x: abs(x - ideal_cut))
                chunk_from_face = math.ceil((closest_face - current_pos) / select_every_nth)
                safe_chunk_from_face = ((chunk_from_face + 6) // 8) * 8 + 1
                if safe_chunk_from_face < 9: safe_chunk_from_face = 9
                best_cut = current_pos + (safe_chunk_from_face * select_every_nth)
                print(f"   -> ✂️ Corte Facial Inteligente (Ajustado x8): {best_cut} (Meta equitativa: {ideal_cut})")
            else:
                best_cut = ideal_cut
                print(f"   -> ⚖️ Sin detectores conectados. Forzando corte equitativo x8: {ideal_cut}")

        effective_chunk_frames = math.ceil((best_cut - current_pos) / select_every_nth)
        effective_chunk_frames = ((effective_chunk_frames + 6) // 8) * 8 + 1

        if effective_chunk_frames < 9:
            effective_chunk_frames = 9

        if current_pos + (effective_chunk_frames * select_every_nth) >= physical_source_frame_count:
            print(f"   -> 🏁 Chunk final LTX detectado. Ajustando a {effective_chunk_frames} frames para mantener regla 8n+1.")
            loop.global_is_final_chunk = True
        else:
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
                        else:
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

                is_next_final = (global_accumulated_frames + estimated_chunk) >= global_source_frame_count
                if is_final_chunk and has_more_batches:
                    is_next_final = False

                for inputs in master_switches:
                    inputs["is_final_cycle"] = is_next_final

                if is_final_chunk and has_more_batches:
                    loop.global_batch_index = getattr(loop, 'global_batch_index', 0) + 1
                    loop.global_is_batch_advancing = True
                    print(f"   -> 📦 Archivo finalizado. Iniciando archivo {loop.global_batch_index + 1} del lote...")
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

            import gc, torch
            gc.collect()
            if torch.cuda.is_available(): torch.cuda.empty_cache()

        else:
            print(f"   -> 🏁 ¡Generación Finalizada! Todos los archivos del lote completados.")
            # ... Mantener aquí el código existente de limpieza extrema de VRAM (mm.unload_all_models, malloc_trim, etc.) ...
            print(f"   -> 🧹 Iniciando vaciado automático de VRAM...")
            import gc
            import torch
            import comfy.model_management as mm
            try:
                mm.unload_all_models()
                mm.soft_empty_cache()
            except Exception as e:
                pass
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
                import ctypes
                try: ctypes.CDLL('libc.so.6').malloc_trim(0)
                except Exception: pass
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                torch.mps.empty_cache()
            print(f"   -> ✨ VRAM liberada con éxito. Gráfica lista para nuevos flujos.")

        print(f"{'='*50}\n")
        return ()
