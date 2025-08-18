#!/usr/bin/env python3
"""
Multi-threaded Dataverse Search Runner
Process all questions with threading and save results to unified JSON
"""

import json
import requests
import threading
import time
import sys
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from collections import Counter
import re
import shutil
import psutil
import platform
import base64
from urllib.parse import urlencode
import subprocess
import signal
import atexit
from search_evaluator import SearchEvaluator

# Get Python path from system configuration
def get_python_path():
    """Dynamically get Python executable path from system"""
    try:
        # First try to get current Python executable
        current_python = sys.executable
        if current_python and os.path.exists(current_python):
            return current_python
        
        # Fallback: try to find python in PATH
        python_path = shutil.which('python')
        if python_path:
            return python_path
            
        # Another fallback: try python3
        python3_path = shutil.which('python3')
        if python3_path:
            return python3_path
            
        # Last resort: use the hardcoded path if nothing else works
        fallback_path = r"C:\Users\jiantmo\AppData\Local\Programs\Python\Python312\python.exe"
        if os.path.exists(fallback_path):
            return fallback_path
            
        raise FileNotFoundError("Could not find Python executable")
        
    except Exception as e:
        print(f"Warning: Could not detect Python path automatically: {e}")
        return sys.executable  # Use current executable as last resort

def get_system_hardware_config():
    """Get system hardware configuration to determine optimal thread count"""
    try:
        # Get CPU information
        cpu_count = psutil.cpu_count(logical=True)  # Logical processors (with hyperthreading)
        cpu_physical = psutil.cpu_count(logical=False)  # Physical cores
        cpu_freq = psutil.cpu_freq()
        
        # Get memory information (in GB)
        memory = psutil.virtual_memory()
        memory_gb = memory.total / (1024**3)
        memory_available_gb = memory.available / (1024**3)
        
        # Get system information
        system_info = {
            "cpu_logical_cores": cpu_count,
            "cpu_physical_cores": cpu_physical,
            "cpu_frequency_mhz": cpu_freq.current if cpu_freq else 0,
            "memory_total_gb": round(memory_gb, 2),
            "memory_available_gb": round(memory_available_gb, 2),
            "memory_usage_percent": memory.percent,
            "platform": platform.system(),
            "platform_release": platform.release()
        }
        
        return system_info
        
    except Exception as e:
        print(f"Warning: Could not detect system configuration: {e}")
        return {
            "cpu_logical_cores": 4,
            "cpu_physical_cores": 4,
            "cpu_frequency_mhz": 2000,
            "memory_total_gb": 8.0,
            "memory_available_gb": 4.0,
            "memory_usage_percent": 50.0,
            "platform": "Unknown",
            "platform_release": "Unknown"
        }

def calculate_optimal_thread_config(system_config, total_questions):
    """Calculate optimal thread count - default to 50 threads for stability"""
    
    # Default thread count optimized for server stability and consistent performance
    # 50 threads provides good balance between speed and server load
    optimal_threads = 50
    
    # Small delay to prevent overwhelming the server
    delay = 0.1  # 100ms delay between requests to reduce server load
    
    return {
        "recommended_threads": optimal_threads,
        "recommended_delay": delay,
        "reasoning": {
            "strategy": "Default 50 threads for balanced performance and stability",
            "thread_count": optimal_threads,
            "delay_ms": int(delay * 1000),
            "rationale": "50 threads provides optimal balance between speed and server stability"
        }
    }

