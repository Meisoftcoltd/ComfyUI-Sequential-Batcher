import os
import sys
import csv

# Setup paths
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TEST_DIR)
SANDBOX_DIR = os.path.join(TEST_DIR, "sandbox")
INPUT_DIR = os.path.join(SANDBOX_DIR, "input")
SECRET_FILE = os.path.join(SANDBOX_DIR, "secret.txt")

# Ensure sandbox exists
if not os.path.exists(INPUT_DIR):
    os.makedirs(INPUT_DIR)

# Create secret file
with open(SECRET_FILE, 'w') as f:
    f.write("secret_key,secret_value\nsuper,secret")

# Create valid csv
with open(os.path.join(INPUT_DIR, "valid.csv"), 'w') as f:
    f.write("col1,col2\nval1,val2")

# Mock folder_paths
import types
folder_paths = types.ModuleType("folder_paths")
folder_paths.get_input_directory = lambda: INPUT_DIR
folder_paths.get_annotated_filepath = lambda x: x # Mock implementation
sys.modules["folder_paths"] = folder_paths

# Load batch.py dynamically
def load_batch_module():
    batch_path = os.path.join(REPO_ROOT, "batch.py")
    with open(batch_path, 'r') as f:
        code = f.read()

    # Mock register_node by replacing the import
    code = code.replace("from . import register_node", "def register_node(c, *args, **kwargs): return c")

    module = types.ModuleType("batch")
    exec(code, module.__dict__)
    return module

batch_module = load_batch_module()
LoadCSV = batch_module.LoadCSV

def verify_fix():
    print("--- Verifying Fix ---")
    node = LoadCSV()

    # Test 1: Exploit attempt (should fail)
    print("Test 1: Exploit attempt (should raise ValueError)")
    target_path = SECRET_FILE
    try:
        # Pass path relative to input, attempting traversal if we were naive,
        # but here we can pass absolute path to check absolute path blocking.
        # Or relative path "../secret.txt"

        # Scenario A: Path traversal relative string
        # node.go("../secret.txt", ...)
        # Scenario B: Absolute path

        # Testing Scenario B (absolute path)
        node.go(target_path, "comma", '"', -1)
        print("FAIL: Exploit succeeded (No exception raised)")
        return False
    except ValueError as e:
        if "Access denied" in str(e):
            print(f"SUCCESS: Blocked absolute path access: {e}")
        else:
            print(f"FAIL: Raised wrong ValueError: {e}")
            return False
    except Exception as e:
        print(f"FAIL: Raised wrong exception: {type(e)} {e}")
        return False

    # Test 2: Valid access (should succeed)
    print("\nTest 2: Valid access (should succeed)")
    try:
        # Can pass just filename or relative path
        result = node.go("valid.csv", "comma", '"', -1)
        batch_data = result["result"][0]
        if batch_data[0]['col1'] == 'val1':
            print("SUCCESS: Valid CSV read correctly")
        else:
            print(f"FAIL: content mismatch: {batch_data}")
            return False
    except Exception as e:
        print(f"FAIL: Valid access raised exception: {e}")
        return False

    # Test 3: Relative path traversal attempt (should fail)
    print("\nTest 3: Relative path traversal attempt (should raise ValueError)")
    try:
        node.go("../secret.txt", "comma", '"', -1)
        print("FAIL: Exploit succeeded (No exception raised)")
        return False
    except ValueError as e:
        if "Access denied" in str(e):
            print(f"SUCCESS: Blocked relative path traversal: {e}")
        else:
            print(f"FAIL: Raised wrong ValueError: {e}")
            return False
    except Exception as e:
        # Depending on how os.path.join works, "input/../secret.txt" -> "sandbox/secret.txt"
        # commonpath should catch it.
        print(f"FAIL: Raised wrong exception: {type(e)} {e}")
        return False

    return True

if __name__ == "__main__":
    if verify_fix():
        print("\nVerification Result: FIX VERIFIED")
        sys.exit(0)
    else:
        print("\nVerification Result: FIX FAILED")
        sys.exit(1)
