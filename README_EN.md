# ComfyUI Sequential Batcher (v1.3.1)

A highly specialized suite of custom nodes for ComfyUI designed for **Recursive Self-Queuing** and autonomous sequential processing. This architecture minimizes VRAM usage by processing heavy tasks (like video generation) sequentially, batch-by-batch, orchestrated entirely from within the graph.

> **Leer en Español:** [README.md](README.md)

## The "Formula 1" Engine Architecture

Starting with v1.0.0, this repository has pivoted exclusively to the autonomous sequential loops and global memory architecture. All legacy technical debt (deprecated batch/sequence/debug nodes) has been pruned, leaving a clean, highly maintainable codebase focused on 6 core nodes.

In **v1.3.1**, we implemented the **"Explorer Cycle 0"**. We eliminated the external dependency on the total original frame count in the calculator by adopting a "Lazy Evaluation". In Cycle 0, the calculator blindly fires the user's intended target, while the video loader dynamically intercepts the true frame count directly from the VHS payload, dynamically calculating the total required loops for the rest of the generation. This removes unnecessary metadata nodes and keeps JSON layouts perfectly clean for n8n API integrations.

## The 6 Core Nodes

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

### 🎞️ Video (Assembly and Validation)
5. **📊 Auto Loop Calculator (`AutoLoopCalculator`)**: The mandatory "Brain" of the machine. In Cycle 0, it operates as an explorer without knowing the total duration of the original video. In subsequent cycles, it proportionally calculates and distributes batches of frames (even when using frame skipping with `select_every_nth`), preventing VRAM spikes. Everything flows smoothly with integration via ghost variables.
6. **🎞️ Incremental Auto-Stitcher (`IncrementalVideoStitcher`)**: Progressively archives generated tensors directly to the hard drive and safely assembles them at the end of all cycles.
   - **🧠 Zero OOM (New!):** Replaces RAM accumulation with progressive temporary disk saves (`.pt`), clearing system memory immediately to enable infinite video processing without crashing the system. By disabling `INPUT_IS_LIST`, it handles raw tensors efficiently.
   - **🎵 Audio Passthrough (New!):** Feeds the original pure audio straight to the assembled output during the final loop iteration (returning `None` during intermediate loops to save resources).
7. **🎥 Load Video + Source Audio (`LoadVideoWithSourceAudio`)**: (New!) This node **inherits directly from the original VHS class (`VHS_LoadVideo`)**. It functions exactly the same (including validations, UI preview widget, and upload button), but extracts and safely exposes the **complete**, uncropped original audio track to ensure it travels unaltered throughout the sequential process.

## Setup & Usage

### Prerequisites
- **VideoHelperSuite (VHS)**: **Mandatory** for the `Load Video + Source Audio` node to function. Since it inherits from its base class, if VHS is not installed in your ComfyUI environment, this node will not load.
- **FFmpeg**: Must be installed and available in your system's PATH to manage underlying video operations.
- **Torchaudio**: (Usually included in ComfyUI environments) is required to extract the original pure audio track from the source.

### Installation
1. Navigate to your ComfyUI `custom_nodes` folder.
2. Clone this repository: `git clone https://github.com/your-repo/ComfyUI-Sequential-Batcher.git`
3. Restart ComfyUI.

### How to use the Autonomous Machine
1. **The Start:** Add the `🏁 Loop Start (Index)` and the `📊 Auto Loop Calculator` nodes.
   - The calculator no longer requires the `source_frame_count` input. Simply define how many frames you want per loop in `target_frames_per_loop` and the `select_every_nth`.
   - Connect the `current_loop_index` output of `Loop Start` to the calculator, and to your Image and Video nodes (Receiver, Sender, Stitcher). *Don't forget the Sender for keyframe saving!*
   - Ensure the `reset_loop` toggle on the Loop Start is set to `False`.
   - Wire the `chunk_frames`, `skip_frames`, and `select_every_nth` outputs from the calculator into your video loader/generator.
2. **Connecting Audio (Optional):** If your workflow has sound, pull a cable from your initial node's audio output (e.g., `VHS_LoadVideo`) and connect it to the blue `audio` port on your `Incremental Auto-Stitcher`.
3. **The End:** Add the `🚀 Loop Trigger (Auto-Queue)` node. Crucially, connect the image or audio output from your `Incremental Auto-Stitcher` into the `trigger_dependency` input. This forces the trigger to wait until the video is physically saved to the temporary disk before firing. (Note: thanks to the global ghost memory, the Trigger already knows how many loops to execute without needing extra cables).
4. **Execution:** **You no longer need to check "Auto Queue".** Just press "Queue Prompt" **once**. Batch 0 starts, and upon finishing, the trigger invisibly signals the server. Thanks to Anti-Cache Injection, cache is destroyed on every iteration, and progress flows until your video is perfectly distributed and complete.

---
*Created to push the boundaries of ComfyUI automation.*