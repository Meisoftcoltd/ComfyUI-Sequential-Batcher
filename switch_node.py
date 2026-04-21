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


# Diccionario global para mantener la memoria durante toda la generación (Ciclos 0 a N)
GLOBAL_SESSION_CACHE = {}

class LazySessionCache:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "current_loop_index": ("INT", {"default": 0, "forceInput": True}),
            },
            "optional": {
                "value_in": (any_type,),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID" # Usamos el ID del nodo para no sobreescribir variables si usan varios cachés
            }
        }

    RETURN_TYPES = (any_type, "STRING")
    RETURN_NAMES = ("value_out", "log")
    FUNCTION = "execute"
    CATEGORY = "🔁 Sequential Batcher/Logic"

    # 🔥 Magia Perezosa: Si no es el ciclo 0, cortamos la ejecución de los nodos anteriores
    def check_lazy_status(self, current_loop_index, **kwargs):
        if current_loop_index == 0:
            return ["value_in"] # Exigimos que se evalúe el nodo anterior (Telegram)
        else:
            return []           # No pedimos nada. El nodo anterior NO se ejecuta.

    def execute(self, current_loop_index, value_in=None, unique_id="0"):
        log_output = []
        def _log(msg):
            print(msg)
            log_output.append(str(msg))

        global GLOBAL_SESSION_CACHE

        _log(f"\n{'='*50}")
        _log(f"🧠 [Secuencial Batcher] NODO: Lazy Session Cache (ID: {unique_id})")
        _log(f"   -> Ciclo actual: {current_loop_index}")

        # CICLO 0: Interceptar el valor y guardarlo en la RAM
        if current_loop_index == 0:
            if value_in is not None:
                GLOBAL_SESSION_CACHE[unique_id] = value_in
                _log(f"   -> 💾 GUARDADO en memoria: Nuevo valor capturado.")
                result = value_in
            else:
                raise ValueError(f"❌ LazySessionCache [{unique_id}]: Se esperaba un valor de entrada en el ciclo 0, pero se recibió None. Revisa las conexiones.")

        # CICLOS POSTERIORES: Recuperar de la RAM instantáneamente
        else:
            if unique_id in GLOBAL_SESSION_CACHE:
                result = GLOBAL_SESSION_CACHE[unique_id]
                _log(f"   -> ♻️ RECUPERADO de memoria: Reutilizando valor del ciclo 0.")
            else:
                _log(f"   -> ❌ ERROR: No hay caché. ¿Se saltó el ciclo 0? Devolviendo nulo.")
                result = value_in

        _log(f"{'='*50}\n")

        return (result, "\n".join(log_output))
