__version__ = "1.0.0" # Subimos a versión 1.0 ya que es una arquitectura nueva

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

def register_node(c, display_name=None):
    assert not isinstance(c.RETURN_TYPES, str), "Error: string found instead of tuple."
    assert not isinstance(c.RETURN_NAMES, str), "Error: string found instead of tuple."
    NODE_CLASS_MAPPINGS[c.__name__] = c
    NODE_DISPLAY_NAME_MAPPINGS[c.__name__] = display_name or c.__name__
    return c

from . import image, loop, video, tools

# Display name mappings with emojis
NODE_DISPLAY_NAME_MAPPINGS.update({
    # Tools
    "ResTool8x": "📐 ResTool 8x (SD1.5)",
    "ResTool16x": "📏 ResTool 16x (SDXL)",
    "ResTool32x": "🎞️ ResTool 32x (WanVideo)",
    "ResTool64x": "🎬 ResTool 64x (Hunyuan)",

    # Image (Memoria de Sesión)
    "SessionImageReceiver": "📥 Session Image Receiver",
    "SessionImageSender": "📤 Session Image Sender",
    
    # Video (Ensamblaje y Validación)
    "IncrementalVideoStitcher": "🎞️ Incremental Auto-Stitcher",
    "VideoAnalyzerWithAudio": "🕵️ Video Analyzer + Audio",
    "AutoLoopCalculator": "📊 Auto Loop Calculator",

    # Loop (Orquestación Autónoma)
    "SequentialLoopStart": "🏁 Loop Start (Index)",
    "SequentialLoopTrigger": "🚀 Loop Trigger (Auto-Queue)",
})

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']