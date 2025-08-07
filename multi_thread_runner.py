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
    """Calculate optimal thread count and delay based on system configuration"""
    cpu_cores = system_config["cpu_logical_cores"]
    memory_gb = system_config["memory_total_gb"]
    memory_available = system_config["memory_available_gb"]
    
    # Base calculation: start with CPU cores
    base_threads = cpu_cores
    
    # Memory adjustment: reduce threads if low memory
    if memory_available < 2:
        memory_factor = 0.5  # Very low memory
    elif memory_available < 4:
        memory_factor = 0.7  # Low memory
    elif memory_available < 8:
        memory_factor = 1.0  # Normal memory
    else:
        memory_factor = 1.5  # High memory
    
    # Question volume adjustment
    if total_questions > 1000:
        volume_factor = 2.0  # Many questions, can use more threads
    elif total_questions > 500:
        volume_factor = 1.5
    elif total_questions > 100:
        volume_factor = 1.2
    else:
        volume_factor = 0.8  # Few questions, don't need many threads
    
    # Calculate optimal thread count
    optimal_threads = 40  # Fixed at 40 threads as requested
    
    # Apply constraints (keep between 2 and 50, but we're using 40)
    optimal_threads = max(2, min(optimal_threads, 50))  # Between 2 and 50 threads
    
    # No delay needed for I/O bound tasks with high thread count
    delay = 0  # No delay for maximum throughput
    
    return {
        "recommended_threads": optimal_threads,
        "recommended_delay": delay,
        "reasoning": {
            "base_cpu_cores": cpu_cores,
            "memory_factor": memory_factor,
            "volume_factor": volume_factor,
            "final_calculation": f"{base_threads} * {memory_factor} * {volume_factor} = {optimal_threads}"
        }
    }

# Global Python path from system configuration
PYTHON_PATH = get_python_path()

# Global shutdown flag and progress tracker for graceful shutdown
shutdown_requested = False
global_progress_tracker = None

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    global shutdown_requested, global_progress_tracker
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

def cleanup_on_exit():
    """Cleanup function called on normal exit"""
    global global_progress_tracker
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
        """Append a single result to the file immediately using append mode"""
        if not self.output_file:
            return
            
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

