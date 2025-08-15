#!/usr/bin/env python3
"""
Enhanced Search Engine Evaluation Script
Reads test cases, executes Dataverse search API calls, and calculates comprehensive IR metrics
Implements: Precision, Recall, F1, MAP, NDCG, MRR, and performance metrics
"""

import json
import os
import sys
import re
import time
import statistics
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

# Import the enhanced search client
from multi_thread_unified_search import DataverseSearchClient

class SearchEngineEvaluator:
    """
    Comprehensive search engine evaluation with standard IR metrics
    
    Metrics Implemented:
    1. Precision@K - Relevant items in top K results / K
    2. Recall@K - Relevant items in top K results / Total relevant items
    3. F1-Score - Harmonic mean of Precision and Recall
    4. MAP (Mean Average Precision) - Average precision across all relevant items
    5. NDCG@K (Normalized DCG) - Ranking quality with position discounting
    6. MRR (Mean Reciprocal Rank) - Position of first relevant result
    7. Response Time Analysis - Latency metrics
    8. Coverage Metrics - Query success rate, zero results rate
    """
    
    def __init__(self):
        self.search_client = None
        self.test_cases = []
        self.search_results = []
        self.ground_truth = {}
        
        # Metrics storage
        self.precision_scores = defaultdict(list)  # precision@k for different k values
        self.recall_scores = defaultdict(list)     # recall@k for different k values
        self.f1_scores = defaultdict(list)         # f1@k for different k values
        self.map_scores = []                       # Mean Average Precision scores
        self.ndcg_scores = defaultdict(list)       # NDCG@k scores
        self.mrr_scores = []                       # Mean Reciprocal Rank scores
        self.response_times = []                   # Response time measurements
        self.query_success_count = 0               # Successful queries
        self.zero_results_count = 0                # Queries with no results
        
    def initialize_search_client(self):
        """Initialize the Dataverse search client"""
        try:
            self.search_client = DataverseSearchClient()
            print("✅ Search client initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize search client: {e}")
            return False
    
    def load_test_cases(self, test_case_dir="test_case"):
        """
        Load test cases from JSON files in the test_case directory
        
        Expected structure:
        {
          "name": "Product Name",
          "description": "Product description",
          "price": 55.0,
          "category": "product_category",
          "questions": {
            "Exact word": "Question about specific product",
            "Price range": "Price-based question",
            "Category": "Category-based question",
            "Description": "Feature-based question",
            "Attribute value": "Attribute-based question"
          }
        }
        """
        print(f"🔍 Loading test cases from {test_case_dir}...")
        
        if not os.path.exists(test_case_dir):
            print(f"❌ Test case directory '{test_case_dir}' not found")
            return False
        
        self.test_cases = []
        self.ground_truth = {}
        
        for filename in sorted(os.listdir(test_case_dir)):
            if filename.endswith('.json'):
                filepath = os.path.join(test_case_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        products = json.load(f)
                        
                    for product in products:
                        # Safe string extraction with null handling
                        product_name = self._safe_string(product.get('name', ''))
                        product_desc = self._safe_string(product.get('description', ''))
                        product_price = product.get('price', 0.0)
                        product_category = self._safe_string(product.get('category', ''))
                        questions = product.get('questions', {})
                        
                        if not product_name or not questions:
                            continue
                            
                        # Process each question type
                        for question_type, question_text in questions.items():
                            # Safe handling of question text
                            safe_question_text = self._safe_string(question_text)
                            safe_question_type = self._safe_string(question_type)
                            
                            if not safe_question_text:
                                continue
                                
                            test_case = {
                                'question': safe_question_text,
                                'question_type': safe_question_type,
                                'expected_product': {
                                    'name': product_name,
                                    'description': product_desc,
                                    'price': product_price,
                                    'category': product_category
                                }
                            }
                            
                            self.test_cases.append(test_case)
                            
                            # Build ground truth mapping
                            if safe_question_text not in self.ground_truth:
                                self.ground_truth[safe_question_text] = []
                            
                            self.ground_truth[safe_question_text].append({
                                'name': product_name.lower(),
                                'category': product_category.lower(),
                                'price': product_price,
                                'relevance_score': self._calculate_relevance_score(safe_question_type, product)
                            })
                            
                except Exception as e:
                    print(f"⚠️ Error loading {filepath}: {e}")
                    continue
        
        print(f"✅ Loaded {len(self.test_cases)} test cases from {len(os.listdir(test_case_dir))} files")
        print(f"📊 Ground truth contains {len(self.ground_truth)} unique questions")
        return True
    
    def _safe_string(self, value):
        """Safely convert a value to a stripped string, handling None values"""
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return str(value).strip()
    
    def _calculate_relevance_score(self, question_type, product):
        """
        Calculate relevance score (0-3) based on question type and expected answer quality
        
        Scoring:
        3 = Highly relevant (exact match expected)
        2 = Relevant (good match expected)  
        1 = Somewhat relevant (partial match acceptable)
        0 = Not relevant
        """
        if question_type == "Exact word":
            return 3  # Should find exact product
        elif question_type == "Price range":
            return 2  # Should find products in similar price range
        elif question_type == "Category":
            return 2  # Should find products in same category
        elif question_type == "Description":
            return 2  # Should find products with similar features
        elif question_type == "Attribute value":
            return 1  # May find products with similar attributes
        else:
            return 1  # Default relevance
    
    def execute_search_evaluation(self, max_test_cases=None, delay_between_requests=0.1):
        """
        Execute searches for all test cases and collect results
        
        Args:
            max_test_cases: Limit number of test cases (for testing)
            delay_between_requests: Delay between API calls to avoid rate limiting
        """
        if not self.search_client:
            print("❌ Search client not initialized")
            return False
            
        print(f"🚀 Executing search evaluation for {len(self.test_cases)} test cases...")
        
        test_cases_to_process = self.test_cases[:max_test_cases] if max_test_cases else self.test_cases
        
        for i, test_case in enumerate(test_cases_to_process, 1):
            if i % 50 == 0:
                print(f"Progress: {i}/{len(test_cases_to_process)} ({i/len(test_cases_to_process)*100:.1f}%)")
            
            question = test_case['question']
            
            try:
                # Execute search with timing
                start_time = time.time()
                search_result = self.search_client.search(question, retry_count=1)
                end_time = time.time()
                
                response_time = end_time - start_time
                self.response_times.append(response_time)
                
                # Store result with test case context
                evaluation_result = {
                    'test_case': test_case,
                    'search_result': search_result,
                    'response_time': response_time,
                    'success': search_result.get('success', False),
                    'result_count': search_result.get('result_count', 0)
                }
                
                self.search_results.append(evaluation_result)
                
                # Update counters
                if search_result.get('success', False):
                    self.query_success_count += 1
                    
                if search_result.get('result_count', 0) == 0:
                    self.zero_results_count += 1
                
                # Add delay to avoid rate limiting
                if delay_between_requests > 0:
                    time.sleep(delay_between_requests)
                    
            except Exception as e:
                print(f"⚠️ Error executing search for question: '{question[:50]}...': {e}")
                continue
        
        print(f"✅ Search evaluation completed: {len(self.search_results)} results collected")
        return True

    
    def _extract_search_results_from_response(self, search_result):
        """
        Extract and normalize search results from API response
        
        Returns: List of dicts with 'name', 'score', 'rank' keys
        """
        results = []
        
        if not search_result.get('success', False):
            return results
            
        response_data = search_result.get('response_data', {})
        query_result = response_data.get('queryResult', {})
        
        if isinstance(query_result, dict) and 'result' in query_result:
            api_results = query_result['result']
            
            if isinstance(api_results, list):
                for rank, item in enumerate(api_results, 1):
                    if isinstance(item, dict):
                        # Extract product name from various possible fields
                        product_name = ""
                        for name_field in ['cr4a3_productname', '@primaryNameValue', 'name', 'productname']:
                            if name_field in item and item[name_field]:
                                product_name = str(item[name_field]).strip()
                                break
                        
                        if product_name:
                            results.append({
                                'name': product_name.lower(),
                                'rank': rank,
                                'score': 1.0 / rank,  # Simple relevance score based on position
                                'raw_data': item
                            })
        
        return results
    
    def _get_relevant_items_for_question(self, question):
        """Get relevant items from ground truth for a specific question"""
        return self.ground_truth.get(question, [])
    
    def _calculate_precision_at_k(self, retrieved_results, relevant_items, k=10):
        """
        Calculate Precision@K
        
        Formula: Precision@K = (Relevant items in top K results) / min(K, total retrieved)
        
        Args:
            retrieved_results: List of retrieved items with 'name' and 'rank'
            relevant_items: List of relevant items with 'name' and 'relevance_score'
            k: Number of top results to consider
            
        Returns: precision@k score (0.0 to 1.0)
        """
        if not retrieved_results:
            return 0.0
            
        # Get top K results
        top_k_results = retrieved_results[:k]
        relevant_names = {item['name'] for item in relevant_items}
        
        # Count relevant items in top K
        relevant_retrieved = sum(1 for result in top_k_results if result['name'] in relevant_names)
        
        # Precision = relevant_retrieved / min(k, total_retrieved)
        precision = relevant_retrieved / min(k, len(retrieved_results))
        return precision
    
    def _calculate_recall_at_k(self, retrieved_results, relevant_items, k=10):
        """
        Calculate Recall@K
        
        Formula: Recall@K = (Relevant items in top K results) / (Total relevant items)
        
        Args:
            retrieved_results: List of retrieved items with 'name' and 'rank'
            relevant_items: List of relevant items with 'name' and 'relevance_score'
            k: Number of top results to consider
            
        Returns: recall@k score (0.0 to 1.0)
        """
        if not relevant_items:
            return 1.0 if not retrieved_results else 0.0
            
        if not retrieved_results:
            return 0.0
            
        # Get top K results
        top_k_results = retrieved_results[:k]
        relevant_names = {item['name'] for item in relevant_items}
        
        # Count relevant items in top K
        relevant_retrieved = sum(1 for result in top_k_results if result['name'] in relevant_names)
        
        # Recall = relevant_retrieved / total_relevant
        recall = relevant_retrieved / len(relevant_items)
        return recall
    
    def _calculate_f1_score(self, precision, recall):
        """
        Calculate F1-Score
        
        Formula: F1 = 2 * (Precision * Recall) / (Precision + Recall)
        
        Returns: f1 score (0.0 to 1.0)
        """
        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)
    
    def _calculate_average_precision(self, retrieved_results, relevant_items):
        """
        Calculate Average Precision (AP) for a single query
        
        Formula: AP = (1/R) * Σ(Precision@k * rel(k))
        where R = total relevant items, rel(k) = 1 if item at rank k is relevant, 0 otherwise
        
        Args:
            retrieved_results: List of retrieved items with 'name' and 'rank'
            relevant_items: List of relevant items with 'name' and 'relevance_score'
            
        Returns: average precision score (0.0 to 1.0)
        """
        if not relevant_items or not retrieved_results:
            return 0.0
            
        relevant_names = {item['name'] for item in relevant_items}
        
        precision_sum = 0.0
        relevant_count = 0
        
        for i, result in enumerate(retrieved_results, 1):
            if result['name'] in relevant_names:
                relevant_count += 1
                # Calculate precision at this position
                precision_at_i = relevant_count / i
                precision_sum += precision_at_i
        
        # Average precision = sum of precisions at relevant positions / total relevant items
        if len(relevant_items) == 0:
            return 0.0
        return precision_sum / len(relevant_items)
    
    def _calculate_dcg_at_k(self, retrieved_results, relevant_items, k=10):
        """
        Calculate Discounted Cumulative Gain at K
        
        Formula: DCG@K = Σ(i=1 to k) (relevance_score_i / log2(i + 1))
        
        Args:
            retrieved_results: List of retrieved items with 'name' and 'rank'
            relevant_items: List of relevant items with 'name' and 'relevance_score'
            k: Number of top results to consider
            
        Returns: DCG@k score
        """
        if not retrieved_results:
            return 0.0
            
        # Create relevance mapping
        relevance_map = {item['name']: item['relevance_score'] for item in relevant_items}
        
        dcg = 0.0
        for i, result in enumerate(retrieved_results[:k], 1):
            relevance = relevance_map.get(result['name'], 0)
            if relevance > 0:
                dcg += relevance / math.log2(i + 1)
        
        return dcg
    
    def _calculate_ndcg_at_k(self, retrieved_results, relevant_items, k=10):
        """
        Calculate Normalized Discounted Cumulative Gain at K
        
        Formula: NDCG@K = DCG@K / IDCG@K
        where IDCG@K is the ideal DCG (best possible ranking)
        
        Args:
            retrieved_results: List of retrieved items with 'name' and 'rank'
            relevant_items: List of relevant items with 'name' and 'relevance_score'
            k: Number of top results to consider
            
        Returns: NDCG@k score (0.0 to 1.0)
        """
        # Calculate actual DCG
        actual_dcg = self._calculate_dcg_at_k(retrieved_results, relevant_items, k)
        
        # Calculate ideal DCG (best possible ranking)
        # Sort relevant items by relevance score in descending order
        sorted_relevant = sorted(relevant_items, key=lambda x: x['relevance_score'], reverse=True)
        ideal_results = [{'name': item['name'], 'rank': i+1} for i, item in enumerate(sorted_relevant[:k])]
        ideal_dcg = self._calculate_dcg_at_k(ideal_results, relevant_items, k)
        
        # NDCG = DCG / IDCG
        if ideal_dcg == 0:
            return 0.0
        return actual_dcg / ideal_dcg
    
    def _calculate_reciprocal_rank(self, retrieved_results, relevant_items):
        """
        Calculate Reciprocal Rank (RR) for a single query
        
        Formula: RR = 1 / rank_of_first_relevant_item
        
        Args:
            retrieved_results: List of retrieved items with 'name' and 'rank'
            relevant_items: List of relevant items with 'name' and 'relevance_score'
            
        Returns: reciprocal rank score (0.0 to 1.0)
        """
        if not retrieved_results or not relevant_items:
            return 0.0
            
        relevant_names = {item['name'] for item in relevant_items}
        
        for result in retrieved_results:
            if result['name'] in relevant_names:
                return 1.0 / result['rank']
        
        return 0.0  # No relevant items found
    
    def calculate_all_metrics(self, k_values=[1, 3, 5, 10, 20]):
        """
        Calculate all evaluation metrics for the collected search results
        
        Args:
            k_values: List of K values for Precision@K, Recall@K, NDCG@K calculations
        """
        print(f"📊 Calculating comprehensive evaluation metrics...")
        
        if not self.search_results:
            print("❌ No search results available for evaluation")
            return
        
        # Reset metric storage
        self.precision_scores = defaultdict(list)
        self.recall_scores = defaultdict(list)
        self.f1_scores = defaultdict(list)
        self.map_scores = []
        self.ndcg_scores = defaultdict(list)
        self.mrr_scores = []
        
        successful_evaluations = 0
        
        for result in self.search_results:
            if not result['success']:
                continue
                
            question = result['test_case']['question']
            retrieved_results = self._extract_search_results_from_response(result['search_result'])
            relevant_items = self._get_relevant_items_for_question(question)
            
            if not relevant_items:
                continue  # Skip if no ground truth available
                
            successful_evaluations += 1
            
            # Calculate metrics for different K values
            for k in k_values:
                precision_k = self._calculate_precision_at_k(retrieved_results, relevant_items, k)
                recall_k = self._calculate_recall_at_k(retrieved_results, relevant_items, k)
                f1_k = self._calculate_f1_score(precision_k, recall_k)
                ndcg_k = self._calculate_ndcg_at_k(retrieved_results, relevant_items, k)
                
                self.precision_scores[k].append(precision_k)
                self.recall_scores[k].append(recall_k)
                self.f1_scores[k].append(f1_k)
                self.ndcg_scores[k].append(ndcg_k)
            
            # Calculate AP for MAP
            ap = self._calculate_average_precision(retrieved_results, relevant_items)
            self.map_scores.append(ap)
            
            # Calculate RR for MRR
            rr = self._calculate_reciprocal_rank(retrieved_results, relevant_items)
            self.mrr_scores.append(rr)
        
        print(f"✅ Metrics calculated for {successful_evaluations} successful evaluations")
    
    def print_evaluation_report(self, k_values=[1, 3, 5, 10, 20]):
        """Print comprehensive evaluation report with all metrics"""
        
        print("\n" + "="*80)
        print("🔬 COMPREHENSIVE SEARCH ENGINE EVALUATION REPORT")
        print("="*80)
        
        # Basic Statistics
        total_queries = len(self.search_results)
        success_rate = (self.query_success_count / total_queries * 100) if total_queries > 0 else 0
        zero_results_rate = (self.zero_results_count / total_queries * 100) if total_queries > 0 else 0
        
        print(f"\n📈 BASIC PERFORMANCE METRICS:")
        print(f"   Total Queries Executed: {total_queries}")
        print(f"   Successful Queries: {self.query_success_count} ({success_rate:.1f}%)")
        print(f"   Zero Results Queries: {self.zero_results_count} ({zero_results_rate:.1f}%)")
        
        # Response Time Analysis
        if self.response_times:
            avg_response_time = statistics.mean(self.response_times)
            median_response_time = statistics.median(self.response_times)
            p95_response_time = statistics.quantiles(self.response_times, n=20)[18]  # 95th percentile
            min_response_time = min(self.response_times)
            max_response_time = max(self.response_times)
            
            print(f"\n⚡ RESPONSE TIME ANALYSIS:")
            print(f"   Average Response Time: {avg_response_time*1000:.1f}ms")
            print(f"   Median Response Time: {median_response_time*1000:.1f}ms")
            print(f"   95th Percentile: {p95_response_time*1000:.1f}ms")
            print(f"   Min Response Time: {min_response_time*1000:.1f}ms")
            print(f"   Max Response Time: {max_response_time*1000:.1f}ms")
        
        # Relevance Metrics
        print(f"\n🎯 RELEVANCE METRICS:")
        
        # Precision@K, Recall@K, F1@K
        for k in k_values:
            if self.precision_scores[k]:
                avg_precision = statistics.mean(self.precision_scores[k])
                avg_recall = statistics.mean(self.recall_scores[k])
                avg_f1 = statistics.mean(self.f1_scores[k])
                
                print(f"   Precision@{k}: {avg_precision:.3f}")
                print(f"   Recall@{k}: {avg_recall:.3f}")
                print(f"   F1-Score@{k}: {avg_f1:.3f}")
                print(f"   ---")
        
        # Ranking Quality Metrics
        print(f"\n🏆 RANKING QUALITY METRICS:")
        
        if self.map_scores:
            avg_map = statistics.mean(self.map_scores)
            print(f"   MAP (Mean Average Precision): {avg_map:.3f}")
        
        if self.mrr_scores:
            avg_mrr = statistics.mean(self.mrr_scores)
            print(f"   MRR (Mean Reciprocal Rank): {avg_mrr:.3f}")
        
        for k in k_values:
            if self.ndcg_scores[k]:
                avg_ndcg = statistics.mean(self.ndcg_scores[k])
                print(f"   NDCG@{k}: {avg_ndcg:.3f}")
        
        # Coverage Metrics
        print(f"\n📊 COVERAGE METRICS:")
        print(f"   Query Success Rate: {success_rate:.1f}%")
        print(f"   Zero Results Rate: {zero_results_rate:.1f}%")
        print(f"   Result Coverage: {(100 - zero_results_rate):.1f}%")
        
        print("\n" + "="*80)
        print("📝 METRIC CALCULATION EXPLANATIONS:")
        print("="*80)
        
        print("\n🔢 HOW METRICS ARE CALCULATED:")
        print("   • Precision@K = (Relevant items in top K) / min(K, total retrieved)")
        print("   • Recall@K = (Relevant items in top K) / (Total relevant items)")
        print("   • F1-Score@K = 2 * (Precision@K * Recall@K) / (Precision@K + Recall@K)")
        print("   • MAP = Average of AP scores across all queries")
        print("   • AP = (1/R) * Σ(Precision@k * rel(k)) where rel(k)=1 if item k is relevant")
        print("   • NDCG@K = DCG@K / IDCG@K (normalized by ideal ranking)")
        print("   • DCG@K = Σ(relevance_score / log2(position + 1)) for top K items")
        print("   • MRR = Average of (1 / rank_of_first_relevant_item) across queries")
        print("   • Response Time = Time from API request to response completion")
        print("   • Success Rate = (Successful API calls) / (Total API calls)")
        print("   • Zero Results Rate = (Queries returning 0 results) / (Total queries)")
        
        print("\n📋 RELEVANCE SCORING:")
        print("   • Exact word questions: 3 points (highest relevance)")
        print("   • Price/Category/Description questions: 2 points (high relevance)")
        print("   • Attribute questions: 1 point (moderate relevance)")
        print("   • Product name matching uses exact string comparison (case-insensitive)")
        
        print("="*80)
    
    def save_evaluation_results(self, output_file="search_evaluation_results.json"):
        """Save detailed evaluation results to JSON file"""
        
        timestamp = datetime.now().isoformat()
        
        # Calculate summary metrics
        summary_metrics = {}
        
        # Basic metrics
        total_queries = len(self.search_results)
        success_rate = (self.query_success_count / total_queries) if total_queries > 0 else 0
        zero_results_rate = (self.zero_results_count / total_queries) if total_queries > 0 else 0
        
        summary_metrics['basic'] = {
            'total_queries': total_queries,
            'successful_queries': self.query_success_count,
            'success_rate': success_rate,
            'zero_results_count': self.zero_results_count,
            'zero_results_rate': zero_results_rate
        }
        
        # Response time metrics
        if self.response_times:
            summary_metrics['response_time'] = {
                'average_ms': statistics.mean(self.response_times) * 1000,
                'median_ms': statistics.median(self.response_times) * 1000,
                'min_ms': min(self.response_times) * 1000,
                'max_ms': max(self.response_times) * 1000,
                'p95_ms': statistics.quantiles(self.response_times, n=20)[18] * 1000 if len(self.response_times) >= 20 else None
            }
        
        # Relevance metrics
        summary_metrics['relevance'] = {}
        
        for k in [1, 3, 5, 10, 20]:
            if self.precision_scores[k]:
                summary_metrics['relevance'][f'precision_at_{k}'] = statistics.mean(self.precision_scores[k])
                summary_metrics['relevance'][f'recall_at_{k}'] = statistics.mean(self.recall_scores[k])
                summary_metrics['relevance'][f'f1_at_{k}'] = statistics.mean(self.f1_scores[k])
                summary_metrics['relevance'][f'ndcg_at_{k}'] = statistics.mean(self.ndcg_scores[k])
        
        if self.map_scores:
            summary_metrics['relevance']['map'] = statistics.mean(self.map_scores)
        
        if self.mrr_scores:
            summary_metrics['relevance']['mrr'] = statistics.mean(self.mrr_scores)
        
        # Prepare output data
        output_data = {
            'evaluation_metadata': {
                'timestamp': timestamp,
                'total_test_cases': len(self.test_cases),
                'total_search_results': len(self.search_results),
                'ground_truth_questions': len(self.ground_truth)
            },
            'summary_metrics': summary_metrics,
            'detailed_results': self.search_results,
            'metric_calculations': {
                'precision_scores': dict(self.precision_scores),
                'recall_scores': dict(self.recall_scores),
                'f1_scores': dict(self.f1_scores),
                'ndcg_scores': dict(self.ndcg_scores),
                'map_scores': self.map_scores,
                'mrr_scores': self.mrr_scores,
                'response_times': self.response_times
            }
        }
        
        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Evaluation results saved to: {output_file}")
        return output_file

