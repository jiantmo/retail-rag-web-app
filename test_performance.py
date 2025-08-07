#!/usr/bin/env python3
"""
快速测试多线程性能
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

def test_question_processing():
    """测试处理一个问题需要多长时间"""
    import sys
    sys.path.append('.')
    from multi_thread_runner import DataverseSearchClient
    
    print("🔍 测试单个问题处理时间...")
    client = DataverseSearchClient()
    
    test_question = "What are the best bike products?"
    start_time = time.time()
    
    result = client.search(test_question)
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    print(f"✅ 单个问题处理时间: {processing_time:.2f} 秒")
    print(f"📊 请求成功: {result.get('success', False)}")
    print(f"📋 结果数量: {result.get('result_count', 0)}")
    
    return processing_time

def test_parallel_processing():
    """测试并行处理性能"""
    import sys
    sys.path.append('.')
    from multi_thread_runner import DataverseSearchClient
    
    print("\n🚀 测试并行处理性能...")
    
    client = DataverseSearchClient()
    test_questions = [
        "What are the best bike products?",
        "Show me mountain bikes",
        "What accessories are available?",
        "Which products are on sale?",
        "Tell me about bike helmets"
    ]
    
    # 测试串行处理
    print("📝 串行处理测试...")
    serial_start = time.time()
    serial_results = []
    for question in test_questions:
        result = client.search(question)
        serial_results.append(result)
    serial_end = time.time()
    serial_time = serial_end - serial_start
    
    print(f"⏱️  串行处理时间: {serial_time:.2f} 秒")
    
    # 测试并行处理
    print("⚡ 并行处理测试...")
    parallel_start = time.time()
    parallel_results = []
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(client.search, question) for question in test_questions]
        for future in as_completed(futures):
            result = future.result()
            parallel_results.append(result)
    
    parallel_end = time.time()
    parallel_time = parallel_end - parallel_start
    
    print(f"⚡ 并行处理时间: {parallel_time:.2f} 秒")
    print(f"🚀 加速比: {serial_time / parallel_time:.2f}x")
    
    # 统计成功率
    serial_success = sum(1 for r in serial_results if r.get('success', False))
    parallel_success = sum(1 for r in parallel_results if r.get('success', False))
    
    print(f"📊 串行成功率: {serial_success}/{len(test_questions)} ({serial_success/len(test_questions)*100:.1f}%)")
    print(f"📊 并行成功率: {parallel_success}/{len(test_questions)} ({parallel_success/len(test_questions)*100:.1f}%)")

if __name__ == "__main__":
    print("🧪 多线程性能测试")
    print("=" * 50)
    
    # 测试单个问题处理时间
    single_time = test_question_processing()
    
    # 测试并行处理性能
    test_parallel_processing()
    
    print("\n" + "=" * 50)
    print("✅ 测试完成")
