#!/usr/bin/env python3
"""
智能批处理版本的 multi_thread_runner
专门为大规模数据处理设计，支持断点续传和自动 token 刷新
"""

import json
import time
import sys
import os
from pathlib import Path
from datetime import datetime
from multi_thread_runner import (
    DataverseSearchClient, 
    QuestionExtractor, 
    ProgressTracker,
    get_system_hardware_config,
    calculate_optimal_thread_config,
    process_single_question
)
from concurrent.futures import ThreadPoolExecutor, as_completed

class SmartBatchProcessor:
    """智能批处理器，支持大规模数据处理"""
    
    def __init__(self, batch_size=1000, checkpoint_interval=300):
        self.batch_size = batch_size  # 每批处理的问题数量
        self.checkpoint_interval = checkpoint_interval  # 保存检查点的间隔（秒）
        self.client = DataverseSearchClient()
        
    def load_checkpoint(self, checkpoint_file):
        """加载检查点"""
        if os.path.exists(checkpoint_file):
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint = json.load(f)
                print(f"📋 Loaded checkpoint: {checkpoint['completed_questions']} questions completed")
                return checkpoint
            except Exception as e:
                print(f"⚠️ Error loading checkpoint: {e}")
        return {"completed_questions": 0, "start_time": datetime.now().isoformat()}
    
    def save_checkpoint(self, checkpoint_file, completed_questions, start_time):
        """保存检查点"""
        try:
            checkpoint = {
                "completed_questions": completed_questions,
                "start_time": start_time,
                "checkpoint_time": datetime.now().isoformat()
            }
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, indent=2)
            print(f"💾 Checkpoint saved: {completed_questions} questions completed")
        except Exception as e:
            print(f"❌ Error saving checkpoint: {e}")
    
    def process_batch(self, questions_batch, progress_tracker, workers=30, delay=0.01):
        """处理一批问题"""
        print(f"🔄 Processing batch of {len(questions_batch)} questions with {workers} workers...")
        
        # 检查 token 状态
        if not self.client._check_and_refresh_token_if_needed():
            print("❌ Token refresh failed, skipping this batch")
            return False
        
        batch_start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(process_single_question, self.client, q, progress_tracker, delay)
                for q in questions_batch
            ]
            
            completed = 0
            for future in as_completed(futures):
                try:
                    future.result()
                    completed += 1
                except Exception as e:
                    print(f"❌ Task failed: {e}")
                    completed += 1
        
        batch_time = time.time() - batch_start_time
        rate = len(questions_batch) / batch_time if batch_time > 0 else 0
        print(f"✅ Batch completed in {batch_time:.1f}s, rate: {rate:.1f} questions/second")
        
        return True
    
    def process_all_questions(self, questions, workers=30, delay=0.01):
        """处理所有问题，支持断点续传"""
        
        total_questions = len(questions)
        print(f"🎯 Processing {total_questions} questions in batches of {self.batch_size}")
        
        # 创建输出文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"smart_batch_results_{timestamp}.json"
        checkpoint_file = f"checkpoint_{timestamp}.json"
        
        # 加载检查点
        checkpoint = self.load_checkpoint(checkpoint_file)
        start_index = checkpoint["completed_questions"]
        start_time = checkpoint["start_time"]
        
        if start_index > 0:
            print(f"🔄 Resuming from question {start_index + 1}")
        
        # 初始化进度追踪
        progress_tracker = ProgressTracker(total_questions, output_file)
        progress_tracker.completed = start_index
        
        # 计算剩余问题
        remaining_questions = questions[start_index:]
        last_checkpoint_time = time.time()
        
        # 分批处理
        for i in range(0, len(remaining_questions), self.batch_size):
            batch = remaining_questions[i:i + self.batch_size]
            current_index = start_index + i
            
            print(f"\n📦 Batch {(i // self.batch_size) + 1}: Questions {current_index + 1}-{current_index + len(batch)}")
            
            # 处理当前批次
            success = self.process_batch(batch, progress_tracker, workers, delay)
            
            if not success:
                print("❌ Batch processing failed, stopping...")
                break
            
            # 定期保存检查点
            current_time = time.time()
            if current_time - last_checkpoint_time >= self.checkpoint_interval:
                self.save_checkpoint(checkpoint_file, current_index + len(batch), start_time)
                last_checkpoint_time = current_time
        
        # 最终保存
        progress_tracker.finalize_output()
        self.save_checkpoint(checkpoint_file, total_questions, start_time)
        
        # 显示最终统计
        stats = progress_tracker.get_statistics()
        print("\n" + "=" * 80)
        print("🏁 SMART BATCH PROCESSING COMPLETED!")
        print("=" * 80)
        print(f"📊 Results: {stats['successful_requests']} successful, {stats['failed_requests']} failed")
        print(f"📈 Success Rate: {stats['success_rate_percentage']:.1f}%")
        print(f"⚡ Processing Rate: {stats['processing_rate_per_second']:.2f} questions/second")
        print(f"⏳ Average Response Time: {stats['average_response_time_seconds']:.3f} seconds")
        print(f"💾 Results saved to: {output_file}")
        print("=" * 80)

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Smart Batch Multi-threaded Dataverse Search')
    parser.add_argument('--workers', '-w', type=int, default=30, help='Number of worker threads')
    parser.add_argument('--delay', '-d', type=float, default=0.01, help='Delay between requests in seconds')
    parser.add_argument('--batch-size', '-b', type=int, default=1000, help='Questions per batch')
    parser.add_argument('--checkpoint-interval', '-c', type=int, default=300, help='Checkpoint save interval in seconds')
    parser.add_argument('--path', '-p', default='.', help='Base path to search for files')
    
    args = parser.parse_args()
    
    # 获取系统配置
    print("🔍 Analyzing system hardware configuration...")
    system_config = get_system_hardware_config()
    
    print("💻 System Configuration:")
    print(f"   CPU: {system_config['cpu_logical_cores']} logical cores, {system_config['cpu_physical_cores']} physical cores")
    print(f"   Memory: {system_config['memory_total_gb']}GB total, {system_config['memory_available_gb']}GB available ({system_config['memory_usage_percent']:.1f}% used)")
    print(f"   Platform: {system_config['platform']} {system_config['platform_release']}")
    
    # 提取问题
    print("\n📁 Finding question files...")
    files = QuestionExtractor.find_question_files(args.path)
    print(f"   Found {len(files)} files")
    
    print("📝 Extracting questions...")
    all_questions = []
    for file_path in files:
        questions = QuestionExtractor.extract_questions_from_file(file_path)
        all_questions.extend(questions)
        print(f"   {file_path.name}: {len(questions)} questions")
    
    if not all_questions:
        print("❌ No questions found!")
        return
    
    print(f"\n🎯 Total questions to process: {len(all_questions)}")
    print(f"⚙️ Configuration:")
    print(f"   Workers: {args.workers}")
    print(f"   Delay: {args.delay}s")
    print(f"   Batch size: {args.batch_size}")
    print(f"   Checkpoint interval: {args.checkpoint_interval}s")
    
    # 创建智能批处理器
    processor = SmartBatchProcessor(
        batch_size=args.batch_size,
        checkpoint_interval=args.checkpoint_interval
    )
    
    # 开始处理
    processor.process_all_questions(
        all_questions,
        workers=args.workers,
        delay=args.delay
    )

if __name__ == "__main__":
    main()