def run_comprehensive_search_evaluation(test_case_dir="test_case", max_test_cases=None, output_file=None):
    """
    Main function to run comprehensive search evaluation
    
    Args:
        test_case_dir: Directory containing test case JSON files
        max_test_cases: Limit number of test cases (for testing)
        output_file: Output file for results (optional)
    
    Returns:
        SearchEngineEvaluator instance with results
    """
    print("🚀 Starting Comprehensive Search Engine Evaluation")
    print("="*60)
    
    # Initialize evaluator
    evaluator = SearchEngineEvaluator()
    
    # Initialize search client
    if not evaluator.initialize_search_client():
        print("❌ Failed to initialize search client. Exiting.")
        return None
    
    # Load test cases
    if not evaluator.load_test_cases(test_case_dir):
        print("❌ Failed to load test cases. Exiting.")
        return None
    
    # Execute search evaluation
    print(f"\n🔍 Executing searches...")
    if not evaluator.execute_search_evaluation(max_test_cases=max_test_cases):
        print("❌ Failed to execute search evaluation. Exiting.")
        return None
    
    # Calculate metrics
    print(f"\n📊 Calculating metrics...")
    evaluator.calculate_all_metrics()
    
    # Print report
    evaluator.print_evaluation_report()
    
    # Save results
    if output_file:
        evaluator.save_evaluation_results(output_file)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_output = f"search_evaluation_{timestamp}.json"
        evaluator.save_evaluation_results(default_output)
    
    print(f"\n✅ Comprehensive evaluation completed!")
    return evaluator

