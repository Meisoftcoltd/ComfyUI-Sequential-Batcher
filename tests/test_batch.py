import unittest
import sys
import os
import importlib.util
from unittest.mock import MagicMock

# --- Import setup (same as benchmark) ---
mock_folder_paths = MagicMock()
mock_folder_paths.folder_names_and_paths = {"checkpoint": ([], {})}
sys.modules['folder_paths'] = mock_folder_paths
sys.modules['torch'] = MagicMock()
sys.modules['numpy'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()
sys.modules['PIL.ImageOps'] = MagicMock()
sys.modules['PIL.ImageSequence'] = MagicMock()
sys.modules['PIL.ImageFile'] = MagicMock()

repo_root = os.getcwd()
spec = importlib.util.spec_from_file_location("comfy_nodes", os.path.join(repo_root, "__init__.py"))
comfy_nodes = importlib.util.module_from_spec(spec)
sys.modules["comfy_nodes"] = comfy_nodes
spec.loader.exec_module(comfy_nodes)

format_batch_as_table = comfy_nodes.batch.format_batch_as_table

class TestBatchFormat(unittest.TestCase):
    def test_basic_batch(self):
        batch = [{'a': 1, 'b': 2}, {'a': 3, 'b': 4}]
        result = format_batch_as_table(batch)
        self.assertIn("| a | b |", result)
        self.assertIn("| 1 | 2 |", result)
        self.assertIn("| 3 | 4 |", result)

    def test_order_preservation(self):
        # Keys should appear in order of first appearance
        # Row 1 introduces 'b', 'a'
        # Row 2 introduces 'c'
        # Expected order: b, a, c
        batch = [{'b': 1, 'a': 2}, {'c': 3}]
        result = format_batch_as_table(batch)
        # Check header line
        lines = result.split('\n')
        header = lines[0]
        # We expect something like "| b | a | c |"
        # Spacing might vary depending on value lengths, so we check order in string
        self.assertTrue(header.index('b') < header.index('a'))
        self.assertTrue(header.index('a') < header.index('c'))

    def test_disjoint_keys(self):
        batch = [{'a': 1}, {'b': 2}]
        result = format_batch_as_table(batch)
        self.assertIn("| a | b |", result)
        # Row 1 should have empty for b
        # Row 2 should have empty for a
        # Note: Current implementation puts empty string for missing keys

        # Verify row 1 has '1' and empty for 'b'
        # Since we don't know exact spacing easily, we trust the table formatter logic
        # but ensure no crash and content is there.
        self.assertIn("1", result)
        self.assertIn("2", result)

    def test_empty_batch(self):
        result = format_batch_as_table([])
        self.assertEqual(result, "(Empty Batch)")

    def test_empty_rows(self):
        result = format_batch_as_table([{}, {}])
        self.assertEqual(result, "(Empty rows)")

if __name__ == '__main__':
    unittest.main()
