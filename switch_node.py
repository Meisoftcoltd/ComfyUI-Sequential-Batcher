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

    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("output",)
    FUNCTION = "route"
    CATEGORY = "🔁 Sequential Batcher/Logic"

    # 🔥 Evaluación Perezosa Nativa (Protege el Ciclo 0)
    def check_lazy_status(self, is_final_cycle, on_true=None, on_false=None):
        if is_final_cycle:
            return ["on_true"]
        else:
            return ["on_false"]

    def route(self, is_final_cycle, on_true=None, on_false=None):
        if is_final_cycle:
            return (on_true,)
        else:
            return (on_false,)
