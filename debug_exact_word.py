#!/usr/bin/env python3
"""
Debug script for testing Exact word scoring with real data
"""

import json
import re

def _score_exact_word(question_text: str, expected_product_name: str, 
                     result_name: str, result_all_text: str) -> int:
    """
    Score for "Exact word" questions - result is relevant if it contains the exact word
    
    Improved logic:
    - 3分: 包含产品名字（完整或主要部分）
    - 2分: 包含产品名字的关键部分 + 其他查询词
    - 1分: 包含其他有意义的查询词
    - 0分: 没有相关匹配
    """
    
    # Extract product names from question using patterns
    product_name_patterns = [
        r'buying\s+([A-Za-z\s]+?)\s*[-–]',  # "buying Product Name -"
        r'about\s+(?:the\s+)?([A-Za-z\s]+?)\?',  # "about the Product Name?"
        r'on\s+([A-Za-z\s]+?)\?',  # "on Product Name?"
        r'([A-Za-z\s]+?)\s+compare',  # "Product Name compare"
        r"'([A-Za-z\s]+?)'",  # 'Product Name'
        r'"([A-Za-z\s]+?)"',  # "Product Name"
    ]
    
    query_product_names = set()
    for pattern in product_name_patterns:
        matches = re.findall(pattern, question_text, re.IGNORECASE)
        for match in matches:
            clean_match = match.strip()
            if len(clean_match) > 2:  # Filter out too short matches
                query_product_names.add(clean_match.lower())
    
    # Extract meaningful query words (excluding stop words)
    stop_words = {
        'i', 'me', 'my', 'we', 'our', 'you', 'your', 'he', 'him', 'his', 'she', 'her',
        'it', 'its', 'they', 'them', 'their', 'what', 'which', 'who', 'whom', 'this',
        'that', 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the',
        'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by',
        'for', 'with', 'about', 'against', 'between', 'into', 'through', 'during',
        'before', 'after', 'above', 'below', 'up', 'down', 'in', 'out', 'on', 'off',
        'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when',
        'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most',
        'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
        'than', 'too', 'very', 'can', 'will', 'just', 'should', 'now', 'good',
        'things', 'compare', 'options', 'suggestions', 'opinion', 'considering',
        'buying', 'worth', 'tell', 'heard'
    }
    
    query_words = set()
    clean_question = re.sub(r'[^\w\s]', ' ', question_text.lower())
    for word in clean_question.split():
        if len(word) > 2 and word not in stop_words:
            query_words.add(word)
    
    result_name_lower = result_name.lower()
    result_all_lower = result_all_text.lower()
    
    print(f"Debug scoring: '{question_text}' vs '{result_name}'")
    print(f"  Expected product: '{expected_product_name}'")
    print(f"  Query product names: {query_product_names}")
    print(f"  Query words: {query_words}")
    
    # Check product name coverage
    best_product_coverage = 0
    for query_name in query_product_names:
        query_name_words = set(query_name.split())
        result_name_words = set(result_name_lower.split())
        
        if query_name_words and result_name_words:
            common_words = query_name_words.intersection(result_name_words)
            coverage = len(common_words) / len(query_name_words)
            best_product_coverage = max(best_product_coverage, coverage)
            print(f"  Product coverage: '{query_name}' vs '{result_name_lower}' -> {coverage:.2f}")
    
    # Check query word coverage
    result_text_words = set(re.findall(r'\w+', result_all_lower))
    query_word_matches = query_words.intersection(result_text_words)
    query_word_coverage = len(query_word_matches) / len(query_words) if query_words else 0
    
    print(f"  Best product coverage: {best_product_coverage:.2f}")
    print(f"  Query word coverage: {query_word_coverage:.2f}")
    print(f"  Query word matches: {query_word_matches}")
    
    # Scoring logic
    if best_product_coverage >= 0.7:
        score = 3
        print(f"  Score: 3 (product coverage >= 0.7)")
    elif best_product_coverage >= 0.3 and query_word_coverage >= 0.3:
        score = 2
        print(f"  Score: 2 (partial product + query words)")
    elif query_word_coverage >= 0.3:
        score = 1
        print(f"  Score: 1 (query words only)")
    else:
        score = 0
        print(f"  Score: 0 (no match)")
    
    return score

# Test with real data from the Yint Mug example
test_cases = [
    {
        'question': "I'm considering buying Yint Mug - is it worth it?",
        'expected_product': 'Yint Mug',
        'result_name': 'Yint Mug',
        'result_description': 'Travel ultralight without losing your morning cup of coffee with the TOAKS Titanium Single Wall 450ml cup. Made of pure lightweight titanium, it resists corrosion and eliminates metallic aftertaste.'
    },
    {
        'question': "I'm considering buying Yint Mug - is it worth it?",
        'expected_product': 'Yint Mug',
        'result_name': 'Oany Mug',
        'result_description': 'Another mug for coffee lovers'
    }
]

print("=== Testing Exact Word Scoring with Real Data ===")
for i, test_case in enumerate(test_cases, 1):
    print(f"\nTest case {i}:")
    result_all_text = f"{test_case['result_name']} {test_case['result_description']}"
    score = _score_exact_word(
        test_case['question'],
        test_case['expected_product'],
        test_case['result_name'],
        result_all_text
    )
    print(f"Final score: {score}")
