# ComfyUI Sequential Batcher (v1.0.0)

A highly specialized suite of custom nodes for ComfyUI designed for **Recursive Self-Queuing** and autonomous sequential processing. This architecture minimizes VRAM usage by processing heavy tasks (like video generation) sequentially, batch-by-batch, orchestrated entirely from within the graph.

> **Read in Spanish:** [README_ES.md](README_ES.md)

## The "Formula 1" Engine Architecture

Starting with v1.0.0, this repository has pivoted exclusively to the autonomous sequential loops and global memory architecture. All legacy technical debt (deprecated batch/sequence/debug nodes) has been pruned, leaving a clean, highly maintainable codebase focused on 6 core nodes.

## The 6 Core Nodes

The system is built around three major categories:

### 🔁 Loop (Autonomous Orchestration)
1. **🏁 Loop Start (Index) (`SequentialLoopStart`)**: Initiates the loop, manages the global loop index, and provides the current iteration index to downstream nodes.
2. **🚀 Loop Trigger (Auto-Queue) (`SequentialLoopTrigger`)**: Placed at the very end of your workflow. It increments the loop counter and autonomously triggers an HTTP POST request to the ComfyUI API (`/prompt`) to queue the next batch cycle.

### 🖼️ Image (Session Memory)
3. **📥 Session Image Receiver (`SessionImageReceiver`)**: Retrieves the initial image or the last generated frame from the previous cycle, intelligently detecting the start of a session.
4. **📤 Session Image Sender (`SessionImageSender`)**: Extracts, saves to global memory, and displays the last frame of a video batch for the next cycle to use.

### 🎞️ Video (Assembly and Validation)
5. **🛡️ Wan Frame Validator (`WanFrameValidator`)**: Validates and corrects the target number of frames to ensure they fit the `4k+1` formula required by specific models (e.g., Wan).
6. **🎞️ Incremental Auto-Stitcher (`IncrementalVideoStitcher`)**: Assembles the generated video chunks of the current session sequentially using FFmpeg, parsing outputs natively from the `VHS_FILENAMES` format.

## Setup & Usage

### Prerequisites
- **FFmpeg**: Must be installed and available in your system's PATH for the `Incremental Auto-Stitcher` to function correctly.

### Installation
1. Navigate to your ComfyUI `custom_nodes` folder.
2. Clone this repository: `git clone https://github.com/your-repo/ComfyUI-Sequential-Batcher.git`
3. Restart ComfyUI.

### How to use the Autonomous Machine
1. **The Start:** Add the `🏁 Loop Start (Index)` node. Connect its `current_loop_index` to the index inputs of your receiver and stitcher nodes. Ensure `reset_loop` is set to `False`.
2. **The End:** Add the `🚀 Loop Trigger (Auto-Queue)` node. Crucially, connect the text output (`final_video_path`) from your `Incremental Auto-Stitcher` to the `trigger_dependency` input. This forces the trigger to wait until the video is physically saved. Set your desired `target_loops`.
3. **Execution:** You no longer need to check "Auto Queue". Just press "Queue Prompt" **once**. The workflow will run the first batch, and upon finishing, the trigger will invisibly signal the server to queue the next batch until the target is reached, at which point it stitches everything together and finishes.

---
*Created to push the boundaries of ComfyUI automation.*