import os

__version__ = "1.6.0"

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

def register_node(c, display_name=None):
    NODE_CLASS_MAPPINGS[c.__name__] = c
    NODE_DISPLAY_NAME_MAPPINGS[c.__name__] = display_name or c.__name__
    return c

# Importar tools
from . import image, loop, video, tools, vram_node
from .switch_node import MasterSwitch, LazySessionCache

NODE_CLASS_MAPPINGS.update({
    "MasterSwitch": MasterSwitch,
    "LazySessionCache": LazySessionCache,
})

NODE_DISPLAY_NAME_MAPPINGS.update({
    "MasterSwitch": "🔀 Master Switch",
    "LazySessionCache": "🗄️ Lazy Session Cache",
    "MeisoftVRAMDefragmenter": "🧹 VRAM Defragmenter",
    "SessionImageReceiver": "📥 Session Image Receiver",
    "SessionImageSender": "📤 Session Image Sender",
    "IncrementalVideoStitcher": "🎞️ Incremental Auto-Stitcher",
    "VideoAnalyzerFaceDetector": "🕵️ Video Analyzer Face detector + Audio",
    "VideoAnalyzerSceneDetector": "🎬 Video Analyzer Scene detector",
    "AutoLoopCalculator": "📊 Auto Loop Calculator",
    "AutoLoopCalculatorWan": "📊 Auto Loop Calculator (WanVideo 3dVAE)",
    "AutoLoopCalculatorLTX": "📊 Auto Loop Calculator (LTX 2.3)",
    "SequentialLoopStart": "🏁 Loop Start (Index)",
    "SequentialLoopTrigger": "🚀 Loop Trigger (Auto-Queue)",
    # Tools
    "AutoFPSLimiter": "⏱️ Auto FPS Limiter",
    "VAESafeFramePadder": "🛡️ VAE Safe Frame Padder",
    "ResTool8x": "📐 ResTool 8x (SD1.5)",
    "ResTool16x": "📏 ResTool 16x (SDXL)",
    "ResTool32x": "🎞️ ResTool 32x (WanVideo)",
    "ResTool64x": "🎬 ResTool 64x (Hunyuan)",
    "ResTool64xLTX": "🌌 ResTool 64x (LTX 2.3)",
    "ConditionalAudioRouter": "🎛️ Conditional Audio Router (Bypass)",
})

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