# Global Python path from system configuration
PYTHON_PATH = get_python_path()

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
        try:
            if global_progress_tracker:
                global_progress_tracker.finalize_output()
        except:
            pass
        # Use os._exit() for immediate termination without cleanup
        os._exit(1)
    
    print(f"\n🛑 Received interrupt signal ({signum}). Initiating graceful shutdown...")
    print("📝 Saving current progress and results...")
    shutdown_requested = True
    
    # Try to finalize results if tracker exists
    if global_progress_tracker:
        try:
            global_progress_tracker.finalize_output()
            print("✅ Results saved successfully before shutdown!")
        except Exception as e:
            print(f"⚠️ Error saving results during shutdown: {e}")
    
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
        
        # On Windows, also try to handle console Ctrl events
        if platform.system() == "Windows":
            try:
                import win32api
                import win32con
                
                def windows_console_handler(ctrl_type):
                    """Windows-specific console control handler"""
                    if ctrl_type in (win32con.CTRL_C_EVENT, win32con.CTRL_BREAK_EVENT):
                        signal_handler(ctrl_type, None)
                        return True  # Return True to indicate we handled the event
                    return False  # Let Windows handle other events
                
                win32api.SetConsoleCtrlHandler(windows_console_handler, True)
                print("✅ Windows console handler registered")
            except ImportError:
                print("⚠️ win32api not available, using standard signal handlers only")
            except Exception as e:
                print(f"⚠️ Failed to register Windows console handler: {e}")
        
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
            print(f"⚠️ Error during exit cleanup: {e}")

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
        
        # Initialize output file
        if self.output_file:
            self._initialize_output_file()
    
    def _initialize_output_file(self):
        """Initialize the output file with metadata"""
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                metadata = {
                    "test_metadata": {
                        "start_time": datetime.now().isoformat(),
                        "total_questions": self.total,
                        "status": "running"
                    }
                }
                # Write metadata first
                json.dump(metadata, f, indent=2, ensure_ascii=False)
                f.write('\n')
                f.flush()
        except Exception as e:
            print(f"❌ Error initializing output file: {e}")
    
    def append_result(self, result):
        """Append a single result to the file immediately using append mode with thread safety"""
        if not self.output_file:
            return
            
        # Use lock to ensure thread-safe file writing
        with self.lock:
            try:
                # Use append mode and write one result per line as JSONL format
                result_file = self.output_file.replace('.json', '_results.jsonl')
                with open(result_file, 'a', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False)
                    f.write('\n')
                    f.flush()
                
                self.results_written += 1
                
                # Check if we need to save a checkpoint
                current_time = time.time()
                if current_time - self.last_checkpoint_time >= self.checkpoint_interval:
                    self._save_checkpoint()
                    self.last_checkpoint_time = current_time
                    
            except Exception as e:
                print(f"❌ Error appending result: {e}")
    
    def _save_checkpoint(self):
        """Save current progress as a checkpoint"""
        if not self.output_file:
            return
            
        try:
            checkpoint_file = self.output_file.replace('.json', '_checkpoint.json')
            checkpoint_data = {
                "checkpoint_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "completed": self.completed,
                    "successful": self.successful,
                    "failed": self.failed,
                    "results_written": self.results_written,
                    "processing_duration_seconds": time.time() - self.start_time,
                    "current_statistics": self.get_statistics()
                }
            }
            
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
                f.flush()
                
        except Exception as e:
            print(f"⚠️ Error saving checkpoint: {e}")
    
    def finalize_output(self):
        """Finalize the output file with final statistics and consolidate results"""
        if not self.output_file or self.finalized:
            return
            
        # Mark as finalized to prevent multiple calls
        self.finalized = True
        
        try:
            # Save final checkpoint first
            self._save_checkpoint()
            
            # Read metadata file
            with open(self.output_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Read all results from JSONL file
            result_file = self.output_file.replace('.json', '_results.jsonl')
            results = []
            if os.path.exists(result_file):
                with open(result_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            try:
                                results.append(json.loads(line.strip()))
                            except json.JSONDecodeError as e:
                                print(f"⚠️ Skipping malformed result line: {e}")
                                continue
            
            # Create final consolidated output
            final_data = {
                "test_metadata": {
                    **metadata["test_metadata"],
                    "end_time": datetime.now().isoformat(),
                    "status": "completed" if not shutdown_requested else "interrupted",
                    "results_written": self.results_written,
                    "final_statistics": self.get_statistics(),
                    "interrupted_by_user": shutdown_requested,
                    "detailed_metrics": {
                        "response_time_analysis": {
                            "all_response_times": self.response_times,
                            "percentiles": {
                                "p50": sorted(self.response_times)[len(self.response_times)//2] if self.response_times else 0,
                                "p95": sorted(self.response_times)[int(len(self.response_times)*0.95)] if self.response_times else 0,
                                "p99": sorted(self.response_times)[int(len(self.response_times)*0.99)] if self.response_times else 0
                            }
                        },
                        "result_count_analysis": {
                            "all_result_counts": self.result_counts,
                            "max_results_in_single_query": max(self.result_counts) if self.result_counts else 0,
                            "min_results_in_single_query": min(self.result_counts) if self.result_counts else 0
                        }
                    }
                },
                "results": results
            }
            
            # Write final consolidated file
            final_file = self.output_file.replace('.json', '_final.json')
            with open(final_file, 'w', encoding='utf-8') as f:
                json.dump(final_data, f, indent=2, ensure_ascii=False)
                f.flush()
                
            if shutdown_requested:
                print(f"🛑 Interrupted results saved to: {final_file}")
                print(f"📊 Partial results were saved to: {result_file}")
                print(f"📈 Progress: {self.completed}/{self.total} questions processed before interruption")
            else:
                print(f"✅ Final results saved to: {final_file}")
                print(f"📊 Real-time results were saved to: {result_file}")
                
        except Exception as e:
            print(f"❌ Error finalizing output: {e}")
        
    def update(self, success=True, status_code=None, error_type=None, response_time=None, result_count=0):
        with self.lock:
            self.completed += 1
            if success:
                self.successful += 1
            else:
                self.failed += 1
            
            # Track status codes
            if status_code:
                self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
            
            # Track error types
            if error_type:
                self.error_types[error_type] = self.error_types.get(error_type, 0) + 1
            
            # Track response times
            if response_time:
                self.response_times.append(response_time)
            
            # Track result counts
            self.result_counts.append(result_count)
            
            # Print progress every 10 items or if shutdown requested
            if self.completed % 10 == 0 or self.completed == self.total or shutdown_requested:
                elapsed = time.time() - self.start_time
                rate = self.completed / elapsed if elapsed > 0 else 0
                progress = (self.completed / self.total) * 100
                
                status_msg = f"Progress: {self.completed}/{self.total} ({progress:.1f}%) ✅{self.successful} ❌{self.failed} Rate: {rate:.1f}/s"
                if shutdown_requested:
                    status_msg += " 🛑"
                print(status_msg)
    
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
            "total_results_returned": sum(self.result_counts)
        }

class EnhancedTokenManager:
    """Enhanced token management with comprehensive Bearer and Refresh token handling"""
    
    def __init__(self, tenant_id, client_id, resource_url):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.resource_url = resource_url
        self.token_endpoint = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        self.device_code_endpoint = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/devicecode"
        
        # Enhanced token storage files
        self.token_config_file = "enhanced_tokens.config"
        self.legacy_token_file = "token.config"
        self.legacy_refresh_file = "refresh_token.config"
        
        # Token cache with expiration tracking
        self._token_cache = {
            "access_token": None,
            "refresh_token": None,
            "expires_at": None,
            "last_refresh": None
        }
        
        # Load existing tokens on initialization
        self._load_token_cache()
    
    def _load_token_cache(self):
        """Load tokens from enhanced config file or migrate from legacy files"""
        try:
            # Try to load from enhanced config first
            if os.path.exists(self.token_config_file):
                with open(self.token_config_file, 'r') as f:
                    stored_data = json.load(f)
                    self._token_cache.update(stored_data)
                    print(f"✅ Loaded tokens from {self.token_config_file}")
                    return
            
            # Migration from legacy files
            print("🔄 Migrating from legacy token files...")
            migrated = False
            
            # Load legacy access token
            if os.path.exists(self.legacy_token_file):
                with open(self.legacy_token_file, 'r') as f:
                    access_token = f.read().strip()
                    if access_token:
                        self._token_cache["access_token"] = access_token
                        # Try to extract expiration from JWT
                        exp_time = self._extract_jwt_expiration(access_token)
                        if exp_time:
                            self._token_cache["expires_at"] = exp_time.isoformat()
                        migrated = True
                        print(f"✅ Migrated access token from {self.legacy_token_file}")
            
            # Load legacy refresh token
            if os.path.exists(self.legacy_refresh_file):
                with open(self.legacy_refresh_file, 'r') as f:
                    refresh_token = f.read().strip()
                    if refresh_token:
                        self._token_cache["refresh_token"] = refresh_token
                        migrated = True
                        print(f"✅ Migrated refresh token from {self.legacy_refresh_file}")
            
            # Save migrated data to new format
            if migrated:
                self._save_token_cache()
                print("✅ Token migration completed")
            
        except Exception as e:
            print(f"⚠️ Error loading token cache: {e}")
            self._token_cache = {
                "access_token": None,
                "refresh_token": None,
                "expires_at": None,
                "last_refresh": None
            }
    
    def _save_token_cache(self):
        """Save current token cache to enhanced config file"""
        try:
            # Update last refresh timestamp
            self._token_cache["last_refresh"] = datetime.now().isoformat()
            
            with open(self.token_config_file, 'w') as f:
                json.dump(self._token_cache, f, indent=2)
            
            # Also update legacy token file for backward compatibility
            if self._token_cache.get("access_token"):
                with open(self.legacy_token_file, 'w') as f:
                    f.write(self._token_cache["access_token"])
            
            print(f"✅ Token cache saved to {self.token_config_file}")
            
        except Exception as e:
            print(f"❌ Error saving token cache: {e}")
    
    def _extract_jwt_expiration(self, token):
        """Extract expiration time from JWT token"""
        try:
            if not token or not isinstance(token, str):
                return None
                
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            payload = parts[1]
            padding = 4 - (len(payload) % 4)
            if padding != 4:
                payload += '=' * padding
            
            decoded_bytes = base64.urlsafe_b64decode(payload)
            decoded_json = json.loads(decoded_bytes.decode('utf-8'))
            
            exp_timestamp = decoded_json.get('exp')
            if exp_timestamp:
                return datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            
        except Exception as e:
            print(f"⚠️ Error extracting JWT expiration: {e}")
        
        return None
    
    def get_valid_access_token(self):
        """Get a valid access token, refreshing if necessary"""
        # Check if current access token is valid
        if self._is_access_token_valid():
            return {
                'success': True,
                'access_token': self._token_cache["access_token"],
                'method': 'cached'
            }
        
        # Try to refresh using refresh token
        if self._token_cache.get("refresh_token"):
            result = self._refresh_with_stored_token()
            if result['success']:
                return result
        
        # Fallback to device code flow
        return self._acquire_token_device_code()
    
    def _is_access_token_valid(self):
        """Check if the current access token is valid and not expired"""
        try:
            access_token = self._token_cache.get("access_token")
            if not access_token:
                return False
            
            # Check expiration time
            expires_at_str = self._token_cache.get("expires_at")
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            else:
                # Extract from JWT if not stored
                expires_at = self._extract_jwt_expiration(access_token)
                if expires_at:
                    self._token_cache["expires_at"] = expires_at.isoformat()
                    self._save_token_cache()
            
            if not expires_at:
                print("⚠️ Cannot determine token expiration, assuming invalid")
                return False
            
            # Add 5-minute buffer
            current_time = datetime.now(tz=timezone.utc)
            buffer_time = expires_at - timedelta(minutes=5)
            
            if current_time >= buffer_time:
                time_remaining = expires_at - current_time
                print(f"❌ Token expires at {expires_at} (in {time_remaining}), refresh needed")
                return False
            else:
                time_remaining = buffer_time - current_time
                print(f"✅ Token valid until {expires_at} (refresh in {time_remaining})")
                return True
                
        except Exception as e:
            print(f"❌ Error validating access token: {e}")
            return False
    
    def _refresh_with_stored_token(self):
        """Refresh access token using stored refresh token"""
        print("🔄 Refreshing access token with stored refresh token...")
        
        refresh_token = self._token_cache.get("refresh_token")
        if not refresh_token:
            return {
                'success': False,
                'error': 'No refresh token available',
                'method': 'refresh_token'
            }
        
        data = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'refresh_token': refresh_token,
            'scope': f'{self.resource_url}user_impersonation'
        }
        
        try:
            response = requests.post(self.token_endpoint, data=data, timeout=30)
            response.raise_for_status()
            
            token_response = response.json()
            
            # Update token cache with new tokens
            self._token_cache["access_token"] = token_response['access_token']
            
            # Update refresh token if provided (might be rotated)
            if 'refresh_token' in token_response:
                self._token_cache["refresh_token"] = token_response['refresh_token']
            
            # Calculate and store expiration time
            expires_in = token_response.get('expires_in', 3600)
            expires_at = datetime.now(tz=timezone.utc) + timedelta(seconds=expires_in)
            self._token_cache["expires_at"] = expires_at.isoformat()
            
            # Save updated cache
            self._save_token_cache()
            
            print("✅ Access token refreshed successfully!")
            return {
                'success': True,
                'access_token': token_response['access_token'],
                'expires_in': expires_in,
                'method': 'refresh_token'
            }
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print("❌ Refresh token is invalid or expired")
                # Clear invalid refresh token
                self._token_cache["refresh_token"] = None
                self._save_token_cache()
            else:
                print(f"❌ HTTP error during token refresh: {e}")
            
            return {
                'success': False,
                'error': f"Token refresh failed: {str(e)}",
                'method': 'refresh_token'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Token refresh failed: {str(e)}",
                'method': 'refresh_token'
            }
    
    
    def _acquire_token_device_code(self):
        """Acquire token using device code flow"""
        global shutdown_requested, force_exit
        print("🔄 Initiating device code authentication flow...")
        
        device_data = {
            'client_id': self.client_id,
            'scope': f'{self.resource_url}user_impersonation'
        }
        
        try:
            device_response = requests.post(self.device_code_endpoint, data=device_data, timeout=30)
            device_response.raise_for_status()
            device_result = device_response.json()
            
            print(f"📱 Device Code Authentication Required:")
            print(f"   1. Open: {device_result['verification_uri']}")
            print(f"   2. Enter code: {device_result['user_code']}")
            print(f"   3. Complete authentication in browser")
            print(f"   4. Waiting for completion... ({device_result.get('expires_in', 900)} seconds)")
            
            token_data = {
                'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
                'client_id': self.client_id,
                'device_code': device_result['device_code']
            }
            
            interval = device_result.get('interval', 5)
            expires_in = device_result.get('expires_in', 900)
            start_time = time.time()
            
            while time.time() - start_time < expires_in:
                if shutdown_requested or force_exit:
                    print("🛑 Authentication interrupted by user request")
                    return {
                        'success': False,
                        'error': 'Authentication interrupted by user',
                        'method': 'device_code'
                    }
                
                try:
                    token_response = requests.post(self.token_endpoint, data=token_data, timeout=30)
                    
                    if token_response.status_code == 200:
                        token_result = token_response.json()
                        print("✅ Authentication completed successfully!")
                        
                        # Update token cache
                        self._token_cache["access_token"] = token_result['access_token']
                        
                        if 'refresh_token' in token_result:
                            self._token_cache["refresh_token"] = token_result['refresh_token']
                        
                        # Calculate expiration
                        expires_in = token_result.get('expires_in', 3600)
                        expires_at = datetime.now(tz=timezone.utc) + timedelta(seconds=expires_in)
                        self._token_cache["expires_at"] = expires_at.isoformat()
                        
                        # Save updated cache
                        self._save_token_cache()
                        
                        return {
                            'success': True,
                            'access_token': token_result['access_token'],
                            'expires_in': expires_in,
                            'method': 'device_code'
                        }
                    
                    elif token_response.status_code == 400:
                        error_data = token_response.json()
                        if error_data.get('error') == 'authorization_pending':
                            remaining_min = int((expires_in - (time.time() - start_time)) / 60)
                            print(f"⏳ Waiting for user authentication... ({remaining_min} min remaining)")
                            time.sleep(interval)
                            continue
                        else:
                            return {
                                'success': False,
                                'error': f"Device code error: {error_data.get('error_description', str(error_data))}",
                                'method': 'device_code'
                            }
                    else:
                        return {
                            'success': False,
                            'error': f"Unexpected response: {token_response.status_code}",
                            'method': 'device_code'
                        }
                        
                except requests.exceptions.RequestException as e:
                    print(f"⚠️ Poll request failed, retrying: {e}")
                    time.sleep(interval)
                    continue
            
            return {
                'success': False,
                'error': "Device code authentication timed out",
                'method': 'device_code'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Device code flow failed: {str(e)}",
                'method': 'device_code'
            }
    
    def acquire_token_silently(self):
        """Main method to acquire token using available methods with automatic refresh"""
        print("🚀 Attempting Token Acquisition with Enhanced Management...")
        return self.get_valid_access_token()
    
    def force_refresh(self):
        """Force refresh of access token using refresh token"""
        if self._token_cache.get("refresh_token"):
            return self._refresh_with_stored_token()
        else:
            return self._acquire_token_device_code()
    
    def clear_tokens(self):
        """Clear all stored tokens (useful for testing or when tokens are corrupted)"""
        self._token_cache = {
            "access_token": None,
            "refresh_token": None,
            "expires_at": None,
            "last_refresh": None
        }
        self._save_token_cache()
        print("🗑️ All tokens cleared")

class DataverseSearchClient:
    """Dataverse API client with enhanced token management and optimized HTTP connection pooling"""
    
    def __init__(self, token_file="token.config"):
        self.base_url = "https://aurorabapenv87b96.crm10.dynamics.com/api/copilot/v1.0/queryskillstructureddata"
        self.token_file = token_file
        self._token_lock = threading.Lock()  # Thread safety for token operations
        self._last_token_check = time.time()  # Track when we last checked token
        self._token_check_interval = 60  # Check token every 60 seconds
        
        # Initialize optimized HTTP session for connection pooling and performance
        self.session = requests.Session()
        
        # Configure session for maximum performance with high concurrency
        # HTTPAdapter configuration for connection pooling
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=50,     # Number of connection pools to cache
            pool_maxsize=200,        # Maximum number of connections in each pool
            max_retries=3,           # Retry failed requests
            pool_block=False         # Don't block when pool is full
        )
        
        # Mount adapter for both HTTP and HTTPS
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # OAuth2 configuration for token refresh
        self.tenant_id = "4abc24ea-2d0b-4011-87d4-3de32ca1e9cc"
        self.client_id = "51f81489-12ee-4a9e-aaae-a2591f45987d"  # Fixed client ID from Copilot team
        self.resource = "https://aurorabapenv87b96.crm10.dynamics.com/"
        self.redirect_url = "https://localhost"
        
        # Initialize enhanced token manager
        self.token_manager = EnhancedTokenManager(self.tenant_id, self.client_id, self.resource)
        
        # Get initial valid token
        token_result = self.token_manager.get_valid_access_token()
        if not token_result['success']:
            print("❌ Failed to get initial access token")
            raise Exception(f"Token acquisition failed: {token_result.get('error', 'Unknown error')}")
        
        self.token = token_result['access_token']
        print(f"✅ Initial token acquired using {token_result['method']} method")
        
        # Initialize headers with current token
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "insomnia/11.4.0",
            "x-ms-crm-query-language": "1033",
            "x-ms-crm-service-root-url": "https://aurorabapenv87b96.crm10.dynamics.com/",
            "x-ms-crm-userid": "aurorauser01@aurorafinanceintegration02.onmicrosoft.com",
            "x-ms-organization-id": "440a70c9-ff61-f011-beb8-6045bd09e9cc",
            "x-ms-user-agent": "PowerVA/2",
            "Authorization": f"Bearer {self.token}",
            "Connection": "keep-alive"
        }
        
        print("🚀 HTTP session initialized with optimized connection pooling (50 pools, 200 max connections)")
        
    def __del__(self):
        """Cleanup HTTP session on object destruction"""
        if hasattr(self, 'session'):
            self.session.close()
        
    def _update_token_and_headers(self, new_token):
        """Update token and headers with thread safety"""
        with self._token_lock:
            self.token = new_token
            self.headers["Authorization"] = f"Bearer {self.token}"
            print("✅ Token and headers updated")
    
    def _is_token_valid(self):
        """Check if the current token is valid using enhanced token manager"""
        return self.token_manager._is_access_token_valid()
    
    def _check_and_refresh_token_if_needed(self):
        """Proactively check and refresh token if needed (thread-safe)"""
        current_time = time.time()
        
        # Only check token every _token_check_interval seconds to avoid excessive checks
        if current_time - self._last_token_check < self._token_check_interval:
            return True
            
        with self._token_lock:
            self._last_token_check = current_time
            
            # Use enhanced token manager for validation and refresh
            token_result = self.token_manager.get_valid_access_token()
            if token_result['success']:
                # Update token if it changed
                new_token = token_result['access_token']
                if new_token != self.token:
                    self._update_token_and_headers(new_token)
                    print(f"🔄 Token refreshed using {token_result['method']} method")
                return True
            else:
                print(f"❌ Token refresh failed: {token_result.get('error', 'Unknown error')}")
                return False
    
    def refresh_token_if_needed(self):
        """Check token validity and refresh if needed using enhanced token manager"""
        with self._token_lock:
            token_result = self.token_manager.get_valid_access_token()
            if token_result['success']:
                new_token = token_result['access_token']
                if new_token != self.token:
                    self._update_token_and_headers(new_token)
                    print(f"✅ Token refreshed using {token_result['method']} method")
                return True
            else:
                print(f"❌ Token refresh failed: {token_result.get('error', 'Unknown error')}")
                return False
    
    def force_token_refresh(self):
        """Force a token refresh using refresh token"""
        with self._token_lock:
            token_result = self.token_manager.force_refresh()
            if token_result['success']:
                self._update_token_and_headers(token_result['access_token'])
                print(f"✅ Token force refreshed using {token_result['method']} method")
                return True
            else:
                print(f"❌ Force token refresh failed: {token_result.get('error', 'Unknown error')}")
                return False
    
    def _extract_product_info(self, response_data):
        """Extract product names and descriptions from the response data"""
        product_info = {
            "product_names": [],
            "product_descriptions": [],
            "products_found": []
        }
        
        try:
            # Navigate through the response structure
            if (response_data and 
                isinstance(response_data, dict) and
                'queryResult' in response_data and 
                response_data['queryResult'] and
                'result' in response_data['queryResult'] and
                response_data['queryResult']['result'] is not None):
                
                result_list = response_data['queryResult']['result']
                
                if isinstance(result_list, list):
                    for item in result_list:
                        if isinstance(item, dict):
                            product_detail = {}
                            
                            # Extract product name
                            if 'cr4a3_productname' in item:
                                product_name = item['cr4a3_productname']
                                product_info['product_names'].append(product_name)
                                product_detail['name'] = product_name
                            elif '@primaryNameValue' in item:
                                product_name = item['@primaryNameValue']
                                product_info['product_names'].append(product_name)
                                product_detail['name'] = product_name
                            
                            # Extract product description
                            if 'cr4a3_productdescription' in item:
                                product_desc = item['cr4a3_productdescription']
                                product_info['product_descriptions'].append(product_desc)
                                product_detail['description'] = product_desc
                            elif 'description' in item:
                                product_desc = item['description']
                                product_info['product_descriptions'].append(product_desc)
                                product_detail['description'] = product_desc
                            
                            # Extract additional product details
                            if 'cr4a3_productprice' in item or 'price' in item:
                                price = item.get('cr4a3_productprice') or item.get('price')
                                product_detail['price'] = price
                            
                            if 'cr4a3_productid' in item:
                                product_detail['id'] = item['cr4a3_productid']
                            
                            if product_detail:  # Only add if we found some product info
                                product_info['products_found'].append(product_detail)
                
        except Exception as e:
            print(f"⚠️ Error extracting product info: {e}")
        
        return product_info

    def search(self, query_text, skill="Product_azzEXjGzazCl78XgkHBkV", retry_count=1):
        """Execute search API call with timing and automatic token refresh on auth errors"""
        
        # Proactively check and refresh token before making the API call
        if not self._check_and_refresh_token_if_needed():
            return {
                "success": False,
                # "query": query_text,  # Moved to test_case_context
                "skill": skill,
                "timestamp": datetime.now().isoformat(),
                # "error": "Token refresh failed before API call",  # Not needed in simplified structure
                # "error_type": "TokenRefreshError",  # Not needed in simplified structure
                "response_time_seconds": 0,
                "result_count": 0,
                "status_code": None,
                "api_response_products": {
                    "product_names_found": []
                    # "products_found": []  # Removed - redundant with product_names_found
                },
                "response_data": {"error": "Token refresh failed before API call", "query": None, "queryResult": None, "history": None, "additionalProperties": None},
                "token_refreshed": False
                # "requires_manual_token_refresh": True  # Not needed in simplified structure
            }
        
        payload = {
            "queryText": query_text,
            "skill": skill,
            "options": ["GetResultsSummary"],
            "additionalProperties": {
                "ExecuteUnifiedSearch": True
            }
        }
        
        start_time = time.time()
        
        for attempt in range(retry_count + 1):
            try:
                response = self.session.post(self.base_url, json=payload, headers=self.headers, timeout=60)
                response.raise_for_status()
                response_time = time.time() - start_time
                
                # Handle JSON decode errors gracefully
                try:
                    response_data = response.json()
                except json.JSONDecodeError as json_err:
                    response_time = time.time() - start_time
                    return {
                        "success": False,
                        # "query": query_text,  # Moved to test_case_context
                        "skill": skill,
                        "timestamp": datetime.now().isoformat(),
                        # "error": f"Invalid JSON response: {str(json_err)}",  # Not needed in simplified structure
                        # "error_type": "JSONDecodeError",  # Not needed in simplified structure
                        "response_time_seconds": response_time,
                        "result_count": 0,
                        "status_code": response.status_code,
                        "api_response_products": {
                            "product_names_found": []
                            # "products_found": []  # Removed - redundant with product_names_found
                        },
                        "response_data": {"error": f"Invalid JSON response: {str(json_err)}", "query": None, "queryResult": None, "history": None, "additionalProperties": None},
                        "token_refreshed": False
                        # "raw_response_preview": response.text[:500] if response.text else "Empty response"  # Not needed in simplified structure
                    }
                
                # Count results with safe null checking
                result_count = 0
                if (response_data and 
                    isinstance(response_data, dict) and
                    'queryResult' in response_data and 
                    response_data['queryResult'] and
                    'result' in response_data['queryResult'] and
                    response_data['queryResult']['result'] is not None):
                    result_list = response_data['queryResult']['result']
                    result_count = len(result_list) if isinstance(result_list, list) else 0
                
                # Extract product information
                product_info = self._extract_product_info(response_data)
                
                return {
                    "success": True,
                    # "product_names": product_info['product_names'],  # Moved to api_response_products
                    # "product_descriptions": product_info['product_descriptions'],  # Removed - not needed
                    # "products_found": product_info['products_found'],  # Moved to api_response_products
                    # "query": query_text,  # Moved to test_case_context
                    "skill": skill,
                    "timestamp": datetime.now().isoformat(),
                    "status_code": response.status_code,
                    "response_time_seconds": response_time,
                    "result_count": result_count,
                    "api_response_products": {
                        "product_names_found": product_info['product_names']
                        # "product_descriptions": product_info['product_descriptions'],  # Removed - not needed
                        # "products_found": product_info['products_found']  # Removed - redundant with product_names_found
                    },
                    "response_data": response_data,
                    "token_refreshed": attempt > 0  # Indicates if token was refreshed during this request
                }
                
            except requests.exceptions.Timeout as e:
                response_time = time.time() - start_time
                return {
                    "success": False,
                    # "query": query_text,  # Moved to test_case_context
                    "skill": skill,
                    "timestamp": datetime.now().isoformat(),
                    # "error": f"Request timeout after 60 seconds: {str(e)}",  # Not needed in simplified structure
                    # "error_type": "TimeoutError",  # Not needed in simplified structure
                    "response_time_seconds": response_time,
                    "result_count": 0,
                    "status_code": None,
                    "api_response_products": {
                        "product_names_found": []
                        # "products_found": []  # Removed - redundant with product_names_found
                    },
                    "response_data": {"error": f"Request timeout after 60 seconds: {str(e)}", "query": None, "queryResult": None, "history": None, "additionalProperties": None},
                    "token_refreshed": False
                    # "retry_recommended": True  # Not needed in simplified structure
                }
            except requests.exceptions.ConnectionError as e:
                response_time = time.time() - start_time
                return {
                    "success": False,
                    # "query": query_text,  # Moved to test_case_context
                    "skill": skill,
                    "timestamp": datetime.now().isoformat(),
                    # "error": f"Connection error: {str(e)}",  # Not needed in simplified structure
                    # "error_type": "ConnectionError",  # Not needed in simplified structure
                    "response_time_seconds": response_time,
                    "result_count": 0,
                    "status_code": None,
                    "api_response_products": {
                        "product_names_found": []
                        # "products_found": []  # Removed - redundant with product_names_found
                    },
                    "response_data": {"error": f"Connection error: {str(e)}", "query": None, "queryResult": None, "history": None, "additionalProperties": None},
                    "token_refreshed": False
                    # "retry_recommended": True  # Not needed in simplified structure
                }
            except requests.exceptions.HTTPError as e:
                # Check for Gateway Timeout errors (504) - server overload
                if e.response.status_code == 504 and attempt < retry_count:
                    # Add exponential backoff for 504 errors to reduce server load
                    backoff_delay = (2 ** attempt) * 0.5  # 0.5s, 1s, 2s backoff
                    print(f"⚠️ Gateway Timeout (504) on attempt {attempt + 1}. Backing off {backoff_delay}s...")
                    time.sleep(backoff_delay)
                    continue
                
                # Check for authentication errors (401 Unauthorized, 403 Forbidden)
                elif e.response.status_code in [401, 403] and attempt < retry_count:
                    print(f"🔄 Authentication error (HTTP {e.response.status_code}) on attempt {attempt + 1}. Checking token...")
                    
                    # Check if token is expired
                    if not self._is_token_valid():
                        print("❌ Token is expired. Triggering refresh process...")
                        if not self.refresh_token_if_needed():
                            # Token refresh failed or requires manual intervention
                            response_time = time.time() - start_time
                            return {
                                "success": False,
                                # "query": query_text,  # Moved to test_case_context
                                "skill": skill,
                                "timestamp": datetime.now().isoformat(),
                                # "error": f"Token expired and refresh failed: {str(e)}",  # Not needed in simplified structure
                                # "error_type": "TokenExpiredError",  # Not needed in simplified structure
                                "response_time_seconds": response_time,
                                "result_count": 0,
                                "status_code": e.response.status_code,
                                "api_response_products": {
                                    "product_names_found": []
                                    # "products_found": []  # Removed - redundant with product_names_found
                                },
                                "response_data": {"error": f"Token expired and refresh failed: {str(e)}", "query": None, "queryResult": None, "history": None, "additionalProperties": None},
                                "token_refreshed": False
                                # "requires_manual_token_refresh": True  # Not needed in simplified structure
                            }
                    else:
                        print("⚠️ Token appears valid but authentication failed. This may indicate other auth issues.")
                    
                    # If we reach here, retry with the current token (even if not refreshed)
                    print(f"🔁 Retrying request (attempt {attempt + 2})...")
                    continue
                else:
                    # Non-auth error or max retries reached
                    response_time = time.time() - start_time
                    return {
                        "success": False,
                        # "query": query_text,  # Moved to test_case_context
                        "skill": skill,
                        "timestamp": datetime.now().isoformat(),
                        # "error": str(e),  # Not needed in simplified structure
                        # "error_type": "HTTPError",  # Not needed in simplified structure
                        "response_time_seconds": response_time,
                        "result_count": 0,
                        "status_code": e.response.status_code,
                        "api_response_products": {
                            "product_names_found": []
                            # "products_found": []  # Removed - redundant with product_names_found
                        },
                        "response_data": {"error": str(e), "query": None, "queryResult": None, "history": None, "additionalProperties": None},
                        "token_refreshed": False
                    }
                    
            except Exception as e:
                response_time = time.time() - start_time
                error_type = type(e).__name__
                
                return {
                    "success": False,
                    # "query": query_text,  # Moved to test_case_context
                    "skill": skill,
                    "timestamp": datetime.now().isoformat(),
                    # "error": str(e),  # Not needed in simplified structure
                    # "error_type": error_type,  # Not needed in simplified structure
                    "response_time_seconds": response_time,
                    "result_count": 0,
                    "status_code": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None,
                    "api_response_products": {
                        "product_names_found": []
                        # "products_found": []  # Removed - redundant with product_names_found
                    },
                    "response_data": {"error": str(e), "query": None, "queryResult": None, "history": None, "additionalProperties": None},
                    "token_refreshed": False
                }
        
        # This should never be reached, but included for completeness
        response_time = time.time() - start_time
        return {
            "success": False,
            # "query": query_text,  # Moved to test_case_context
            "skill": skill,
            "timestamp": datetime.now().isoformat(),
            # "error": "Maximum retry attempts exceeded",  # Not needed in simplified structure
            # "error_type": "MaxRetriesExceededError",  # Not needed in simplified structure
            "response_time_seconds": response_time,
            "result_count": 0,
            "status_code": None,
            "api_response_products": {
                "product_names_found": []
                # "products_found": []  # Removed - redundant with product_names_found
            },
            "response_data": {"error": "Maximum retry attempts exceeded", "query": None, "queryResult": None, "history": None, "additionalProperties": None},
            "token_refreshed": False
        }

