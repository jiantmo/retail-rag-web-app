#!/usr/bin/env python3
"""
Search Engine Evaluation System
Calculates comprehensive metrics for search quality assessment
"""

import json
import math
import statistics
from collections import defaultdict, Counter
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

class SearchEvaluator:
    """Comprehensive search engine evaluation with multiple metrics"""
    
    def __init__(self):
        self.reset_metrics()
    
    def reset_metrics(self):
        """Reset all metric tracking variables"""
        self.evaluations = []
        self.query_results = []
        self.relevance_judgments = {}
        
    def add_search_result(self, 
                         question_data: Dict[str, Any], 
                         search_results: List[Dict], 
                         response_time_ms: float,
                         success: bool = True):
        """
        Add a search result for evaluation
        
        Args:
            question_data: Original question with product context
            search_results: List of search results from API
            response_time_ms: Response time in milliseconds
            success: Whether the search was successful
        """
        
        # Calculate relevance for each result
        relevance_scores = self._calculate_relevance_scores(question_data, search_results)
        
        evaluation = {
            'question': question_data.get('question', ''),
            'question_type': question_data.get('question_type', ''),
            'original_product': {
                'name': question_data.get('original_product_name', ''),
                'description': question_data.get('original_product_description', ''),
                'price': question_data.get('original_product_price', 0.0),
                'category': question_data.get('original_product_category', ''),
                'attributes': question_data.get('original_product_attributes', [])
            },
            'search_results': search_results,
            'relevance_scores': relevance_scores,
            'response_time_ms': response_time_ms,
            'success': success,
            'timestamp': datetime.now().isoformat(),
            'results_count': len(search_results) if search_results else 0
        }
        
        self.evaluations.append(evaluation)
        
    def _calculate_relevance_scores(self, question_data: Dict, search_results: List[Dict]) -> List[int]:
        """
        Calculate relevance scores (0-3) for each search result
        
        Relevance Scale:
        0 = Not relevant
        1 = Marginally relevant (related category/type)
        2 = Relevant (matches some criteria)
        3 = Highly relevant (exact or very close match)
        
        Returns:
            List of relevance scores corresponding to search results
        """
        if not search_results:
            return []
            
        relevance_scores = []
        original_name = question_data.get('original_product_name', '').lower()
        original_category = question_data.get('original_product_category', '').lower()
        original_price = question_data.get('original_product_price', 0.0)
        original_attributes = question_data.get('original_product_attributes', [])
        question_type = question_data.get('question_type', '')
        question_text = question_data.get('question', '').lower()
        
        # Extract attribute values for comparison
        original_attr_values = set()
        for attr in original_attributes:
            if isinstance(attr, dict) and 'value' in attr:
                original_attr_values.add(attr['value'].lower())
        
        for result in search_results:
            score = self._score_single_result(
                result, original_name, original_category, original_price, 
                original_attr_values, question_type, question_text
            )
            relevance_scores.append(score)
            
        return relevance_scores
    
    def _score_single_result(self, result: Dict, original_name: str, original_category: str, 
                           original_price: float, original_attr_values: set, 
                           question_type: str, question_text: str) -> int:
        """Score a single search result based on relevance criteria"""
        
        # Extract result information
        result_name = result.get('DisplayName', '').lower()
        result_category = result.get('Category', '').lower()
        result_price = float(result.get('Price', 0.0))
        result_description = result.get('Description', '').lower()
        
        score = 0
        
        # Exact name match (highest score)
        if original_name and original_name in result_name:
            return 3
            
        # Question type specific scoring
        if question_type == "Exact word":
            # For exact word questions, prioritize name similarity
            if self._calculate_text_similarity(original_name, result_name) > 0.7:
                score = 3
            elif self._calculate_text_similarity(original_name, result_name) > 0.4:
                score = 2
                
        elif question_type == "Price range":
            # For price questions, check if price is in reasonable range
            if original_price > 0:
                price_diff_ratio = abs(result_price - original_price) / original_price
                if price_diff_ratio <= 0.1:  # Within 10%
                    score = 3
                elif price_diff_ratio <= 0.3:  # Within 30%
                    score = 2
                elif price_diff_ratio <= 0.5:  # Within 50%
                    score = 1
                    
        elif question_type == "Category":
            # For category questions, check category match
            if original_category and original_category == result_category:
                score = 3
            elif original_category and original_category in result_category:
                score = 2
            elif self._has_related_category(original_category, result_category):
                score = 1
                
        elif question_type == "Attribute value":
            # For attribute questions, check if result has matching attributes
            result_text = f"{result_name} {result_description}".lower()
            matching_attrs = sum(1 for attr_val in original_attr_values if attr_val in result_text)
            if matching_attrs >= len(original_attr_values):
                score = 3
            elif matching_attrs > 0:
                score = 2
                
        elif question_type == "Description":
            # For description questions, check description similarity
            if original_name and original_name in result_description:
                score = 3
            elif self._calculate_text_similarity(question_text, result_description) > 0.3:
                score = 2
            elif original_category and original_category in result_description:
                score = 1
        
        # Boost score for category match (unless already high)
        if score < 3 and original_category and original_category == result_category:
            score = max(score, 2)
        elif score < 2 and original_category and original_category in result_category:
            score = max(score, 1)
            
        return min(score, 3)  # Cap at 3
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity using common words"""
        if not text1 or not text2:
            return 0.0
            
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _has_related_category(self, cat1: str, cat2: str) -> bool:
        """Check if categories are related"""
        if not cat1 or not cat2:
            return False
            
        # Define category relationships
        related_categories = {
            'accessory': ['accessories', 'gear', 'equipment'],
            'sleeping': ['camping', 'outdoor', 'rest'],
            'clothing': ['apparel', 'wear', 'garment'],
        }
        
        for main_cat, related in related_categories.items():
            if main_cat in cat1.lower() and any(rel in cat2.lower() for rel in related):
                return True
            if main_cat in cat2.lower() and any(rel in cat1.lower() for rel in related):
                return True
                
        return False
    
    def calculate_precision_at_k(self, k: int = 10) -> Dict[str, float]:
        """
        Calculate Precision@K for different question types
        
        Formula: P@K = (Relevant items in top K) / K
        """
        precisions = defaultdict(list)
        
        for eval_data in self.evaluations:
            if not eval_data['success'] or not eval_data['relevance_scores']:
                continue
                
            relevance_scores = eval_data['relevance_scores'][:k]
            relevant_count = sum(1 for score in relevance_scores if score >= 2)  # Score >= 2 is relevant
            
            precision = relevant_count / min(k, len(relevance_scores)) if relevance_scores else 0.0
            
            question_type = eval_data['question_type']
            precisions[question_type].append(precision)
            precisions['overall'].append(precision)
        
        # Calculate average precisions
        avg_precisions = {}
        for q_type, prec_list in precisions.items():
            avg_precisions[q_type] = statistics.mean(prec_list) if prec_list else 0.0
            
        return avg_precisions
    
    def calculate_recall_at_k(self, k: int = 10) -> Dict[str, float]:
        """
        Calculate Recall@K for different question types
        
        Formula: R@K = (Relevant items in top K) / (Total relevant items)
        Note: For our test cases, we assume 1 perfect match per query
        """
        recalls = defaultdict(list)
        
        for eval_data in self.evaluations:
            if not eval_data['success'] or not eval_data['relevance_scores']:
                continue
                
            relevance_scores = eval_data['relevance_scores'][:k]
            # For test cases, we expect 1 highly relevant result (the original product)
            highly_relevant_found = sum(1 for score in relevance_scores if score >= 3)
            
            recall = min(1.0, highly_relevant_found)  # Cap at 1.0 since we expect 1 perfect match
            
            question_type = eval_data['question_type']
            recalls[question_type].append(recall)
            recalls['overall'].append(recall)
        
        # Calculate average recalls
        avg_recalls = {}
        for q_type, recall_list in recalls.items():
            avg_recalls[q_type] = statistics.mean(recall_list) if recall_list else 0.0
            
        return avg_recalls
    
    def calculate_f1_scores(self, k: int = 10) -> Dict[str, float]:
        """
        Calculate F1 scores from precision and recall
        
        Formula: F1 = 2 * (Precision * Recall) / (Precision + Recall)
        """
        precisions = self.calculate_precision_at_k(k)
        recalls = self.calculate_recall_at_k(k)
        
        f1_scores = {}
        for q_type in precisions.keys():
            p = precisions[q_type]
            r = recalls[q_type]
            
            f1_scores[q_type] = 2 * (p * r) / (p + r) if (p + r) > 0 else 0.0
            
        return f1_scores
    
    def calculate_mean_average_precision(self) -> Dict[str, float]:
        """
        Calculate Mean Average Precision (MAP)
        
        Formula: MAP = (1/Q) * Σ(AP_q) where AP_q is Average Precision for query q
        AP_q = (1/R) * Σ(P@k * rel(k)) where R is total relevant docs
        """
        average_precisions = defaultdict(list)
        
        for eval_data in self.evaluations:
            if not eval_data['success'] or not eval_data['relevance_scores']:
                continue
                
            relevance_scores = eval_data['relevance_scores']
            
            # Calculate Average Precision for this query
            relevant_count = 0
            precision_sum = 0.0
            total_relevant = sum(1 for score in relevance_scores if score >= 2)
            
            if total_relevant == 0:
                ap = 0.0
            else:
                for i, score in enumerate(relevance_scores):
                    if score >= 2:  # Relevant
                        relevant_count += 1
                        precision_at_i = relevant_count / (i + 1)
                        precision_sum += precision_at_i
                
                ap = precision_sum / total_relevant
            
            question_type = eval_data['question_type']
            average_precisions[question_type].append(ap)
            average_precisions['overall'].append(ap)
        
        # Calculate MAP for each question type
        map_scores = {}
        for q_type, ap_list in average_precisions.items():
            map_scores[q_type] = statistics.mean(ap_list) if ap_list else 0.0
            
        return map_scores
    
    def calculate_ndcg(self, k: int = 10) -> Dict[str, float]:
        """
        Calculate Normalized Discounted Cumulative Gain (NDCG@K)
        
        Formula: NDCG@K = DCG@K / IDCG@K
        DCG@K = Σ(rel_i / log2(i+1)) for i=1 to K
        IDCG@K = DCG of perfect ranking
        """
        ndcg_scores = defaultdict(list)
        
        for eval_data in self.evaluations:
            if not eval_data['success'] or not eval_data['relevance_scores']:
                continue
                
            relevance_scores = eval_data['relevance_scores'][:k]
            
            # Calculate DCG
            dcg = 0.0
            for i, score in enumerate(relevance_scores):
                dcg += score / math.log2(i + 2)  # i+2 because log2(1) = 0
            
            # Calculate IDCG (perfect ranking)
            ideal_scores = sorted(relevance_scores, reverse=True)
            idcg = 0.0
            for i, score in enumerate(ideal_scores):
                idcg += score / math.log2(i + 2)
            
            ndcg = dcg / idcg if idcg > 0 else 0.0
            
            question_type = eval_data['question_type']
            ndcg_scores[question_type].append(ndcg)
            ndcg_scores['overall'].append(ndcg)
        
        # Calculate average NDCG for each question type
        avg_ndcg = {}
        for q_type, ndcg_list in ndcg_scores.items():
            avg_ndcg[q_type] = statistics.mean(ndcg_list) if ndcg_list else 0.0
            
        return avg_ndcg
    
    def calculate_mrr(self) -> Dict[str, float]:
        """
        Calculate Mean Reciprocal Rank (MRR)
        
        Formula: MRR = (1/Q) * Σ(1/rank_i) where rank_i is rank of first relevant result
        """
        reciprocal_ranks = defaultdict(list)
        
        for eval_data in self.evaluations:
            if not eval_data['success'] or not eval_data['relevance_scores']:
                continue
                
            relevance_scores = eval_data['relevance_scores']
            
            # Find rank of first relevant result (score >= 2)
            first_relevant_rank = None
            for i, score in enumerate(relevance_scores):
                if score >= 2:
                    first_relevant_rank = i + 1  # 1-indexed
                    break
            
            rr = 1.0 / first_relevant_rank if first_relevant_rank else 0.0
            
            question_type = eval_data['question_type']
            reciprocal_ranks[question_type].append(rr)
            reciprocal_ranks['overall'].append(rr)
        
        # Calculate MRR for each question type
        mrr_scores = {}
        for q_type, rr_list in reciprocal_ranks.items():
            mrr_scores[q_type] = statistics.mean(rr_list) if rr_list else 0.0
            
        return mrr_scores
    
    def calculate_percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile without numpy"""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        n = len(sorted_data)
        k = (percentile / 100) * (n - 1)
        
        if k == int(k):
            return sorted_data[int(k)]
        else:
            lower = sorted_data[int(k)]
            upper = sorted_data[int(k) + 1]
            return lower + (k - int(k)) * (upper - lower)
    
    def calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calculate response time and throughput metrics"""
        if not self.evaluations:
            return {}
            
        response_times = [eval_data['response_time_ms'] for eval_data in self.evaluations if eval_data['success']]
        success_count = sum(1 for eval_data in self.evaluations if eval_data['success'])
        total_count = len(self.evaluations)
        
        return {
            'average_response_time_ms': statistics.mean(response_times) if response_times else 0.0,
            'median_response_time_ms': statistics.median(response_times) if response_times else 0.0,
            'p95_response_time_ms': self.calculate_percentile(response_times, 95) if response_times else 0.0,
            'p99_response_time_ms': self.calculate_percentile(response_times, 99) if response_times else 0.0,
            'success_rate': success_count / total_count if total_count > 0 else 0.0,
            'total_queries': total_count,
            'successful_queries': success_count,
            'failed_queries': total_count - success_count
        }
    
    def calculate_coverage_metrics(self) -> Dict[str, Any]:
        """Calculate query coverage and result metrics"""
        if not self.evaluations:
            return {}
            
        # Query success metrics
        zero_results_count = sum(1 for eval_data in self.evaluations if eval_data['results_count'] == 0)
        total_queries = len(self.evaluations)
        
        # Result count statistics
        result_counts = [eval_data['results_count'] for eval_data in self.evaluations if eval_data['success']]
        
        # Question type coverage
        question_types = Counter(eval_data['question_type'] for eval_data in self.evaluations)
        
        return {
            'zero_results_rate': zero_results_count / total_queries if total_queries > 0 else 0.0,
            'query_success_rate': 1.0 - (zero_results_count / total_queries) if total_queries > 0 else 0.0,
            'average_results_per_query': statistics.mean(result_counts) if result_counts else 0.0,
            'median_results_per_query': statistics.median(result_counts) if result_counts else 0.0,
            'question_type_distribution': dict(question_types),
            'total_results_returned': sum(result_counts)
        }
    
    def generate_comprehensive_report(self, k: int = 10) -> Dict[str, Any]:
        """Generate comprehensive evaluation report with all metrics"""
        
        report = {
            'evaluation_summary': {
                'total_evaluations': len(self.evaluations),
                'timestamp': datetime.now().isoformat(),
                'k_value': k
            },
            'relevance_metrics': {
                'precision_at_k': self.calculate_precision_at_k(k),
                'recall_at_k': self.calculate_recall_at_k(k),
                'f1_scores': self.calculate_f1_scores(k),
                'mean_average_precision': self.calculate_mean_average_precision(),
                'ndcg_at_k': self.calculate_ndcg(k),
                'mean_reciprocal_rank': self.calculate_mrr()
            },
            'performance_metrics': self.calculate_performance_metrics(),
            'coverage_metrics': self.calculate_coverage_metrics()
        }
        
        return report
    
    def save_evaluation_report(self, output_file: str, k: int = 10):
        """Save comprehensive evaluation report to file"""
        report = self.generate_comprehensive_report(k)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Evaluation report saved to: {output_file}")
        return report

    def print_metric_calculations(self):
        """Print detailed explanation of how metrics are calculated"""
        
        print("📊 SEARCH ENGINE EVALUATION METRICS - CALCULATION METHODS")
        print("=" * 80)
        
        print("\n🎯 RELEVANCE SCORING (0-3 scale):")
        print("   0 = Not relevant")
        print("   1 = Marginally relevant (related category/type)")
        print("   2 = Relevant (matches some criteria)")
        print("   3 = Highly relevant (exact or very close match)")
        
        print("\n📏 PRECISION@K:")
        print("   Formula: P@K = (Relevant items in top K) / K")
        print("   Example: If top 10 results have 7 relevant items: P@10 = 7/10 = 0.7")
        print("   Measures: How many retrieved results are actually relevant")
        
        print("\n🔍 RECALL@K:")
        print("   Formula: R@K = (Relevant items found in top K) / (Total relevant items)")
        print("   Example: If 1 perfect match exists and found in top 10: R@10 = 1/1 = 1.0")
        print("   Measures: How many relevant items we successfully found")
        
        print("\n⚖️ F1-SCORE:")
        print("   Formula: F1 = 2 × (Precision × Recall) / (Precision + Recall)")
        print("   Example: P=0.7, R=1.0 → F1 = 2×(0.7×1.0)/(0.7+1.0) = 0.82")
        print("   Measures: Harmonic mean of precision and recall")
        
        print("\n📈 MEAN AVERAGE PRECISION (MAP):")
        print("   Formula: MAP = (1/Q) × Σ(AP_q) where AP_q = Average Precision per query")
        print("   AP calculation: For each relevant result at position i, add P@i, then divide by total relevant")
        print("   Example: Relevant items at positions 1,3,5 in 10 results:")
        print("            AP = (1/1 + 2/3 + 3/5) / 3 = (1.0 + 0.67 + 0.6) / 3 = 0.76")
        print("   Measures: Quality of ranking across all queries")
        
        print("\n🏆 NDCG@K (Normalized Discounted Cumulative Gain):")
        print("   Formula: NDCG@K = DCG@K / IDCG@K")
        print("   DCG@K = Σ(relevance_score_i / log₂(i+1)) for i=1 to K")
        print("   IDCG@K = DCG of perfect ranking (ideal order)")
        print("   Example: Relevance scores [3,2,1,0] in positions [1,2,3,4]:")
        print("            DCG = 3/log₂(2) + 2/log₂(3) + 1/log₂(4) + 0/log₂(5)")
        print("            DCG = 3/1 + 2/1.58 + 1/2 + 0 = 3 + 1.27 + 0.5 = 4.77")
        print("            IDCG = 3/1 + 2/1.58 + 1/2 + 0 = 4.77 (same order)")
        print("            NDCG = 4.77/4.77 = 1.0")
        print("   Measures: Ranking quality with position discount")
        
        print("\n🥇 MEAN RECIPROCAL RANK (MRR):")
        print("   Formula: MRR = (1/Q) × Σ(1/rank_i) where rank_i = position of first relevant result")
        print("   Example: First relevant results at positions [1,3,2] across 3 queries:")
        print("            MRR = (1/1 + 1/3 + 1/2) / 3 = (1.0 + 0.33 + 0.5) / 3 = 0.61")
        print("   Measures: How quickly users find their first good result")
        
        print("\n⚡ PERFORMANCE METRICS:")
        print("   • Average Response Time: Mean of all successful query response times")
        print("   • P95/P99 Response Time: 95th/99th percentile response times")
        print("   • Success Rate: Successful queries / Total queries")
        print("   • Throughput: Queries processed per second")
        
        print("\n📊 COVERAGE METRICS:")
        print("   • Zero Results Rate: Queries returning no results / Total queries")
        print("   • Query Success Rate: 1 - Zero Results Rate")
        print("   • Average Results per Query: Mean number of results returned")
        
        print("\n🔬 RELEVANCE CALCULATION LOGIC:")
        print("   Question Type 'Exact word': Name similarity matching")
        print("   Question Type 'Price range': Price difference within thresholds (10%/30%/50%)")
        print("   Question Type 'Category': Exact or partial category matching")
        print("   Question Type 'Attribute value': Attribute value presence in result")
        print("   Question Type 'Description': Description and content similarity")
        print("=" * 80)
