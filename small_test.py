#!/usr/bin/env python3
"""
Small test for multi-thread agentic search
"""
import json
import sys
sys.path.append('.')

from multi_thread_agentic_search import AgenticSearchClient, QuestionExtractor, ProgressTracker, process_single_question

def small_test():
    """Test with a few queries"""
    print("🧪 Small scale test of multi-thread agentic search...")
    
    # Initialize client
    client = AgenticSearchClient()
    
    # Test questions that previously failed
    test_questions = [
        {"question": "Do you have premium accessory?", "question_type": "Category"},
        {"question": "gloves under 50", "question_type": "Category + Price range"},
        {"question": "What clothing is made of nylon?", "question_type": "Category + Attribute value"}
    ]
    
    # Initialize progress tracker
    progress_tracker = ProgressTracker(len(test_questions), "test_output")
    
    print(f"Testing {len(test_questions)} queries...")
    
    for i, question_data in enumerate(test_questions):
        print(f"\n📝 Query {i+1}: '{question_data['question']}'")
        
        result = process_single_question(client, question_data, progress_tracker)
        
        if result:
            print(f"   Success: {result['success']}")
            print(f"   Products: {result['result_count']}")
            if result['result_count'] > 0:
                print(f"   First product: {result['extracted_products'][0]['name']}")
            else:
                response_data = result.get('response_data', {})
                if response_data.get('Success') == False:
                    print(f"   Error: {response_data.get('Error', 'Unknown error')}")
                else:
                    print("   No products found but no error")
    
    print("\n🏁 Small test completed!")
    
    # Show final stats
    stats = progress_tracker.get_statistics()
    print(f"📊 Final Stats:")
    print(f"   Success Rate: {stats['success_rate_percentage']:.1f}%")
    print(f"   Average Response Time: {stats['average_response_time_seconds']:.2f}s")
    print(f"   Total Results: {stats['total_results_returned']}")

if __name__ == "__main__":
    small_test()
