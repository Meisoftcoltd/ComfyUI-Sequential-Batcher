__version__ = "0.9.3-beta"

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}


def register_node(c, display_name=None):
    assert not isinstance(c.RETURN_TYPES, str), "Error: string found instead of tuple."
    assert not isinstance(c.RETURN_NAMES, str), "Error: string found instead of tuple."
    NODE_CLASS_MAPPINGS[c.__name__] = c
    NODE_DISPLAY_NAME_MAPPINGS[c.__name__] = display_name or c.__name__
    return c


from . import sequence, paths, batch, image, debug, loop, video

# Display name mappings with emojis
NODE_DISPLAY_NAME_MAPPINGS.update({
    # Sequence
    "Range": "🔢 Range",
    "Literal": "📝 Literal",
    "Reorder": "🔄 Reorder",
    "Combinations": "🧬 Combinations",
    "Permutations": "🔀 Permutations",
    "Slice": "✂️ Slice",
    "Join": "🔗 Join",
    "ModelFinder": "🔍 Model Finder",
    
    # Batch
    "MakeBatch": "🛠️ Make Batch",
    "CombineBatches": "🖇️ Combine Batches",
    "EnumerateBatch": "🔢 Enumerate Batch",
    "GetBatchStep": "📍 Get Batch Step",
    "FormatAttributes": "📝 Format Attributes",
    "GetAttribute": "📥 Get Attribute",
    "GetAttributeInt": "📥 Get Attribute (Int)",
    "GetAttributeFloat": "📥 Get Attribute (Float)",
    "GetAttributeString": "📥 Get Attribute (String)",
    "BatchToList": "🔄 Batch To List",
    "LoadCSV": "📂 Load CSV",
    "PreviewBatch": "📊 Preview Batch",
    
    # Image
    "JoinImageBatch": "🖼️ Join Image Batch",
    "JoinImages": "🖼️ Join Images",
    "SelectImageBatch": "🎯 Select Image Batch",
    "SelectImageList": "🎯 Select Image List",
    "GetImageSize": "📏 Get Image Size",
    "StringToImage": "🔤 String To Image",
    "ProgressBar": "⏳ Progress Bar",
    "ImageBatchToList": "🖼️ Image Batch To List",
    "ImageListToBatch": "🖼️ Image List To Batch",
    "LatentBatchToList": "🎞️ Latent Batch To List",
    "LatentListToBatch": "🎞️ Latent List To Batch",
    
    # Video
    "FFmpegVideoStitcher": "🎞️ FFmpeg Video Stitcher",
    "IncrementalVideoStitcher": "🎞️ Incremental Auto-Stitcher",

    # Debug
    "Stringify": "🧵 Stringify",
    "Interact": "⌨️ Interact",
    
    # Loop
    "LoopIndex": "🔁 Sequential Loop Index",
    "Repeat": "🔁 Repeat",
})

# Backward compatibility for "Job" naming
NODE_CLASS_MAPPINGS.update({
    "MakeJob": batch.MakeBatch,
    "CombineJobs": batch.CombineBatches,
    "EnumerateJob": batch.EnumerateBatch,
    "GetJobStep": batch.GetBatchStep,
    "JobToList": batch.BatchToList,
})
