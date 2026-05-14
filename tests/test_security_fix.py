import torch
import os
import tempfile
import unittest
from safetensors.torch import save_file, load_file

class TestTorchLoadSecurity(unittest.TestCase):
    def test_safetensors_serialization(self):
        # Create a dummy tensor and save it
        data = {
            "waveform": torch.randn(1, 44100),
            "sample_rate": torch.tensor(44100, dtype=torch.int32)
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.safetensors")
            save_file(data, file_path)

            # Safetensors completely eliminates pickle
            loaded_data = load_file(file_path)

            self.assertEqual(loaded_data["sample_rate"].item(), 44100)
            self.assertTrue(torch.equal(loaded_data["waveform"], data["waveform"]))

if __name__ == "__main__":
    unittest.main()
