# ♾️ ComfyUI Sequential Batcher
**v1.5.2** | **VRAM-Optimized Generation** | **Recursive Self-Queuing**

A professional-grade suite of custom nodes for ComfyUI. Designed to bypass VRAM limitations in heavy video generation (WanVideo, Hunyuan, etc.) through **Recursive Self-Queuing** and autonomous, batch-by-batch processing.

> 🌍 **Leer en Español:** [README.md](README.md)

---

## ✨ Key Features

* **Autonomous Orchestration:** Turn your ComfyUI into a continuous rendering engine. Press "Queue" once and the workflow will feed itself until the entire video is finished.
* **Smart Chunking:** Analyzes the base video and performs mathematical cuts avoiding the separation of frames where faces are sharpest, thus maintaining identity coherence.
* **Native Audio Extraction:** Extracts the original audio track straight from the entry node and seamlessly injects it back into the final stitch.
* **Dual Input Engine:** The explorer node accepts both manually uploaded videos and dynamically injected string paths from downloaders (e.g., YTDLP), behaving exactly like VideoHelperSuite.
* **Native LTX 2.3 Support:** Specific mathematical calculators (`AutoLoopCalculatorLTX` and `ResTool64xLTX`) have been added to ensure video batches comply with the strict DiT architecture decompression rules and latent downscale factors (resolutions strictly divisible by 64 and frame partitions of `8n + 1`).

---

## ⚠️ System Requirements (Critical)

For the `VideoAnalyzerWithAudio` node to unpack `.mp4` containers and extract audio via `torchaudio`, **FFmpeg is absolutely mandatory**.

* **🐧 Ubuntu / Linux / WSL2:**
  The ComfyUI Manager script will attempt to install it for you. If it fails, run:
  ```bash
  sudo apt update && sudo apt install ffmpeg -y
  ```
* **🪟 Windows:**
  Download the pre-compiled binaries from FFmpeg and add the bin folder to your environment variables (PATH).

## 🧠 The Hybrid Architecture (How it works)
Video processing is divided into highly specialized roles:

* **🕵️ Video Analyzer + Audio (The Explorer):** Scans the video via OpenCV, extracts audio, and outputs a visual Reference Frame. It acts as the ultimate main gateway.
* **📊 Auto Loop Calculator (The Brain):** Receives biometrics from the Explorer and calculates asymmetric cut coordinates (chunk_frames, skip_frames) featuring a ±10% dynamic margin to avoid residual micro-batches.
* **📊 Auto Loop Calculator (WanVideo 3dVAE):** An alternative for WanVideo that ensures frame chunks are strictly multiples of 4, protecting the 3D VAE from crashing.
* **🛠️ The Worker (VHS_LoadVideo):** Freed from analytical tasks, this standard ComfyUI node simply extracts the exact tensors the Brain commands.
* **🎞️ Incremental Auto-Stitcher (The Assembler):** Collects the rendered batches and the pristine original audio track, progressively stitching the final video.
* **📥 Session Image Receiver** and **📤 Session Image Sender:** Hold and pass the last valid keyframe (reference frame) across iterations to maintain temporal identity coherence.
* **⏱️ Auto FPS Limiter (The Synchronizer):** Prevents VRAM OOM errors on high framerate videos (e.g., 60 FPS) by automatically calculating the required frame skip (`select_every_nth`) and adjusting the final FPS to ensure audio and motion maintain perfect synchronization.
* **Protected Resolutions (Megapixel Shield):** Mathematical resolution tools that scale dimensions to avoid artifacts by protecting the "training floor" of each model:
  * **📐 ResTool 8x (SD1.5)**
  * **📏 ResTool 16x (SDXL)**
  * **🎞️ ResTool 32x (WanVideo)**
  * **🎬 ResTool 64x (Hunyuan)**

## 🔌 Wiring Guide (Workflow Setup)
To build the perfect sequential workflow, follow these steps:

1. **Initial Setup:** Place the 🕵️ Video Analyzer + Audio at the very beginning. Upload a video or connect a STRING cable from your favorite downloader.
2. **The Math:** Route total_frames and safe_faces_list from the Explorer into the 📊 Auto Loop Calculator (or 📊 Auto Loop Calculator (WanVideo 3dVAE) if using WanVideo).
3. **Extraction:** Add a VHS_LoadVideo node. Right-click on it -> Convert Widget to Input -> video. Connect the video_name from the Explorer to this new input. Feed the cutting parameters from the Brain.
4. **Audio Passthrough:** Route the source_audio cable from the Explorer all the way to the audio port of your 🎞️ Incremental Auto-Stitcher (at the end of your workflow).
5. **The Trigger:** Connect your Stitcher's output to the 🚀 Loop Trigger (Auto-Queue) input.
6. **Execution:** Wire the 🏁 Loop Start (Index) to the Brain and the Stitcher. Press "Queue Prompt" ONLY ONCE (do not check Auto Queue in the UI). Sit back and enjoy the autonomous magic!

## 🧹 Auto VRAM Cleanup (NEW)
The `SequentialLoopTrigger` node now acts as an intelligent cleanup manager. Once it detects that all frames have been processed and video generation has finished, it automatically:
1. Forces ComfyUI to release all heavy models from memory (WanVideo, VAE, etc.).
2. Triggers Python's garbage collector to eliminate residual memory in RAM.
3. Deeply empties PyTorch caches, supporting multiple platforms (CUDA/ROCm for NVIDIA/AMD, and MPS for Apple Silicon).

This ensures your GPU returns to 0GB usage upon completion, preventing OOM errors in your subsequent generations!

**Changelog v1.5.3:** Introduced an automatic deep VRAM cleanup system within the `SequentialLoopTrigger` node, ensuring complete release of GPU (and RAM) memory after generating heavy videos across CUDA, ROCm, and Mac MPS architectures.
**Changelog v1.5.2:** Automated FFmpeg installation, critical enhancement on ComfyUI pre-flight check bypass for dynamic inputs in the Analyzer, and detailed exposure of torchaudio exceptions.