from . import register_node

class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False

@register_node
class LoopIndex:
    """Iterates a number of times."""
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"count": ("INT", {"default": 2, "min": 1, "max": 1000000})}}
    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("index",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "go"
    CATEGORY = "🔁 Sequential Batcher/Loop"
    def go(self, count):
        return (list(range(count)),)

@register_node
class Repeat:
    """Repeats an input N times."""
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "input": (AnyType("*"),),
                "count": ("INT", {"default": 2, "min": 1, "max": 1000000}),
            }
        }
    RETURN_TYPES = (AnyType("*"),)
    RETURN_NAMES = ("output",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "go"
    CATEGORY = "🔁 Sequential Batcher/Loop"
    def go(self, input, count):
        return ([input] * count,)
