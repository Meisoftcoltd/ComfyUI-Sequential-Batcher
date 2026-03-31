__version__ = "1.5.1"

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

def register_node(c, display_name=None):
    NODE_CLASS_MAPPINGS[c.__name__] = c
    NODE_DISPLAY_NAME_MAPPINGS[c.__name__] = display_name or c.__name__
    return c

# Importar tools
from . import image, loop, video, tools

NODE_DISPLAY_NAME_MAPPINGS.update({
    "SessionImageReceiver": "📥 Session Image Receiver",
    "SessionImageSender": "📤 Session Image Sender",
    "IncrementalVideoStitcher": "🎞️ Incremental Auto-Stitcher",
    "VideoAnalyzerWithAudio": "🕵️ Video Analyzer + Audio",
    "AutoLoopCalculator": "📊 Auto Loop Calculator",
    "AutoLoopCalculatorWan": "📊 Auto Loop Calculator (WanVideo 3dVAE)",
    "SequentialLoopStart": "🏁 Loop Start (Index)",
    "SequentialLoopTrigger": "🚀 Loop Trigger (Auto-Queue)",
    # Tools
    "ResTool8x": "📐 ResTool 8x (SD1.5)",
    "ResTool16x": "📏 ResTool 16x (SDXL)",
    "ResTool32x": "🎞️ ResTool 32x (WanVideo)",
    "ResTool64x": "🎬 ResTool 64x (Hunyuan)",
})

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
