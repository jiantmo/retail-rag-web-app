#!/usr/bin/env python3
"""
Enhanced Search Results Analysis Script
Uses improved relevance scoring logic for better evaluation of search engine performance
"""

import json
import os
import sys
import statistics
import math
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List, Any, Tuple
from unified_relevance_scorer import UnifiedRelevanceScorer
from simplified_relevance_scorer import SimplifiedRelevanceScorer

class EnhancedSearchAnalyzer:
    """
    Enhanced search analyzer with improved relevance scoring based on question types:
    
    1. Exact word – Result is relevant if it contains the exact word
    2. Category – Result is relevant if it belongs to the same category  
    3. Category + Attribute – Result is relevant if same category AND attribute value matches
    4. Category + Price – Result is relevant if same category AND price falls within range
    5. Description – Result is relevant if semantically related to the question
    """
    
    def __init__(self):
        self.relevance_scorer = SimplifiedRelevanceScorer()
        
    def analyze_jsonl_results(self, jsonl_file_path: str) -> Dict[str, Any]:
        """
        Analyze JSONL search results with improved relevance scoring
        
        Args:
            jsonl_file_path: Path to the JSONL file containing search results
            
        Returns:
            Dictionary containing comprehensive analysis results
        """
        print(f"🔬 Enhanced Analysis of: {jsonl_file_path}")
        print("=" * 80)
        
        # Load search results
        search_results = self._load_jsonl_file(jsonl_file_path)
        if not search_results:
            return None
        
        print(f"📊 Loaded {len(search_results)} search results")
        
        # Calculate metrics with improved scoring
        analysis_results = {
            'file_info': self._get_file_info(jsonl_file_path, search_results),
            'search_performance': self._calculate_performance_metrics(search_results),
            'relevance_metrics': self._calculate_relevance_metrics(search_results),
            'coverage_metrics': self._calculate_coverage_metrics(search_results),
            'detailed_analysis': self._calculate_detailed_analysis(search_results),
            'analysis_metadata': {
                'generated_at': datetime.now().isoformat(),
                'analysis_type': 'enhanced_search_evaluation_with_improved_relevance',
                'relevance_scoring': 'question_type_specific',
                'metrics_included': [
                    'precision_at_k', 'recall_at_k', 'f1_score_at_k', 
                    'map_score', 'ndcg_at_k', 'mrr_score',
                    'response_times', 'coverage_metrics'
                ]
            }
        }
        
        # Generate report
        self._print_analysis_report(analysis_results)
        
        # Save results
        output_file = jsonl_file_path.replace('.jsonl', '_enhanced_analysis.json')
        self._save_analysis_results(analysis_results, output_file)
        
        return analysis_results
    
    def _load_jsonl_file(self, file_path: str) -> List[Dict]:
        """Load and parse JSONL file"""
        search_results = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
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
        
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            return []
        
        return search_results
    
    def _get_file_info(self, file_path: str, search_results: List[Dict]) -> Dict[str, Any]:
        """Get file information and basic statistics"""
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        return {
            'file_path': file_path,
            'file_size_mb': round(file_size_mb, 2),
            'total_lines': len(search_results),
            'valid_results': len(search_results),
            'parsing_success_rate': 100.0
        }
    
    def _calculate_performance_metrics(self, search_results: List[Dict]) -> Dict[str, Any]:
        """Calculate response time and performance metrics"""
        successful_searches = [r for r in search_results if r.get('success', False)]
        response_times = [r.get('response_time_seconds', 0) for r in search_results]
        status_codes = [r.get('status_code') for r in search_results if r.get('status_code')]
        
        return {
            'total_searches': len(search_results),
            'successful_searches': len(successful_searches),
            'failed_searches': len(search_results) - len(successful_searches),
            'success_rate': len(successful_searches) / len(search_results) * 100 if search_results else 0,
            'avg_response_time_ms': statistics.mean(response_times) * 1000 if response_times else 0,
            'median_response_time_ms': statistics.median(response_times) * 1000 if response_times else 0,
            'p95_response_time_ms': sorted(response_times)[int(len(response_times) * 0.95)] * 1000 if response_times else 0,
            'p99_response_time_ms': sorted(response_times)[int(len(response_times) * 0.99)] * 1000 if response_times else 0,
            'min_response_time_ms': min(response_times) * 1000 if response_times else 0,
            'max_response_time_ms': max(response_times) * 1000 if response_times else 0,
            'status_code_distribution': dict(Counter(status_codes))
        }
    
    def _calculate_relevance_metrics(self, search_results: List[Dict]) -> Dict[str, Any]:
        """Calculate comprehensive relevance metrics using improved scoring"""
        print("\n🎯 Calculating Enhanced Relevance Metrics...")
        
        # K values for evaluation
        k_values = [1, 3, 5, 10]
        
        # Store metrics for different K values
        precision_metrics = {k: [] for k in k_values}
        recall_metrics = {k: [] for k in k_values}
        f1_metrics = {k: [] for k in k_values}
        ndcg_metrics = {k: [] for k in k_values}
        map_scores = []
        mrr_scores = []
        
        # Question type specific metrics
        question_type_metrics = defaultdict(lambda: {
            'precision': {k: [] for k in k_values},
            'recall': {k: [] for k in k_values},
            'f1': {k: [] for k in k_values},
            'ndcg': {k: [] for k in k_values},
            'map': [],
            'mrr': [],
            'query_count': 0,
            'total_relevant_found': 0,
            'exact_matches': 0
        })
        
        total_relevant_items = 0
        exact_name_matches = 0
        
        # Process each search result
        for result in search_results:
            if not result.get('success', False):
                continue
            
            # Extract test case context
            test_context = result.get('test_case_context', {})
            question_type = test_context.get('question_type', 'Unknown')
            
            # Extract search results
            detailed_results = self._extract_detailed_results(result)
            if not detailed_results:
                continue
            
            # Calculate relevance scores using unified scorer (convert 0-3 scale to 0-1 scale)
            relevance_scores = []
            for search_item in detailed_results:
                raw_score = self.relevance_scorer.score_result_relevance(search_item, test_context, 'dataverse')
                # Convert 0-3 scale to 0-1 scale: 0->0.0, 1->0.33, 2->0.67, 3->1.0
                normalized_score = raw_score / 3.0 if raw_score > 0 else 0.0
                relevance_scores.append(normalized_score)
            
            # Count relevant items and exact matches (using normalized scale)
            relevant_items = [score for score in relevance_scores if score >= 0.67]  # Score >= 0.67 (was 2/3) is relevant
            exact_matches = [score for score in relevance_scores if score >= 1.0]    # Score >= 1.0 (was 3/3) is exact match
            
            total_relevant_items += len(relevant_items)
            exact_name_matches += len(exact_matches)
            
            # Update question type metrics
            q_type_metrics = question_type_metrics[question_type]
            q_type_metrics['query_count'] += 1
            q_type_metrics['total_relevant_found'] += len(relevant_items)
            q_type_metrics['exact_matches'] += len(exact_matches)
            
            # Calculate metrics for different K values
            for k in k_values:
                # Precision@K, Recall@K, F1@K
                precision_k, recall_k, f1_k = self._calculate_precision_recall_f1(relevance_scores, k)
                
                precision_metrics[k].append(precision_k)
                recall_metrics[k].append(recall_k)
                f1_metrics[k].append(f1_k)
                
                q_type_metrics['precision'][k].append(precision_k)
                q_type_metrics['recall'][k].append(recall_k)
                q_type_metrics['f1'][k].append(f1_k)
                
                # NDCG@K
                ndcg_k = self._calculate_ndcg_at_k(relevance_scores, k)
                ndcg_metrics[k].append(ndcg_k)
                q_type_metrics['ndcg'][k].append(ndcg_k)
            
            # MAP and MRR
            map_score = self._calculate_average_precision(relevance_scores)
            mrr_score = self._calculate_reciprocal_rank(relevance_scores)
            
            map_scores.append(map_score)
            mrr_scores.append(mrr_score)
            q_type_metrics['map'].append(map_score)
            q_type_metrics['mrr'].append(mrr_score)
        
        # Calculate overall averages
        overall_metrics = {
            'precision_at_k': {f'P@{k}': statistics.mean(precision_metrics[k]) if precision_metrics[k] else 0 for k in k_values},
            'recall_at_k': {f'R@{k}': statistics.mean(recall_metrics[k]) if recall_metrics[k] else 0 for k in k_values},
            'f1_score_at_k': {f'F1@{k}': statistics.mean(f1_metrics[k]) if f1_metrics[k] else 0 for k in k_values},
            'ndcg_at_k': {f'NDCG@{k}': statistics.mean(ndcg_metrics[k]) if ndcg_metrics[k] else 0 for k in k_values},
            'map_score': statistics.mean(map_scores) if map_scores else 0,
            'mrr_score': statistics.mean(mrr_scores) if mrr_scores else 0,
            'relevance_analysis': {
                'total_queries_analyzed': len([r for r in search_results if r.get('success', False)]),
                'total_relevant_items_found': total_relevant_items,
                'exact_name_matches': exact_name_matches,
                'average_relevance_per_query': total_relevant_items / len(search_results) if search_results else 0
            }
        }
        
        # Calculate question type specific averages
        question_type_breakdown = {}
        for q_type, metrics in question_type_metrics.items():
            if metrics['query_count'] > 0:
                question_type_breakdown[q_type] = {
                    'precision_at_k': {f'P@{k}': statistics.mean(metrics['precision'][k]) if metrics['precision'][k] else 0 for k in k_values},
                    'recall_at_k': {f'R@{k}': statistics.mean(metrics['recall'][k]) if metrics['recall'][k] else 0 for k in k_values},
                    'f1_score_at_k': {f'F1@{k}': statistics.mean(metrics['f1'][k]) if metrics['f1'][k] else 0 for k in k_values},
                    'ndcg_at_k': {f'NDCG@{k}': statistics.mean(metrics['ndcg'][k]) if metrics['ndcg'][k] else 0 for k in k_values},
                    'map_score': statistics.mean(metrics['map']) if metrics['map'] else 0,
                    'mrr_score': statistics.mean(metrics['mrr']) if metrics['mrr'] else 0,
                    'query_count': metrics['query_count'],
                    'relevance_analysis': {
                        'total_queries_analyzed': metrics['query_count'],
                        'total_relevant_items_found': metrics['total_relevant_found'],
                        'exact_name_matches': metrics['exact_matches'],
                        'average_relevance_per_query': metrics['total_relevant_found'] / metrics['query_count'] if metrics['query_count'] > 0 else 0
                    }
                }
        
        overall_metrics['question_type_breakdown'] = question_type_breakdown
        
        return overall_metrics
    
    def _extract_detailed_results(self, result: Dict) -> List[Dict]:
        """Extract detailed search results from API response"""
        # Try different possible structures
        response_data = result.get('response_data', {})
        
        # Handle case where queryResult is None/null
        query_result = response_data.get('queryResult')
        if query_result is None:
            return []
        
        # Handle case where queryResult is a dict with 'result' key
        if isinstance(query_result, dict) and 'result' in query_result:
            result_data = query_result['result']
            return result_data if isinstance(result_data, list) else []
        
        return []
    
    def _calculate_precision_recall_f1(self, relevance_scores: List[float], k: int) -> Tuple[float, float, float]:
        """Calculate Precision@K, Recall@K, and F1@K"""
        if not relevance_scores:
            return 0.0, 0.0, 0.0
        
        # Take top K results
        top_k_scores = relevance_scores[:k]
        
        # Count relevant items (score >= 0.67, which was 2/3 in 0-3 scale)
        relevant_in_k = sum(1 for score in top_k_scores if score >= 0.67)
        total_relevant = sum(1 for score in relevance_scores if score >= 0.67)
        
        # Precision@K = relevant items in top K / K
        precision = relevant_in_k / min(k, len(top_k_scores)) if top_k_scores else 0.0
        
        # Recall@K = relevant items in top K / total relevant items
        recall = relevant_in_k / max(1, total_relevant) if total_relevant > 0 else 0.0
        
        # F1@K = harmonic mean of precision and recall
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return precision, recall, f1
    
    def _calculate_ndcg_at_k(self, relevance_scores: List[int], k: int) -> float:
        """Calculate NDCG@K"""
        if not relevance_scores:
            return 0.0
        
        # Calculate DCG@K
        dcg = sum(score / math.log2(i + 2) for i, score in enumerate(relevance_scores[:k]))
        
        # Calculate IDCG@K (ideal ranking)
        ideal_scores = sorted(relevance_scores, reverse=True)[:k]
        idcg = sum(score / math.log2(i + 2) for i, score in enumerate(ideal_scores))
        
        return dcg / idcg if idcg > 0 else 0.0
    
    def _calculate_average_precision(self, relevance_scores: List[float]) -> float:
        """Calculate Average Precision (AP)"""
        if not relevance_scores:
            return 0.0
        
        relevant_count = 0
        precision_sum = 0.0
        total_relevant = sum(1 for score in relevance_scores if score >= 0.67)
        
        if total_relevant == 0:
            return 0.0
        
        for i, score in enumerate(relevance_scores):
            if score >= 0.67:  # Relevant (was >= 2 in 0-3 scale)
                relevant_count += 1
                precision_at_i = relevant_count / (i + 1)
                precision_sum += precision_at_i
        
        return precision_sum / total_relevant
    
    def _calculate_reciprocal_rank(self, relevance_scores: List[float]) -> float:
        """Calculate Reciprocal Rank (RR)"""
        for i, score in enumerate(relevance_scores):
            if score >= 0.67:  # First relevant result (was >= 2 in 0-3 scale)
                return 1.0 / (i + 1)
        return 0.0
    
    def _calculate_coverage_metrics(self, search_results: List[Dict]) -> Dict[str, Any]:
        """Calculate coverage and result distribution metrics"""
        result_counts = [r.get('result_count', 0) for r in search_results]
        zero_results = [r for r in search_results if r.get('result_count', 0) == 0]
        
        return {
            'total_results_returned': sum(result_counts),
            'avg_results_per_query': statistics.mean(result_counts) if result_counts else 0,
            'median_results_per_query': statistics.median(result_counts) if result_counts else 0,
            'zero_results_count': len(zero_results),
            'zero_results_rate': len(zero_results) / len(search_results) * 100 if search_results else 0,
            'max_results_single_query': max(result_counts) if result_counts else 0,
            'min_results_single_query': min(result_counts) if result_counts else 0
        }
    
    def _calculate_detailed_analysis(self, search_results: List[Dict]) -> Dict[str, Any]:
        """Calculate detailed analysis including question types and categories"""
        question_types = Counter()
        categories = Counter()
        
        for result in search_results:
            test_context = result.get('test_case_context', {})
            q_type = test_context.get('question_type', 'Unknown')
            category = test_context.get('original_product_category', 'Unknown')
            
            question_types[q_type] += 1
            categories[category] += 1
        
        return {
            'question_type_distribution': dict(question_types),
            'product_category_distribution': dict(categories)
        }
    
    def _print_analysis_report(self, analysis_results: Dict[str, Any]):
        """Print comprehensive analysis report"""
        print("\n📋 ENHANCED SEARCH ENGINE EVALUATION REPORT")
        print("=" * 60)
        print("🎯 Using Question-Type Specific Relevance Scoring")
        
        # File info
        file_info = analysis_results['file_info']
        print(f"\n📁 FILE INFORMATION:")
        print(f"   File: {file_info['file_path']}")
        print(f"   Valid results: {file_info['valid_results']}")
        
        # Performance metrics
        perf = analysis_results['search_performance']
        print(f"\n⚡ PERFORMANCE METRICS:")
        print(f"   Success rate: {perf['success_rate']:.1f}%")
        print(f"   Average response time: {perf['avg_response_time_ms']:.1f}ms")
        print(f"   P95 response time: {perf['p95_response_time_ms']:.1f}ms")
        
        # Relevance metrics
        relevance = analysis_results['relevance_metrics']
        print(f"\n🎯 ENHANCED RELEVANCE METRICS:")
        
        print(f"\n   📏 PRECISION@K (Question-Type Aware):")
        for metric, value in relevance['precision_at_k'].items():
            print(f"      {metric}: {value:.3f}")
        
        print(f"\n   📏 RECALL@K (Question-Type Aware):")
        for metric, value in relevance['recall_at_k'].items():
            print(f"      {metric}: {value:.3f}")
        
        print(f"\n   📏 RANKING QUALITY:")
        print(f"      MAP: {relevance['map_score']:.3f}")
        print(f"      MRR: {relevance['mrr_score']:.3f}")
        
        # Question type breakdown
        print(f"\n   🔍 QUESTION TYPE PERFORMANCE (Enhanced Scoring):")
        for q_type, metrics in relevance['question_type_breakdown'].items():
            print(f"\n      {q_type.upper()} ({metrics['query_count']} queries):")
            print(f"         P@1: {metrics['precision_at_k']['P@1']:.3f}, P@10: {metrics['precision_at_k']['P@10']:.3f}")
            print(f"         R@1: {metrics['recall_at_k']['R@1']:.3f}, R@10: {metrics['recall_at_k']['R@10']:.3f}")
            print(f"         MAP: {metrics['map_score']:.3f}, MRR: {metrics['mrr_score']:.3f}")
            rel_stats = metrics['relevance_analysis']
            print(f"         Found {rel_stats['total_relevant_items_found']} relevant items, {rel_stats['exact_name_matches']} exact matches")
    
    def _save_analysis_results(self, analysis_results: Dict[str, Any], output_file: str):
        """Save analysis results to JSON file"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_results, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Enhanced analysis saved to: {output_file}")
        except Exception as e:
            print(f"❌ Error saving analysis: {e}")

def main():
    """Main function"""
    if len(sys.argv) != 2:
        print("Usage: python analyze_search_results.py <jsonl_file_path>")
        sys.exit(1)
    
    jsonl_file = sys.argv[1]
    
    if not os.path.exists(jsonl_file):
        print(f"❌ File not found: {jsonl_file}")
        sys.exit(1)
    
    analyzer = EnhancedSearchAnalyzer()
    results = analyzer.analyze_jsonl_results(jsonl_file)
    
    if results:
        print(f"\n✅ Enhanced analysis completed!")
    else:
        print(f"\n❌ Analysis failed!")

if __name__ == "__main__":
    main()