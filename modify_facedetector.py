import re

def update_node():
    with open('video.py', 'r') as f:
        content = f.read()

    # Update INPUT_TYPES optional
    content = re.sub(
        r'"optional": \{\s*"bbox_detector": \("BBOX_DETECTOR", \),\s*# 💡 Puerto para YOLO/ONNX\s*\}',
        '"optional": {\n                "bbox_detector": ("BBOX_DETECTOR", ), # 💡 Puerto para YOLO/ONNX\n                "current_loop_index": ("INT", {"default": 0, "forceInput": True}),\n            }',
        content
    )

    # Update analyze method signature
    content = content.replace(
        'def analyze(self, video, reference_frame_idx, use_face_detector, blur_threshold, unload_detector_after_analysis=True, bbox_detector=None, **kwargs):',
        'def analyze(self, video, reference_frame_idx, use_face_detector, blur_threshold, unload_detector_after_analysis=True, bbox_detector=None, current_loop_index=0, **kwargs):'
    )

    with open('video.py', 'w') as f:
        f.write(content)

if __name__ == '__main__':
    update_node()