# Legacy function for backward compatibility with existing JSONL analysis
def analyze_jsonl_file(file_path):
    """
    Legacy function to analyze existing JSONL files (backward compatibility)
    
    NOTE: This function provides basic analysis of pre-existing JSONL files.
    For comprehensive evaluation with live API calls, use run_comprehensive_search_evaluation()
    """
    print("⚠️  Using legacy JSONL analysis mode.")
    print("💡 For comprehensive evaluation with live API calls, use run_comprehensive_search_evaluation()")
    print()
    
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return None
    
    # Basic file analysis
    file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
    print(f'File: {file_path}')
    print(f'File size: {file_size:.2f} MB')
    
    # Count lines and basic statistics
    line_count = 0
    success_count = 0
    response_times = []
    result_counts = []
    status_codes = Counter()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    line_count += 1
                    
                    if data.get('success'):
                        success_count += 1
                    
                    if 'response_time_seconds' in data:
                        response_times.append(data['response_time_seconds'])
                    
                    if 'result_count' in data:
                        result_counts.append(data['result_count'])
                    
                    status_codes[data.get('status_code')] += 1
                    
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"Error reading file: {e}")
        return None
    
    # Print basic results
    print(f'\n=== Basic File Analysis ===')
    print(f'Total lines: {line_count}')
    print(f'Successful requests: {success_count} ({success_count/line_count*100:.1f}%)')
    print(f'Status code distribution: {dict(status_codes)}')
    
    if response_times:
        avg_time = statistics.mean(response_times)
        print(f'Average response time: {avg_time:.3f} seconds')
    
    if result_counts:
        zero_results = result_counts.count(0)
        print(f'Zero results rate: {zero_results/len(result_counts)*100:.1f}%')
    
    return {
        'line_count': line_count,
        'success_count': success_count,
        'success_rate': success_count/line_count*100 if line_count > 0 else 0,
        'avg_response_time': statistics.mean(response_times) if response_times else 0,
        'zero_results_rate': result_counts.count(0)/len(result_counts)*100 if result_counts else 0
    }