class SilentTokenGenerator:
    """Silent token generation functionality integrated into the main client"""
    
    def __init__(self, tenant_id, client_id, resource_url):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.resource_url = resource_url
        self.token_endpoint = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        self.device_code_endpoint = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/devicecode"
        self.refresh_token_file = "refresh_token.config"
    
    def load_refresh_token(self):
        """Load refresh token if available"""
        try:
            if os.path.exists(self.refresh_token_file):
                with open(self.refresh_token_file, 'r') as f:
                    return f.read().strip()
            return None
        except Exception as e:
            print(f"⚠️ Error loading refresh token: {e}")
            return None
    
    def save_refresh_token(self, refresh_token):
        """Save refresh token for future use"""
        try:
            with open(self.refresh_token_file, 'w') as f:
                f.write(refresh_token)
            print(f"✅ Refresh token saved to {self.refresh_token_file}")
        except Exception as e:
            print(f"❌ Error saving refresh token: {e}")
    
    def get_token_with_refresh_token(self, refresh_token):
        """Get access token using refresh token"""
        print("🔄 Attempting token refresh with stored refresh token...")
        
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
            
            # Save new refresh token if provided
            if 'refresh_token' in token_response:
                self.save_refresh_token(token_response['refresh_token'])
            
            return {
                'success': True,
                'access_token': token_response['access_token'],
                'expires_in': token_response.get('expires_in', 3600),
                'method': 'refresh_token'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Refresh token failed: {str(e)}",
                'method': 'refresh_token'
            }
    
    def get_token_with_device_code(self):
        """Get token using device code flow (user-friendly silent method)"""
        print("🔄 Initiating device code authentication flow...")
        
        # Step 1: Request device code
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
            
            # Step 2: Poll for token
            token_data = {
                'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
                'client_id': self.client_id,
                'device_code': device_result['device_code']
            }
            
            interval = device_result.get('interval', 5)
            expires_in = device_result.get('expires_in', 900)
            start_time = time.time()
            
            while time.time() - start_time < expires_in:
                try:
                    token_response = requests.post(self.token_endpoint, data=token_data, timeout=30)
                    
                    if token_response.status_code == 200:
                        token_result = token_response.json()
                        print("✅ Authentication completed successfully!")
                        
                        # Save refresh token if provided
                        if 'refresh_token' in token_result:
                            self.save_refresh_token(token_result['refresh_token'])
                        
                        return {
                            'success': True,
                            'access_token': token_result['access_token'],
                            'expires_in': token_result.get('expires_in', 3600),
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
        """Main method to acquire token using available silent methods"""
        print("🚀 Attempting Silent Token Acquisition...")
        
        # Method 1: Try refresh token
        refresh_token = self.load_refresh_token()
        if refresh_token:
            result = self.get_token_with_refresh_token(refresh_token)
            if result['success']:
                print(f"✅ Token acquired using refresh token!")
                return result
            else:
                print(f"⚠️ Refresh token failed: {result['error']}")
        
        # Method 2: Device code flow (minimal user interaction)
        print("📱 Falling back to device code authentication...")
        return self.get_token_with_device_code()

class DataverseSearchClient:
    """Dataverse API client with integrated silent token generation"""
    
    def __init__(self, token_file="token.config"):
        self.base_url = "https://aurorabapenv87b96.crm10.dynamics.com/api/copilot/v1.0/queryskillstructureddata"
        self.token_file = token_file
        self.token = self._load_token(token_file)
        self._token_lock = threading.Lock()  # Thread safety for token operations
        self._last_token_check = time.time()  # Track when we last checked token
        self._token_check_interval = 60  # Check token every 60 seconds
        
        # OAuth2 configuration for token refresh
        self.tenant_id = "4abc24ea-2d0b-4011-87d4-3de32ca1e9cc"
        self.client_id = "51f81489-12ee-4a9e-aaae-a2591f45987d"  # Fixed client ID from Copilot team
        self.resource = "https://aurorabapenv87b96.crm10.dynamics.com/"
        self.redirect_url = "https://localhost"
        self.auth_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        # Initialize integrated silent token generator
        self.token_generator = SilentTokenGenerator(self.tenant_id, self.client_id, self.resource)
        
        # Validate token on initialization
        if not self._is_token_valid():
            print("⚠️ Token is expired or invalid. Attempting automatic refresh...")
            self.refresh_token_if_needed()
            
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
        
    def _load_token(self, token_file):
        try:
            with open(token_file, 'r') as f:
                return f.read().strip()
        except Exception as e:
            print(f"❌ Error reading token file: {e}")
            raise
    
    def _decode_jwt_payload(self, token):
        """Manually decode JWT payload without verification (for expiration check only)"""
        try:
            if not token or not isinstance(token, str):
                raise ValueError("Token must be a non-empty string")
                
            # JWT has 3 parts separated by dots: header.payload.signature
            parts = token.split('.')
            if len(parts) != 3:
                raise ValueError(f"Invalid JWT format: expected 3 parts, got {len(parts)}")
            
            # Decode the payload (middle part)
            payload = parts[1]
            
            if not payload:
                raise ValueError("JWT payload part is empty")
            
            # Add padding if needed (base64 requires length to be multiple of 4)
            padding = 4 - (len(payload) % 4)
            if padding != 4:
                payload += '=' * padding
            
            # Decode from base64
            try:
                decoded_bytes = base64.urlsafe_b64decode(payload)
            except Exception as decode_error:
                raise ValueError(f"Base64 decoding failed: {decode_error}")
            
            try:
                decoded_json = json.loads(decoded_bytes.decode('utf-8'))
            except Exception as json_error:
                raise ValueError(f"JSON parsing failed: {json_error}")
            
            return decoded_json
            
        except ValueError as ve:
            print(f"❌ JWT validation error: {ve}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error decoding JWT payload: {e}")
            return None
    
    def _is_token_valid(self):
        """Check if the current JWT token is valid and not expired"""
        try:
            if not self.token:
                return False
                
            # Decode JWT token payload to get expiration time
            decoded = self._decode_jwt_payload(self.token)
            if not decoded:
                return False
            
            # Get expiration time from token
            exp_timestamp = decoded.get('exp')
            if not exp_timestamp:
                print("⚠️ Token does not contain expiration information")
                return False
            
            # Convert to datetime and check if expired
            exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            current_time = datetime.now(tz=timezone.utc)
            
            # Add a 5-minute buffer before expiration
            buffer_minutes = 5
            effective_expiry = exp_datetime - timedelta(minutes=buffer_minutes)
            
            if current_time >= effective_expiry:
                print(f"❌ Token will expire soon at {exp_datetime} (current time: {current_time})")
                return False
            else:
                time_remaining = effective_expiry - current_time
                print(f"✅ Token valid until {exp_datetime} (refresh needed in: {time_remaining})")
                return True
                
        except Exception as e:
            print(f"❌ Error validating token: {e}")
            return False
    
    def _save_token(self, new_token):
        """Save new token to file and update instance (thread-safe)"""
        with self._token_lock:
            try:
                with open(self.token_file, 'w') as f:
                    f.write(new_token.strip())
                
                # Update the instance token and headers
                self.token = new_token.strip()
                self.headers["Authorization"] = f"Bearer {self.token}"
                
                print(f"✅ Token saved to {self.token_file} and headers updated")
                return True
            except Exception as e:
                print(f"❌ Error saving token: {e}")
                return False
    
    def _reload_token_from_file(self):
        """Reload token from file and update headers (thread-safe)"""
        with self._token_lock:
            try:
                new_token = self._load_token(self.token_file)
                if new_token and new_token != self.token:
                    self.token = new_token
                    self.headers["Authorization"] = f"Bearer {self.token}"
                    print("🔄 Token reloaded from file and headers updated")
                    return True
                return False
            except Exception as e:
                print(f"❌ Error reloading token: {e}")
                return False
    
    def _refresh_token_automatic(self):
        """
        Automatic token refresh using integrated silent token generator
        """
        print("🔄 Attempting automatic token refresh...")
        
        try:
            # Use integrated token generator
            result = self.token_generator.acquire_token_silently()
            
            if result['success']:
                # Save the new token
                new_token = result['access_token']
                if self._save_token(new_token):
                    print(f"✅ Token automatically refreshed using {result['method']} method!")
                    return True
                else:
                    print("❌ Failed to save new token")
                    return False
            else:
                print(f"❌ Automatic token refresh failed: {result['error']}")
                # For large batch processing, we don't want to fallback to interactive
                # Instead, we'll ask user to manually refresh token
                print("⚠️ Please manually refresh your token using get_new_token.py")
                return False
                
        except Exception as e:
            print(f"❌ Error during automatic token refresh: {e}")
            print("⚠️ Please manually refresh your token using get_new_token.py")
            return False
    
    def _refresh_token_interactive(self):
        """
        Interactive token refresh - fallback when automatic methods fail
        """
        auth_endpoint = f"https://login.microsoftonline.com/common/oauth2/authorize"
        auth_params = {
            'resource': self.resource,
            'client_id': self.client_id,
            'redirect_uri': self.redirect_url,
            'response_type': 'token',
            'prompt': 'login'
        }
        
        auth_url = f"{auth_endpoint}?{urlencode(auth_params)}"
        
        print("\n" + "="*60)
        print("🔄 MANUAL TOKEN REFRESH REQUIRED")
        print("="*60)
        print("Automatic token refresh failed. Manual steps:")
        print("1. Open this URL in your browser:")
        print(f"   {auth_url}")
        print("2. Log in with your Azure credentials")
        print("3. After successful login, you'll be redirected to localhost")
        print("4. Copy the access_token from the URL fragment")
        print("5. Update the token.config file with the new token")
        print("6. Restart this application")
        print("="*60)
        
        return False
        
    def _check_and_refresh_token_if_needed(self):
        """Proactively check and refresh token if needed (thread-safe)"""
        current_time = time.time()
        
        # Only check token every _token_check_interval seconds to avoid excessive checks
        if current_time - self._last_token_check < self._token_check_interval:
            return True
            
        with self._token_lock:
            self._last_token_check = current_time
            
            if not self._is_token_valid():
                print("🔄 Token needs refresh, attempting automatic refresh...")
                return self.refresh_token_if_needed()
            return True
    
    def refresh_token_if_needed(self):
        """Check token validity and refresh if needed using automatic methods first"""
        if not self._is_token_valid():
            print("🔄 Token refresh needed...")
            
            # First try to reload from file in case it was updated externally
            if self._reload_token_from_file():
                print("✅ Token was updated externally, checking validity...")
                if self._is_token_valid():
                    print("✅ Reloaded token is valid!")
                    return True
                else:
                    print("❌ Reloaded token is still invalid")
            
            # Try automatic refresh first, then fallback to interactive
            return self._refresh_token_automatic()
        return True
    
    def search(self, query_text, skill="Product_azzEXjGzazCl78XgkHBkV", retry_count=1):
        """Execute search API call with timing and automatic token refresh on auth errors"""
        
        # Proactively check and refresh token before making the API call
        if not self._check_and_refresh_token_if_needed():
            return {
                "success": False,
                "query": query_text,
                "skill": skill,
                "timestamp": datetime.now().isoformat(),
                "error": "Token refresh failed before API call",
                "error_type": "TokenRefreshError",
                "response_time_seconds": 0,
                "result_count": 0,
                "status_code": None,
                "requires_manual_token_refresh": True
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
                response = requests.post(self.base_url, json=payload, headers=self.headers, timeout=60)
                response.raise_for_status()
                response_time = time.time() - start_time
                
                # Handle JSON decode errors gracefully
                try:
                    response_data = response.json()
                except json.JSONDecodeError as json_err:
                    response_time = time.time() - start_time
                    return {
                        "success": False,
                        "query": query_text,
                        "skill": skill,
                        "timestamp": datetime.now().isoformat(),
                        "error": f"Invalid JSON response: {str(json_err)}",
                        "error_type": "JSONDecodeError", 
                        "response_time_seconds": response_time,
                        "result_count": 0,
                        "status_code": response.status_code,
                        "raw_response_preview": response.text[:500] if response.text else "Empty response"
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
                
                return {
                    "success": True,
                    "query": query_text,
                    "skill": skill,
                    "timestamp": datetime.now().isoformat(),
                    "status_code": response.status_code,
                    "response_time_seconds": response_time,
                    "result_count": result_count,
                    "response_data": response_data,
                    "token_refreshed": attempt > 0  # Indicates if token was refreshed during this request
                }
                
            except requests.exceptions.Timeout as e:
                response_time = time.time() - start_time
                return {
                    "success": False,
                    "query": query_text,
                    "skill": skill,
                    "timestamp": datetime.now().isoformat(),
                    "error": f"Request timeout after 60 seconds: {str(e)}",
                    "error_type": "TimeoutError",
                    "response_time_seconds": response_time,
                    "result_count": 0,
                    "status_code": None,
                    "retry_recommended": True
                }
            except requests.exceptions.ConnectionError as e:
                response_time = time.time() - start_time
                return {
                    "success": False,
                    "query": query_text,
                    "skill": skill,
                    "timestamp": datetime.now().isoformat(),
                    "error": f"Connection error: {str(e)}",
                    "error_type": "ConnectionError",
                    "response_time_seconds": response_time,
                    "result_count": 0,
                    "status_code": None,
                    "retry_recommended": True
                }
            except requests.exceptions.HTTPError as e:
                # Check for authentication errors (401 Unauthorized, 403 Forbidden)
                if e.response.status_code in [401, 403] and attempt < retry_count:
                    print(f"🔄 Authentication error (HTTP {e.response.status_code}) on attempt {attempt + 1}. Checking token...")
                    
                    # Check if token is expired
                    if not self._is_token_valid():
                        print("❌ Token is expired. Triggering refresh process...")
                        if not self.refresh_token_if_needed():
                            # Token refresh failed or requires manual intervention
                            response_time = time.time() - start_time
                            return {
                                "success": False,
                                "query": query_text,
                                "skill": skill,
                                "timestamp": datetime.now().isoformat(),
                                "error": f"Token expired and refresh failed: {str(e)}",
                                "error_type": "TokenExpiredError",
                                "response_time_seconds": response_time,
                                "result_count": 0,
                                "status_code": e.response.status_code,
                                "requires_manual_token_refresh": True
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
                        "query": query_text,
                        "skill": skill,
                        "timestamp": datetime.now().isoformat(),
                        "error": str(e),
                        "error_type": "HTTPError",
                        "response_time_seconds": response_time,
                        "result_count": 0,
                        "status_code": e.response.status_code
                    }
                    
            except Exception as e:
                response_time = time.time() - start_time
                error_type = type(e).__name__
                
                return {
                    "success": False,
                    "query": query_text,
                    "skill": skill,
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e),
                    "error_type": error_type,
                    "response_time_seconds": response_time,
                    "result_count": 0,
                    "status_code": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
                }
        
        # This should never be reached, but included for completeness
        response_time = time.time() - start_time
        return {
            "success": False,
            "query": query_text,
            "skill": skill,
            "timestamp": datetime.now().isoformat(),
            "error": "Maximum retry attempts exceeded",
            "error_type": "MaxRetriesExceededError",
            "response_time_seconds": response_time,
            "result_count": 0,
            "status_code": None
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
        """Extract questions from a single file"""
        questions = []
        
        try:
            if file_path.suffix.lower() == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and 'questions' in item:
                            questions.extend(item['questions'])
                        elif isinstance(item, str):
                            questions.append(item)
                            
            elif file_path.suffix.lower() == '.md':
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for line in content.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                        
                    # Extract numbered questions
                    if re.match(r'^\s*\d+\.\s+(.+)$', line):
                        questions.append(re.match(r'^\s*\d+\.\s+(.+)$', line).group(1))
                    # Extract bullet points
                    elif re.match(r'^\s*[-*]\s+(.+)$', line):
                        questions.append(re.match(r'^\s*[-*]\s+(.+)$', line).group(1))
                    # Extract questions ending with ?
                    elif line.endswith('?'):
                        questions.append(line)
            
            # Clean and add metadata
            result = []
            for q in questions:
                if isinstance(q, str) and q.strip():
                    result.append({
                        "question": q.strip(),
                        "source_file": str(file_path),
                        "file_type": file_path.suffix.lower()
                    })
            
            return result
            
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
            return []

def process_single_question(client, question_data, progress_tracker, delay=0, max_retries=2):
    """Process a single question with detailed progress tracking and real-time file output"""
    # Check for shutdown request before processing
    if shutdown_requested:
        return {
            "success": False,
            "query": question_data.get("question", "Unknown"),
            "error": "Processing interrupted by user",
            "error_type": "UserInterruption",
            "timestamp": datetime.now().isoformat(),
            "response_time_seconds": 0,
            "result_count": 0,
            "status_code": None
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
        result.update(question_data)
        
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
        
        print("⚙️  Intelligent Configuration:")
        print(f"   Recommended threads: {optimal_config['recommended_threads']}")
        print(f"   Recommended delay: {optimal_config['recommended_delay']}s")
        print(f"   Reasoning: {optimal_config['reasoning']['final_calculation']}")
        print(f"   Using: {workers} workers, {delay}s delay")
    else:
        # Use manual or default values
        workers = args.workers if args.workers is not None else 40
        delay = args.delay if args.delay is not None else 0
        print(f"⚙️  Manual Configuration: {workers} workers, {delay}s delay")
    
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
    
    # Create output file with timestamp
    start_time = datetime.now()
    timestamp = start_time.strftime("%Y%m%d_%H%M%S")
    output_file = f"dataverse_results_{timestamp}.json"
    
    print(f"� Output file: {output_file}")
    print("�🔄 Starting API calls...")
    
    # Initialize progress tracking with output file
    progress_tracker = ProgressTracker(len(all_questions), output_file)
    global_progress_tracker = progress_tracker  # Set global reference for signal handler
    
    print("💡 Press Ctrl+C at any time to gracefully stop and save current progress")
    
    # Process with threading
    completed_futures = 0
    total_futures = len(all_questions)
    
    try:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(process_single_question, client, q, progress_tracker, delay)
                for q in all_questions
            ]
            
            # Process completed futures and handle shutdown gracefully
            for future in as_completed(futures):
                if shutdown_requested:
                    print("🛑 Shutdown requested. Waiting for current tasks to complete...")
                    # Cancel remaining futures
                    for remaining_future in futures:
                        if not remaining_future.done():
                            remaining_future.cancel()
                    break
                
                try:
                    future.result()  # Just wait for completion
                    completed_futures += 1
                except Exception as e:
                    print(f"❌ Task failed: {e}")
                    completed_futures += 1
                
                # Print periodic progress updates
                if completed_futures % 50 == 0 or completed_futures == total_futures:
                    remaining = total_futures - completed_futures
                    print(f"📊 Completed: {completed_futures}/{total_futures}, Remaining: {remaining}")
                    
    except KeyboardInterrupt:
        print("\n🛑 KeyboardInterrupt caught. Initiating graceful shutdown...")
        shutdown_requested = True
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
    
    # Show file locations
    result_file = output_file.replace('.json', '_results.jsonl')
    final_file = output_file.replace('.json', '_final.json')
    checkpoint_file = output_file.replace('.json', '_checkpoint.json')
    
    print("📁 Generated Files:")
    print(f"   🔄 Real-time results: {result_file}")
    print(f"   📊 Final report: {final_file}")
    print(f"   💾 Latest checkpoint: {checkpoint_file}")
    print("=" * 60)

if __name__ == "__main__":
    main()
