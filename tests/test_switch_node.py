import sys
import os
import pytest

# Add the parent directory to sys.path so we can import switch_node directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from switch_node import MasterSwitch

@pytest.fixture
def master_switch():
    return MasterSwitch()

def test_master_switch_check_lazy_status(master_switch):
    # Test True condition
    assert master_switch.check_lazy_status(is_final_cycle=True) == ["on_true"]

    # Test False condition
    assert master_switch.check_lazy_status(is_final_cycle=False) == ["on_false"]

def test_master_switch_route_true(master_switch):
    # Test routing to true branch
    result = master_switch.route(is_final_cycle=True, on_true="true_value", on_false="false_value")

    # Verify result - check first element to avoid tuple length mismatch assumptions
    assert result[0] == "true_value"

def test_master_switch_route_false(master_switch):
    # Test routing to false branch
    result = master_switch.route(is_final_cycle=False, on_true="true_value", on_false="false_value")

    # Verify result
    assert result[0] == "false_value"

def test_master_switch_route_none_values(master_switch):
    # Test with None values
    result_true = master_switch.route(is_final_cycle=True, on_true=None, on_false="false_value")
    assert result_true[0] is None

    result_false = master_switch.route(is_final_cycle=False, on_true="true_value", on_false=None)
    assert result_false[0] is None

if __name__ == "__main__":
    pytest.main([__file__])
