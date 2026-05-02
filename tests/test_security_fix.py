import torch
import os
import tempfile
import unittest

class TestTorchLoadSecurity(unittest.TestCase):
    def test_torch_load_weights_only(self):
        # Create a dummy tensor and save it
        data = {
            "waveform": torch.randn(1, 44100),
            "sample_rate": 44100
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.pt")
            torch.save(data, file_path)

            # This should work with weights_only=True for simple tensors/dicts
            loaded_data = torch.load(file_path, weights_only=True)

            self.assertEqual(loaded_data["sample_rate"], 44100)
            self.assertTrue(torch.equal(loaded_data["waveform"], data["waveform"]))

if __name__ == "__main__":
    unittest.main()
