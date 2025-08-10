#!/usr/bin/env python3
"""
Simple test for unstructured search functionality
"""

from multi_thread_unstructured_search import UnstructuredSearchRunner

def test_single_query():
    """Test a single query"""
    print("Testing single unstructured search query...")
    
    runner = UnstructuredSearchRunner(max_workers=1)
    
    # Test with a simple query
    test_query = "gloves"
    
    print(f"Testing query: '{test_query}'")
    result = runner.search_single_query(test_query, 1)
    
    print("\nResult:")
    print(f"  Success: {result.get('success', False)}")
    print(f"  Status Code: {result.get('status_code', 'N/A')}")
    print(f"  Duration: {result.get('duration_seconds', 'N/A')}s")
    
    if result.get('success'):
        print(f"  Result Count: {result.get('result_count', 'N/A')}")
    else:
        print(f"  Error: {result.get('error', 'Unknown error')}")
    
    return result

if __name__ == "__main__":
    try:
        result = test_single_query()
        print(f"\nTest completed. Success: {result.get('success', False)}")
    except Exception as e:
        print(f"Test failed with error: {e}")