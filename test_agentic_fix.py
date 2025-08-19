#!/usr/bin/env python3
"""
Quick test script to verify the agentic search fixes
"""
import json
import sys
sys.path.append('.')

from multi_thread_agentic_search import AgenticSearchClient

def test_agentic_search():
    """Test the fixed agentic search implementation"""
    print("🧪 Testing Agentic Search API fixes...")
    
    # Initialize client
    client = AgenticSearchClient()
    
    # Test queries that were previously failing
    test_queries = [
        "Do you have premium accessory?",
        "gloves under 50",
        "What accessory is made of cotton?"
    ]
    
    for query in test_queries:
        print(f"\n📝 Testing query: '{query}'")
        result = client.search(query)
        
        print(f"   Success: {result['success']}")
        print(f"   Product count: {result['result_count']}")
        
        # Show response data structure
        response_data = result.get('response_data', {})
        if response_data.get('Success') == False:
            print(f"   ❌ API Error: {response_data.get('Error', 'Unknown error')}")
        elif result['result_count'] > 0:
            print(f"   ✅ Found {result['result_count']} products")
            # Show first product if available
            extracted_products = result.get('extracted_products', [])
            if extracted_products:
                first_product = extracted_products[0]
                print(f"   First product: {first_product.get('name')} - ${first_product.get('price')}")
        else:
            print(f"   ⚠️ No products found but no error reported")
    
    print("\n🏁 Test completed!")

if __name__ == "__main__":
    test_agentic_search()