class QuestionExtractor:
    """Extract questions from various file types"""
    
    @staticmethod
    def find_question_files(base_path="."):
        """Find question files only in test_case directory"""
        path = Path(base_path)
        files = []
        
        # Only search in test_case directory
        test_case_path = path / "test_case"
        if test_case_path.exists():
            files.extend(test_case_path.glob("questions_run_*.json"))
        
        return files
    
    @staticmethod
    def extract_questions_from_file(file_path):
        """Extract questions from a single file with original product context"""
        questions = []
        
        try:
            if file_path.suffix.lower() == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and 'questions' in item:
                            # Extract original product info from test case
                            original_product_name = item.get('name', '')
                            original_product_description = item.get('description', '')
                            original_product_price = item.get('price', 0.0)
                            original_product_attributes = item.get('attributes', [])
                            original_product_category = item.get('category', '')
                            
                            # Handle both old and new question formats
                            questions_data = item['questions']
                            if isinstance(questions_data, dict):
                                # New format: questions is a dict with question types
                                for question_type, question_text in questions_data.items():
                                    if isinstance(question_text, str) and question_text.strip():
                                        questions.append({
                                            "question": question_text.strip(),
                                            "question_type": question_type,
                                            "source_file": str(file_path),
                                            "file_type": file_path.suffix.lower(),
                                            "original_product_name": original_product_name,
                                            "original_product_description": original_product_description,
                                            "original_product_price": original_product_price,
                                            "original_product_attributes": original_product_attributes,
                                            "original_product_category": original_product_category
                                        })
                            elif isinstance(questions_data, list):
                                # Old format: questions is a list
                                for question in questions_data:
                                    if isinstance(question, str) and question.strip():
                                        questions.append({
                                            "question": question.strip(),
                                            "question_type": "legacy",
                                            "source_file": str(file_path),
                                            "file_type": file_path.suffix.lower(),
                                            "original_product_name": original_product_name,
                                            "original_product_description": original_product_description,
                                            "original_product_price": original_product_price,
                                            "original_product_attributes": original_product_attributes,
                                            "original_product_category": original_product_category
                                        })
                        elif isinstance(item, str):
                            questions.append({
                                "question": item.strip(),
                                "question_type": "legacy",
                                "source_file": str(file_path),
                                "file_type": file_path.suffix.lower(),
                                "original_product_name": "",
                                "original_product_description": "",
                                "original_product_price": 0.0,
                                "original_product_attributes": [],
                                "original_product_category": ""
                            })
                            
            elif file_path.suffix.lower() == '.md':
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for line in content.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                        
                    # Extract numbered questions
                    if re.match(r'^\s*\d+\.\s+(.+)$', line):
                        question_text = re.match(r'^\s*\d+\.\s+(.+)$', line).group(1)
                        questions.append({
                            "question": question_text,
                            "question_type": "numbered",
                            "source_file": str(file_path),
                            "file_type": file_path.suffix.lower(),
                            "original_product_name": "",
                            "original_product_description": "",
                            "original_product_price": 0.0,
                            "original_product_attributes": [],
                            "original_product_category": ""
                        })
                    # Extract bullet points
                    elif re.match(r'^\s*[-*]\s+(.+)$', line):
                        question_text = re.match(r'^\s*[-*]\s+(.+)$', line).group(1)
                        questions.append({
                            "question": question_text,
                            "question_type": "bullet",
                            "source_file": str(file_path),
                            "file_type": file_path.suffix.lower(),
                            "original_product_name": "",
                            "original_product_description": "",
                            "original_product_price": 0.0,
                            "original_product_attributes": [],
                            "original_product_category": ""
                        })
                    # Extract questions ending with ?
                    elif line.endswith('?'):
                        questions.append({
                            "question": line,
                            "question_type": "question",
                            "source_file": str(file_path),
                            "file_type": file_path.suffix.lower(),
                            "original_product_name": "",
                            "original_product_description": "",
                            "original_product_price": 0.0,
                            "original_product_attributes": [],
                            "original_product_category": ""
                        })
            
            return questions
            
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
            return []

