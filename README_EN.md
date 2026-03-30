# ComfyUI Sequential Batcher (v1.5.1)

A highly specialized suite of custom nodes for ComfyUI designed for **Recursive Self-Queuing** and autonomous sequential processing. This architecture minimizes VRAM usage by processing heavy tasks (like video generation) sequentially, batch-by-batch, orchestrated entirely from within the graph itself.

> **Leer en Español:** [README.md](README.md)

---

## 🌟 The Hybrid Identity Architecture

The **Hybrid Identity Architecture** (introduced in v1.4.1) eliminates the technical debt of older coupled loaders and divides video processing into three main logical roles:

1. **🕵️ The Explorer (`VideoAnalyzerWithAudio`)**: Natively integrated with VideoHelperSuite, it uses OpenCV to scan the input video for sharp faces, extracts the pure intact audio track (via Torchaudio), and **generates and outputs a Reference Frame (Visual Preview)** in image format (`IMAGE`) directly onto the ComfyUI canvas.
2. **📊 The Brain (`AutoLoopCalculator`)**: Receives the safe frames list from the Explorer and plans asymmetric, intelligent cuts (`chunk_frames`, `skip_frames`). It prioritizes cuts on frames where the face is sharp to maintain identity coherence across loops, and includes a **Dynamic ±10% Margin** to absorb final remainders without creating inefficient small batches.
3. **🛠️ The Worker (`VHS_LoadVideo`)**: The standard ComfyUI VideoHelperSuite node is now solely responsible for the heavy lifting: extracting the exact video tensors according to the Brain's orders.

---

## 🧩 The Core Nodes

The system is organized into four main categories in the ComfyUI interface under the `🔁 Sequential Batcher` menu:

### 🔁 Loop (Autonomous Orchestration)

1. **`🏁 Loop Start (Index)`**
   - **Inputs:** `reset_loop` (BOOLEAN), `loop_idx` (INT)
   - **Outputs:** `current_loop_index` (INT)
   - **Description:** Initiates the loop, manages the global loop index, and provides the current iteration index to image and video nodes downstream.

2. **`🚀 Loop Trigger (Auto-Queue)`**
   - **Inputs:** `trigger_dependency` (*), `port` (INT)
   - **Description:** Placed at the very end of your workflow. It increments the counter and autonomously triggers an HTTP POST request to the ComfyUI API (`/prompt`) to queue the next cycle.
   - **Special Functions:**
     - **Seed Mutator:** Injects new random 32-bit seeds into any node with a `seed` or `noise_seed` on the canvas to break forward cache.
     - **💉 Anti-Cache Injection:** Specifically searches for the `Loop Start` node within the JSON payload and forcefully injects the new index to shatter the reverse cache that freezes workflow progression.

### 🖼️ Image (Session Memory)

3. **`📥 Session Image Receiver`**
   - **Inputs:** `initial_image` (IMAGE), `current_loop_index` (INT)
   - **Outputs:** `current_image` (IMAGE)
   - **Description:** Retrieves the initial image or the last generated frame from the previous cycle, recovering the session stored in global RAM.

4. **`📤 Session Image Sender`**
   - **Inputs:** `generated_images` (IMAGE), `current_loop_index` (INT), `validate_face` (BOOLEAN)
   - **Outputs:** `VALIDATED_IMAGES` (IMAGE)
   - **Description:** Extracts the final valid image from a batch and secures it in system global memory (`.clone().cpu()`) for the next cycle.
   - **Special Functions:**
     - **💾 Keyframe Dumping:** Performs a safety dump to the hard drive, progressively saving `keyframe_XXX.png` every cycle.
     - **🏎️ Dynamic F1 Engine:** Dynamically truncates the generated tensor backwards looking for the last valid face (if `validate_face` is True), and updates the global accumulator so the `Auto Loop Calculator` readjusts the next cycle seamlessly, avoiding audio desyncs.

### 🛠️ Tools (Resolutions & Megapixel Shield)

Dedicated nodes to calculate strictly divisible safe resolutions, shielding your VRAM from tensor mismatch errors by applying strict downward mathematical constraints.

- **`📐 ResTool 8x (SD1.5)`**: Multiples of 8. Native base ~262,144 px.
- **`📏 ResTool 16x (SDXL)`**: Multiples of 16. Native base ~1,048,576 px.
- **`🎞️ ResTool 32x (WanVideo)`**: Multiples of 32. Native base ~399,360 px.
- **`🎬 ResTool 64x (Hunyuan)`**: Multiples of 64. Native base ~921,600 px.

