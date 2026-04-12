# ♾️ ComfyUI Sequential Batcher
**v1.6.0** | **VRAM-Optimized Generation** | **Recursive Self-Queuing** | **Perfect Audio Sync**

A professional-grade suite of custom nodes for ComfyUI. Designed to bypass extreme VRAM limits in heavy video generation (WanVideo, Hunyuan, LTX) through **Recursive Auto-Queuing**, autonomous batch-by-batch processing, and forensic memory management.

> 🇪🇸 **Leer en Español:** [README.md](README.md)

---

## 🌟 What's New in v1.6.0 (Perfect Sync Update)
* **🛡️ VAE Safe Frame Padder (Hold Last Frame):** The engine now dynamically expands incomplete tensors at the end of the video. If frames are missing to meet the strict requirements of WanVideo (multiples of 4) or LTX (8n+1), it clones the last frame imperceptibly. **Result: Zero VAE crashes and 100% audio sync with no micro-stutters.**
* **📈 Mathematical Inversion to "Expansion":** The `AutoLoopCalculatorWan` and `AutoLoopCalculatorLTX` calculators now safely round the timeline upwards, guaranteeing total fluidity in intermediate cycles.

---

## ✨ Key Features

* **Autonomous Orchestration:** Turn your ComfyUI into a continuous rendering engine. Press "Queue Prompt" just once and the flow will feed itself by modifying seeds and indices until the entire video is finished.
* **Smart Chunking:** Analyzes the base video and makes mathematical cuts protecting the frames where faces are sharpest, maintaining identity coherence (Face Cuts).
* **Native Audio Extraction:** Extracts the original track directly from the initial node and injects it back into the final assembly.
* **DiT Architectures Support (WanVideo & LTX 2.3):** Specific mathematical calculators ensure video batches comply with strict decompression rules (multiples of 4 for WanVideo, or the `8n + 1` rule for LTX).
* **Protected Resolutions (Megapixel Shield):** Mathematical tools (`ResTool`) that automatically scale dimensions protecting the *training floor* of each base model.

---

## ⚠️ System Requirements (Critical)

For the `VideoAnalyzerWithAudio` node to unpack `.mp4` containers and extract audio with `torchaudio`, **FFmpeg is absolutely mandatory**.

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
Processing is divided into highly specialized roles:

* **🕵️ Video Analyzer Face detector + Audio:** Scans the video via OpenCV or using a GPU-accelerated YOLO model. Extracts faces, audio, and the Reference Frame.
* **📊 Auto Loop Calculator (Base / WanVideo / LTX):** Receives the biometrics and calculates cut coordinates (chunk_frames, skip_frames).
* **🛡️ VAE Safe Frame Padder:** Intercepts the final VHS tensor and pads it by cloning the last frame if material is missing, saving the VAE from a collapse.
* **🎞️ Incremental Auto-Stitcher:** Collects rendered batches and the audio track, progressively stitching the final video in the temporary folder.
* **📥 Receiver & 📤 Sender:** Retain and transfer the last valid keyframe across cycles to maintain temporal coherence.
* **⏱️ Auto FPS Limiter:** Smartly reduces FPS guaranteeing audio and motion maintain perfect synchronization without breaking VRAM.
* **🔀 Master Switch (Lazy Evaluation):** Physically amputates wires from inactive routes in the JSON sent to ComfyUI. Heavy nodes not needed in a specific cycle aren't even loaded into memory.
* **🧹 VRAM Defragmenter:** Forensic memory purge (Sacred Sequence) that clears CUDA/MPS cache and forces the Garbage Collector between heavy cycles.

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
The `VideoAnalyzerWithAudio` has a `bbox_detector` port to delegate facial scanning to the graphics card:
1. Install the *Impact Pack*.
2. Add the `UltralyticsDetectorProvider` node and select a face model (e.g. `face_yolov8m.pt`).
3. Connect its output to the Analyzer's port.
*(The node features auto-unload: it will destroy this model from VRAM upon completion to make room for generation).*

---

## 📝 Recent Changelog
* **v1.6.0:** Implementation of `VAESafeFramePadder` (Hold Last Frame) and mathematical redesign to Expansion mode. Goodbye to audio cuts and crashes in the final cycle of WanVideo and LTX.
* **v1.5.4:** Injection of the PyTorch environment variable `max_split_size_mb:128` to avoid VRAM micro-fragmentation with Triton kernels (SageAttention). Early YOLO model auto-unload.
* **v1.5.3:** "Sacred Sequence" in the VRAM Defragmenter (Break cycles -> Soft Evacuation -> IPC Cleanup -> Thread Synchronization).
