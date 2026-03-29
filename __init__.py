__version__ = "1.0.0" # Subimos a versión 1.0 ya que es una arquitectura nueva

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

def register_node(c, display_name=None):
    assert not isinstance(c.RETURN_TYPES, str), "Error: string found instead of tuple."
    assert not isinstance(c.RETURN_NAMES, str), "Error: string found instead of tuple."
    NODE_CLASS_MAPPINGS[c.__name__] = c
    NODE_DISPLAY_NAME_MAPPINGS[c.__name__] = display_name or c.__name__
    return c

from . import image, loop, video

# Display name mappings with emojis
NODE_DISPLAY_NAME_MAPPINGS.update({
    # Image (Memoria de Sesión)
    "SessionImageReceiver": "📥 Session Image Receiver",
    "SessionImageSender": "📤 Session Image Sender",
    
    # Video (Ensamblaje y Validación)
    "IncrementalVideoStitcher": "🎞️ Incremental Auto-Stitcher",
    "LoadVideoWithSourceAudio": "🎥 Load Video + Source Audio",
    "AutoLoopCalculator": "📊 Auto Loop Calculator",

    # Loop (Orquestación Autónoma)
    "SequentialLoopStart": "🏁 Loop Start (Index)",
    "SequentialLoopTrigger": "🚀 Loop Trigger (Auto-Queue)",
})

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']