#!/usr/bin/env python3
"""
Multi-threaded Agentic Search Runner
Process all questions with threading and save results to unified JSON
Based on multi_thread_unified_search.py logic but calling agentic search API
"""
import requests
import json
import time
import threading
import argparse
import os
import sys
import signal
import platform
import atexit
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError, wait, FIRST_COMPLETED
from datetime import datetime, timezone, timedelta
from collections import Counter
from urllib.parse import urlencode

# Global shutdown flag and progress tracker for graceful shutdown
shutdown_requested = False
force_exit = False
global_progress_tracker = None
interrupt_count = 0

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully with double-press detection"""
    global shutdown_requested, global_progress_tracker, force_exit, interrupt_count
    
    interrupt_count += 1
    
    if interrupt_count >= 2:
        # Second Ctrl+C - force immediate exit
        print(f"\n🚨 Second interrupt signal received. Forcing immediate exit!")
        force_exit = True
        # Use os._exit() for immediate termination without cleanup
        os._exit(1)
    
    print(f"\n🛑 Received interrupt signal ({signum}). Initiating graceful shutdown...")
    print("📝 Saving current progress and results...")
    shutdown_requested = True
    
    # Try to finalize results if tracker exists
    if global_progress_tracker:
        try:
            global_progress_tracker.finalize_output()
        except Exception as e:
            print(f"⚠️ Error during progress finalization: {e}")
    
    # Give the main thread a moment to handle the shutdown gracefully
    print("⏳ Waiting for active tasks to complete... (Press Ctrl+C again to force exit)")
    time.sleep(0.1)

def register_signal_handlers():
    """Register signal handlers for graceful shutdown"""
    try:
        # Handle Ctrl+C (SIGINT)
        signal.signal(signal.SIGINT, signal_handler)
        # Handle termination signal (SIGTERM) on Unix-like systems
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)
        
        print("✅ Signal handlers registered for graceful shutdown")
    except Exception as e:
        print(f"⚠️ Could not register signal handlers: {e}")

def start_monitoring_thread():
    """Start a monitoring thread that listens for keyboard input to stop execution"""
    def monitor():
        global shutdown_requested, force_exit
        try:
            while not shutdown_requested and not force_exit:
                # This is a simple fallback - user can type 'q' and Enter to quit
                user_input = input().strip().lower()
                if user_input in ['q', 'quit', 'exit', 'stop']:
                    print("🛑 Stop command received via input. Initiating shutdown...")
                    shutdown_requested = True
                    break
        except (EOFError, KeyboardInterrupt):
            # Handle Ctrl+C in this thread
            print("🛑 Interrupt received in monitoring thread")
            shutdown_requested = True
        except:
            # Ignore other errors in monitoring thread
            pass
    
    import threading
    monitor_thread = threading.Thread(target=monitor, daemon=True)
    monitor_thread.start()
    return monitor_thread

def cleanup_on_exit():
    """Cleanup function called on normal exit"""
    global global_progress_tracker, shutdown_requested
    if global_progress_tracker and not shutdown_requested:
        try:
            global_progress_tracker.finalize_output()
        except Exception as e:
            print(f"⚠️ Error during cleanup: {e}")

# Register cleanup function
atexit.register(cleanup_on_exit)

class ProgressTracker:
    """Thread-safe progress tracking with detailed statistics and real-time file output"""
    
    def __init__(self, total, output_file=None):
        self.total = total
        self.completed = 0
        self.successful = 0
        self.failed = 0
        self.lock = threading.Lock()
        self.start_time = time.time()
        self.status_codes = {}
        self.error_types = {}
        self.response_times = []
        self.result_counts = []
        self.output_file = output_file
        self.results_written = 0
        self.last_checkpoint_time = time.time()
        self.checkpoint_interval = 30  # Save checkpoint every 30 seconds
        self.finalized = False  # Track if finalization has been called
        
        # Store sample failed/throttled requests for analysis
        self.failed_request_samples = []
        self.throttled_request_samples = []
        self.max_samples = 3  # Store up to 3 samples of each type
        
        # Initialize output file
        if self.output_file:
            self._initialize_output_file()
    
    def _initialize_output_file(self):
        """Initialize the output file with metadata"""
        try:
            base_path = Path(self.output_file)
            results_file = base_path.with_suffix('.jsonl').with_name(f"{base_path.stem}_results.jsonl")
            
            # Create directory if it doesn't exist
            results_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Initialize with empty file
            with open(results_file, 'w', encoding='utf-8') as f:
                pass  # Just create empty file
                
            print(f"📄 Initialized results file: {results_file}")
        except Exception as e:
            print(f"⚠️ Could not initialize output file: {e}")
    
    def append_result(self, result):
        """Append a single result to the file immediately using append mode with thread safety"""
        if not self.output_file:
            return
            
        # Use lock to ensure thread-safe file writing
        with self.lock:
            try:
                base_path = Path(self.output_file)
                results_file = base_path.with_suffix('.jsonl').with_name(f"{base_path.stem}_results.jsonl")
                
                with open(results_file, 'a', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False)
                    f.write('\n')
                    
                self.results_written += 1
                
                # Save checkpoint periodically
                current_time = time.time()
                if current_time - self.last_checkpoint_time > self.checkpoint_interval:
                    self._save_checkpoint()
                    self.last_checkpoint_time = current_time
                    
            except Exception as e:
                print(f"⚠️ Error writing result to file: {e}")
    
    def add_failed_sample(self, result):
        """Add a sample failed or throttled request for analysis"""
        with self.lock:
            # Check if this is a throttled request
            is_throttled = False
            try:
                response_data = result.get('response_data', {})
                if isinstance(response_data, dict):
                    formatted_text = response_data.get('FormattedText', '')
                    if 'TooManyRequests' in formatted_text or 'Rate limit' in formatted_text:
                        is_throttled = True
            except:
                pass
            
            # Store sample based on type
            if is_throttled and len(self.throttled_request_samples) < self.max_samples:
                sample = {
                    'timestamp': result.get('timestamp'),
                    'error_type': 'throttled',
                    'status_code': result.get('status_code'),
                    'response_time': result.get('response_time_seconds'),
                    'error_message': self._extract_error_message(result),
                    'question': result.get('test_case_context', {}).get('question', 'Unknown')[:100]
                }
                self.throttled_request_samples.append(sample)
            elif not is_throttled and len(self.failed_request_samples) < self.max_samples:
                sample = {
                    'timestamp': result.get('timestamp'),
                    'error_type': result.get('error_type', 'unknown'),
                    'status_code': result.get('status_code'),
                    'response_time': result.get('response_time_seconds'),
                    'error_message': self._extract_error_message(result),
                    'question': result.get('test_case_context', {}).get('question', 'Unknown')[:100]
                }
                self.failed_request_samples.append(sample)
    
    def _extract_error_message(self, result):
        """Extract error message from result for sampling"""
        try:
            response_data = result.get('response_data', {})
            if isinstance(response_data, dict):
                # Try FormattedText first
                formatted_text = response_data.get('FormattedText', '')
                if formatted_text and 'Error' in formatted_text:
                    return formatted_text[:200]  # First 200 chars
                
                # Try error field
                error = response_data.get('error', '')
                if error:
                    return str(error)[:200]
            
            # Fall back to error_type
            return result.get('error_type', 'No error message available')
        except:
            return 'Error extracting error message'
    
    def _save_checkpoint(self):
        """Save current progress as a checkpoint"""
        if not self.output_file:
            return
            
        try:
            base_path = Path(self.output_file)
            checkpoint_file = base_path.with_suffix('.json').with_name(f"{base_path.stem}_checkpoint.json")
            
            checkpoint_data = {
                "timestamp": datetime.now().isoformat(),
                "progress": {
                    "total_questions": self.total,
                    "completed": self.completed,
                    "successful": self.successful,
                    "failed": self.failed,
                    "results_written": self.results_written
                },
                "statistics": self.get_statistics()
            }
            
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"⚠️ Error saving checkpoint: {e}")
        
    def finalize_output(self):
        """Finalize the output file with final statistics and consolidate results"""
        if not self.output_file or self.finalized:
            return
            
        # Mark as finalized to prevent multiple calls
        self.finalized = True
        
        try:
            base_path = Path(self.output_file)
            final_file = base_path.with_suffix('.json').with_name(f"{base_path.stem}_final.json")
            
            final_data = {
                "metadata": {
                    "script_version": "multi_thread_agentic_search.py",
                    "completion_timestamp": datetime.now().isoformat(),
                    "execution_mode": "agentic_search_api",
                    "total_execution_time_seconds": time.time() - self.start_time
                },
                "final_statistics": self.get_statistics(),
                "summary": {
                    "questions_processed": self.completed,
                    "success_rate": (self.successful / self.total * 100) if self.total > 0 else 0,
                    "average_response_time": sum(self.response_times) / len(self.response_times) if self.response_times else 0,
                    "total_results_found": sum(self.result_counts)
                }
            }
            
            with open(final_file, 'w', encoding='utf-8') as f:
                json.dump(final_data, f, indent=2, ensure_ascii=False)
                
            print(f"📊 Final report saved: {final_file}")
                
        except Exception as e:
            print(f"⚠️ Error finalizing output: {e}")
        
    def update(self, success=True, status_code=None, error_type=None, response_time=None, result_count=0, result_data=None):
        with self.lock:
            self.completed += 1
            if success:
                self.successful += 1
            else:
                self.failed += 1
                # Collect failed request sample for analysis
                if result_data:
                    self.add_failed_sample(result_data)
                
            if status_code is not None:
                self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
                
            if error_type is not None:
                self.error_types[error_type] = self.error_types.get(error_type, 0) + 1
                
            if response_time is not None:
                self.response_times.append(response_time)
                
            self.result_counts.append(result_count)
            
            # Progress update
            if self.completed % 10 == 0 or self.completed == self.total:
                elapsed = time.time() - self.start_time
                rate = self.completed / elapsed if elapsed > 0 else 0
                print(f"📊 Progress: {self.completed}/{self.total} ({self.completed/self.total*100:.1f}%) - "
                      f"Success: {self.successful} - Rate: {rate:.2f} q/s")
    
    def get_statistics(self):
        """Get comprehensive statistics"""
        elapsed = time.time() - self.start_time
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        avg_result_count = sum(self.result_counts) / len(self.result_counts) if self.result_counts else 0
        
        return {
            "total_questions": self.total,
            "successful_requests": self.successful,
            "failed_requests": self.failed,
            "success_rate_percentage": (self.successful / self.total * 100) if self.total > 0 else 0,
            "processing_time_seconds": elapsed,
            "processing_rate_per_second": self.completed / elapsed if elapsed > 0 else 0,
            "average_response_time_seconds": avg_response_time,
            "min_response_time_seconds": min(self.response_times) if self.response_times else 0,
            "max_response_time_seconds": max(self.response_times) if self.response_times else 0,
            "status_code_distribution": dict(self.status_codes),
            "error_type_distribution": dict(self.error_types),
            "average_results_per_query": avg_result_count,
            "total_results_returned": sum(self.result_counts),
            "error_analysis": {
                "throttled_request_samples": self.throttled_request_samples,
                "failed_request_samples": self.failed_request_samples,
                "total_throttled_samples": len(self.throttled_request_samples),
                "total_failed_samples": len(self.failed_request_samples)
            }
        }

class AgenticSearchClient:
    """Agentic Search API client with optimized HTTP connection pooling"""
    
    def __init__(self):
        self.base_url = "https://jiantmo-retail-rag-web-app.azurewebsites.net/agentic/search"
        
        # Initialize optimized HTTP session for connection pooling and performance
        self.session = requests.Session()
        
        # Configure session for maximum performance with high concurrency
        # HTTPAdapter configuration for connection pooling
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=50,
            pool_maxsize=200,
            max_retries=3,
            pool_block=False
        )
        
        # Mount adapter for both HTTP and HTTPS
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # Initialize headers
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "agentic-search-tester/1.0",
            "Connection": "keep-alive"
        }
        
        print("🚀 HTTP session initialized with optimized connection pooling (50 pools, 200 max connections)")
        
    def __del__(self):
        """Cleanup HTTP session on object destruction"""
        if hasattr(self, 'session'):
            self.session.close()
        
    def _extract_product_info(self, response_data):
        """Extract product names and descriptions from the agentic search response"""
        product_info = {
            "product_names": [],
            "product_descriptions": [],
            "products_found": []
        }
        
        try:
            # Check if response has FormattedText field
            formatted_text = response_data.get("FormattedText", "")
            
            if formatted_text:
                # Try to parse as JSON if it looks like JSON
                if formatted_text.strip().startswith('{') or formatted_text.strip().startswith('['):
                    try:
                        parsed_data = json.loads(formatted_text)
                        
                        # Handle different response structures
                        if isinstance(parsed_data, list):
                            for item in parsed_data:
                                if isinstance(item, dict) and "content" in item:
                                    content = item["content"]
                                    if isinstance(content, dict):
                                        product_name = content.get("name", "")
                                        product_desc = content.get("description", "")
                                        if product_name:
                                            product_info["product_names"].append(product_name)
                                            product_info["product_descriptions"].append(product_desc)
                                            product_info["products_found"].append({
                                                "name": product_name,
                                                "description": product_desc,
                                                "price": content.get("price"),
                                                "ref_id": item.get("ref_id")
                                            })
                                        
                        elif isinstance(parsed_data, dict):
                            # Handle single product or other dict structures
                            if "content" in parsed_data:
                                content = parsed_data["content"]
                                product_name = content.get("name", "")
                                product_desc = content.get("description", "")
                                if product_name:
                                    product_info["product_names"].append(product_name)
                                    product_info["product_descriptions"].append(product_desc)
                                    product_info["products_found"].append({
                                        "name": product_name,
                                        "description": product_desc,
                                        "price": content.get("price"),
                                        "ref_id": parsed_data.get("ref_id")
                                    })
                                    
                    except json.JSONDecodeError:
                        # If not valid JSON, try to extract product names from text
                        import re
                        name_matches = re.findall(r'"name":\s*"([^"]+)"', formatted_text)
                        desc_matches = re.findall(r'"description":\s*"([^"]+)"', formatted_text)
                        product_info["product_names"] = name_matches
                        product_info["product_descriptions"] = desc_matches
                        
                        # Create products_found from extracted names/descriptions
                        for i, name in enumerate(name_matches):
                            desc = desc_matches[i] if i < len(desc_matches) else ""
                            product_info["products_found"].append({
                                "name": name,
                                "description": desc,
                                "price": None,
                                "ref_id": None
                            })
                            
        except Exception as e:
            print(f"⚠️ Error extracting product info: {e}")
        
        return product_info

    def search(self, query_text, retry_count=1):
        """Execute agentic search API call with timing"""
        
        payload = {
            "query": query_text
        }
        
        start_time = time.time()
        
        for attempt in range(retry_count + 1):
            try:
                response = self.session.post(
                    self.base_url, 
                    json=payload, 
                    headers=self.headers, 
                    timeout=30
                )
                
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    response_data = response.json()
                    
                    # Extract product information
                    product_info = self._extract_product_info(response_data)
                    
                    return {
                        "success": True,
                        "api_type": "agentic_search",
                        "timestamp": datetime.now().isoformat(),
                        "response_time_seconds": response_time,
                        "result_count": len(product_info.get("products_found", [])),
                        "status_code": response.status_code,
                        "api_response_products": {
                            "product_names_found": product_info.get("product_names", [])
                        },
                        "response_data": response_data,
                        "extracted_products": product_info.get("products_found", [])
                    }
                else:
                    # Handle HTTP errors
                    if attempt < retry_count:
                        print(f"⚠️ HTTP {response.status_code} on attempt {attempt + 1}, retrying...")
                        time.sleep(1)
                        continue
                    
                    response_time = time.time() - start_time
                    return {
                        "success": False,
                        "api_type": "agentic_search",
                        "timestamp": datetime.now().isoformat(),
                        "response_time_seconds": response_time,
                        "result_count": 0,
                        "status_code": response.status_code,
                        "error_type": f"HTTP_{response.status_code}",
                        "api_response_products": {
                            "product_names_found": []
                        },
                        "response_data": {"error": f"HTTP {response.status_code}", "text": response.text[:500]},
                        "extracted_products": []
                    }
                    
            except requests.exceptions.Timeout:
                if attempt < retry_count:
                    print(f"⚠️ Timeout on attempt {attempt + 1}, retrying...")
                    continue
                
                response_time = time.time() - start_time
                return {
                    "success": False,
                    "api_type": "agentic_search",
                    "timestamp": datetime.now().isoformat(),
                    "response_time_seconds": response_time,
                    "result_count": 0,
                    "status_code": None,
                    "error_type": "timeout",
                    "api_response_products": {
                        "product_names_found": []
                    },
                    "response_data": {"error": "Request timeout", "query": query_text},
                    "extracted_products": []
                }
                
            except requests.exceptions.RequestException as e:
                if attempt < retry_count:
                    print(f"⚠️ Request error on attempt {attempt + 1}: {e}, retrying...")
                    continue
                
                response_time = time.time() - start_time
                return {
                    "success": False,
                    "api_type": "agentic_search",
                    "timestamp": datetime.now().isoformat(),
                    "response_time_seconds": response_time,
                    "result_count": 0,
                    "status_code": None,
                    "error_type": "request_error",
                    "api_response_products": {
                        "product_names_found": []
                    },
                    "response_data": {"error": str(e), "query": query_text},
                    "extracted_products": []
                }
        
        # This should never be reached, but included for completeness
        response_time = time.time() - start_time
        return {
            "success": False,
            "api_type": "agentic_search",
            "timestamp": datetime.now().isoformat(),
            "response_time_seconds": response_time,
            "result_count": 0,
            "status_code": None,
            "error_type": "max_retries_exceeded",
            "api_response_products": {
                "product_names_found": []
            },
            "response_data": {"error": "Maximum retry attempts exceeded", "query": query_text},
            "extracted_products": []
        }

class QuestionExtractor:
    """Extract questions from various file types"""
    
    @staticmethod
    def find_question_files(base_path="."):
        """Find all question files in the given path"""
        files = []
        base_dir = Path(base_path)
        
        # Look for test case files
        test_case_dir = base_dir / "test_case"
        if test_case_dir.exists():
            for file_path in test_case_dir.glob("questions_run_*.json"):
                files.append(str(file_path))
        
        # Also look in current directory
        for file_path in base_dir.glob("questions_run_*.json"):
            files.append(str(file_path))
            
        return sorted(files)
    
    @staticmethod
    def extract_questions_from_file(file_path):
        """Extract questions from a single JSON file"""
        questions = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "questions" in item:
                        product_name = item.get("name", "Unknown Product")
                        product_description = item.get("description", "")
                        product_price = item.get("price", 0)
                        product_category = item.get("category", "")
                        product_attributes = item.get("attributes", [])
                        
                        for question_type, question_text in item["questions"].items():
                            questions.append({
                                "question": question_text,
                                "question_type": question_type,
                                "original_product_name": product_name,
                                "original_product_description": product_description,
                                "original_product_price": product_price,
                                "original_product_category": product_category,
                                "original_product_attributes": product_attributes,
                                "source_file": file_path
                            })
                            
        except Exception as e:
            print(f"⚠️ Error reading {file_path}: {e}")
            
        return questions

def process_single_question(client, question_data, progress_tracker, delay=0, max_retries=2):
    """Process a single question with detailed progress tracking and real-time file output"""
    # Check for shutdown request before processing
    if shutdown_requested:
        return None
    
    # No delay between threads for maximum throughput
    # All threads run in parallel without any artificial delays
    
    # Retry mechanism for failed requests
    last_result = None
    for retry_attempt in range(max_retries + 1):
        try:
            # Execute the search
            result = client.search(question_data["question"], retry_count=1)
            
            # Add test case context to result
            result["test_case_context"] = {
                "original_product_name": question_data.get("original_product_name"),
                "original_product_description": question_data.get("original_product_description"),
                "original_product_price": question_data.get("original_product_price"),
                "original_product_attributes": question_data.get("original_product_attributes"),
                "original_product_category": question_data.get("original_product_category"),
                "question": question_data.get("question"),
                "question_type": question_data.get("question_type")
            }
            
            last_result = result
            
            if result["success"]:
                break  # Success, no need to retry
            elif retry_attempt < max_retries:
                print(f"⚠️ Failed attempt {retry_attempt + 1} for question, retrying...")
                time.sleep(1)  # Brief delay before retry
                
        except Exception as e:
            print(f"⚠️ Exception during processing: {e}")
            if retry_attempt == max_retries:
                # Final attempt failed, create error result
                last_result = {
                    "success": False,
                    "api_type": "agentic_search",
                    "timestamp": datetime.now().isoformat(),
                    "response_time_seconds": 0,
                    "result_count": 0,
                    "status_code": None,
                    "error_type": "processing_exception",
                    "api_response_products": {
                        "product_names_found": []
                    },
                    "response_data": {"error": str(e), "query": question_data.get("question")},
                    "extracted_products": [],
                    "test_case_context": {
                        "original_product_name": question_data.get("original_product_name"),
                        "original_product_description": question_data.get("original_product_description"),
                        "original_product_price": question_data.get("original_product_price"),
                        "original_product_attributes": question_data.get("original_product_attributes"),
                        "original_product_category": question_data.get("original_product_category"),
                        "question": question_data.get("question"),
                        "question_type": question_data.get("question_type")
                    }
                }
    
    # Extract detailed metrics for tracking
    success = last_result["success"]
    status_code = last_result.get("status_code")
    error_type = last_result.get("error_type")
    response_time = last_result.get("response_time_seconds", 0)
    result_count = last_result.get("result_count", 0)
    
    # Update progress tracker
    progress_tracker.update(
        success=success,
        status_code=status_code,
        error_type=error_type,
        response_time=response_time,
        result_count=result_count,
        result_data=last_result  # Pass the full result for sample collection
    )
    
    # Immediately append result to file
    progress_tracker.append_result(last_result)
    
    return last_result

def main():
    """Main execution function"""
    global global_progress_tracker
    
    # Register signal handlers for graceful shutdown
    register_signal_handlers()
    
    parser = argparse.ArgumentParser(description='Multi-threaded Agentic Search Runner')
    parser.add_argument('--workers', '-w', type=int, default=50, help='Number of worker threads (default: 50)')
    parser.add_argument('--delay', '-d', type=float, default=0.1, help='Delay between requests in seconds (default: 0.1)')
    parser.add_argument('--path', '-p', default='.', help='Base path to search for files')
    
    args = parser.parse_args()
    
    print("\n🚀 Multi-threaded Agentic Search Runner")
    print("=" * 60)
    
    # Initialize client
    client = AgenticSearchClient()
    
    # Find and extract questions
    print("📁 Finding question files...")
    files = QuestionExtractor.find_question_files(args.path)
    print(f"   Found {len(files)} files")
    
    print("📝 Extracting questions...")
    all_questions = []
    for file_path in files:
        questions = QuestionExtractor.extract_questions_from_file(file_path)
        all_questions.extend(questions)
        print(f"   {Path(file_path).name}: {len(questions)} questions")
    
    if not all_questions:
        print("❌ No questions found!")
        return
    
    print(f"🎯 Total questions to process: {len(all_questions)}")
    
    # Create output directory
    output_dir = Path("test_case_acs_analysis")
    output_dir.mkdir(exist_ok=True)
    print(f"📁 Output directory: {output_dir.absolute()}")
    
    # Create output file with timestamp inside the analysis folder
    start_time = datetime.now()
    timestamp = start_time.strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"agentic_results_{timestamp}.json"
    
    print(f"📄 Output file: {output_file}")
    print("🔄 Starting API calls...")
    
    # Initialize progress tracking with output file
    progress_tracker = ProgressTracker(len(all_questions), str(output_file))
    global_progress_tracker = progress_tracker  # Set global reference for signal handler
    
    print("💡 Press Ctrl+C at any time to gracefully stop and save current progress")
    print("💡 Alternative: Type 'q' or 'quit' and press Enter to stop")
    
    # Start monitoring thread for alternative stop method
    monitor_thread = start_monitoring_thread()
    
    # Process with threading
    completed_futures = 0
    total_futures = len(all_questions)
    
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            # Submit all tasks
            future_to_question = {
                executor.submit(process_single_question, client, question, progress_tracker, args.delay): question
                for question in all_questions
            }
            
            # Process completed futures
            for future in as_completed(future_to_question):
                if shutdown_requested or force_exit:
                    print("🛑 Shutdown requested, cancelling remaining tasks...")
                    # Cancel remaining futures
                    for remaining_future in future_to_question:
                        if not remaining_future.done():
                            remaining_future.cancel()
                    break
                    
                completed_futures += 1
                
                try:
                    result = future.result()
                except Exception as e:
                    print(f"⚠️ Task exception: {e}")
                    
        # Force executor shutdown with short wait
        print("🔄 Waiting for thread pool shutdown...")
        executor.shutdown(wait=False)  # Don't wait for remaining tasks
                    
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        shutdown_requested = True
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        
    end_time = datetime.now()
    duration = end_time - start_time
    
    # Finalize the output file with final statistics
    progress_tracker.finalize_output()
    
    # Get detailed statistics
    stats = progress_tracker.get_statistics()
    
    print("\n" + "=" * 60)
    if shutdown_requested:
        print("🛑 EXECUTION STOPPED (Graceful Shutdown)")
    else:
        print("✅ EXECUTION COMPLETED")
    
    print(f"⏱️ Total Time: {duration}")
    print(f"📊 Questions Processed: {progress_tracker.completed}/{len(all_questions)}")
    print(f"📈 Success Rate: {stats['success_rate_percentage']:.1f}%")
    print(f"⚡ Processing Rate: {stats['processing_rate_per_second']:.2f} questions/second")
    print(f"⏳ Average Response Time: {stats['average_response_time_seconds']:.3f} seconds")
    print(f"📋 Total Results Returned: {stats['total_results_returned']}")
    print(f"🔢 Average Results per Query: {stats['average_results_per_query']:.1f}")
    print(f"💾 Results saved to: {output_file}")
    
    # Show status code distribution
    if stats['status_code_distribution']:
        print("\n📊 Status Code Distribution:")
        for code, count in stats['status_code_distribution'].items():
            print(f"   {code}: {count}")
    
    # Show error types if any
    if stats['error_type_distribution']:
        print("\n⚠️ Error Types:")
        for error_type, count in stats['error_type_distribution'].items():
            print(f"   {error_type}: {count}")
    
    # Show error analysis samples
    error_analysis = stats.get('error_analysis', {})
    if error_analysis.get('throttled_request_samples'):
        print(f"\n🚫 Throttled Request Examples ({error_analysis['total_throttled_samples']} samples):")
        for i, sample in enumerate(error_analysis['throttled_request_samples'][:2], 1):
            print(f"   {i}. [{sample['timestamp']}] {sample['question']}")
            print(f"      Error: {sample['error_message'][:100]}...")
            print(f"      Response time: {sample['response_time']:.2f}s")
    
    if error_analysis.get('failed_request_samples'):
        print(f"\n❌ Failed Request Examples ({error_analysis['total_failed_samples']} samples):")
        for i, sample in enumerate(error_analysis['failed_request_samples'][:2], 1):
            print(f"   {i}. [{sample['timestamp']}] {sample['question']}")
            print(f"      Error: {sample['error_message'][:100]}...")
            print(f"      Type: {sample['error_type']}, Response time: {sample['response_time']:.2f}s")
    
    print("=" * 60)
    
    # Show file locations
    base_path = Path(output_file)
    result_file = base_path.with_suffix('.jsonl').with_name(f"{base_path.stem}_results.jsonl")
    final_file = base_path.with_suffix('.json').with_name(f"{base_path.stem}_final.json")
    checkpoint_file = base_path.with_suffix('.json').with_name(f"{base_path.stem}_checkpoint.json")
    
    print("📁 Generated Files:")
    print(f"   🔄 Real-time results: {result_file}")
    print(f"   📊 Final report: {final_file}")
    print(f"   💾 Latest checkpoint: {checkpoint_file}")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        import traceback
        traceback.print_exc()
