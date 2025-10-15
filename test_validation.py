#!/usr/bin/env python3
"""
Test script for graph update validation and pattern detection.
Run this to verify the "scold" behavior works correctly.
"""

import sys
import importlib.util

# Import the module directly without going through __init__.py
spec = importlib.util.spec_from_file_location("graph_tool", "/home/isaac/axion/axion_swarm/graph_tool.py")
graph_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(graph_tool)

validate_graph_update = graph_tool.validate_graph_update

def test_validation():
    """Test various malformed patterns and verify correct detection"""
    
    print("=" * 80)
    print("GRAPH UPDATE VALIDATION TEST")
    print("=" * 80)
    
    # Test Case 1: Multiple answers at same level (most common)
    print("\n[Test 1] Multiple answers at same level:")
    test1 = "@[Graph][Update][Q:single][What is the budget?][A][$200][A][$500][A][$1000]"
    is_valid, error_msg, pattern_info = validate_graph_update(test1)
    print(f"  Input: {test1}")
    print(f"  Valid: {is_valid}")
    print(f"  Error: {error_msg}")
    print(f"  Pattern: has_question={pattern_info['has_question']}, answer_count={pattern_info['answer_count']}, has_nested={pattern_info['has_nested_question']}")
    assert not is_valid, "Should be invalid"
    assert pattern_info['has_question'] and pattern_info['answer_count'] > 1 and not pattern_info['has_nested_question'], "Should detect multiple answers at same level"
    print("  ✓ PASS - Detected as: Multiple answers at same level")
    
    # Test Case 2: Multiple answers across nested levels
    print("\n[Test 2] Multiple answers across nested levels:")
    test2 = "@[Graph][Update][Q:single][Parent?][A][Answer1][Q:single][Child?][A][Answer2][A][Answer3]"
    is_valid, error_msg, pattern_info = validate_graph_update(test2)
    print(f"  Input: {test2}")
    print(f"  Valid: {is_valid}")
    print(f"  Error: {error_msg}")
    print(f"  Pattern: has_question={pattern_info['has_question']}, answer_count={pattern_info['answer_count']}, has_nested={pattern_info['has_nested_question']}")
    assert not is_valid, "Should be invalid"
    assert pattern_info['has_nested_question'] and pattern_info['answer_count'] > 1, "Should detect nested structure with multiple answers"
    print("  ✓ PASS - Detected as: Multiple answers across nested levels")
    
    # Test Case 3: Valid single answer
    print("\n[Test 3] Valid single answer:")
    test3 = "@[Graph][Update][Q:single][What is the approach?][A][Phased approach][👍][Reduces risk]"
    is_valid, error_msg, pattern_info = validate_graph_update(test3)
    print(f"  Input: {test3}")
    print(f"  Valid: {is_valid}")
    print(f"  Pattern: has_question={pattern_info['has_question']}, answer_count={pattern_info['answer_count']}, has_nested={pattern_info['has_nested_question']}")
    assert is_valid, "Should be valid"
    print("  ✓ PASS - Valid entry")
    
    # Test Case 4: Valid nested path (one answer per level)
    print("\n[Test 4] Valid nested path:")
    test4 = "@[Graph][Update][Q:single][Parent?][A][Answer1][Q:single][Child?][A][Answer2]"
    is_valid, error_msg, pattern_info = validate_graph_update(test4)
    print(f"  Input: {test4}")
    print(f"  Valid: {is_valid}")
    print(f"  Pattern: has_question={pattern_info['has_question']}, answer_count={pattern_info['answer_count']}, has_nested={pattern_info['has_nested_question']}")
    assert is_valid, "Should be valid"
    assert pattern_info['answer_count'] == 2 and pattern_info['has_nested_question'], "Should have 2 answers in nested structure"
    print("  ✓ PASS - Valid nested entry")
    
    print("\n" + "=" * 80)
    print("ALL TESTS PASSED ✓")
    print("=" * 80)
    print("\nValidation logic is working correctly:")
    print("- Detects multiple answers at same level (Pattern 1)")
    print("- Detects multiple answers across nested levels (Pattern 2)")
    print("- Accepts valid single answer")
    print("- Accepts valid nested paths with one answer per level")
    print("\nThe 'scold' behavior will show targeted Notice based on detected pattern.")

if __name__ == "__main__":
    test_validation()

