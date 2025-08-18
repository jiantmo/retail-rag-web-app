#!/usr/bin/env python3
"""
Agentic Search Results Analysis Script
Specialized for analyzing agentic search API results with FormattedText structure
"""

import json
import os
import sys
import statistics
import math
import re
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List, Any, Tuple
from improved_relevance_scorer import ImprovedRelevanceScorer

class AgenticSearchAnalyzer:
    """
    Agentic search analyzer with improved relevance scoring.
    Designed specifically for agentic search API results that use FormattedText structure.
    
    Key differences from standard search analysis:
    1. Results are in response_data.result.FormattedText as JSON string
    2. Products are extracted from ref_id content items
    3. Uses same relevance scoring logic but adapted for agentic response format
    """
    
    def __init__(self):
        self.relevance_scorer = ImprovedRelevanceScorer()
        
    def analyze_jsonl_results(self, jsonl_file_path: str) -> Dict[str, Any]:
        """
        Analyze JSONL agentic search results with improved relevance scoring
        
        Args:
            jsonl_file_path: Path to the JSONL file containing agentic search results
            
        Returns:
            Dictionary containing comprehensive analysis results
        """
        print(f"🤖 Agentic Search Analysis of: {jsonl_file_path}")
        print("=" * 80)
        
        # Load search results
        search_results = self._load_jsonl_file(jsonl_file_path)
        if not search_results:
            return None
        
        print(f"📊 Loaded {len(search_results)} agentic search results")
        
        # Calculate metrics with improved scoring
        analysis_results = {
            'file_info': self._get_file_info(jsonl_file_path, search_results),
            'search_performance': self._calculate_performance_metrics(search_results),
            'relevance_metrics': self._calculate_relevance_metrics(search_results),
            'coverage_metrics': self._calculate_coverage_metrics(search_results),
            'detailed_analysis': self._calculate_detailed_analysis(search_results),
            'throttling_summary': self._calculate_throttling_summary(search_results),
            'agentic_specific_metrics': self._calculate_agentic_specific_metrics(search_results),
            'analysis_metadata': {
                'generated_at': datetime.now().isoformat(),
                'analysis_type': 'agentic_search_evaluation_with_improved_relevance',
                'relevance_scoring': 'question_type_specific',
                'search_api_type': 'agentic_search_api',
                'response_format': 'formatted_text_with_ref_ids',
                'metrics_included': [
                    'precision_at_k', 'recall_at_k', 'f1_score_at_k', 
                    'map_score', 'ndcg_at_k', 'mrr_score',
                    'response_times', 'coverage_metrics', 'agentic_activity_metrics'
                ]
            }
        }
        
        # Generate report
        self._print_analysis_report(analysis_results)
        
        # Save results
        output_file = jsonl_file_path.replace('.jsonl', '_agentic_analysis.json')
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
        """Calculate response time and performance metrics with enhanced error detection"""
        # Classify results based on API call success and actual search execution
        api_successful = [r for r in search_results if r.get('success', False)]
        search_successful = []
        throttled_requests = []
        other_errors = []
        
        for result in search_results:
            api_success = result.get('success', False)
            search_execution_success = self._is_search_execution_successful(result)
            
            if api_success and search_execution_success:
                search_successful.append(result)
            elif api_success and not search_execution_success:
                # API call succeeded but search execution failed
                if self._is_throttled_request(result):
                    throttled_requests.append(result)
                else:
                    other_errors.append(result)
        
        response_times = [r.get('response_time_seconds', 0) for r in search_results]
        status_codes = [r.get('status_code') for r in search_results if r.get('status_code')]
        
        return {
            'total_searches': len(search_results),
            'api_successful_calls': len(api_successful),
            'search_execution_successful': len(search_successful),
            'throttled_requests': len(throttled_requests),
            'other_errors': len(other_errors),
            'api_failed_calls': len(search_results) - len(api_successful),
            'api_success_rate': len(api_successful) / len(search_results) * 100 if search_results else 0,
            'search_execution_success_rate': len(search_successful) / len(search_results) * 100 if search_results else 0,
            'throttling_rate': len(throttled_requests) / len(search_results) * 100 if search_results else 0,
            'avg_response_time_ms': statistics.mean(response_times) * 1000 if response_times else 0,
            'median_response_time_ms': statistics.median(response_times) * 1000 if response_times else 0,
            'p95_response_time_ms': sorted(response_times)[int(len(response_times) * 0.95)] * 1000 if response_times else 0,
            'p99_response_time_ms': sorted(response_times)[int(len(response_times) * 0.99)] * 1000 if response_times else 0,
            'min_response_time_ms': min(response_times) * 1000 if response_times else 0,
            'max_response_time_ms': max(response_times) * 1000 if response_times else 0,
            'status_code_distribution': dict(Counter(status_codes)),
            'error_analysis': {
                'throttled_examples': [self._extract_error_message(r) for r in throttled_requests[:3]],
                'other_error_examples': [self._extract_error_message(r) for r in other_errors[:3]]
            }
        }
    
    def _calculate_relevance_metrics(self, search_results: List[Dict]) -> Dict[str, Any]:
        """Calculate comprehensive relevance metrics using improved scoring for agentic search"""
        print("\n🤖 Calculating Agentic Search Relevance Metrics...")
        
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
        total_product_items_extracted = 0
        
        # Count throttling and other errors for summary
        throttled_count = 0
        other_error_count = 0
        successful_execution_count = 0
        
        for result in search_results:
            if not result.get('success', False):
                continue
            
            # Check if search execution was actually successful
            if not self._is_search_execution_successful(result):
                if self._is_throttled_request(result):
                    throttled_count += 1
                else:
                    other_error_count += 1
                continue
            else:
                successful_execution_count += 1
        
        # Process each search result - ONLY successful executions for relevance metrics
        for result in search_results:
            if not result.get('success', False):
                continue
            
            # EXCLUDE throttled requests and other errors from relevance calculations
            if not self._is_search_execution_successful(result):
                continue
                
            # Extract test case context
            test_context = result.get('test_case_context', {})
            query_metadata = result.get('query_metadata', {})
            
            # Use query_metadata if test_case_context is empty
            if not test_context and query_metadata:
                test_context = query_metadata
            
            question_type = test_context.get('question_type', 'Unknown')
            
            # Extract products from agentic search response
            detailed_results = self._extract_agentic_products(result)
            if not detailed_results:
                continue
            
            total_product_items_extracted += len(detailed_results)
            
            # Calculate relevance scores using agentic-specific logic
            relevance_scores = []
            for product_item in detailed_results:
                score = self._score_agentic_relevance(product_item, test_context)
                relevance_scores.append(score)
            
            # Count relevant items and exact matches
            relevant_items = [score for score in relevance_scores if score >= 2]  # Score >= 2 is relevant
            exact_matches = [score for score in relevance_scores if score >= 3]   # Score >= 3 is exact match
            
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
                'total_queries_for_relevance_calculation': successful_execution_count,
                'total_api_calls_made': len([r for r in search_results if r.get('success', False)]),
                'throttled_requests_excluded': throttled_count,
                'other_errors_excluded': other_error_count,
                'total_relevant_items_found': total_relevant_items,
                'exact_name_matches': exact_name_matches,
                'total_product_items_extracted': total_product_items_extracted,
                'average_relevance_per_successful_query': total_relevant_items / successful_execution_count if successful_execution_count > 0 else 0,
                'average_products_per_successful_query': total_product_items_extracted / successful_execution_count if successful_execution_count > 0 else 0,
                'exclusion_summary': {
                    'excluded_for_throttling': throttled_count,
                    'excluded_for_other_errors': other_error_count,
                    'included_in_relevance_metrics': successful_execution_count,
                    'exclusion_rate': (throttled_count + other_error_count) / len(search_results) * 100 if search_results else 0
                }
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
    
    def _extract_agentic_products(self, result: Dict) -> List[Dict]:
        """Extract product data from agentic search FormattedText response"""
        try:
            # Get response data
            response_data = result.get('response_data', {})
            search_result = response_data.get('result', {})
            formatted_text = search_result.get('FormattedText', '')
            
            if not formatted_text:
                return []
            
            # Parse the FormattedText JSON string
            try:
                formatted_data = json.loads(formatted_text)
            except json.JSONDecodeError:
                return []
            
            # Extract products from ref_id content items
            products = []
            for item in formatted_data:
                if isinstance(item, dict) and 'content' in item:
                    # Parse product data from content string
                    product = self._parse_product_content(item['content'])
                    if product:
                        products.append(product)
            
            return products
            
        except Exception as e:
            # print(f"Debug: Error extracting agentic products: {e}")
            return []
    
    def _parse_product_content(self, content: str) -> Dict:
        """Parse product information from content string"""
        try:
            # Extract key product information using regex patterns
            product = {}
            
            # Extract ProductNumber
            product_number_match = re.search(r'ProductNumber:\s*([^;]+)', content)
            if product_number_match:
                product['ProductNumber'] = product_number_match.group(1).strip()
            
            # Extract Price
            price_match = re.search(r'Price:\s*([\d.]+)', content)
            if price_match:
                product['Price'] = float(price_match.group(1))
            
            # Extract Name
            name_match = re.search(r'Name:\s*([^;]+)', content)
            if name_match:
                product['Name'] = name_match.group(1).strip()
            
            # Extract ItemId
            item_id_match = re.search(r'ItemId:\s*([^;]+)', content)
            if item_id_match:
                product['ItemId'] = item_id_match.group(1).strip()
            
            # Extract Description
            description_match = re.search(r'Description:\s*([^;]+)', content)
            if description_match:
                product['Description'] = description_match.group(1).strip()
            
            # Store the full content for attribute scoring
            product['FullContent'] = content
            
            # Extract AttributeValues using improved parsing
            attributes = {}
            try:
                # Look for AttributeValues section
                attr_values_match = re.search(r'AttributeValues:\s*(\[.*?\])', content, re.DOTALL)
                if attr_values_match:
                    attr_text = attr_values_match.group(1)
                    
                    # Extract TextValue attributes with various quote patterns
                    text_value_patterns = [
                        r"'TextValue':\s*'([^']+)'",  # Single quotes
                        r'"TextValue":\s*"([^"]+)"',  # Double quotes
                        r"'TextValue':\s*\"([^\"]+)\"",  # Mixed quotes
                    ]
                    
                    for pattern in text_value_patterns:
                        matches = re.findall(pattern, attr_text)
                        for match in matches:
                            # Try to categorize the attribute
                            if re.match(r'^[MLXS].*|.*[MLXS]$', match, re.IGNORECASE):
                                if 'sizes' not in attributes:
                                    attributes['sizes'] = []
                                # Handle pipe-separated sizes
                                sizes = [s.strip() for s in match.split('|') if s.strip()]
                                attributes['sizes'].extend(sizes)
                            else:
                                if 'materials' not in attributes:
                                    attributes['materials'] = []
                                attributes['materials'].append(match.lower())
                    
                    # Extract Color values specifically
                    color_patterns = [
                        r"'Color'[^}]*'TextValue':\s*'([^']+)'",
                        r'"Color"[^}]*"TextValue":\s*"([^"]+)"',
                        r"'Color'[^}]*'TextValue':\s*\"([^\"]+)\"",
                    ]
                    
                    for pattern in color_patterns:
                        color_matches = re.findall(pattern, attr_text)
                        for color in color_matches:
                            if 'colors' not in attributes:
                                attributes['colors'] = []
                            # Handle pipe-separated colors
                            colors = [c.strip() for c in color.split('|') if c.strip()]
                            attributes['colors'].extend(colors)
                    
                    product['Attributes'] = attributes
                    
            except Exception as e:
                # Fallback to basic attribute extraction
                # Store the full content so attribute scoring can access it
                pass
            
            # Only return product if we have essential fields
            if 'Name' in product:
                return product
            
            return None
            
        except Exception as e:
            return None
    
    def _is_search_execution_successful(self, result: Dict) -> bool:
        """Check if the search execution was actually successful (not just API call)"""
        try:
            response_data = result.get('response_data', {})
            search_result = response_data.get('result', {})
            formatted_text = search_result.get('FormattedText', '')
            
            # Check for error messages in FormattedText
            if not formatted_text:
                return False
            
            # Check for common error patterns
            error_patterns = [
                'Error processing search request',
                'Agentic retrieval failed',
                'TooManyRequests',
                'Rate limit is exceeded',
                'System.Net.Http.HttpRequestException',
                'error":{',
                'Exception:',
                'failed:'
            ]
            
            formatted_text_lower = formatted_text.lower()
            for pattern in error_patterns:
                if pattern.lower() in formatted_text_lower:
                    return False
            
            # If FormattedText contains actual JSON array with ref_id items, it's successful
            try:
                formatted_data = json.loads(formatted_text)
                if isinstance(formatted_data, list) and len(formatted_data) > 0:
                    # Check if items have ref_id and content
                    first_item = formatted_data[0]
                    if isinstance(first_item, dict) and 'ref_id' in first_item and 'content' in first_item:
                        return True
                return len(formatted_data) == 0  # Empty results are still successful execution
            except json.JSONDecodeError:
                return False
                
        except Exception:
            return False
    
    def _is_throttled_request(self, result: Dict) -> bool:
        """Check if the request was throttled/rate limited"""
        try:
            response_data = result.get('response_data', {})
            search_result = response_data.get('result', {})
            formatted_text = search_result.get('FormattedText', '')
            
            throttling_patterns = [
                'TooManyRequests',
                'Rate limit is exceeded',
                'status code \'429\'',
                'rate limit',
                'too many requests'
            ]
            
            formatted_text_lower = formatted_text.lower()
            for pattern in throttling_patterns:
                if pattern.lower() in formatted_text_lower:
                    return True
                    
            return False
        except Exception:
            return False
    
    def _extract_error_message(self, result: Dict) -> str:
        """Extract error message from failed result"""
        try:
            response_data = result.get('response_data', {})
            search_result = response_data.get('result', {})
            formatted_text = search_result.get('FormattedText', '')
            
            # Extract error message from FormattedText
            if 'Error processing search request:' in formatted_text:
                # Find the error message part
                error_start = formatted_text.find('Error processing search request:')
                error_part = formatted_text[error_start:error_start+200]  # First 200 chars
                return error_part.replace('\n', ' ').strip()
            
            return formatted_text[:200] if formatted_text else 'No error message found'
            
        except Exception:
            return 'Error extracting error message'
    
    def _score_agentic_relevance(self, product: Dict, test_context: Dict) -> int:
        """
        Score relevance for agentic search results based on question context
        
        Args:
            product: Extracted product data from agentic response
            test_context: Test context containing question and type
            
        Returns:
            Relevance score: 0-3 (0=not relevant, 3=highly relevant)
        """
        try:
            question_type = test_context.get('question_type', '').strip()
            question_text = test_context.get('question', '').lower()
            
            # Get product information
            product_name = product.get('Name', '').lower()
            product_description = product.get('Description', '').lower()
            product_price = product.get('Price', 0)
            product_attributes = product.get('Attributes', {})
            product_full_content = product.get('FullContent', '')
            
            # Create combined text for searching
            product_text = f"{product_name} {product_description}".lower()
            
            # Question type specific scoring
            if question_type == "Exact word":
                return self._score_exact_word_agentic(question_text, product_name, product_text)
            
            elif question_type == "Category":
                return self._score_category_agentic(question_text, product_text, product_name)
            
            elif question_type == "Category + Price range":
                return self._score_price_range_agentic(question_text, product_text, product_price)
            
            elif question_type == "Category + Attribute value":
                return self._score_attribute_agentic(question_text, product_full_content, product_attributes)
            
            elif question_type == "Description":
                return self._score_description_agentic(question_text, product_text, product_name)
            
            else:
                # General relevance for unknown types
                return self._score_general_agentic(question_text, product_text, product_name)
                
        except Exception as e:
            return 0
    
    def _score_exact_word_agentic(self, question: str, product_name: str, product_text: str) -> int:
        """Score exact word matches"""
        # Extract product name from question
        for word in question.split():
            if len(word) > 3 and word in product_name:
                if word in product_name.split():
                    return 3  # Exact match
                else:
                    return 2  # Partial match
        
        # Check for brand/model matches
        question_words = set(question.lower().split())
        product_words = set(product_name.split())
        
        if len(question_words & product_words) >= 2:
            return 2
        elif len(question_words & product_words) >= 1:
            return 1
            
        return 0
    
    def _score_category_agentic(self, question: str, product_text: str, product_name: str) -> int:
        """Score category matches"""
        category_keywords = {
            'clothing': ['clothing', 'shirt', 'jacket', 'coat', 'vest', 'hoodie', 'sweater'],
            'footwear': ['shoes', 'boots', 'sneakers', 'sandals'],
            'bike': ['bike', 'bicycle', 'cycling'],
            'tent': ['tent', 'shelter'],
            'backpack': ['backpack', 'pack', 'bag'],
            'gloves': ['gloves', 'glove'],
            'helmet': ['helmet'],
            'accessory': ['accessory', 'gear', 'equipment']
        }
        
        question_words = question.lower().split()
        
        for category, keywords in category_keywords.items():
            # Check if question mentions this category
            if any(keyword in question for keyword in keywords):
                # Check if product belongs to this category
                if any(keyword in product_text for keyword in keywords):
                    return 3  # High relevance
                elif any(keyword in product_name for keyword in keywords):
                    return 2  # Medium relevance
        
        return 0
    
    def _score_price_range_agentic(self, question: str, product_text: str, product_price: float) -> int:
        """Score price range matches"""
        import re
        
        # Extract price range from question
        price_patterns = [
            r'\$(\d+)-\$?(\d+)',  # $80-$120 or $80-120
            r'between \$?(\d+) and \$?(\d+)',  # between $80 and $120
            r'under \$?(\d+)',  # under $100
            r'over \$?(\d+)',  # over $50
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, question)
            if match:
                if 'under' in question:
                    max_price = float(match.group(1))
                    if product_price <= max_price:
                        return 3
                elif 'over' in question:
                    min_price = float(match.group(1))
                    if product_price >= min_price:
                        return 3
                else:
                    # Range query
                    min_price = float(match.group(1))
                    max_price = float(match.group(2))
                    if min_price <= product_price <= max_price:
                        return 3  # Perfect price match
                    elif abs(product_price - min_price) <= 20 or abs(product_price - max_price) <= 20:
                        return 2  # Close to range
        
        # Also check for category relevance
        category_score = self._score_category_agentic(question, product_text, product_text.split()[0] if product_text else "")
        return min(category_score, 2)  # Price relevance but not perfect
    
    def _score_attribute_agentic(self, question: str, product_text: str, product_attributes: Dict) -> int:
        """Score attribute matches with improved dynamic attribute extraction"""
        # Common attribute keywords
        attribute_keywords = {
            'nylon': ['nylon'],
            'cotton': ['cotton'],
            'leather': ['leather'],
            'waterproof': ['waterproof', 'water-resistant'],
            'breathable': ['breathable'],
            'insulated': ['insulated', 'insulation'],
            'lightweight': ['lightweight', 'light'],
        }
        
        question_lower = question.lower()
        product_text_lower = product_text.lower()
        
        # First check predefined attribute keywords
        for attr_name, keywords in attribute_keywords.items():
            if any(keyword in question_lower for keyword in keywords):
                # Check if product has this attribute
                if any(keyword in product_text_lower for keyword in keywords):
                    return 3  # Perfect attribute match
                
                # Check in attributes dict if available
                if product_attributes:
                    attr_text = str(product_attributes).lower()
                    if any(keyword in attr_text for keyword in keywords):
                        return 3
        
        # Enhanced: Extract and match dynamic attributes from product data
        import re
        import json
        
        # Extract AttributeValues from product text if available
        attribute_values = []
        try:
            # Look for AttributeValues in the product text (using both single and double quotes)
            attr_patterns = [
                r"'TextValue':\s*'([^']+)'",  # Single quotes
                r'"TextValue":\s*"([^"]+)"',  # Double quotes
                r"'TextValue':\s*\"([^\"]+)\"",  # Mixed quotes
            ]
            for pattern in attr_patterns:
                matches = re.findall(pattern, product_text)
                attribute_values.extend([val.lower() for val in matches])
            
            # Also extract from Color attribute specifically
            color_patterns = [
                r"'Color'[^}]*'TextValue':\s*'([^']+)'",
                r'"Color"[^}]*"TextValue":\s*"([^"]+)"',
                r"'Color'[^}]*'TextValue':\s*\"([^\"]+)\"",
            ]
            for pattern in color_patterns:
                color_matches = re.findall(pattern, product_text)
                attribute_values.extend([val.lower() for val in color_matches])
            
            # Extract size values
            size_patterns = [
                r"'Size'[^}]*'TextValue':\s*'([^']+)'",
                r'"Size"[^}]*"TextValue":\s*"([^"]+)"',
                r"'Size'[^}]*'TextValue':\s*\"([^\"]+)\"",
            ]
            for pattern in size_patterns:
                size_matches = re.findall(pattern, product_text)
                for size_val in size_matches:
                    # Split pipe-separated sizes
                    sizes = [s.strip().lower() for s in size_val.split('|') if s.strip()]
                    attribute_values.extend(sizes)
                
        except Exception:
            pass
        
        # Check if any words from question match extracted attribute values
        question_words = re.findall(r'\b\w+\b', question_lower)
        for word in question_words:
            if len(word) > 2:  # Ignore very short words
                # Debug: uncomment to see what's being compared
                if 'trinidad' in word or 'ice' in word or 'gloves' in question_lower:
                    print(f"DEBUG: Question '{question}' word '{word}' against attributes: {attribute_values}")
                    if not attribute_values:  # If no attributes found, print sample of product text
                        print(f"DEBUG: Sample product text: {product_text[:500]}")
                
                # Direct match in attribute values
                if word in attribute_values:
                    return 3  # Perfect attribute match
                
                # Partial match for compound colors like "trinidad-ice"
                for attr_val in attribute_values:
                    if word in attr_val or attr_val in word:
                        return 3
                        
                # Check for size queries (m, l, xl, etc.)
                if word in ['small', 's', 'medium', 'm', 'large', 'l', 'xl', 'xxl', 'xxxl', 'xs']:
                    size_variants = {
                        'small': ['s', 'small'],
                        's': ['s', 'small'],
                        'medium': ['m', 'medium'],
                        'm': ['m', 'medium'],
                        'large': ['l', 'large'],
                        'l': ['l', 'large'],
                        'xl': ['xl', 'extra large'],
                        'xxl': ['xxl'],
                        'xxxl': ['xxxl'],
                        'xs': ['xs', 'extra small']
                    }
                    if word in size_variants:
                        for size_var in size_variants[word]:
                            if size_var in attribute_values:
                                return 3
        
        # Also check for category relevance
        category_score = self._score_category_agentic(question, product_text, product_text.split()[0] if product_text else "")
        return min(category_score, 1)  # Some relevance but not attribute specific
    
    def _score_description_agentic(self, question: str, product_text: str, product_name: str) -> int:
        """Score description-based matches"""
        # Extract key descriptive words from question
        descriptive_keywords = {
            'warm': ['warm', 'warmth', 'insulation', 'thermal'],
            'waterproof': ['waterproof', 'water-resistant', 'dry'],
            'lightweight': ['lightweight', 'light', 'packable'],
            'durable': ['durable', 'strong', 'tough'],
            'comfortable': ['comfortable', 'comfort', 'soft'],
            'breathable': ['breathable', 'ventilation'],
            'outdoor': ['outdoor', 'hiking', 'climbing', 'adventure'],
        }
        
        question_lower = question.lower()
        match_count = 0
        
        for concept, keywords in descriptive_keywords.items():
            if any(keyword in question_lower for keyword in keywords):
                if any(keyword in product_text for keyword in keywords):
                    match_count += 1
        
        if match_count >= 2:
            return 3  # Multiple concept matches
        elif match_count == 1:
            return 2  # Single concept match
        
        # Fallback to general matching
        return self._score_general_agentic(question, product_text, product_name)
    
    def _score_general_agentic(self, question: str, product_text: str, product_name: str) -> int:
        """General relevance scoring"""
        question_words = set(question.lower().split())
        product_words = set(product_text.split())
        
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'}
        question_words = question_words - stop_words
        product_words = product_words - stop_words
        
        if not question_words:
            return 0
            
        # Calculate word overlap
        overlap = len(question_words & product_words)
        overlap_ratio = overlap / len(question_words)
        
        if overlap_ratio >= 0.5:
            return 3
        elif overlap_ratio >= 0.3:
            return 2
        elif overlap_ratio >= 0.1:
            return 1
            
        return 0
    
    def _extract_retry_after_time(self, result: Dict) -> int:
        """Extract retry-after time from throttled request"""
        try:
            response_data = result.get('response_data', {})
            search_result = response_data.get('result', {})
            formatted_text = search_result.get('FormattedText', '')
            
            # Look for "Try again in X seconds" pattern
            import re
            retry_match = re.search(r'Try again in (\d+) seconds', formatted_text)
            if retry_match:
                return int(retry_match.group(1))
            
            return None
            
        except Exception:
            return None
    
    def _calculate_precision_recall_f1(self, relevance_scores: List[int], k: int) -> Tuple[float, float, float]:
        """Calculate Precision@K, Recall@K, and F1@K"""
        if not relevance_scores:
            return 0.0, 0.0, 0.0
        
        # Take top K results
        top_k_scores = relevance_scores[:k]
        
        # Count relevant items (score >= 2)
        relevant_in_k = sum(1 for score in top_k_scores if score >= 2)
        total_relevant = sum(1 for score in relevance_scores if score >= 2)
        
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
    
    def _calculate_average_precision(self, relevance_scores: List[int]) -> float:
        """Calculate Average Precision (AP)"""
        if not relevance_scores:
            return 0.0
        
        relevant_count = 0
        precision_sum = 0.0
        total_relevant = sum(1 for score in relevance_scores if score >= 2)
        
        if total_relevant == 0:
            return 0.0
        
        for i, score in enumerate(relevance_scores):
            if score >= 2:  # Relevant
                relevant_count += 1
                precision_at_i = relevant_count / (i + 1)
                precision_sum += precision_at_i
        
        return precision_sum / total_relevant
    
    def _calculate_reciprocal_rank(self, relevance_scores: List[int]) -> float:
        """Calculate Reciprocal Rank (RR)"""
        for i, score in enumerate(relevance_scores):
            if score >= 2:  # First relevant result
                return 1.0 / (i + 1)
        return 0.0
    
    def _calculate_coverage_metrics(self, search_results: List[Dict]) -> Dict[str, Any]:
        """Calculate coverage and result distribution metrics for agentic search"""
        formatted_text_counts = []
        zero_results = []
        successful_execution_count = 0
        
        for result in search_results:
            # Only count products from successfully executed searches
            if self._is_search_execution_successful(result):
                successful_execution_count += 1
                products = self._extract_agentic_products(result)
                count = len(products)
                formatted_text_counts.append(count)
                
                if count == 0:
                    zero_results.append(result)
            else:
                # Failed executions contribute to zero results
                zero_results.append(result)
        
        return {
            'total_products_returned': sum(formatted_text_counts),
            'avg_products_per_query': statistics.mean(formatted_text_counts) if formatted_text_counts else 0,
            'avg_products_per_successful_query': statistics.mean(formatted_text_counts) if formatted_text_counts else 0,
            'median_products_per_query': statistics.median(formatted_text_counts) if formatted_text_counts else 0,
            'zero_results_count': len(zero_results),
            'zero_results_rate': len(zero_results) / len(search_results) * 100 if search_results else 0,
            'successful_executions': successful_execution_count,
            'successful_execution_rate': successful_execution_count / len(search_results) * 100 if search_results else 0,
            'max_products_single_query': max(formatted_text_counts) if formatted_text_counts else 0,
            'min_products_single_query': min(formatted_text_counts) if formatted_text_counts else 0
        }
    
    def _calculate_detailed_analysis(self, search_results: List[Dict]) -> Dict[str, Any]:
        """Calculate detailed analysis including question types and categories"""
        question_types = Counter()
        categories = Counter()
        
        for result in search_results:
            test_context = result.get('test_case_context', {})
            query_metadata = result.get('query_metadata', {})
            
            # Use query_metadata if test_case_context is empty
            if not test_context and query_metadata:
                test_context = query_metadata
            
            q_type = test_context.get('question_type', 'Unknown')
            category = test_context.get('original_product_category', 'Unknown')
            
            question_types[q_type] += 1
            categories[category] += 1
        
        return {
            'question_type_distribution': dict(question_types),
            'product_category_distribution': dict(categories)
        }
    
    def _calculate_throttling_summary(self, search_results: List[Dict]) -> Dict[str, Any]:
        """Calculate detailed throttling and error summary"""
        throttled_requests = []
        other_errors = []
        successful_executions = []
        api_failures = []
        
        throttling_by_question_type = Counter()
        throttling_by_category = Counter()
        retry_after_times = []
        
        for result in search_results:
            test_context = result.get('test_case_context', {})
            query_metadata = result.get('query_metadata', {})
            
            # Use query_metadata if test_case_context is empty
            if not test_context and query_metadata:
                test_context = query_metadata
            
            q_type = test_context.get('question_type', 'Unknown')
            category = test_context.get('original_product_category', 'Unknown')
            
            if not result.get('success', False):
                api_failures.append(result)
                continue
            
            if self._is_search_execution_successful(result):
                successful_executions.append(result)
            elif self._is_throttled_request(result):
                throttled_requests.append(result)
                throttling_by_question_type[q_type] += 1
                throttling_by_category[category] += 1
                
                # Extract retry-after time if available
                retry_time = self._extract_retry_after_time(result)
                if retry_time:
                    retry_after_times.append(retry_time)
            else:
                other_errors.append(result)
        
        return {
            'total_requests': len(search_results),
            'successful_executions': len(successful_executions),
            'throttled_requests': len(throttled_requests),
            'other_errors': len(other_errors),
            'api_failures': len(api_failures),
            'throttling_rate': len(throttled_requests) / len(search_results) * 100 if search_results else 0,
            'success_rate': len(successful_executions) / len(search_results) * 100 if search_results else 0,
            'throttling_by_question_type': dict(throttling_by_question_type),
            'throttling_by_category': dict(throttling_by_category),
            'retry_after_analysis': {
                'retry_times_found': len(retry_after_times),
                'avg_retry_after_seconds': statistics.mean(retry_after_times) if retry_after_times else 0,
                'max_retry_after_seconds': max(retry_after_times) if retry_after_times else 0,
                'min_retry_after_seconds': min(retry_after_times) if retry_after_times else 0
            },
            'relevance_calculation_impact': {
                'requests_excluded_from_relevance': len(throttled_requests) + len(other_errors) + len(api_failures),
                'requests_included_in_relevance': len(successful_executions),
                'exclusion_percentage': (len(throttled_requests) + len(other_errors) + len(api_failures)) / len(search_results) * 100 if search_results else 0
            }
        }
    
    def _calculate_agentic_specific_metrics(self, search_results: List[Dict]) -> Dict[str, Any]:
        """Calculate metrics specific to agentic search API - only for successful executions"""
        activity_counts = Counter()
        planning_tokens = []
        search_operations = []
        total_steps = []
        references_counts = []
        
        # Only process successfully executed searches
        for result in search_results:
            if not result.get('success', False):
                continue
                
            # Skip throttled and error requests
            if not self._is_search_execution_successful(result):
                continue
                
            response_data = result.get('response_data', {})
            
            # Extract activity information
            activity_info = response_data.get('ActivityInfo', '')
            if 'AI planning:' in activity_info:
                planning_match = re.search(r'AI planning:\s*(\d+)', activity_info)
                if planning_match:
                    activity_counts['ai_planning'] += int(planning_match.group(1))
            
            if 'Search operations:' in activity_info:
                search_match = re.search(r'Search operations:\s*(\d+)', activity_info)
                if search_match:
                    search_operations.append(int(search_match.group(1)))
            
            if 'Total steps:' in activity_info:
                steps_match = re.search(r'Total steps:\s*(\d+)', activity_info)
                if steps_match:
                    total_steps.append(int(steps_match.group(1)))
            
            # Extract token usage
            query_planning_tokens = response_data.get('QueryPlanningTokens', '')
            if 'Input:' in query_planning_tokens and 'Output:' in query_planning_tokens:
                input_match = re.search(r'Input:\s*(\d+)', query_planning_tokens)
                output_match = re.search(r'Output:\s*(\d+)', query_planning_tokens)
                if input_match and output_match:
                    planning_tokens.append({
                        'input': int(input_match.group(1)),
                        'output': int(output_match.group(1))
                    })
            
            # Extract references count
            references_info = response_data.get('ReferencesInfo', '')
            if 'Referenced' in references_info:
                ref_match = re.search(r'Referenced\s*(\d+)\s*document', references_info)
                if ref_match:
                    references_counts.append(int(ref_match.group(1)))
        
        # Calculate statistics
        successful_count = len([r for r in search_results if r.get('success', False) and self._is_search_execution_successful(r)])
        
        return {
            'successful_executions_analyzed': successful_count,
            'activity_metrics': {
                'total_ai_planning_operations': activity_counts.get('ai_planning', 0),
                'avg_search_operations_per_query': statistics.mean(search_operations) if search_operations else 0,
                'avg_total_steps_per_query': statistics.mean(total_steps) if total_steps else 0,
                'search_operations_distribution': dict(Counter(search_operations))
            },
            'token_usage': {
                'avg_planning_input_tokens': statistics.mean([t['input'] for t in planning_tokens]) if planning_tokens else 0,
                'avg_planning_output_tokens': statistics.mean([t['output'] for t in planning_tokens]) if planning_tokens else 0,
                'total_planning_input_tokens': sum([t['input'] for t in planning_tokens]) if planning_tokens else 0,
                'total_planning_output_tokens': sum([t['output'] for t in planning_tokens]) if planning_tokens else 0
            },
            'knowledge_base_usage': {
                'avg_documents_referenced': statistics.mean(references_counts) if references_counts else 0,
                'max_documents_referenced': max(references_counts) if references_counts else 0,
                'min_documents_referenced': min(references_counts) if references_counts else 0,
                'references_distribution': dict(Counter(references_counts))
            }
        }
    
    def _print_analysis_report(self, analysis_results: Dict[str, Any]):
        """Print comprehensive analysis report for agentic search"""
        print("\n📋 AGENTIC SEARCH ENGINE EVALUATION REPORT")
        print("=" * 60)
        print("🤖 Specialized Analysis for Agentic Search API Results")
        
        # File info
        file_info = analysis_results['file_info']
        print(f"\n📁 FILE INFORMATION:")
        print(f"   File: {file_info['file_path']}")
        print(f"   Valid results: {file_info['valid_results']}")
        
        # Performance metrics
        perf = analysis_results['search_performance']
        print(f"\n⚡ PERFORMANCE METRICS:")
        print(f"   API Success rate: {perf['api_success_rate']:.1f}% ({perf['api_successful_calls']}/{perf['total_searches']})")
        print(f"   Search Execution Success rate: {perf['search_execution_success_rate']:.1f}% ({perf['search_execution_successful']}/{perf['total_searches']})")
        print(f"   Throttling rate: {perf['throttling_rate']:.1f}% ({perf['throttled_requests']} requests)")
        print(f"   Other errors: {perf['other_errors']} requests")
        print(f"   Average response time: {perf['avg_response_time_ms']:.1f}ms")
        print(f"   P95 response time: {perf['p95_response_time_ms']:.1f}ms")
        
        # Show error examples if available
        if perf['error_analysis']['throttled_examples']:
            print(f"\n   📝 THROTTLING ERROR EXAMPLES:")
            for i, error in enumerate(perf['error_analysis']['throttled_examples'][:2], 1):
                print(f"      {i}. {error[:100]}...")
        
        if perf['error_analysis']['other_error_examples']:
            print(f"\n   📝 OTHER ERROR EXAMPLES:")
            for i, error in enumerate(perf['error_analysis']['other_error_examples'][:2], 1):
                print(f"      {i}. {error[:100]}...")
        
        # Throttling Summary
        throttling = analysis_results['throttling_summary']
        print(f"\n🚫 THROTTLING & ERROR SUMMARY:")
        print(f"   Total requests: {throttling['total_requests']}")
        print(f"   Successfully executed: {throttling['successful_executions']} ({throttling['success_rate']:.1f}%)")
        print(f"   Throttled (TooManyRequests): {throttling['throttled_requests']} ({throttling['throttling_rate']:.1f}%)")
        print(f"   Other errors: {throttling['other_errors']}")
        print(f"   API failures: {throttling['api_failures']}")
        
        if throttling['retry_after_analysis']['retry_times_found'] > 0:
            retry_stats = throttling['retry_after_analysis']
            print(f"\n   ⏳ RETRY-AFTER ANALYSIS:")
            print(f"      Average retry time: {retry_stats['avg_retry_after_seconds']:.1f} seconds")
            print(f"      Max retry time: {retry_stats['max_retry_after_seconds']} seconds")
            print(f"      Min retry time: {retry_stats['min_retry_after_seconds']} seconds")
        
        print(f"\n   📊 RELEVANCE CALCULATION IMPACT:")
        rel_impact = throttling['relevance_calculation_impact']
        print(f"      Requests excluded from relevance metrics: {rel_impact['requests_excluded_from_relevance']} ({rel_impact['exclusion_percentage']:.1f}%)")
        print(f"      Requests included in relevance metrics: {rel_impact['requests_included_in_relevance']}")
        print(f"      Note: Precision/Recall calculated only on {rel_impact['requests_included_in_relevance']} successful executions")
        
        if throttling['throttling_by_question_type']:
            print(f"\n   🔍 THROTTLING BY QUESTION TYPE:")
            for q_type, count in sorted(throttling['throttling_by_question_type'].items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"      {q_type}: {count} throttled requests")
        
        # Agentic-specific metrics (only for successful executions)
        agentic = analysis_results['agentic_specific_metrics']
        print(f"\n🤖 AGENTIC SEARCH SPECIFIC METRICS (Successful Executions Only):")
        print(f"   Average search operations per query: {agentic['activity_metrics']['avg_search_operations_per_query']:.1f}")
        print(f"   Average total steps per query: {agentic['activity_metrics']['avg_total_steps_per_query']:.1f}")
        print(f"   Average documents referenced: {agentic['knowledge_base_usage']['avg_documents_referenced']:.1f}")
        print(f"   Average planning tokens (input/output): {agentic['token_usage']['avg_planning_input_tokens']:.0f}/{agentic['token_usage']['avg_planning_output_tokens']:.0f}")
        
        # Coverage metrics
        coverage = analysis_results['coverage_metrics']
        print(f"\n📊 COVERAGE METRICS:")
        print(f"   Successful search executions: {coverage['successful_executions']} ({coverage['successful_execution_rate']:.1f}%)")
        print(f"   Total products returned: {coverage['total_products_returned']}")
        print(f"   Average products per successful query: {coverage['avg_products_per_successful_query']:.1f}")
        print(f"   Zero results rate: {coverage['zero_results_rate']:.1f}% (includes failed executions)")
        
        # Relevance metrics
        relevance = analysis_results['relevance_metrics']
        print(f"\n🎯 RELEVANCE METRICS (Question-Type Aware):")
        
        print(f"\n   📏 PRECISION@K:")
        for metric, value in relevance['precision_at_k'].items():
            print(f"      {metric}: {value:.3f}")
        
        print(f"\n   📏 RECALL@K:")
        for metric, value in relevance['recall_at_k'].items():
            print(f"      {metric}: {value:.3f}")
        
        print(f"\n   📏 RANKING QUALITY:")
        print(f"      MAP: {relevance['map_score']:.3f}")
        print(f"      MRR: {relevance['mrr_score']:.3f}")
        
        # Question type breakdown
        print(f"\n   🔍 QUESTION TYPE PERFORMANCE:")
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
            print(f"\n💾 Agentic search analysis saved to: {output_file}")
        except Exception as e:
            print(f"❌ Error saving analysis: {e}")

def main():
    """Main function"""
    if len(sys.argv) != 2:
        print("Usage: python analyze_agentic_search_results.py <jsonl_file_path>")
        print("Example: python analyze_agentic_search_results.py test_case_acs_analysis/agentic_results_20250815_025254_results.jsonl")
        sys.exit(1)
    
    jsonl_file = sys.argv[1]
    
    if not os.path.exists(jsonl_file):
        print(f"❌ File not found: {jsonl_file}")
        sys.exit(1)
    
    analyzer = AgenticSearchAnalyzer()
    results = analyzer.analyze_jsonl_results(jsonl_file)
    
    if results:
        print(f"\n✅ Agentic search analysis completed!")
    else:
        print(f"\n❌ Analysis failed!")

if __name__ == "__main__":
    main()
