# ♾️ ComfyUI Sequential Batcher
**v0.8.3** | **VRAM-Optimized Generation** | **Recursive Self-Queuing** | **Perfect Audio Sync**

A professional-grade suite of custom nodes for ComfyUI. Designed to bypass extreme VRAM limits in heavy video generation (WanVideo, Hunyuan, LTX) through **Recursive Auto-Queuing**, autonomous batch-by-batch processing, and forensic memory management.

> 🇪🇸 **Leer en Español:** [README.md](README.md)

---

## ✨ Key Features

* **Autonomous Orchestration:** Turn your ComfyUI into a continuous rendering engine. Press "Queue Prompt" just once and the flow will feed itself by modifying seeds and indices until the entire video is finished.
* **Smart Chunking:** Analyzes the base video and makes mathematical cuts protecting the frames where faces are sharpest, maintaining identity coherence (Face Cuts).
* **Native Audio Extraction:** Extracts the original track directly from the initial node and injects it back into the final assembly.
* **DiT Architectures Support (WanVideo & LTX 2.3):** Specific mathematical calculators ensure video batches comply with strict decompression rules (multiples of 4 for WanVideo, or the `8n + 1` rule for LTX).
* **Protected Resolutions (Megapixel Shield):** Mathematical tools (`ResTool`) that automatically scale dimensions protecting the *training floor* of each base model.

---

## ⚠️ System Requirements (Critical)

For the `VideoAnalyzerFaceDetector` node to unpack `.mp4` containers and extract audio with `torchaudio`, **FFmpeg is absolutely mandatory**.

* **🐧 Ubuntu / Linux / WSL2:**
  The script will attempt to install it for you. If it fails, run manually:
  ```bash
  sudo apt update && sudo apt install ffmpeg -y
  ```
* **🪟 Windows:**
  Download the precompiled FFmpeg binaries and add the `bin` folder to your environment variables (PATH).

### 🚨 Critical Warning Regarding VRAM Usage
The use of the `--highvram` argument when starting ComfyUI is **strongly discouraged**.

The `--highvram` argument gives ComfyUI the strict command to keep models locked in video memory. This directly sabotages the operation of our `VRAM Defragmenter`, as it blocks the `mm.unload_all_models()` command, preventing the graphics card from emptying between cycles. For this suite to work correctly with massive models like WanVideo and avoid OOM (Out Of Memory) errors, users must use the standard startup (or `--normalvram`), allowing the system to dynamically release memory down to 0 GB between batches.

---

## 🧠 The Hybrid Architecture (Node Breakdown)

Processing is divided into highly specialized roles, organized in the following categories:

### 🎼 Orchestration
* **🏁 Loop Start (Index):** Starts the loop sequence and tracks the current index.
* **🚀 Loop Trigger (Auto-Queue):** Autonomously triggers the next ComfyUI iteration until the task is complete.

### 🎬 Director / Storyboard
* **🎬 Dynamic Scene Director:** State machine to orchestrate metadata (prompts, durations) in preproduction (Split-Workflow).
* **💾 Save Scene Keyframe / 🖼️ Load Scene Keyframe:** Saves and loads the scene's keyframes to maintain continuity across decoupled flows.

### 📦 Batches
* **📂 Batch Audio Folder Loader:** Dynamically loads entire folders of files (e.g. audio batches).
* **🎛️ Audio Batch Selector:** Dispatches files from the batch one by one in sync with the loop.

### 🔬 Analysis and Calculations
* **🕵️ Video Analyzer Face detector + Audio:** Scans the video via OpenCV/YOLO, extracting faces, audio, and the reference frame.
* **🎬 Video Analyzer Scene detector:** Detects scene cuts in videos.
* **📊 Auto Loop Calculators:** Specialized nodes (`Base`, `WanVideo`, `LTX`, `TTS`) that receive metadata and mathematically calculate the exact cut coordinates (`chunk_frames`, `skip_frames`).

### 🎞️ Video
* **🎞️ Incremental Auto-Stitcher:** Progressively stitches rendered video chunks into a single final file.
* **🛡️ VAE Safe Frame Padder:** Pads incomplete tensors by cloning the last frame to save the VAE from a collapse in restrictive models (e.g. 4n+1 rules).
* **💉 LTXV Single Frame Injector:** Injects specific individual frames required by LTX flows.
* **⏱️ Auto FPS Limiter:** Smartly limits frames per second to save VRAM while maintaining audio sync.

### 🎵 Audio
* **✂️ Precise Audio Slicer:** Precisely slices audio (at mathematical sample level) based on the corresponding video frames.
* **🎛️ Conditional Audio Router (Bypass):** Conditionally routes audio allowing its processing to be bypassed if not needed.

### 📐 Resolution Tools
* **ResTool (`8x`, `16x`, `32x`, `64x`, `64xLTX`):** Calculate optimal resolutions based on VRAM limits and geometric rules (multipliers) of different models (SD1.5, SDXL, WanVideo, Hunyuan, LTX).

### 🧠 Memory Management / Logic
* **🔀 Master Switch & 🗄️ Lazy Session Cache:** Native lazy evaluation; they cut inactive routes so heavy nodes aren't even loaded into memory.
* **🧹 VRAM Defragmenter:** Forensic memory purge (Sacred Sequence) that clears CUDA/MPS cache and forces the Python Garbage Collector (GC) between cycles.
* **📥 Session Image Receiver / 📤 Session Image Sender:** Retain and transfer in-memory images across different cycles.

---

## 🔌 Quick Wiring Guide (Workflow Setup)

1. **The Explorer:** Place the `Video Analyzer` at the beginning. Upload a video (or use a YTDLP path).
2. **Math:** Connect `total_frames` and `safe_faces_list` to your chosen `Auto Loop Calculator`.
3. **Safe Extraction:** Add the native `VHS_LoadVideo` node. Convert its input to *video_name* and connect it to the Analyzer. Connect its `IMAGE` output to the new `VAE Safe Frame Padder` node.
4. **Audio Passthrough:** Route the `source_audio` wire from the Explorer directly to the `audio` port of your `Incremental Auto-Stitcher` (at the end of the flow).
5. **The Trigger:** Connect the output of your Stitcher to the `Loop Trigger (Auto-Queue)` node.
6. **Execution:** Connect the `Loop Start (Index)` to the Brain and the Stitcher.
7. **Fire:** Click "Queue Prompt" **JUST ONCE**. Enjoy the autonomous magic!

---

## 🚀 GPU Acceleration (Face Scanning)
The `VideoAnalyzerFaceDetector` has a `bbox_detector` port to delegate facial scanning to the graphics card:
1. Install the *Impact Pack*.
2. Add the `UltralyticsDetectorProvider` node and select a face model (e.g. `face_yolov8m.pt`).
3. Connect its output to the Analyzer's port.
*(The node features auto-unload: it will destroy this model from VRAM upon completion to make room for generation).*
