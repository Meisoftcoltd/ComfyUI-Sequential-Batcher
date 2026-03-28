# ComfyUI Sequential Batcher (v1.1.0)

A highly specialized suite of custom nodes for ComfyUI designed for **Recursive Self-Queuing** and autonomous sequential processing. This architecture minimizes VRAM usage by processing heavy tasks (like video generation) sequentially, batch-by-batch, orchestrated entirely from within the graph.

> **Leer en Español:** [README.md](README.md)

## The "Formula 1" Engine Architecture

Starting with v1.0.0, this repository has pivoted exclusively to the autonomous sequential loops and global memory architecture. All legacy technical debt (deprecated batch/sequence/debug nodes) has been pruned, leaving a clean, highly maintainable codebase focused on 6 core nodes.

In **v1.1.0**, we have introduced progressive disk saving capabilities, audio multiplexing support, and a deep JSON hack to defeat ComfyUI's aggressive cache.

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
5. **🛡️ Wan Frame Validator (`WanFrameValidator`)**: Validates and corrects the target number of frames to ensure they fit the `4k+1` formula required by specific models (e.g., Wan).
6. **🎞️ Incremental Auto-Stitcher (`IncrementalVideoStitcher`)**: Progressively archives generated tensors directly to the hard drive and safely assembles them at the end of all cycles.
   - **🧠 Zero OOM (New!):** Replaces RAM accumulation with progressive temporary disk saves (`.pt`), clearing system memory immediately to enable infinite video processing without crashing the system.
   - **🎵 Audio Passthrough (New!):** Feeds the original pure audio straight to the assembled output during the final loop iteration.
7. **🎥 Load Video + Source Audio (`LoadVideoWithSourceAudio`)**: (New!) Functions exactly like the standard VHS video loader, but extracts and safely exposes the **complete**, uncropped original audio track to ensure it travels unaltered throughout the sequential process.

## Setup & Usage

### Prerequisites
- **VideoHelperSuite (VHS)**: Dynamically required for the `Load Video + Source Audio` node to function and replicate its UI seamlessly.
- **FFmpeg**: Must be installed and available in your system's PATH to manage underlying video operations.
- **Torchaudio**: (Usually included in ComfyUI environments) is required to extract the original pure audio track from the source.

### Installation
1. Navigate to your ComfyUI `custom_nodes` folder.
2. Clone this repository: `git clone https://github.com/your-repo/ComfyUI-Sequential-Batcher.git`
3. Restart ComfyUI.

### How to use the Autonomous Machine
1. **The Start:** Add the `🏁 Loop Start (Index)` node.
   - Connect its `current_loop_index` to the index inputs of your `SessionImageReceiver`, `SessionImageSender`, and `Incremental Auto-Stitcher`. *Don't forget the Sender for keyframe saving!*
   - Ensure `reset_loop` is set to `False`.
2. **Connecting Audio (Optional):** If your workflow has sound, pull a cable from your initial node's audio output (e.g., `VHS_LoadVideo`) and connect it to the blue `audio` port on your `Incremental Auto-Stitcher`.
3. **The End:** Add the `🚀 Loop Trigger (Auto-Queue)` node. Crucially, connect the text output (`final_video_path`) from your `Incremental Auto-Stitcher` to the `trigger_dependency` input. This forces the trigger to wait until the video is physically saved. Set your desired `target_loops`.
4. **Execution:** **You no longer need to check "Auto Queue".** Just press "Queue Prompt" **once**. Batch 0 starts, and upon finishing, the trigger invisibly signals the server. Thanks to Anti-Cache Injection, cache is destroyed on every iteration, and progress flows until your video is complete.

---
*Created to push the boundaries of ComfyUI automation.*