def analyze_existing_jsonl_results(jsonl_file_path):
    """
    Comprehensive analysis of existing JSONL search results file
    Calculates all search engine evaluation metrics from pre-existing results
    
    This function analyzes search results that have already been generated,
    providing comprehensive IR metrics without making new API calls.
    """
    print("🔬 Comprehensive JSONL Results Analysis")
    print("="*60)
    print(f"📁 Analyzing file: {jsonl_file_path}")
    
    if not os.path.exists(jsonl_file_path):
        print(f"❌ File not found: {jsonl_file_path}")
        return None
    
    # Initialize analysis data structures
    analysis_results = {
        'file_info': {},
        'search_performance': {},
        'relevance_metrics': {},
        'coverage_metrics': {},
        'detailed_analysis': {},
        'metric_calculations': {}
    }
    
    # Load and parse JSONL file
    search_results = []
    line_count = 0
    
    print("\n📊 Loading and parsing JSONL file...")
    
    try:
        with open(jsonl_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line_count += 1
                if line.strip():
                    try:
                        result = json.loads(line.strip())
                        search_results.append(result)
                    except json.JSONDecodeError as e:
                        print(f"⚠️ Skipping malformed line {line_num}: {e}")
                        continue
    
        print(f"✅ Loaded {len(search_results)} search results from {line_count} lines")
        
        # File information
        file_size_mb = os.path.getsize(jsonl_file_path) / (1024 * 1024)
        analysis_results['file_info'] = {
            'file_path': jsonl_file_path,
            'file_size_mb': round(file_size_mb, 2),
            'total_lines': line_count,
            'valid_results': len(search_results),
            'parsing_success_rate': len(search_results) / line_count * 100 if line_count > 0 else 0
        }
        
        # Basic performance metrics
        successful_searches = [r for r in search_results if r.get('success', False)]
        failed_searches = [r for r in search_results if not r.get('success', False)]
        
        # Response times
        response_times = [r.get('response_time_seconds', 0) for r in search_results if r.get('response_time_seconds')]
        
        # Result counts
        result_counts = [r.get('result_count', 0) for r in search_results]
        
        # Status codes
        status_codes = [r.get('status_code') for r in search_results if r.get('status_code')]
        status_code_dist = dict(Counter(status_codes))
        
        analysis_results['search_performance'] = {
            'total_searches': len(search_results),
            'successful_searches': len(successful_searches),
            'failed_searches': len(failed_searches),
            'success_rate': len(successful_searches) / len(search_results) * 100 if search_results else 0,
            'avg_response_time_ms': statistics.mean(response_times) * 1000 if response_times else 0,
            'median_response_time_ms': statistics.median(response_times) * 1000 if response_times else 0,
            'p95_response_time_ms': sorted(response_times)[int(len(response_times) * 0.95)] * 1000 if response_times else 0,
            'p99_response_time_ms': sorted(response_times)[int(len(response_times) * 0.99)] * 1000 if response_times else 0,
            'min_response_time_ms': min(response_times) * 1000 if response_times else 0,
            'max_response_time_ms': max(response_times) * 1000 if response_times else 0,
            'status_code_distribution': status_code_dist
        }
        
        # Coverage metrics
        zero_result_searches = [r for r in search_results if r.get('result_count', 0) == 0]
        
        analysis_results['coverage_metrics'] = {
            'total_results_returned': sum(result_counts),
            'avg_results_per_query': statistics.mean(result_counts) if result_counts else 0,
            'median_results_per_query': statistics.median(result_counts) if result_counts else 0,
            'zero_results_count': len(zero_result_searches),
            'zero_results_rate': len(zero_result_searches) / len(search_results) * 100 if search_results else 0,
            'max_results_single_query': max(result_counts) if result_counts else 0,
            'min_results_single_query': min(result_counts) if result_counts else 0
        }
        
        print("\n🎯 Calculating Relevance Metrics...")
        
        # Relevance Analysis
        relevance_data = analyze_relevance_from_results(search_results)
        analysis_results['relevance_metrics'] = relevance_data
        
        # Question Type Relevance Breakdown
        print("   Calculating relevance metrics by question type...")
        question_type_relevance = analyze_relevance_by_question_type(search_results)
        analysis_results['relevance_metrics']['question_type_breakdown'] = question_type_relevance
        
        # Question type analysis
        question_types = {}
        categories = {}
        
        for result in search_results:
            test_context = result.get('test_case_context', {})
            q_type = test_context.get('question_type', 'Unknown')
            category = test_context.get('original_product_category', 'Unknown')
            
            question_types[q_type] = question_types.get(q_type, 0) + 1
            categories[category] = categories.get(category, 0) + 1
        
        analysis_results['detailed_analysis'] = {
            'question_type_distribution': question_types,
            'product_category_distribution': categories,
            'search_patterns': analyze_search_patterns(search_results)
        }
        
        # Generate comprehensive report
        print_comprehensive_analysis_report(analysis_results)
        
        # Save detailed results
        output_file = jsonl_file_path.replace('.jsonl', '_comprehensive_analysis.json')
        save_analysis_results(analysis_results, output_file)
        
        return analysis_results
        
    except Exception as e:
        print(f"❌ Error analyzing JSONL file: {e}")
        import traceback
        traceback.print_exc()
        return None

def analyze_relevance_from_results(search_results):
    """
    Calculate comprehensive relevance metrics from search results
    
    Metrics calculated:
    1. Precision@K - Relevant items in top K results / K
    2. Recall@K - Relevant items in top K results / Total relevant items
    3. F1-Score@K - Harmonic mean of Precision and Recall
    4. MAP (Mean Average Precision) - Average precision across all relevant items
    5. NDCG@K (Normalized DCG) - Ranking quality with position discounting
    6. MRR (Mean Reciprocal Rank) - Position of first relevant result
    """
    
    metrics = {
        'precision_at_k': {},
        'recall_at_k': {},
        'f1_score_at_k': {},
        'map_score': 0,
        'ndcg_at_k': {},
        'mrr_score': 0,
        'relevance_analysis': {},
        'calculation_explanations': {}
    }
    
    # K values for evaluation
    k_values = [1, 3, 5, 10]
    
    # Store individual query results for detailed analysis
    query_precisions = {k: [] for k in k_values}
    query_recalls = {k: [] for k in k_values}
    query_dcgs = {k: [] for k in k_values}
    query_ndcgs = {k: [] for k in k_values}
    reciprocal_ranks = []
    average_precisions = []
    
    relevant_found_total = 0
    total_relevant_items = 0
    exact_matches = 0
    category_matches = 0
    
    print(f"   Analyzing {len(search_results)} search results...")
    
    for idx, result in enumerate(search_results):
        if not result.get('success', False):
            continue
            
        # Extract test case context and search results
        test_context = result.get('test_case_context', {})
        api_response = result.get('api_response_products', {})
        found_products = api_response.get('product_names_found', [])
        
        original_product_name = test_context.get('original_product_name', '').lower()
        original_category = test_context.get('original_product_category', '').lower()
        question_type = test_context.get('question_type', '')
        
        # Determine relevant items for this query
        relevant_items = []
        if original_product_name:
            relevant_items.append(original_product_name)
            total_relevant_items += 1
        
        # Calculate relevance scores for found products
        # Calculate query-level relevance using new approach
        query_relevance_score, relevant_count, total_count, explanation = calculate_relevance_for_query(
            result, original_product_name, original_category, question_type
        )
        
        # Store detailed relevance information
        relevant_results = []
        if found_products:
            for i, product_name in enumerate(found_products):
                # Determine if this specific product is relevant based on question type
                product_relevance = 0
                if query_relevance_score > 0:  # If query has any relevance
                    # Simple heuristic: distribute relevance across products
                    if i < relevant_count:
                        product_relevance = 1  # Mark as relevant
                
                if product_relevance > 0:
                    relevant_results.append({
                        'product': product_name,
                        'relevance_score': product_relevance,
                        'position': i + 1
                    })
                    
                    # Count exact matches
                    if product_name.lower() == original_product_name.lower():
                        exact_matches += 1
        
        # Add to overall totals (using new relevance scoring)
        relevant_found_total += relevant_count
        
        # Calculate metrics for different K values
        for k in k_values:
            # Precision@K
            relevant_at_k = len([r for r in relevant_results[:k] if r['relevance_score'] > 0])
            precision_k = relevant_at_k / min(k, len(found_products)) if found_products else 0
            query_precisions[k].append(precision_k)
            
            # Recall@K  
            recall_k = relevant_at_k / len(relevant_items) if relevant_items else 0
            query_recalls[k].append(recall_k)
            
            # DCG@K calculation
            dcg_k = 0
            for i, result_item in enumerate(relevant_results[:k]):
                if i < len(relevant_results):
                    relevance = result_item['relevance_score']
                    dcg_k += relevance / math.log2(i + 2)  # i+2 because positions start from 1
            query_dcgs[k].append(dcg_k)
            
            # IDCG@K (Ideal DCG) - Perfect ranking of relevant items
            ideal_relevances = sorted([r['relevance_score'] for r in relevant_results], reverse=True)[:k]
            idcg_k = sum(rel / math.log2(i + 2) for i, rel in enumerate(ideal_relevances))
            
            # NDCG@K
            ndcg_k = dcg_k / idcg_k if idcg_k > 0 else 0
            query_ndcgs[k].append(ndcg_k)
        
        # Mean Reciprocal Rank calculation
        first_relevant_position = None
        for i, result_item in enumerate(relevant_results):
            if result_item['relevance_score'] > 0:
                first_relevant_position = i + 1
                break
        
        if first_relevant_position:
            reciprocal_ranks.append(1.0 / first_relevant_position)
        else:
            reciprocal_ranks.append(0)
        
        # Average Precision calculation
        if relevant_results:
            precisions_at_relevant = []
            relevant_count = 0
            for i, result_item in enumerate(relevant_results):
                if result_item['relevance_score'] > 0:
                    relevant_count += 1
                    precision_at_i = relevant_count / (i + 1)
                    precisions_at_relevant.append(precision_at_i)
            
            if precisions_at_relevant:
                avg_precision = sum(precisions_at_relevant) / len(precisions_at_relevant)
                average_precisions.append(avg_precision)
            else:
                average_precisions.append(0)
        else:
            average_precisions.append(0)
    
    # Calculate final metrics
    for k in k_values:
        metrics['precision_at_k'][f'P@{k}'] = statistics.mean(query_precisions[k]) if query_precisions[k] else 0
        metrics['recall_at_k'][f'R@{k}'] = statistics.mean(query_recalls[k]) if query_recalls[k] else 0
        
        # F1-Score@K
        p_k = metrics['precision_at_k'][f'P@{k}']
        r_k = metrics['recall_at_k'][f'R@{k}']
        f1_k = 2 * (p_k * r_k) / (p_k + r_k) if (p_k + r_k) > 0 else 0
        metrics['f1_score_at_k'][f'F1@{k}'] = f1_k
        
        metrics['ndcg_at_k'][f'NDCG@{k}'] = statistics.mean(query_ndcgs[k]) if query_ndcgs[k] else 0
    
    # MAP and MRR
    metrics['map_score'] = statistics.mean(average_precisions) if average_precisions else 0
    metrics['mrr_score'] = statistics.mean(reciprocal_ranks) if reciprocal_ranks else 0
    
    # Relevance analysis with new approach
    metrics['relevance_analysis'] = {
        'total_queries_analyzed': len([r for r in search_results if r.get('success', False)]),
        'total_relevant_items_found': relevant_found_total,
        'exact_name_matches': exact_matches,
        'average_relevance_per_query': relevant_found_total / len(search_results) if search_results else 0,
        'search_effectiveness': f"Found {relevant_found_total} relevant results across {len(search_results)} queries"
    }
    
    # Add calculation explanations
    metrics['calculation_explanations'] = {
        'precision_at_k': "Precision@K = (Relevant items in top K results) / K",
        'recall_at_k': "Recall@K = (Relevant items in top K results) / (Total relevant items)",
        'f1_score_at_k': "F1@K = 2 × (Precision@K × Recall@K) / (Precision@K + Recall@K)",
        'map_score': "MAP = Average of precision scores at each relevant document position",
        'ndcg_at_k': "NDCG@K = DCG@K / IDCG@K, where DCG considers relevance scores and position discounting",
        'mrr_score': "MRR = Average of reciprocal ranks of first relevant result (1/rank)"
    }
    
    return metrics

def analyze_relevance_by_question_type(search_results):
    """
    Calculate detailed relevance metrics breakdown by question type
    
    Returns metrics for each question type:
    - Precision@K, Recall@K, F1@K for K=[1,3,5,10]
    - MAP, MRR, NDCG@K
    - Individual performance statistics
    """
    
    # Group results by question type
    results_by_type = {}
    for result in search_results:
        if not result.get('success', False):
            continue
            
        test_context = result.get('test_case_context', {})
        question_type = test_context.get('question_type', 'Unknown')
        
        if question_type not in results_by_type:
            results_by_type[question_type] = []
        results_by_type[question_type].append(result)
    
    question_type_metrics = {}
    
    for question_type, type_results in results_by_type.items():
        print(f"      Analyzing {question_type}: {len(type_results)} queries...")
        
        # Calculate metrics for this question type using the same logic
        type_metrics = {
            'precision_at_k': {},
            'recall_at_k': {},
            'f1_score_at_k': {},
            'map_score': 0,
            'ndcg_at_k': {},
            'mrr_score': 0,
            'query_count': len(type_results),
            'relevance_analysis': {}
        }
        
        # K values for evaluation
        k_values = [1, 3, 5, 10]
        
        # Store individual query results for detailed analysis
        query_precisions = {k: [] for k in k_values}
        query_recalls = {k: [] for k in k_values}
        query_dcgs = {k: [] for k in k_values}
        query_ndcgs = {k: [] for k in k_values}
        reciprocal_ranks = []
        average_precisions = []
        
        relevant_found_total = 0
        total_relevant_items = 0
        exact_matches = 0
        
        for idx, result in enumerate(type_results):
            # Extract test case context and search results
            test_context = result.get('test_case_context', {})
            api_response = result.get('api_response_products', {})
            found_products = api_response.get('product_names_found', [])
            
            original_product_name = test_context.get('original_product_name', '').lower()
            original_category = test_context.get('original_product_category', '').lower()
            current_question_type = test_context.get('question_type', '')
            
            # Determine relevant items for this query
            relevant_items = []
            if original_product_name:
                relevant_items.append(original_product_name)
                total_relevant_items += 1
            
            # Calculate query-level relevance using new approach
            query_relevance_score, relevant_count, total_count, explanation = calculate_relevance_for_query(
                result, original_product_name, original_category, current_question_type
            )
            
            # Store detailed relevance information
            relevant_results = []
            if found_products:
                for i, product_name in enumerate(found_products):
                    # Determine if this specific product is relevant based on question type
                    product_relevance = 0
                    if query_relevance_score > 0:  # If query has any relevance
                        # Simple heuristic: distribute relevance across products
                        if i < relevant_count:
                            product_relevance = 1  # Mark as relevant
                    
                    if product_relevance > 0:
                        relevant_results.append({
                            'product': product_name,
                            'relevance_score': product_relevance,
                            'position': i + 1
                        })
                        
                        # Count exact matches
                        if product_name.lower() == original_product_name.lower():
                            exact_matches += 1
            
            # Add to overall totals (using new relevance scoring)
            relevant_found_total += relevant_count
            
            # Calculate metrics for different K values
            for k in k_values:
                # Precision@K
                relevant_at_k = len([r for r in relevant_results[:k] if r['relevance_score'] > 0])
                precision_k = relevant_at_k / min(k, len(found_products)) if found_products else 0
                query_precisions[k].append(precision_k)
                
                # Recall@K  
                recall_k = relevant_at_k / len(relevant_items) if relevant_items else 0
                query_recalls[k].append(recall_k)
                
                # DCG@K calculation
                dcg_k = 0
                for i, result_item in enumerate(relevant_results[:k]):
                    if i < len(relevant_results):
                        relevance = result_item['relevance_score']
                        dcg_k += relevance / math.log2(i + 2)  # i+2 because positions start from 1
                query_dcgs[k].append(dcg_k)
                
                # IDCG@K (Ideal DCG) - Perfect ranking of relevant items
                ideal_relevances = sorted([r['relevance_score'] for r in relevant_results], reverse=True)[:k]
                idcg_k = sum(rel / math.log2(i + 2) for i, rel in enumerate(ideal_relevances))
                
                # NDCG@K
                ndcg_k = dcg_k / idcg_k if idcg_k > 0 else 0
                query_ndcgs[k].append(ndcg_k)
            
            # Mean Reciprocal Rank calculation
            first_relevant_position = None
            for i, result_item in enumerate(relevant_results):
                if result_item['relevance_score'] > 0:
                    first_relevant_position = i + 1
                    break
            
            if first_relevant_position:
                reciprocal_ranks.append(1.0 / first_relevant_position)
            else:
                reciprocal_ranks.append(0)
            
            # Average Precision calculation
            if relevant_results:
                precisions_at_relevant = []
                relevant_count = 0
                for i, result_item in enumerate(relevant_results):
                    if result_item['relevance_score'] > 0:
                        relevant_count += 1
                        precision_at_i = relevant_count / (i + 1)
                        precisions_at_relevant.append(precision_at_i)
                
                if precisions_at_relevant:
                    avg_precision = sum(precisions_at_relevant) / len(precisions_at_relevant)
                    average_precisions.append(avg_precision)
                else:
                    average_precisions.append(0)
            else:
                average_precisions.append(0)
        
        # Calculate final metrics for this question type
        for k in k_values:
            type_metrics['precision_at_k'][f'P@{k}'] = statistics.mean(query_precisions[k]) if query_precisions[k] else 0
            type_metrics['recall_at_k'][f'R@{k}'] = statistics.mean(query_recalls[k]) if query_recalls[k] else 0
            
            # F1-Score@K
            p_k = type_metrics['precision_at_k'][f'P@{k}']
            r_k = type_metrics['recall_at_k'][f'R@{k}']
            f1_k = 2 * (p_k * r_k) / (p_k + r_k) if (p_k + r_k) > 0 else 0
            type_metrics['f1_score_at_k'][f'F1@{k}'] = f1_k
            
            type_metrics['ndcg_at_k'][f'NDCG@{k}'] = statistics.mean(query_ndcgs[k]) if query_ndcgs[k] else 0
        
        # MAP and MRR for this question type
        type_metrics['map_score'] = statistics.mean(average_precisions) if average_precisions else 0
        type_metrics['mrr_score'] = statistics.mean(reciprocal_ranks) if reciprocal_ranks else 0
        
        # Relevance analysis for this question type with new approach
        type_metrics['relevance_analysis'] = {
            'total_queries_analyzed': len(type_results),
            'total_relevant_items_found': relevant_found_total,
            'exact_name_matches': exact_matches,
            'average_relevance_per_query': relevant_found_total / len(type_results) if type_results else 0,
            'search_effectiveness': f"Found {relevant_found_total} relevant results across {len(type_results)} queries"
        }
        
        question_type_metrics[question_type] = type_metrics
    
    return question_type_metrics

def calculate_relevance_for_query(search_result, expected_product_name, expected_category, question_type):
    """
    Calculate relevance for an entire query based on whether results match what was asked
    
    Returns:
    - relevance_score: Float between 0-1 representing how well results match the question
    - relevant_count: Number of results that are relevant to the question
    - total_count: Total number of results returned
    - explanation: Text explaining the relevance assessment
    """
    
    if not search_result.get('api_response_products', {}).get('product_names_found'):
        return 0.0, 0, 0, "No results returned"
    
    found_products = search_result['api_response_products']['product_names_found']
    total_count = len(found_products)
    relevant_count = 0
    explanations = []
    
    # Analyze relevance based on question type
    if question_type == "Exact word":
        # For exact word questions, look for products that contain the key terms
        expected_words = set(expected_product_name.lower().split())
        
        for product in found_products:
            product_words = set(product.lower().split())
            common_words = expected_words.intersection(product_words)
            
            if product.lower() == expected_product_name.lower():
                relevant_count += 1
                explanations.append(f"'{product}' is exact match")
            elif len(common_words) >= 2:
                relevant_count += 1
                explanations.append(f"'{product}' shares key words: {', '.join(common_words)}")
            elif len(common_words) >= 1:
                relevant_count += 0.5
                explanations.append(f"'{product}' partially matches: {', '.join(common_words)}")
    
    elif question_type == "Category":
        # For category questions, check if products belong to the requested category
        for product in found_products:
            product_lower = product.lower()
            category_lower = expected_category.lower() if expected_category else ""
            
            # Check for category keywords in product name
            category_keywords = {
                "backpack": ["backpack", "pack", "bag"],
                "footwear": ["shoes", "boots", "sneakers", "sandals"],
                "helmet": ["helmet"],
                "accessory": ["accessory", "gear", "equipment"],
                "clothing": ["shirt", "jacket", "coat", "apparel"],
                "sleeping": ["sleeping", "sleep"]
            }
            
            if category_lower in category_keywords:
                for keyword in category_keywords[category_lower]:
                    if keyword in product_lower:
                        relevant_count += 1
                        explanations.append(f"'{product}' matches {category_lower} category")
                        break
            elif category_lower and category_lower in product_lower:
                relevant_count += 1
                explanations.append(f"'{product}' contains category '{category_lower}'")
    
    elif question_type == "Category + Price range":
        # For category + price questions, products should be in the right category
        # (price filtering is assumed to be done by the search engine)
        for product in found_products:
            product_lower = product.lower()
            category_lower = expected_category.lower() if expected_category else ""
            
            category_keywords = {
                "backpack": ["backpack", "pack", "bag"],
                "footwear": ["shoes", "boots", "sneakers", "sandals"],
                "helmet": ["helmet"],
                "accessory": ["accessory", "gear", "equipment"],
                "clothing": ["shirt", "jacket", "coat", "apparel"],
                "sleeping": ["sleeping", "sleep"]
            }
            
            if category_lower in category_keywords:
                for keyword in category_keywords[category_lower]:
                    if keyword in product_lower:
                        relevant_count += 1
                        explanations.append(f"'{product}' matches {category_lower} category (price filtered)")
                        break
    
    elif question_type == "Category + Attribute value":
        # For category + attribute questions, products should be in the right category
        # (attribute filtering is assumed to be done by the search engine)
        for product in found_products:
            product_lower = product.lower()
            category_lower = expected_category.lower() if expected_category else ""
            
            category_keywords = {
                "backpack": ["backpack", "pack", "bag"],
                "footwear": ["shoes", "boots", "sneakers", "sandals"],
                "helmet": ["helmet"],
                "accessory": ["accessory", "gear", "equipment"],
                "clothing": ["shirt", "jacket", "coat", "apparel"],
                "sleeping": ["sleeping", "sleep"]
            }
            
            if category_lower in category_keywords:
                for keyword in category_keywords[category_lower]:
                    if keyword in product_lower:
                        relevant_count += 1
                        explanations.append(f"'{product}' matches {category_lower} category (attribute filtered)")
                        break
    
    elif question_type == "Description":
        # For description-based questions, look for semantic similarity
        expected_words = set(expected_product_name.lower().split())
        
        for product in found_products:
            product_words = set(product.lower().split())
            common_words = expected_words.intersection(product_words)
            
            if len(common_words) >= 2:
                relevant_count += 1
                explanations.append(f"'{product}' semantically similar: {', '.join(common_words)}")
            elif len(common_words) >= 1:
                relevant_count += 0.5
                explanations.append(f"'{product}' partially similar: {', '.join(common_words)}")
    
    elif question_type == "Price range":
        # For price range questions, all returned products are assumed relevant
        # (since search engine should filter by price)
        relevant_count = total_count
        explanations.append(f"All {total_count} products assumed relevant for price range query")
    
    elif question_type == "Attribute value":
        # For attribute searches, look for semantic similarity
        expected_words = set(expected_product_name.lower().split())
        
        for product in found_products:
            product_words = set(product.lower().split())
            common_words = expected_words.intersection(product_words)
            
            if len(common_words) >= 1:
                relevant_count += 1
                explanations.append(f"'{product}' matches attribute criteria: {', '.join(common_words)}")
    
    # Calculate relevance score
    if total_count == 0:
        relevance_score = 0.0
    else:
        relevance_score = relevant_count / total_count
    
    explanation = f"Question type: {question_type}. " + "; ".join(explanations[:3])  # Limit explanations
    
    return relevance_score, relevant_count, total_count, explanation

def analyze_search_patterns(search_results):
    """Analyze search patterns and behavior from results"""
    patterns = {
        'question_success_rates': {},
        'category_performance': {},
        'response_time_by_type': {},
        'result_count_patterns': {}
    }
    
    # Group by question types
    by_question_type = {}
    by_category = {}
    
    for result in search_results:
        test_context = result.get('test_case_context', {})
        question_type = test_context.get('question_type', 'Unknown')
        category = test_context.get('original_product_category', 'Unknown')
        
        # Group by question type
        if question_type not in by_question_type:
            by_question_type[question_type] = []
        by_question_type[question_type].append(result)
        
        # Group by category
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(result)
    
    # Analyze success rates by question type
    for q_type, results in by_question_type.items():
        successful = len([r for r in results if r.get('success', False)])
        total = len(results)
        patterns['question_success_rates'][q_type] = {
            'success_rate': successful / total * 100 if total > 0 else 0,
            'total_queries': total,
            'avg_response_time': statistics.mean([r.get('response_time_seconds', 0) for r in results]) if results else 0,
            'avg_result_count': statistics.mean([r.get('result_count', 0) for r in results]) if results else 0
        }
    
    # Analyze performance by category
    for category, results in by_category.items():
        successful = len([r for r in results if r.get('success', False)])
        total = len(results)
        patterns['category_performance'][category] = {
            'success_rate': successful / total * 100 if total > 0 else 0,
            'total_queries': total,
            'avg_response_time': statistics.mean([r.get('response_time_seconds', 0) for r in results]) if results else 0,
            'avg_result_count': statistics.mean([r.get('result_count', 0) for r in results]) if results else 0
        }
    
    return patterns

def print_comprehensive_analysis_report(analysis_results):
    """Print a comprehensive analysis report with all metrics"""
    
    print("\n📋 COMPREHENSIVE SEARCH ENGINE EVALUATION REPORT")
    print("="*60)
    
    # File Information
    file_info = analysis_results['file_info']
    print(f"\n📁 FILE INFORMATION:")
    print(f"   File: {file_info['file_path']}")
    print(f"   Size: {file_info['file_size_mb']} MB")
    print(f"   Total lines: {file_info['total_lines']}")
    print(f"   Valid results: {file_info['valid_results']}")
    print(f"   Parsing success: {file_info['parsing_success_rate']:.1f}%")
    
    # Search Performance
    perf = analysis_results['search_performance']
    print(f"\n⚡ SEARCH PERFORMANCE METRICS:")
    print(f"   Total searches: {perf['total_searches']}")
    print(f"   Success rate: {perf['success_rate']:.1f}%")
    print(f"   Average response time: {perf['avg_response_time_ms']:.1f}ms")
    print(f"   Median response time: {perf['median_response_time_ms']:.1f}ms")
    print(f"   95th percentile: {perf['p95_response_time_ms']:.1f}ms")
    print(f"   99th percentile: {perf['p99_response_time_ms']:.1f}ms")
    print(f"   Status codes: {perf['status_code_distribution']}")
    
    # Coverage Metrics
    coverage = analysis_results['coverage_metrics']
    print(f"\n📊 COVERAGE METRICS:")
    print(f"   Total results returned: {coverage['total_results_returned']}")
    print(f"   Average results per query: {coverage['avg_results_per_query']:.2f}")
    print(f"   Zero results rate: {coverage['zero_results_rate']:.1f}%")
    print(f"   Max results (single query): {coverage['max_results_single_query']}")
    
    # Relevance Metrics
    relevance = analysis_results['relevance_metrics']
    print(f"\n🎯 RELEVANCE METRICS:")
    
    print(f"\n   📏 PRECISION@K (How many retrieved results are relevant):")
    for metric, value in relevance['precision_at_k'].items():
        print(f"      {metric}: {value:.3f}")
    
    print(f"\n   📏 RECALL@K (How many relevant results are retrieved):")
    for metric, value in relevance['recall_at_k'].items():
        print(f"      {metric}: {value:.3f}")
    
    print(f"\n   📏 F1-SCORE@K (Harmonic mean of Precision and Recall):")
    for metric, value in relevance['f1_score_at_k'].items():
        print(f"      {metric}: {value:.3f}")
    
    print(f"\n   📏 RANKING QUALITY:")
    print(f"      MAP (Mean Average Precision): {relevance['map_score']:.3f}")
    print(f"      MRR (Mean Reciprocal Rank): {relevance['mrr_score']:.3f}")
    
    for metric, value in relevance['ndcg_at_k'].items():
        print(f"      {metric}: {value:.3f}")
    
    # Relevance Analysis with new approach
    rel_analysis = relevance['relevance_analysis']
    print(f"\n   📈 RELEVANCE ANALYSIS:")
    print(f"      Queries analyzed: {rel_analysis['total_queries_analyzed']}")
    print(f"      Relevant items found: {rel_analysis['total_relevant_items_found']}")
    print(f"      Exact matches: {rel_analysis['exact_name_matches']}")
    print(f"      Average relevance per query: {rel_analysis['average_relevance_per_query']:.1f}")
    print(f"      Search effectiveness: {rel_analysis['search_effectiveness']}")
    
    # Question Type Relevance Breakdown
    question_type_breakdown = relevance.get('question_type_breakdown', {})
    if question_type_breakdown:
        print(f"\n   🔍 RELEVANCE METRICS BY QUESTION TYPE:")
        for q_type, metrics in question_type_breakdown.items():
            print(f"\n      {q_type.upper()} ({metrics['query_count']} queries):")
            print(f"         Precision@1: {metrics['precision_at_k']['P@1']:.3f}, P@10: {metrics['precision_at_k']['P@10']:.3f}")
            print(f"         Recall@1: {metrics['recall_at_k']['R@1']:.3f}, R@10: {metrics['recall_at_k']['R@10']:.3f}")
            print(f"         F1@10: {metrics['f1_score_at_k']['F1@10']:.3f}")
            print(f"         MAP: {metrics['map_score']:.3f}, MRR: {metrics['mrr_score']:.3f}, NDCG@10: {metrics['ndcg_at_k']['NDCG@10']:.3f}")
            rel_stats = metrics['relevance_analysis']
            print(f"         Found {rel_stats['total_relevant_items_found']} relevant items, avg {rel_stats['average_relevance_per_query']:.1f} per query")
        print(f"")  # Add spacing
    
    # Detailed Analysis
    detailed = analysis_results['detailed_analysis']
    print(f"\n📋 DETAILED ANALYSIS:")
    
    print(f"\n   Question Type Performance:")
    search_patterns = detailed.get('search_patterns', {})
    question_success_rates = search_patterns.get('question_success_rates', {})
    
    if question_success_rates:
        for q_type, stats in question_success_rates.items():
            print(f"      {q_type}: {stats['success_rate']:.1f}% success, "
                  f"{stats['avg_result_count']:.1f} avg results, "
                  f"{stats['avg_response_time']:.2f}s avg time")
    else:
        print("      No question type data available")
    
    print(f"\n   Category Performance:")
    category_performance = search_patterns.get('category_performance', {})
    
    if category_performance:
        for category, stats in category_performance.items():
            print(f"      {category}: {stats['success_rate']:.1f}% success, "
                  f"{stats['avg_result_count']:.1f} avg results")
    else:
        print("      No category performance data available")
    
    # Metric Calculation Explanations
    print(f"\n📚 METRIC CALCULATION EXPLANATIONS:")
    explanations = relevance['calculation_explanations']
    for metric, explanation in explanations.items():
        print(f"   {metric.upper()}: {explanation}")

def save_analysis_results(analysis_results, output_file):
    """Save comprehensive analysis results to JSON file with executive summary"""
    try:
        # Extract key metrics for executive summary
        file_info = analysis_results.get('file_info', {})
        performance = analysis_results.get('search_performance', {})
        relevance = analysis_results.get('relevance_metrics', {})
        coverage = analysis_results.get('coverage_metrics', {})
        detailed = analysis_results.get('detailed_analysis', {})
        
        # Create executive summary
        executive_summary = {
            "title": "Comprehensive Search Engine Evaluation Results",
            "analysis_overview": {
                "file_analyzed": file_info.get('file_path', file_info.get('file_name', 'Unknown')),
                "total_searches": f"{file_info.get('valid_results', 0)} queries",
                "success_rate": f"{performance.get('success_rate', 0):.1f}% (all searches completed successfully)" if performance.get('success_rate', 0) >= 99 else f"{performance.get('success_rate', 0):.1f}%",
                "average_response_time": f"{performance.get('avg_response_time_ms', 0)/1000:.1f} seconds per query"
            },
            "key_performance_metrics": {
                "1_relevance_metrics": {
                    "description": "Primary Quality Indicators",
                    "precision_at_k": {
                        "description": "Measures accuracy of top K results",
                        "P@1": f"{relevance.get('precision_at_k', {}).get('P@1', 0):.3f} ({relevance.get('precision_at_k', {}).get('P@1', 0)*100:.1f}% of top results are relevant)",
                        "P@10": f"{relevance.get('precision_at_k', {}).get('P@10', 0):.3f} ({relevance.get('precision_at_k', {}).get('P@10', 0)*100:.1f}% of top 10 results are relevant)"
                    },
                    "recall_at_k": {
                        "description": "Measures completeness of retrieval",
                        "R@1": f"{relevance.get('recall_at_k', {}).get('R@1', 0):.3f} (finds {relevance.get('recall_at_k', {}).get('R@1', 0)*100:.1f}% of all relevant items in top 1)",
                        "R@10": f"{relevance.get('recall_at_k', {}).get('R@10', 0):.3f} (finds {relevance.get('recall_at_k', {}).get('R@10', 0)*100:.1f}% - {'indicates some false positives' if relevance.get('recall_at_k', {}).get('R@10', 0) > 1 else 'good recall'})"
                    },
                    "f1_score_at_k": {
                        "description": "Balanced measure of precision and recall",
                        "F1@10": f"{relevance.get('f1_score_at_k', {}).get('F1@10', 0):.3f} ({relevance.get('f1_score_at_k', {}).get('F1@10', 0)*100:.1f}% overall relevance quality)"
                    }
                },
                "2_ranking_quality_metrics": {
                    "MAP": f"{relevance.get('map_score', 0):.3f} - {'Good' if relevance.get('map_score', 0) > 0.4 else 'Fair' if relevance.get('map_score', 0) > 0.2 else 'Poor'} ranking of relevant results",
                    "MRR": f"{relevance.get('mrr_score', 0):.3f} - First relevant result typically at position ~{(1/relevance.get('mrr_score', 0.001)):.1f}" if relevance.get('mrr_score', 0) > 0 else "0.000 - No relevant results found",
                    "NDCG@10": f"{relevance.get('ndcg_at_k', {}).get('NDCG@10', 0):.3f} - {'Good' if relevance.get('ndcg_at_k', {}).get('NDCG@10', 0) > 0.5 else 'Decent' if relevance.get('ndcg_at_k', {}).get('NDCG@10', 0) > 0.3 else 'Poor'} ranking quality considering relevance grades"
                },
                "3_coverage_and_performance": {
                    "zero_results_rate": f"{coverage.get('zero_results_rate', 0):.1f}% ({int(coverage.get('zero_results_count', 0))} out of {file_info.get('valid_results', 0)} queries returned no results)",
                    "average_results_per_query": f"{coverage.get('avg_results_per_query', 0):.2f} products found",
                    "response_time_analysis": f"P95 = {performance.get('p95_response_time_ms', 0)/1000:.1f} seconds ({'some queries are slow' if performance.get('p95_response_time_ms', 0)/1000 > 5 else 'good performance'})"
                }
            },
            "metric_calculations": {
                "precision_at_k": "Precision@K = (Number of relevant items in top K results) / K",
                "recall_at_k": "Recall@K = (Number of relevant items in top K results) / (Total relevant items available)",
                "f1_score_at_k": "F1@K = 2 × (Precision@K × Recall@K) / (Precision@K + Recall@K)",
                "map": "MAP = Average of precision scores at each relevant document position",
                "ndcg_at_k": "NDCG@K = DCG@K / IDCG@K, where DCG considers relevance scores and position discounting",
                "mrr": "MRR = Average of reciprocal ranks of first relevant result (1/rank)"
            },
            "question_type_performance": {},
            "category_performance": {}
        }
        
        # Add question type performance
        search_patterns = detailed.get('search_patterns', {})
        question_success_rates = search_patterns.get('question_success_rates', {})
        
        for q_type, stats in question_success_rates.items():
            performance_desc = "Most precise" if stats['avg_result_count'] < 1 else "Highest recall" if stats['avg_result_count'] > 7 else "Balanced performance"
            executive_summary["question_type_performance"][q_type] = f"{performance_desc} ({stats['avg_result_count']:.1f} avg results, fastest at {stats['avg_response_time']:.2f}s)" if q_type == "Exact word" else f"{performance_desc} ({stats['avg_result_count']:.1f} avg results, {stats['avg_response_time']:.2f}s)"
        
        # Add category performance insights
        category_performance = search_patterns.get('category_performance', {})
        
        for category, stats in category_performance.items():
            if category and category != 'Unknown':
                insight = ""
                if stats['avg_result_count'] > 10:
                    insight = "possibly too broad"
                elif stats['avg_result_count'] == 0:
                    insight = "potential coverage gap"
                elif stats['avg_result_count'] < 1:
                    insight = "may need improvement"
                else:
                    insight = "good coverage"
                
                executive_summary["category_performance"][category] = f"Highest result count ({stats['avg_result_count']:.1f} avg) - {insight}" if stats['avg_result_count'] > 10 else f"Zero results on average - {insight}" if stats['avg_result_count'] == 0 else f"Low results ({stats['avg_result_count']:.1f} avg) - {insight}" if stats['avg_result_count'] < 1 else f"Good results ({stats['avg_result_count']:.1f} avg) - {insight}"
        
        # Add detailed question type relevance metrics
        question_type_breakdown = relevance.get('question_type_breakdown', {})
        if question_type_breakdown:
            executive_summary["detailed_question_type_relevance"] = {}
            for q_type, metrics in question_type_breakdown.items():
                executive_summary["detailed_question_type_relevance"][q_type] = {
                    "query_count": metrics.get('query_count', 0),
                    "precision_metrics": {
                        "P@1": f"{metrics.get('precision_at_k', {}).get('P@1', 0):.3f}",
                        "P@3": f"{metrics.get('precision_at_k', {}).get('P@3', 0):.3f}",
                        "P@5": f"{metrics.get('precision_at_k', {}).get('P@5', 0):.3f}",
                        "P@10": f"{metrics.get('precision_at_k', {}).get('P@10', 0):.3f}"
                    },
                    "recall_metrics": {
                        "R@1": f"{metrics.get('recall_at_k', {}).get('R@1', 0):.3f}",
                        "R@3": f"{metrics.get('recall_at_k', {}).get('R@3', 0):.3f}",
                        "R@5": f"{metrics.get('recall_at_k', {}).get('R@5', 0):.3f}",
                        "R@10": f"{metrics.get('recall_at_k', {}).get('R@10', 0):.3f}"
                    },
                    "f1_metrics": {
                        "F1@1": f"{metrics.get('f1_score_at_k', {}).get('F1@1', 0):.3f}",
                        "F1@3": f"{metrics.get('f1_score_at_k', {}).get('F1@3', 0):.3f}",
                        "F1@5": f"{metrics.get('f1_score_at_k', {}).get('F1@5', 0):.3f}",
                        "F1@10": f"{metrics.get('f1_score_at_k', {}).get('F1@10', 0):.3f}"
                    },
                    "ranking_quality": {
                        "MAP": f"{metrics.get('map_score', 0):.3f}",
                        "MRR": f"{metrics.get('mrr_score', 0):.3f}",
                        "NDCG@1": f"{metrics.get('ndcg_at_k', {}).get('NDCG@1', 0):.3f}",
                        "NDCG@3": f"{metrics.get('ndcg_at_k', {}).get('NDCG@3', 0):.3f}",
                        "NDCG@5": f"{metrics.get('ndcg_at_k', {}).get('NDCG@5', 0):.3f}",
                        "NDCG@10": f"{metrics.get('ndcg_at_k', {}).get('NDCG@10', 0):.3f}"
                    },
                    "relevance_summary": {
                        "found_items": metrics.get('relevance_analysis', {}).get('total_relevant_items_found', 0),
                        "exact_matches": metrics.get('relevance_analysis', {}).get('exact_name_matches', 0),
                        "avg_relevance_per_query": f"{metrics.get('relevance_analysis', {}).get('average_relevance_per_query', 0):.1f}",
                        "search_effectiveness": metrics.get('relevance_analysis', {}).get('search_effectiveness', "No data")
                    }
                }
        
        # Add timestamp and metadata
        analysis_results['analysis_metadata'] = {
            'generated_at': datetime.now().isoformat(),
            'analysis_type': 'comprehensive_jsonl_evaluation',
            'metrics_included': [
                'precision_at_k', 'recall_at_k', 'f1_score_at_k', 
                'map_score', 'ndcg_at_k', 'mrr_score',
                'response_times', 'coverage_metrics'
            ]
        }
        
        # Structure the final output with executive summary first
        final_output = {
            "executive_summary": executive_summary,
            "detailed_analysis": analysis_results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Comprehensive analysis saved to: {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error saving analysis results: {e}")
        import traceback
        traceback.print_exc()
        return False


def analyze_jsonl_comprehensive(jsonl_file_path):
    """
    Comprehensive analysis of JSONL search results file
    Calculates all standard search engine evaluation metrics
    """
    print(f"🔍 Comprehensive Analysis of: {jsonl_file_path}")
    print("="*80)
    
    # Storage for analysis data
    search_results = []
    relevance_data = []
    performance_data = []
    coverage_data = []
    
    # Load and parse JSONL data
    try:
        with open(jsonl_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    result = json.loads(line)
                    search_results.append(result)
                except json.JSONDecodeError as e:
                    print(f"⚠️ Error parsing line {line_num}: {e}")
                    continue
        
        print(f"📊 Loaded {len(search_results)} search results")
        
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return
    
    if not search_results:
        print("❌ No valid search results found")
        return
    
    # Analyze each search result
    for result in search_results:
        # Extract key information
        success = result.get('success', False)
        response_time = result.get('response_time_seconds', 0.0)
        result_count = result.get('result_count', 0)
        
        # Test case context
        test_context = result.get('test_case_context', {})
        original_product_name = test_context.get('original_product_name', '').lower()
        original_category = test_context.get('original_product_category', '').lower()
        question = test_context.get('question', '')
        question_type = test_context.get('question_type', '')
        
        # API response products
        api_products = result.get('api_response_products', {})
        found_products = api_products.get('product_names_found', [])
        
        # Detailed query results
        query_result = result.get('response_data', {}).get('queryResult', {})
        detailed_results = query_result.get('result', []) if query_result else []
        
        # Performance tracking
        performance_data.append({
            'response_time': response_time,
            'success': success,
            'result_count': result_count,
            'question_type': question_type
        })
        
        # Coverage tracking
        coverage_data.append({
            'success': success,
            'has_results': result_count > 0,
            'question_type': question_type
        })
        
        # Relevance analysis
        relevance_scores = []
        retrieved_items = []
        
        # Process detailed results for relevance scoring
        for item in detailed_results:
            product_name = item.get('cr4a3_productname', '').lower()
            product_desc = item.get('description', '').lower()
            product_price = item.get('price', 0.0)
            
            retrieved_items.append({
                'name': product_name,
                'description': product_desc,
                'price': product_price
            })
            
            # Calculate relevance score (0-3 scale)
            relevance_score = calculate_detailed_relevance_score(
                question_type, question, original_product_name, original_category,
                product_name, product_desc, product_price, test_context.get('original_product_price', 0.0)
            )
            
            relevance_scores.append(relevance_score)
        
        # Store relevance data for metric calculations
        relevance_data.append({
            'question': question,
            'question_type': question_type,
            'expected_product': original_product_name,
            'expected_category': original_category,
            'retrieved_items': retrieved_items,
            'relevance_scores': relevance_scores,
            'result_count': len(retrieved_items)
        })
    
    # Calculate comprehensive metrics
    print("\n🎯 CALCULATING SEARCH ENGINE METRICS")
    print("="*80)
    
    # 1. RELEVANCE METRICS
    print("\n📊 1. RELEVANCE METRICS")
    print("-"*40)
    
    k_values = [1, 3, 5, 10, 20]
    relevance_metrics = {}
    
    for k in k_values:
        precision_scores = []
        recall_scores = []
        f1_scores = []
        
        for rel_data in relevance_data:
            if not rel_data['retrieved_items']:
                precision_scores.append(0.0)
                recall_scores.append(0.0)
                f1_scores.append(0.0)
                continue
            
            # Calculate Precision@K
            relevant_at_k = sum(1 for score in rel_data['relevance_scores'][:k] if score >= 2)
            total_at_k = min(k, len(rel_data['relevance_scores']))
            precision_k = relevant_at_k / max(total_at_k, 1)
            precision_scores.append(precision_k)
            
            # Calculate Recall@K
            total_relevant = sum(1 for score in rel_data['relevance_scores'] if score >= 2)
            recall_k = relevant_at_k / max(total_relevant, 1) if total_relevant > 0 else 0.0
            recall_scores.append(recall_k)
            
            # Calculate F1@K
            if precision_k + recall_k > 0:
                f1_k = 2 * (precision_k * recall_k) / (precision_k + recall_k)
            else:
                f1_k = 0.0
            f1_scores.append(f1_k)
        
        # Store averages
        relevance_metrics[f'precision_at_{k}'] = sum(precision_scores) / len(precision_scores)
        relevance_metrics[f'recall_at_{k}'] = sum(recall_scores) / len(recall_scores)
        relevance_metrics[f'f1_at_{k}'] = sum(f1_scores) / len(f1_scores)
        
        print(f"Precision@{k:2d}: {relevance_metrics[f'precision_at_{k}']:.4f}")
        print(f"Recall@{k:2d}:    {relevance_metrics[f'recall_at_{k}']:.4f}")
        print(f"F1@{k:2d}:        {relevance_metrics[f'f1_at_{k}']:.4f}")
        print()
    
    # 2. RANKING QUALITY METRICS
    print("\n📈 2. RANKING QUALITY METRICS")
    print("-"*40)
    
    # Mean Average Precision (MAP)
    ap_scores = []
    for rel_data in relevance_data:
        if not rel_data['retrieved_items']:
            ap_scores.append(0.0)
            continue
        
        relevant_count = 0
        precision_sum = 0.0
        
        for i, score in enumerate(rel_data['relevance_scores']):
            if score >= 2:  # Relevant threshold
                relevant_count += 1
                precision_at_i = relevant_count / (i + 1)
                precision_sum += precision_at_i
        
        total_relevant = sum(1 for score in rel_data['relevance_scores'] if score >= 2)
        avg_precision = precision_sum / max(total_relevant, 1) if total_relevant > 0 else 0.0
        ap_scores.append(avg_precision)
    
    map_score = sum(ap_scores) / len(ap_scores)
    print(f"Mean Average Precision (MAP): {map_score:.4f}")
    
    # NDCG@K calculation
    import math
    
    def dcg_at_k(relevance_scores, k):
        return sum(score / math.log2(i + 2) for i, score in enumerate(relevance_scores[:k]))
    
    def ndcg_at_k(relevance_scores, k):
        dcg = dcg_at_k(relevance_scores, k)
        idcg = dcg_at_k(sorted(relevance_scores, reverse=True), k)
        return dcg / idcg if idcg > 0 else 0.0
    
    for k in [1, 3, 5, 10]:
        ndcg_scores = []
        for rel_data in relevance_data:
            if rel_data['retrieved_items']:
                ndcg = ndcg_at_k(rel_data['relevance_scores'], k)
                ndcg_scores.append(ndcg)
            else:
                ndcg_scores.append(0.0)
        
        avg_ndcg = sum(ndcg_scores) / len(ndcg_scores)
        print(f"NDCG@{k:2d}:                     {avg_ndcg:.4f}")
    
    # Mean Reciprocal Rank (MRR)
    rr_scores = []
    for rel_data in relevance_data:
        if not rel_data['retrieved_items']:
            rr_scores.append(0.0)
            continue
        
        for i, score in enumerate(rel_data['relevance_scores']):
            if score >= 2:  # First relevant result
                rr_scores.append(1.0 / (i + 1))
                break
        else:
            rr_scores.append(0.0)  # No relevant results found
    
    mrr_score = sum(rr_scores) / len(rr_scores)
    print(f"Mean Reciprocal Rank (MRR):  {mrr_score:.4f}")
    
    # 3. PERFORMANCE METRICS
    print("\n⚡ 3. PERFORMANCE METRICS")
    print("-"*40)
    
    response_times = [p['response_time'] for p in performance_data if p['success']]
    if response_times:
        avg_response_time = sum(response_times) / len(response_times)
        min_response_time = min(response_times)
        max_response_time = max(response_times)
        
        # Calculate percentiles
        sorted_times = sorted(response_times)
        p50 = sorted_times[len(sorted_times) // 2]
        p95 = sorted_times[int(len(sorted_times) * 0.95)]
        p99 = sorted_times[int(len(sorted_times) * 0.99)]
        
        print(f"Average Response Time:  {avg_response_time:.3f} seconds")
        print(f"Median (P50):          {p50:.3f} seconds")
        print(f"P95 Response Time:     {p95:.3f} seconds")
        print(f"P99 Response Time:     {p99:.3f} seconds")
        print(f"Min Response Time:     {min_response_time:.3f} seconds")
        print(f"Max Response Time:     {max_response_time:.3f} seconds")
    
    success_rate = sum(1 for p in performance_data if p['success']) / len(performance_data)
    print(f"Success Rate:          {success_rate:.1%}")
    
    # 4. COVERAGE METRICS
    print("\n📊 4. COVERAGE METRICS")
    print("-"*40)
    
    query_success_rate = sum(1 for c in coverage_data if c['success']) / len(coverage_data)
    zero_results_rate = sum(1 for c in coverage_data if not c['has_results']) / len(coverage_data)
    avg_results_per_query = sum(p['result_count'] for p in performance_data) / len(performance_data)
    
    print(f"Query Success Rate:    {query_success_rate:.1%}")
    print(f"Zero Results Rate:     {zero_results_rate:.1%}")
    print(f"Avg Results per Query: {avg_results_per_query:.2f}")
    
    # 5. QUESTION TYPE ANALYSIS
    print("\n📋 5. QUESTION TYPE BREAKDOWN")
    print("-"*40)
    
    question_type_stats = defaultdict(lambda: {'count': 0, 'success': 0, 'avg_results': 0})
    
    for perf in performance_data:
        qtype = perf['question_type']
        question_type_stats[qtype]['count'] += 1
        if perf['success']:
            question_type_stats[qtype]['success'] += 1
        question_type_stats[qtype]['avg_results'] += perf['result_count']
    
    for qtype, stats in question_type_stats.items():
        success_rate_type = stats['success'] / stats['count']
        avg_results_type = stats['avg_results'] / stats['count']
        print(f"{qtype:15s}: {stats['count']:3d} queries, {success_rate_type:.1%} success, {avg_results_type:.1f} avg results")
    
    # 6. SAVE DETAILED ANALYSIS
    print("\n💾 6. SAVING ANALYSIS RESULTS")
    print("-"*40)
    
    analysis_results = {
        'metadata': {
            'source_file': jsonl_file_path,
            'analysis_timestamp': datetime.now().isoformat(),
            'total_queries': len(search_results),
            'analysis_type': 'comprehensive_search_evaluation'
        },
        'relevance_metrics': relevance_metrics,
        'ranking_metrics': {
            'mean_average_precision': map_score,
            'mean_reciprocal_rank': mrr_score
        },
        'performance_metrics': {
            'average_response_time': avg_response_time if response_times else 0,
            'median_response_time': p50 if response_times else 0,
            'p95_response_time': p95 if response_times else 0,
            'p99_response_time': p99 if response_times else 0,
            'success_rate': success_rate
        },
        'coverage_metrics': {
            'query_success_rate': query_success_rate,
            'zero_results_rate': zero_results_rate,
            'average_results_per_query': avg_results_per_query
        },
        'question_type_analysis': dict(question_type_stats)
    }
    
    # Save analysis results
    output_file = jsonl_file_path.replace('.jsonl', '_comprehensive_analysis.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_results, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Analysis saved to: {output_file}")
    
    print("\n🎯 METRIC CALCULATION EXPLANATIONS")
    print("="*80)
    print("""
📊 RELEVANCE METRICS:
• Precision@K = Relevant items in top K / K
• Recall@K = Relevant items in top K / Total relevant items  
• F1@K = 2 × (Precision × Recall) / (Precision + Recall)

📈 RANKING QUALITY:
• MAP = Average of precision scores at each relevant document position
• NDCG@K = DCG@K / IDCG@K (accounts for position with logarithmic discount)
• MRR = Average of 1/rank for first relevant result

⚡ PERFORMANCE:
• Response times in seconds (avg, median, P95, P99)
• Success rate = Successful queries / Total queries

📊 COVERAGE:
• Query success rate = Queries with successful response / Total
• Zero results rate = Queries with no results / Total
• Average results per query

📋 RELEVANCE SCORING (0-3 scale):
• 3 = Perfect match (exact product name/very high relevance)
• 2 = Good match (relevant product or category)
• 1 = Partial match (some relevance)
• 0 = No match (irrelevant)
""")


def calculate_detailed_relevance_score(question_type, question, expected_product, expected_category, 
                                     found_product, found_desc, found_price, expected_price):
    """
    Calculate detailed relevance score (0-3) based on multiple factors
    """
    score = 0
    
    # Exact product name match
    if expected_product and found_product:
        if expected_product == found_product:
            return 3  # Perfect match
        elif expected_product in found_product or found_product in expected_product:
            score += 2  # Very good match
        elif any(word in found_product for word in expected_product.split() if len(word) > 3):
            score += 1  # Partial match
    
    # Category relevance
    if expected_category and found_desc:
        if expected_category in found_desc.lower():
            score += 1
    
    # Question type specific scoring
    if question_type == "Price range" and found_price > 0 and expected_price > 0:
        price_diff_ratio = abs(found_price - expected_price) / max(expected_price, 1)
        if price_diff_ratio < 0.1:  # Within 10%
            score += 1
        elif price_diff_ratio < 0.3:  # Within 30%
            score += 0.5
    
    # Question text relevance
    if question and found_desc:
        question_words = set(question.lower().split())
        desc_words = set(found_desc.lower().split())
        common_words = question_words.intersection(desc_words)
        if len(common_words) >= 2:
            score += 0.5
    
    return min(3, score)  # Cap at 3


def main():
    """Main function with enhanced functionality"""
    
    print("🔬 Enhanced Search Engine Evaluation Tool")
    print("="*50)
    print("Choose evaluation mode:")
    print("1. Comprehensive Live Evaluation (Execute API calls with test cases)")
    print("2. Legacy JSONL Analysis (Analyze existing JSONL files)")
    print("3. Comprehensive JSONL Analysis (Advanced IR metrics)")
    print()
    
    if len(sys.argv) > 1:
        # Command line argument provided
        arg = sys.argv[1]
        
        if arg.lower() in ['live', 'comprehensive', '1']:
            mode = 'live'
        elif arg.lower() in ['3', 'comp']:
            mode = 'comprehensive'
        elif arg.endswith('.jsonl'):
            mode = 'comprehensive'  # Default to comprehensive for JSONL files
            filename = arg
        else:
            mode = 'live'  # Default to live evaluation
    else:
        # Interactive mode selection
        choice = input("Enter your choice (1 for Live, 2 for Legacy, 3 for Comprehensive, or filename.jsonl): ").strip()
        
        if choice in ['1', 'live', 'comprehensive']:
            mode = 'live'
        elif choice in ['2', 'legacy']:
            mode = 'legacy'
            filename = input("Enter JSONL filename: ").strip()
        elif choice in ['3', 'comp', 'comprehensive']:
            mode = 'comprehensive'
            filename = input("Enter JSONL filename for comprehensive analysis: ").strip()
        elif choice.endswith('.jsonl'):
            mode = 'legacy'
            filename = choice
        else:
            mode = 'live'  # Default
    
    if mode == 'live':
        print("\n🚀 Running Comprehensive Live Evaluation...")
        print("This will:")
        print("• Load test cases from test_case/ directory")
        print("• Execute live API calls to Dataverse search")
        print("• Calculate comprehensive IR metrics (Precision, Recall, F1, MAP, NDCG, MRR)")
        print("• Analyze response times and coverage")
        print()
        
        # Optional parameters
        max_cases = None
        test_limit = input("Limit test cases for testing? (Enter number or press Enter for all): ").strip()
        if test_limit.isdigit():
            max_cases = int(test_limit)
            print(f"✅ Will process first {max_cases} test cases")
        
        # Run comprehensive evaluation
        evaluator = run_comprehensive_search_evaluation(
            test_case_dir="test_case",
            max_test_cases=max_cases
        )
        
        if evaluator:
            print("\n🎉 Live evaluation completed successfully!")
        else:
            print("\n❌ Live evaluation failed!")
            
    elif mode == 'legacy':
        print(f"\n📁 Running Legacy JSONL Analysis on: {filename}")
        
        # Ensure .jsonl extension
        if not filename.endswith('.jsonl'):
            filename += '.jsonl'
        
        # Run legacy analysis
        results = analyze_jsonl_file(filename)
        
        if results:
            print(f"\n✅ Legacy analysis completed for '{filename}'")
        else:
            print(f"\n❌ Legacy analysis failed for '{filename}'")
            
    elif mode == 'comprehensive':
        print(f"\n🎯 Running Comprehensive JSONL Analysis on: {filename}")
        
        # Ensure .jsonl extension
        if not filename.endswith('.jsonl'):
            filename += '.jsonl'
        
        # Add path if not absolute
        if not os.path.isabs(filename) and not os.path.exists(filename):
            filename = os.path.join("test_case_analysis", filename)
        
        if not os.path.exists(filename):
            print(f"❌ File not found: {filename}")
            return
        
        # Run comprehensive analysis (use the function that saves results properly)
        results = analyze_existing_jsonl_results(filename)
        if results:
            print(f"\n✅ Comprehensive analysis completed for '{filename}'")
        else:
            print(f"\n❌ Comprehensive analysis failed for '{filename}'")

if __name__ == "__main__":
    main()
