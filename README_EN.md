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
Video processing is divided into 4 highly specialized roles:

* **🕵️ The Explorer (VideoAnalyzerWithAudio):** Scans the video via OpenCV, extracts audio, and outputs a visual Reference Frame. It acts as the ultimate main gateway.
* **📊 The Brain (AutoLoopCalculator):** Receives biometrics from the Explorer and calculates asymmetric cut coordinates (chunk_frames, skip_frames) featuring a ±10% dynamic margin to avoid residual micro-batches.
* **🛠️ The Worker (VHS_LoadVideo):** Freed from analytical tasks, this standard ComfyUI node simply extracts the exact tensors the Brain commands.
* **🎞️ The Assembler (IncrementalVideoStitcher):** Collects the rendered batches and the pristine original audio track, progressively stitching the final video.

## 🔌 Wiring Guide (Workflow Setup)
To build the perfect sequential workflow, follow these steps:

1. **Initial Setup:** Place the 🕵️ Video Analyzer + Audio at the very beginning. Upload a video or connect a STRING cable from your favorite downloader.
2. **The Math:** Route total_frames and safe_faces_list from the Explorer into the 📊 Auto Loop Calculator.
3. **Extraction:** Add a VHS_LoadVideo node. Right-click on it -> Convert Widget to Input -> video. Connect the video_name from the Explorer to this new input. Feed the cutting parameters from the Brain.
4. **Audio Passthrough:** Route the source_audio cable from the Explorer all the way to the audio port of your 🎞️ Incremental Auto-Stitcher (at the end of your workflow).
5. **The Trigger:** Connect your Stitcher's output to the 🚀 Loop Trigger (Auto-Queue) input.
6. **Execution:** Wire the 🏁 Loop Start to the Brain and the Stitcher. Press "Queue Prompt" ONLY ONCE (do not check Auto Queue in the UI). Sit back and enjoy the autonomous magic!

**Changelog v1.5.2:** Automated FFmpeg installation, critical enhancement on ComfyUI pre-flight check bypass for dynamic inputs in the Analyzer, and detailed exposure of torchaudio exceptions.