#!/usr/bin/env python3
"""
Multi-threaded Unstructured Dataverse Search
Process search queries using QueryTextContext endpoint with threading
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

class UnstructuredSearchRunner:
    def __init__(self, max_workers=10):
        self.max_workers = max_workers
        self.session = requests.Session()
        self.token = self._read_token()
        self.endpoint = "https://aurorabapenv87b96.crm10.dynamics.com/api/copilot/v1.0/QueryTextContext"
        self.results = []
        self.lock = threading.Lock()
        
        # Set up headers
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "insomnia/11.4.0",
            "x-ms-crm-query-language": "1033",
            "x-ms-crm-service-root-url": "https://aurorabapenv87b96.crm10.dynamics.com/",
            "x-ms-crm-userid": "aurorauser01@aurorafinanceintegration02.onmicrosoft.com",
            "x-ms-organization-id": "440a70c9-ff61-f011-beb8-6045bd09e9cc",
            "x-ms-user-agent": "PowerVA/2",
            "Authorization": f"Bearer {self.token}"
        }
    
    def _read_token(self):
        """Read token from token.config file"""
        try:
            with open("token.config", "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            print("ERROR: token.config file not found")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR reading token: {e}")
            sys.exit(1)
    
    def _create_search_payload(self, search_text):
        """Create the search payload for QueryTextContext endpoint"""
        return {
            "searchText": search_text,
            "entityParameters": [
                {
                    "name": "cr4a3_product",
                    "searchColumns": ["cr4a3_memodata"]
                }
            ],
            "totalResultCount": True,
            "top": 100,
            "searchType": "semantic",
            "options": {
                "EnableSyntheticQuestionSearch": False,
                "queryLocale": "en-US"
            }
        }
    
    def search_single_query(self, search_text, query_id=None):
        """Perform a single search query"""
        start_time = time.time()
        try:
            payload = self._create_search_payload(search_text)
            
            response = self.session.post(
                self.endpoint,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            result = {
                "query_id": query_id or len(self.results) + 1,
                "search_text": search_text,
                "duration_seconds": round(duration, 2),
                "timestamp": datetime.now().isoformat(),
                "status_code": response.status_code,
                "success": response.status_code == 200
            }
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    result["response_data"] = response_data
                    result["result_count"] = len(response_data.get("value", []))
                    print(f"✓ Query {query_id}: '{search_text[:50]}...' - {result['result_count']} results ({duration:.2f}s)")
                except json.JSONDecodeError as e:
                    result["error"] = f"JSON decode error: {str(e)}"
                    result["raw_response"] = response.text
                    print(f"✗ Query {query_id}: JSON decode error")
            else:
                result["error"] = f"HTTP {response.status_code}: {response.text}"
                print(f"✗ Query {query_id}: HTTP {response.status_code}")
            
            with self.lock:
                self.results.append(result)
            
            return result
            
        except requests.exceptions.RequestException as e:
            end_time = time.time()
            duration = end_time - start_time
            
            result = {
                "query_id": query_id or len(self.results) + 1,
                "search_text": search_text,
                "duration_seconds": round(duration, 2),
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": f"Request error: {str(e)}"
            }
            
            with self.lock:
                self.results.append(result)
            
            print(f"✗ Query {query_id}: Request error - {str(e)}")
            return result
    
    def run_batch_search(self, search_queries):
        """Run multiple search queries with threading"""
        print(f"Starting batch search with {len(search_queries)} queries using {self.max_workers} threads")
        print(f"Target endpoint: {self.endpoint}")
        print("-" * 80)
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_query = {}
            for i, query in enumerate(search_queries):
                if isinstance(query, dict):
                    search_text = query.get("question", query.get("query", str(query)))
                else:
                    search_text = str(query)
                
                future = executor.submit(self.search_single_query, search_text, i + 1)
                future_to_query[future] = (i + 1, search_text)
            
            # Process completed tasks
            completed = 0
            for future in as_completed(future_to_query):
                completed += 1
                query_id, search_text = future_to_query[future]
                
                try:
                    result = future.result()
                    progress = (completed / len(search_queries)) * 100
                    print(f"Progress: {completed}/{len(search_queries)} ({progress:.1f}%)")
                except Exception as e:
                    print(f"✗ Query {query_id}: Exception - {str(e)}")
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        print("-" * 80)
        print(f"Batch search completed in {total_duration:.2f} seconds")
        print(f"Average time per query: {total_duration/len(search_queries):.2f} seconds")
        
        # Print summary
        successful = sum(1 for r in self.results if r.get("success", False))
        failed = len(self.results) - successful
        
        print(f"Results summary:")
        print(f"  ✓ Successful: {successful}")
        print(f"  ✗ Failed: {failed}")
        print(f"  📊 Total queries: {len(self.results)}")
        
        return self.results
    
    def save_results(self, filename=None):
        """Save results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"unstructured_search_results_{timestamp}.json"
        
        # Sort results by query_id for consistent output
        sorted_results = sorted(self.results, key=lambda x: x.get("query_id", 0))
        
        output_data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_queries": len(sorted_results),
                "successful_queries": sum(1 for r in sorted_results if r.get("success", False)),
                "failed_queries": sum(1 for r in sorted_results if not r.get("success", False)),
                "endpoint": self.endpoint,
                "search_type": "unstructured_semantic"
            },
            "results": sorted_results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"Results saved to: {filename}")
        return filename

def load_test_queries():
    """Load test queries from various sources"""
    queries = []
    
    # Try to load from test case files
    test_case_dir = Path("test_case")
    if test_case_dir.exists():
        print("Loading queries from test_case directory...")
        for json_file in test_case_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        queries.extend(data)
                    elif isinstance(data, dict) and "questions" in data:
                        queries.extend(data["questions"])
            except Exception as e:
                print(f"Error loading {json_file}: {e}")
    
    # If no test cases found, use sample queries
    if not queries:
        print("No test case files found, using sample queries...")
        queries = [
            "gloves",
            "red jacket",
            "winter boots",
            "running shoes",
            "backpack",
            "water bottle",
            "laptop bag",
            "sports equipment",
            "outdoor gear",
            "camping supplies"
        ]
    
    print(f"Loaded {len(queries)} queries")
    return queries

def main():
    """Main execution function"""
    print("Unstructured Dataverse Search Runner")
    print("="*50)
    
    # Load queries
    queries = load_test_queries()
    
    if not queries:
        print("No queries to process!")
        return
    
    # Create runner and execute
    runner = UnstructuredSearchRunner(max_workers=10)
    
    try:
        results = runner.run_batch_search(queries)
        filename = runner.save_results()
        
        print(f"\n🎉 Search completed successfully!")
        print(f"📄 Results saved to: {filename}")
        print(f"📈 Processed {len(results)} queries")
        
    except KeyboardInterrupt:
        print("\n❌ Search interrupted by user")
        if runner.results:
            filename = runner.save_results("interrupted_results.json")
            print(f"💾 Partial results saved to: {filename}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during search: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()