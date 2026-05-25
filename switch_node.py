class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False

any_type = AnyType("*")

class MasterSwitch:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "is_final_cycle": ("BOOLEAN", {"default": False, "forceInput": False}),
            },
            "optional": {
                "on_true": (any_type,),
                "on_false": (any_type,),
            }
        }

    RETURN_TYPES = (any_type, "STRING")
    RETURN_NAMES = ("output", "log")
    FUNCTION = "route"
    CATEGORY = "🔁 Sequential Batcher/Logic"

    # 🔥 Evaluación Perezosa Nativa (Protege el Ciclo 0)
    def check_lazy_status(self, is_final_cycle, on_true=None, on_false=None):
        if is_final_cycle:
            return ["on_true"]
        else:
            return ["on_false"]

    def route(self, is_final_cycle, on_true=None, on_false=None):
        log_output = []
        def _log(msg):
            print(msg)
            log_output.append(str(msg))
        if is_final_cycle:
            return (on_true, "\n".join(log_output))
        else:
            return (on_false, "\n".join(log_output))


# Diccionario global para persistencia entre ciclos de ejecución
GLOBAL_SESSION_CACHE = {}

class LazySessionCache:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                # Mantenemos el índice como obligatorio para saber en qué ciclo estamos
                "current_loop_index": ("INT", {"default": 0, "forceInput": True}),
            },
            "optional": {
                # 'value_in' DEBE ser opcional para que la evaluación perezosa funcione
                "value_in": (any_type, {"forceInput": True}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID"
            }
        }

    RETURN_TYPES = (any_type, "STRING")
    RETURN_NAMES = ("value_out", "log")
    FUNCTION = "execute"
    CATEGORY = "🔁 Sequential Batcher/Logic"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()

    # 🔥 LA CLAVE: Aquí es donde ComfyUI decide si "tira del cable" o no
    def check_lazy_status(self, current_loop_index, **kwargs):
        # El índice llega como una lista o un int dependiendo del nodo anterior
        idx = current_loop_index[0] if isinstance(current_loop_index, list) else current_loop_index

        if idx == 0:
            # Ciclo 0: Obligamos a ComfyUI a ejecutar todo lo que haya atrás
            return ["value_in"]
        else:
            # Ciclos > 0: NO pedimos 'value_in'. ComfyUI NO ejecutará los nodos anteriores.
            return []

    def execute(self, current_loop_index, value_in=None, unique_id="0"):
        global GLOBAL_SESSION_CACHE
        log_output = []
        def _log(msg):
            print(msg); log_output.append(str(msg))

        idx = current_loop_index[0] if isinstance(current_loop_index, list) else current_loop_index

        _log(f"🧠 [Cache] Ciclo {idx} | Nodo ID: {unique_id}")

        # --- LÓGICA DE CAPTURA (Ciclo 0) ---
        if idx == 0:
            if value_in is not None:
                GLOBAL_SESSION_CACHE[unique_id] = value_in
                _log("   -> 💾 Valor capturado y guardado en RAM.")
                return (value_in, "\n".join(log_output))
            else:
                # Si es el ciclo 0 y no hay nada, algo va mal en el flujo
                raise ValueError(f"❌ Error en LazySessionCache [{unique_id}]: No se recibió valor en el Ciclo 0.")

        # --- LÓGICA DE RECUPERACIÓN (Ciclos > 0) ---
        else:
            if unique_id in GLOBAL_SESSION_CACHE:
                _log("   -> ♻️ Recuperando valor de RAM (Upstream bloqueado con éxito).")
                return (GLOBAL_SESSION_CACHE[unique_id], "\n".join(log_output))
            else:
                # Fallback de seguridad por si el caché se limpió o se saltó el ciclo 0
                _log("   -> ⚠️ No hay caché. Intentando usar entrada directa.")
                return (value_in, "\n".join(log_output))