def process_single_question(client, question_data, progress_tracker, delay=0, max_retries=2, evaluator=None):
    """Process a single question with detailed progress tracking and real-time file output"""
    # Check for shutdown request before processing
    if shutdown_requested:
        return {
            "success": False,
            # "query": question_data.get("question", "Unknown"),  # Moved to test_case_context
            # "error": "Processing interrupted by user",  # Not needed in simplified structure
            # "error_type": "UserInterruption",  # Not needed in simplified structure
            "skill": "Product_azzEXjGzazCl78XgkHBkV",  # Default skill
            "timestamp": datetime.now().isoformat(),
            "response_time_seconds": 0,
            "result_count": 0,
            "status_code": None,
            "test_case_context": {
                "original_product_name": question_data.get("original_product_name", ""),
                "original_product_description": question_data.get("original_product_description", ""),
                "original_product_price": question_data.get("original_product_price", 0.0),
                "original_product_attributes": question_data.get("original_product_attributes", []),
                "original_product_category": question_data.get("original_product_category", ""),
                "question": question_data.get("question", "Unknown"),
                "question_type": question_data.get("question_type", "")
            },
            "api_response_products": {
                "product_names_found": []
                # "products_found": []  # Removed - redundant with product_names_found
            },
            "response_data": {"error": "Processing interrupted by user", "query": None, "queryResult": None, "history": None, "additionalProperties": None},
            "token_refreshed": False
        }
    
    # No delay between threads for maximum throughput
    # All threads run in parallel without any artificial delays
    
    # Retry mechanism for failed requests
    last_result = None
    for retry_attempt in range(max_retries + 1):
        # Check for shutdown request during retries
        if shutdown_requested:
            break
            
        if retry_attempt > 0:
            # Exponential backoff for retries only
            retry_delay = 0.1 * (2 ** retry_attempt)  # Start with 0.1s, then 0.2s, 0.4s
            print(f"🔄 Retrying question (attempt {retry_attempt + 1}/{max_retries + 1}) after {retry_delay}s delay")
            time.sleep(retry_delay)
        
        result = client.search(question_data["question"], retry_count=1)
        
        # Enhance result with original product information from test case
        # Reorganize the result to move test_case_context before api_response_products
        enhanced_result = {
            "success": result.get("success", False),
            "skill": result.get("skill", ""),
            "timestamp": result.get("timestamp", ""),
            "status_code": result.get("status_code"),
            "response_time_seconds": result.get("response_time_seconds", 0),
            "result_count": result.get("result_count", 0),
            "test_case_context": {
                "original_product_name": question_data.get("original_product_name", ""),
                "original_product_description": question_data.get("original_product_description", ""),
                "original_product_price": question_data.get("original_product_price", 0.0),
                "original_product_attributes": question_data.get("original_product_attributes", []),
                "original_product_category": question_data.get("original_product_category", ""),
                "question": question_data.get("question", ""),
                "question_type": question_data.get("question_type", "")
            },
            "api_response_products": result.get("api_response_products", {
                "product_names_found": []
                # "products_found": []  # Removed - redundant with product_names_found
            }),
            "response_data": result.get("response_data", {}),
            "token_refreshed": result.get("token_refreshed", False)
        }
        
        # Replace the original result with enhanced result
        result = enhanced_result
        
        # Check if retry is needed based on error type
        should_retry = (
            not result.get("success", False) and 
            retry_attempt < max_retries and
            result.get("error_type") in ["TimeoutError", "ConnectionError", "JSONDecodeError"] and
            not shutdown_requested  # Don't retry if shutdown requested
        )
        
        if not should_retry:
            break
            
        last_result = result
    
    # Extract detailed metrics for tracking
    success = result["success"]
    status_code = result.get("status_code")
    error_type = result.get("error_type")
    response_time = result.get("response_time_seconds", 0)
    result_count = result.get("result_count", 0)
    
    # Add to search evaluator if provided
    if evaluator and success:
        try:
            # Extract search results from the API response
            search_results = []
            api_response = result.get("response_data", {})
            query_result = api_response.get("queryResult", {})
            
            if isinstance(query_result, dict) and "products" in query_result:
                search_results = query_result["products"]
            elif isinstance(query_result, list):
                search_results = query_result
            
            # Add to evaluator with response time in milliseconds
            evaluator.add_search_result(
                question_data=question_data,
                search_results=search_results,
                response_time_ms=response_time * 1000,  # Convert seconds to milliseconds
                success=success
            )
        except Exception as e:
            print(f"⚠️ Error adding to evaluator: {e}")
    
    # Update progress tracker
    progress_tracker.update(
        success=success,
        status_code=status_code,
        error_type=error_type,
        response_time=response_time,
        result_count=result_count
    )
    
    # Immediately append result to file
    progress_tracker.append_result(result)
    
    return result

