# ComfyUI Sequential Batcher (v1.5.0)

A highly specialized suite of custom nodes for ComfyUI designed for **Recursive Self-Queuing** and autonomous sequential processing. This architecture minimizes VRAM usage by processing heavy tasks (like video generation) sequentially, batch-by-batch, orchestrated entirely from within the graph.

> **Leer en Español:** [README.md](README.md)

## The Hybrid Identity Architecture

Starting with version 1.4.1, we have taken a step further by implementing the **Hybrid Identity Architecture**. All technical debt from older coupled loaders has been eliminated. Now, video processing is divided into three main logical roles:

1. **The Explorer (`VideoAnalyzerWithAudio`)**: A redesigned node with an ultra-clean interface (natively integrated with the VideoHelperSuite widget). It uses OpenCV to scan the input video for sharp faces, extracts the intact audio track, and **generates and outputs a Reference Frame (Visual Preview)** directly onto the ComfyUI canvas.
2. **The Brain (`AutoLoopCalculator`)**: Receives the safe frames list from the Explorer and plans asymmetric, intelligent cuts. Instead of blindly dividing the video mathematically, it prioritizes making cuts on frames where the face is sharp, thereby maintaining identity coherence between loops.
3. **The Worker (`VHS_LoadVideo`)**: The standard ComfyUI VideoHelperSuite node is now solely responsible for the heavy lifting: extracting the exact video tensors according to the Brain's orders.

## The Core Nodes

The system is built around three major categories:

### 🔁 Loop (Autonomous Orchestration)
1. **🏁 Loop Start (Index) (`SequentialLoopStart`)**: Initiates the loop, manages the global loop index, and provides the current iteration index to downstream nodes.
2. **🚀 Loop Trigger (Auto-Queue) (`SequentialLoopTrigger`)**: Placed at the very end of your workflow. It increments the loop counter and autonomously triggers an HTTP POST request to the ComfyUI API (`/prompt`) to queue the next batch cycle.
   - **Seed Mutator:** Scans the canvas, locates nodes with a seed (`seed` or `noise_seed`), and injects a new 32-bit random seed, breaking forward cache in samplers.
   - **💉 Anti-Cache Injection (New in v1.1.0!):** Specifically searches for the `Loop Start` node within the JSON payload and **forcefully injects the new index**. This shatters ComfyUI's infamous "reverse cache" (bottom-up) that froze initial nodes during Auto-Queue, guaranteeing uninterrupted progression.

### 🖼️ Image (Session Memory)
3. **📥 Session Image Receiver (`SessionImageReceiver`)**: Retrieves the initial image or the last generated frame from the previous cycle, intelligently detecting the start of a RAM session.
4. **📤 Session Image Sender (`SessionImageSender`)**: Extracts the final image of a batch and secures it in system memory for the next cycle.
   - **💾 Keyframe Dumping (New in v1.1.0!):** Now receives the current index and performs a safety dump to the hard drive, progressively saving `keyframe_XXX.png` every cycle to prevent data loss.
   - **✨ Dynamic Engine:** The `Session Image Sender` dynamically truncates generated tensors if the AI hallucination occurs (e.g., character turns their back), and updates the global accumulator so the `Auto Loop Calculator` accurately readjusts the next extraction cycle, ensuring flawless identity continuity without desyncing audio.

### 🛠️ Tools
**🛠️ Tools Suite:** Dedicated nodes (`ResTool 8x, 16x, 32x, 64x`) to calculate strictly divisible safe resolutions, shielding VRAM. Select your aspect ratio (e.g., 9:16) and base resolution (e.g., 1080). The specific node will apply a strict downward mathematical constraint to guarantee that the width and height are perfectly divisible by your model's architecture, shielding your VRAM from tensor errors.

### 🎞️ Video (Assembly and Validation)
5. **🕵️ Video Analyzer + Audio (`VideoAnalyzerWithAudio`)**: The "Explorer" of the machine. Scans the video using OpenCV to detect frames with sharp faces, extracts the pure, intact audio track using Torchaudio, and generates a **Reference Frame Visual Preview** on its own interface. It outputs this reference frame as an IMAGE format for the rest of the workflow.
6. **📊 Auto Loop Calculator (`AutoLoopCalculator`)**: The "Brain". Receives information from the Explorer and calculates frame cuts (chunk, skip) asymmetrically. If provided with a `safe_faces_list`, it forces cuts on frames with recognizable faces to maintain fluid continuity. Now includes a **Dynamic ±10% Margin** to absorb video remainders at the final boundary, ensuring all cycles maintain a stable duration without generating inefficient tail ends.
7. **🎞️ Incremental Auto-Stitcher (`IncrementalVideoStitcher`)**: Progressively archives generated tensors directly to the hard drive and safely assembles them at the end of all cycles.
   - **🧠 Zero OOM:** Replaces RAM accumulation with progressive temporary disk saves (`.pt`), clearing system memory immediately to enable infinite video processing without crashing the system.
   - **🎵 Audio Passthrough:** Feeds the original pure audio straight to the assembled output during the final loop iteration (returning `None` during intermediate loops to save resources).

## Setup & Usage

### Prerequisites
- **VideoHelperSuite (VHS)**: **Recommended/Standard** for the "Worker" extraction node (`VHS_LoadVideo`).
- **OpenCV (`opencv-python`)**: Required for the Explorer (`VideoAnalyzerWithAudio`) to scan for sharp faces. If not installed, face detection will safely be disabled.
- **FFmpeg**: Must be installed and available in your system's PATH to manage underlying video operations.
- **Torchaudio**: (Usually included in ComfyUI environments) is required for the Explorer node to extract the original pure audio track from the source.

### Installation
1. Navigate to your ComfyUI `custom_nodes` folder.
2. Clone this repository: `git clone https://github.com/your-repo/ComfyUI-Sequential-Batcher.git`
3. Install the required dependencies if necessary (e.g., `pip install opencv-python`).
4. Restart ComfyUI.

### How to Connect the Hybrid Identity Architecture
1. **The Explorer (`🕵️ Video Analyzer + Audio`)**: Place this node at the very beginning of your workflow. Upload your video here.
2. **The Brain (`📊 Auto Loop Calculator`)**: Connect the `total_frames` output from the Explorer to the `source_frame_count` input of the Brain. Connect the `safe_faces_list` as well. Connect the `current_loop_index` from the `🏁 Loop Start` node.
3. **The Worker (`VHS_LoadVideo`)**: Right-click on this standard ComfyUI node and select **Convert Widget to Input -> video**.
   - Connect the `video_name` output from the Explorer to the new `video` input on the Worker.
   - Connect the `chunk_frames`, `skip_frames`, and `select_every_nth` outputs from the Brain to the Worker.
4. **Connecting Audio:** Pull a cable from the `source_audio` output of the Explorer and connect it directly to the blue `audio` port on your `🎞️ Incremental Auto-Stitcher`.
5. **The End:** Add the `🚀 Loop Trigger (Auto-Queue)` node at the end. Connect the image or audio output from your `Incremental Auto-Stitcher` into the `trigger_dependency` input.
6. **Execution:** Press "Queue Prompt" **once** (do not check Auto Queue). Batch 0 begins, the Explorer analyzes the video once, passes the cuts to the Brain, and the Worker iteratively extracts the tensors as the Anti-Cache Injection drives each successive cycle.

---
*Created to push the boundaries of ComfyUI automation.*