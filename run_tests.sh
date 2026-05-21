#!/bin/bash
cd tests
sed -i 's/mock_torch.__version__ = "2.0.0"/mock_torch.__version__ = "2.0.0"\nmock_torch.dtype = type("dtype", (), {})\nmock_torch.empty = MagicMock()\nmock_torch.randn = MagicMock()/g' test_loop_calculator.py
PYTHONPATH=.. pytest test_loop_calculator.py