def main():
    """Main execution function with intelligent hardware-based configuration"""
    import argparse
    global global_progress_tracker
    
    # Register signal handlers for graceful shutdown
    register_signal_handlers()
    
    # Get system hardware configuration first
    print("🔍 Analyzing system hardware configuration...")
    system_config = get_system_hardware_config()
    
    print("💻 System Configuration:")
    print(f"   CPU: {system_config['cpu_logical_cores']} logical cores, {system_config['cpu_physical_cores']} physical cores")
    print(f"   Memory: {system_config['memory_total_gb']}GB total, {system_config['memory_available_gb']}GB available ({system_config['memory_usage_percent']:.1f}% used)")
    print(f"   Platform: {system_config['platform']} {system_config['platform_release']}")
    
    parser = argparse.ArgumentParser(description='Multi-threaded Dataverse Search with Intelligent Hardware Configuration')
    parser.add_argument('--workers', '-w', type=int, default=None, help='Number of worker threads (auto-detected if not specified)')
    parser.add_argument('--delay', '-d', type=float, default=None, help='Delay between requests in seconds (auto-calculated if not specified)')
    parser.add_argument('--path', '-p', default='.', help='Base path to search for files')
    parser.add_argument('--auto', '-a', action='store_true', default=True, help='Use automatic hardware-based configuration (default)')
    parser.add_argument('--manual', '-m', action='store_true', help='Use manual configuration (disable auto-detection)')
    
    args = parser.parse_args()
    
    # Find and extract questions first to get total count for optimization
    print("� Finding question files...")
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
    
    print(f"🎯 Total questions to process: {len(all_questions)}")
    
    # Calculate optimal configuration unless manual mode
    if not args.manual and (args.workers is None or args.delay is None):
        print("\n🧠 Calculating optimal thread configuration...")
        optimal_config = calculate_optimal_thread_config(system_config, len(all_questions))
        
        # Use calculated values if not specified
        workers = args.workers if args.workers is not None else optimal_config["recommended_threads"]
        delay = args.delay if args.delay is not None else optimal_config["recommended_delay"]
        
        print("⚙️  Fixed Configuration (Server Optimized):")
        print(f"   Threads: {optimal_config['recommended_threads']} (fixed for server stability)")
        print(f"   Delay: {optimal_config['recommended_delay']}s between requests")
        print(f"   Strategy: {optimal_config['reasoning']['strategy']}")
        print(f"   Rationale: {optimal_config['reasoning']['rationale']}")
        print(f"   Using: {workers} workers, {delay}s delay")
    else:
        # Use manual values if specified, otherwise use default 50 threads
        if args.workers is not None or args.delay is not None:
            # User specified some manual values
            workers = args.workers if args.workers is not None else 50
            delay = args.delay if args.delay is not None else 0.1
            print(f"⚙️  Manual Configuration: {workers} workers, {delay}s delay")
        else:
            # No manual values specified, use default 50 threads
            workers = 50
            delay = 0.1
            print(f"⚙️  Default Configuration: {workers} workers, {delay}s delay")
            print(f"   Optimized for balanced performance and server stability")
    
    print("\n🚀 Multi-threaded Dataverse Search Runner")
    print("=" * 60)
    
    # Initialize client
    client = DataverseSearchClient()
    
    # Find and extract questions
    print("📁 Finding question files...")
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
    
    print(f"🎯 Total questions to process: {len(all_questions)}")
    
    # Create output directory
    output_dir = Path("test_case_analysis")
    output_dir.mkdir(exist_ok=True)
    print(f"📁 Output directory: {output_dir.absolute()}")
    
    # Create output file with timestamp inside the analysis folder
    start_time = datetime.now()
    timestamp = start_time.strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"dataverse_results_{timestamp}.json"
    
    print(f"📄 Output file: {output_file}")
    print("🔄 Starting API calls...")
    
    # Initialize progress tracking with output file
    progress_tracker = ProgressTracker(len(all_questions), str(output_file))
    global_progress_tracker = progress_tracker  # Set global reference for signal handler
    
    # Initialize search evaluator
    search_evaluator = SearchEvaluator()
    print("📊 Search evaluator initialized for comprehensive metrics")
    
    print("💡 Press Ctrl+C at any time to gracefully stop and save current progress")
    print("💡 Alternative: Type 'q' or 'quit' and press Enter to stop")
    
    # Start monitoring thread for alternative stop method
    monitor_thread = start_monitoring_thread()
    
    # Process with threading
    completed_futures = 0
    total_futures = len(all_questions)
    
    try:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(process_single_question, client, q, progress_tracker, delay, 2, search_evaluator)
                for q in all_questions
            ]
            
            # Process completed futures and handle shutdown gracefully
            import concurrent.futures
            
            while futures and not shutdown_requested:
                try:
                    # Use timeout to make it interruptible
                    for future in concurrent.futures.as_completed(futures, timeout=0.5):
                        futures.remove(future)
                        try:
                            future.result()
                            completed_futures += 1
                        except Exception as e:
                            print(f"❌ Task failed: {e}")
                            completed_futures += 1
                        
                        # Check for shutdown after each completed task
                        if shutdown_requested:
                            break
                            
                        # Print progress updates
                        if completed_futures % 50 == 0 or completed_futures == total_futures:
                            remaining = total_futures - completed_futures
                            print(f"📊 Completed: {completed_futures}/{total_futures}, Remaining: {remaining}")
                
                except concurrent.futures.TimeoutError:
                    # Timeout is expected, just continue and check shutdown flag
                    continue
                except KeyboardInterrupt:
                    print("\n🛑 KeyboardInterrupt caught in main loop - delegating to signal handler!")
                    # Don't handle here - let the signal handler manage it
                    # Just break the loop and let shutdown_requested handle cleanup
                    break
            
            # Handle shutdown: cancel remaining futures if shutdown was requested
            if shutdown_requested and futures:
                print("🛑 Shutdown requested. Cancelling remaining tasks...")
                for remaining_future in futures:
                    if not remaining_future.done():
                        remaining_future.cancel()
                print(f"✅ Cancelled {len(futures)} remaining tasks")
                    
    except KeyboardInterrupt:
        print("\n🛑 KeyboardInterrupt caught in outer handler - delegating to signal handler!")
        # Don't override shutdown_requested here - let signal handler manage it
        pass
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        shutdown_requested = True
    
    end_time = datetime.now()
    duration = end_time - start_time
    
    # Finalize the output file with final statistics
    progress_tracker.finalize_output()
    
    # Get detailed statistics
    stats = progress_tracker.get_statistics()
    
    print("\n" + "=" * 60)
    if shutdown_requested:
        print("🛑 PROCESSING INTERRUPTED!")
        print("=" * 60)
        print(f"⏱️  Duration before interruption: {duration}")
        print(f"📊 Processed: {stats['successful_requests']} successful, {stats['failed_requests']} failed")
        print(f"📈 Completion: {completed_futures}/{total_futures} questions ({(completed_futures/total_futures)*100:.1f}%)")
        print(f"✅ All processed results have been saved!")
    else:
        print("🏁 PROCESSING COMPLETED!")
        print("=" * 60)
        print(f"⏱️  Duration: {duration}")
        print(f"📊 Results: {stats['successful_requests']} successful, {stats['failed_requests']} failed")
    
    print(f"📈 Success Rate: {stats['success_rate_percentage']:.1f}%")
    print(f"⚡ Processing Rate: {stats['processing_rate_per_second']:.2f} questions/second")
    print(f"⏳ Average Response Time: {stats['average_response_time_seconds']:.3f} seconds")
    print(f"📋 Total Results Returned: {stats['total_results_returned']}")
    print(f"🔢 Average Results per Query: {stats['average_results_per_query']:.1f}")
    print(f"💾 Results saved to: {output_file}")
    
    # Show status code distribution
    if stats['status_code_distribution']:
        print(f"📊 Status Codes: {stats['status_code_distribution']}")
    
    # Show error types if any
    if stats['error_type_distribution']:
        print(f"❌ Error Types: {stats['error_type_distribution']}")
    
    print("=" * 60)
    
    # Generate comprehensive search evaluation report
    if search_evaluator:
        print("\n🔬 GENERATING SEARCH EVALUATION METRICS...")
        evaluation_file = output_file.replace('.json', '_evaluation.json')
        
        try:
            # Print calculation explanations
            search_evaluator.print_metric_calculations()
            
            # Generate and save evaluation report
            evaluation_report = search_evaluator.save_evaluation_report(str(evaluation_file), k=10)
            
            print("\n📊 SEARCH EVALUATION SUMMARY:")
            print("=" * 60)
            
            # Display key metrics
            relevance_metrics = evaluation_report['relevance_metrics']
            performance_metrics = evaluation_report['performance_metrics']
            coverage_metrics = evaluation_report['coverage_metrics']
            
            print("🎯 RELEVANCE METRICS (K=10):")
            for metric_name, values in relevance_metrics.items():
                if isinstance(values, dict):
                    print(f"   {metric_name.replace('_', ' ').title()}:")
                    for q_type, score in values.items():
                        print(f"      {q_type}: {score:.3f}")
            
            print("\n⚡ PERFORMANCE METRICS:")
            print(f"   Average Response Time: {performance_metrics.get('average_response_time_ms', 0):.1f}ms")
            print(f"   P95 Response Time: {performance_metrics.get('p95_response_time_ms', 0):.1f}ms")
            print(f"   Success Rate: {performance_metrics.get('success_rate', 0):.1%}")
            print(f"   Total Queries: {performance_metrics.get('total_queries', 0)}")
            
            print("\n📊 COVERAGE METRICS:")
            print(f"   Query Success Rate: {coverage_metrics.get('query_success_rate', 0):.1%}")
            print(f"   Zero Results Rate: {coverage_metrics.get('zero_results_rate', 0):.1%}")
            print(f"   Avg Results per Query: {coverage_metrics.get('average_results_per_query', 0):.1f}")
            
            print("=" * 60)
            
        except Exception as e:
            print(f"⚠️ Error generating evaluation report: {e}")
    
    # Show file locations
    result_file = output_file.replace('.json', '_results.jsonl')
    final_file = output_file.replace('.json', '_final.json')
    checkpoint_file = output_file.replace('.json', '_checkpoint.json')
    evaluation_file = output_file.replace('.json', '_evaluation.json')
    
    print("📁 Generated Files:")
    print(f"   🔄 Real-time results: {result_file}")
    print(f"   📊 Final report: {final_file}")
    print(f"   💾 Latest checkpoint: {checkpoint_file}")
    print(f"   🔬 Evaluation metrics: {evaluation_file}")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 KeyboardInterrupt caught at top level. Forcing shutdown...")
        # Set shutdown flags
        shutdown_requested = True
        force_exit = True
        # Try to save any pending results
        if global_progress_tracker:
            try:
                global_progress_tracker.finalize_output()
                print("✅ Final results saved!")
            except:
                print("⚠️ Could not save final results")
        print("👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error at top level: {e}")
        sys.exit(1)