**All Tools share the same interface:**
- **Inputs:** `aspect_ratio` (e.g., 16:9, 9:16), `base_resolution` (Free INT numerical field, write the exact value you need, e.g., 832 or 1024)
- **Outputs:** `width` (INT), `height` (INT), `debug_info` (STRING)

> **🛡️ Megapixel Shield (NEW in v1.5.1):** Each tool knows its model's "training floor" area. If you request an extreme aspect ratio that falls below this vital threshold, the node will first scale the resolution up proportionally to protect the generation against melting artifacts, and only then apply strict divisibility.

### 🎞️ Video (Assembly and Validation)

5. **`🕵️ Video Analyzer + Audio`**
   - **Inputs:** `video` (STRING), `reference_frame_idx` (INT), `use_face_detector` (BOOLEAN), `blur_threshold` (FLOAT)
   - **Outputs:** `video_name` (STRING), `total_frames` (INT), `source_fps` (FLOAT), `source_audio` (AUDIO), `safe_faces_list` (FACE_CUTS), `reference_frame` (IMAGE)
   - **Description:** Scans the video using OpenCV to detect sharp faces, extracts the pure audio track using Torchaudio, and outputs a visual and tensor Reference Frame (`IMAGE`).

6. **`📊 Auto Loop Calculator`**
   - **Inputs:** `source_frame_count` (INT), `target_frames_per_loop` (INT), `select_every_nth` (INT), `current_loop_index` (INT)
   - **Optional Input:** `safe_faces_list` (FACE_CUTS)
   - **Outputs:** `chunk_frames` (INT), `skip_frames` (INT), `select_every_nth` (INT)
   - **Description:** Calculates frame cuts asymmetrically based on safe faces and applies the dynamic ±10% margin.

7. **`🎞️ Incremental Auto-Stitcher`**
   - **Inputs:** `images` (IMAGE), `audio` (AUDIO), `current_loop_index` (INT)
   - **Outputs:** `ALL_IMAGES` (IMAGE), `AUDIO_OUT` (AUDIO)
   - **Description:** Progressively archives generated tensors temporarily to the hard drive (`.pt`), clearing RAM immediately (**Zero OOM**). On the final cycle, it safely assembles all blocks utilizing a clean passthrough of the original audio track.

---

## 🚀 Setup & Usage

### Prerequisites
- **VideoHelperSuite (VHS)**: Mandatory for the "Worker" extraction node (`VHS_LoadVideo`).
- **OpenCV (`opencv-python`)**: Required for the Explorer (`VideoAnalyzerWithAudio`). Face detection will safely fail without it.
- **FFmpeg**: Must be installed and available in your system's PATH.
- **Torchaudio**: Required for pure audio extraction (usually pre-installed with PyTorch).

### Installation
1. Navigate to your ComfyUI `custom_nodes` folder.
2. Run: `git clone https://github.com/your-repo/ComfyUI-Sequential-Batcher.git`
3. Install required dependencies if needed: `pip install -r requirements.txt` (or `pip install opencv-python`).
4. Restart ComfyUI.

### 🔌 Hybrid Architecture Connection Guide

1. **The Explorer (`🕵️ Video Analyzer + Audio`)**: Place this node at the very beginning of your workflow and upload/select your source video.
2. **The Brain (`📊 Auto Loop Calculator`)**:
   - Connect the `total_frames` from the Explorer to `source_frame_count`.
   - Connect the `safe_faces_list` from the Explorer (optional but highly recommended).
   - Connect the `current_loop_index` from the `🏁 Loop Start` node.
3. **The Worker (`VHS_LoadVideo`)**:
   - Right-click on this standard VHS node and select **Convert Widget to Input -> video**.
   - Connect the `video_name` from the Explorer to the `video` input on the Worker.
   - Connect the `chunk_frames`, `skip_frames`, and `select_every_nth` from the Brain to their respective pins on the Worker.
4. **Audio Passthrough**: Pull a cable directly from the `source_audio` output of the Explorer and connect it to the `audio` port of your `🎞️ Incremental Auto-Stitcher` at the end of the workflow.
5. **Loop Closure (`🚀 Loop Trigger`)**: Connect the image or audio output from your Auto-Stitcher into the `trigger_dependency` input.
6. **Execution**: Press **"Queue Prompt" ONLY ONCE** (do not check the Auto Queue box in the Comfy interface). The Trigger node will handle the recursive self-queuing autonomously in the background.

---
*Designed and optimized to push the boundaries of ComfyUI sequential automation and identity coherence.*
