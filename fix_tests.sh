#!/bin/bash
cd tests
# Because we mocked torch.Tensor as a MagicMock in other tests, and they pollute test_tools, we will run the tests individually like memory suggested.
PYTHONPATH=.. pytest test_loop_calculator.py
PYTHONPATH=.. pytest test_ssrf_fix.py
PYTHONPATH=.. pytest test_switch_node.py
PYTHONPATH=.. pytest test_tools.py
PYTHONPATH=.. pytest test_video_audio.py
PYTHONPATH=.. pytest test_vram_node.py
