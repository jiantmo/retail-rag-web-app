#!/usr/bin/env python3
"""
Search Results Analysis Tool
Analyzes JSONL search results to evaluate if answers match questions
Generates comprehensive analysis summary similar to ANALYSIS_SUMMARY.json
"""

import json
import sys
import os
from datetime import datetime
from collections import defaultdict, Counter
import re
from pathlib import Path

class SearchResultsAnalyzer:
    def __init__(self, jsonl_file_path):
        self.jsonl_file_path = jsonl_file_path
        self.results = []
        self.analysis_metrics = {
            'total_questions': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'questions_with_results': 0,
            'questions_without_results': 0,
            'answer_relevance_scores': [],
            'question_types': defaultdict(int),
            'error_types': defaultdict(int),
            'source_files': defaultdict(int),
            'response_times': [],
            'result_counts': []
        }
        
    def load_and_process_jsonl(self):
        """Load and process the JSONL file in chunks to handle large files"""
        print(f"📁 Loading results from: {self.jsonl_file_path}")
        
        try:
            with open(self.jsonl_file_path, 'r', encoding='utf-8') as f:
                line_count = 0
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                        
                    try:
                        result = json.loads(line)
                        self.results.append(result)
                        line_count += 1
                        
                        # Progress indicator for large files
                        if line_count % 1000 == 0:
                            print(f"   Processed {line_count:,} lines...")
                            
                    except json.JSONDecodeError as e:
                        print(f"⚠️ Skipping malformed JSON line {line_count + 1}: {e}")
                        continue
                        
            print(f"✅ Successfully loaded {len(self.results):,} search results")
            return True
            
        except Exception as e:
            print(f"❌ Error loading file: {e}")
            return False
    
    def analyze_question_type(self, question):
        """Categorize question types based on content patterns"""
        question_lower = question.lower()
        
        # Define question type patterns
        patterns = {
            'product_search': [r'\b(find|search|show|get)\b.*\b(product|item)\b', r'\bwhere can i find\b', r'\bdo you have\b'],
            'price_inquiry': [r'\b(price|cost|how much|expensive|cheap)\b', r'\$\d+', r'\bcost\b'],
            'availability': [r'\b(available|in stock|out of stock|availability)\b'],
            'comparison': [r'\b(compare|difference|better|vs|versus)\b', r'\bwhich is\b'],
            'specification': [r'\b(spec|feature|dimension|size|weight|material)\b'],
            'compatibility': [r'\b(compatible|work with|fits|supports)\b'],
            'recommendation': [r'\b(recommend|suggest|best|top)\b'],
            'location_store': [r'\b(store|location|where|nearby)\b'],
            'general_info': [r'\b(what|how|when|why|tell me)\b']
        }
        
        for q_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, question_lower):
                    return q_type
        
        return 'other'
    
    def evaluate_answer_relevance(self, question, search_results):
        """Evaluate how well the search results answer the question"""
        if not search_results or not isinstance(search_results, dict):
            return 0, "No search results returned"
        
        # Extract query result data
        query_result = search_results.get('queryResult', {})
        if not query_result:
            return 0, "No query result in response"
            
        results_list = query_result.get('result', [])
        if not results_list or len(results_list) == 0:
            return 10, "No results found for query"
        
        question_lower = question.lower()
        score = 0
        evaluation_notes = []
        
        # Check if we have actual product results
        if isinstance(results_list, list) and len(results_list) > 0:
            score += 30  # Base score for having results
            evaluation_notes.append(f"Found {len(results_list)} results")
            
            # Analyze first few results for relevance
            for i, result in enumerate(results_list[:3]):  # Check top 3 results
                if isinstance(result, dict):
                    # Check product name relevance
                    product_name = result.get('name', '').lower()
                    description = result.get('description', '').lower()
                    
                    # Extract key terms from question
                    question_terms = re.findall(r'\b\w{3,}\b', question_lower)
                    question_terms = [term for term in question_terms if term not in ['the', 'and', 'with', 'for', 'are', 'can', 'you', 'how', 'what', 'where', 'when']]
                    
                    # Check term matches
                    name_matches = sum(1 for term in question_terms if term in product_name)
                    desc_matches = sum(1 for term in question_terms if term in description)
                    
                    if name_matches > 0:
                        score += 20  # Product name matches question terms
                        evaluation_notes.append(f"Product name matches: {name_matches} terms")
                    
                    if desc_matches > 0:
                        score += 10  # Description matches question terms
                        evaluation_notes.append(f"Description matches: {desc_matches} terms")
                    
                    # Check for specific question types
                    if 'price' in question_lower and ('price' in result or 'cost' in result):
                        score += 15
                        evaluation_notes.append("Price information available")
                    
                    if 'available' in question_lower and ('availability' in result or 'stock' in result):
                        score += 15
                        evaluation_notes.append("Availability information available")
        
        # Quality adjustments
        if len(results_list) > 10:
            score += 5  # Bonus for comprehensive results
        elif len(results_list) < 3:
            score -= 5  # Penalty for too few results
            
        # Cap the score at 100
        score = min(100, max(0, score))
        
        return score, "; ".join(evaluation_notes)
    
    def analyze_results(self):
        """Perform comprehensive analysis of all search results"""
        print("🔍 Analyzing search results...")
        
        relevance_scores = []
        source_file_stats = defaultdict(lambda: {'questions': 0, 'scores': []})
        
        for i, result in enumerate(self.results):
            if (i + 1) % 500 == 0:
                print(f"   Analyzed {i + 1:,} results...")
                
            # Extract basic metrics
            self.analysis_metrics['total_questions'] += 1
            
            success = result.get('success', False)
            if success:
                self.analysis_metrics['successful_requests'] += 1
            else:
                self.analysis_metrics['failed_requests'] += 1
                error_type = result.get('error_type', 'Unknown')
                self.analysis_metrics['error_types'][error_type] += 1
            
            # Extract timing and result count data
            response_time = result.get('response_time_seconds', 0)
            result_count = result.get('result_count', 0)
            
            self.analysis_metrics['response_times'].append(response_time)
            self.analysis_metrics['result_counts'].append(result_count)
            
            if result_count > 0:
                self.analysis_metrics['questions_with_results'] += 1
            else:
                self.analysis_metrics['questions_without_results'] += 1
            
            # Analyze question and answer relevance
            question = result.get('question', '')
            source_file = result.get('source_file', 'unknown')
            
            if question:
                # Categorize question type
                q_type = self.analyze_question_type(question)
                self.analysis_metrics['question_types'][q_type] += 1
                
                # Evaluate answer relevance
                if success and 'response_data' in result:
                    relevance_score, evaluation_note = self.evaluate_answer_relevance(question, result['response_data'])
                    relevance_scores.append(relevance_score)
                    
                    # Track by source file
                    source_file_stats[source_file]['questions'] += 1
                    source_file_stats[source_file]['scores'].append(relevance_score)
                    
                    # Store detailed evaluation (optional, for debugging)
                    if hasattr(self, 'store_detailed_evaluations') and self.store_detailed_evaluations:
                        result['relevance_score'] = relevance_score
                        result['evaluation_note'] = evaluation_note
                else:
                    relevance_scores.append(0)  # Failed requests get 0 score
                    source_file_stats[source_file]['questions'] += 1
                    source_file_stats[source_file]['scores'].append(0)
        
        self.analysis_metrics['answer_relevance_scores'] = relevance_scores
        self.source_file_stats = source_file_stats
        
        print(f"✅ Analysis complete!")
        return True
    
    def generate_analysis_summary(self):
        """Generate analysis summary in the same format as ANALYSIS_SUMMARY.json"""
        print("📊 Generating analysis summary...")
        
        # Calculate overall metrics
        total_questions = self.analysis_metrics['total_questions']
        relevance_scores = self.analysis_metrics['answer_relevance_scores']
        average_score = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
        
        # Calculate response time metrics
        response_times = self.analysis_metrics['response_times']
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Calculate result count metrics
        result_counts = self.analysis_metrics['result_counts']
        avg_result_count = sum(result_counts) / len(result_counts) if result_counts else 0
        
        # Generate file details
        file_details = []
        for source_file, stats in self.source_file_stats.items():
            if stats['questions'] > 0:
                file_avg_score = sum(stats['scores']) / len(stats['scores']) if stats['scores'] else 0
                file_details.append({
                    "FileName": Path(source_file).name,
                    "QuestionCount": stats['questions'],
                    "AverageScore": round(file_avg_score, 2),
                    "SuccessfulRequests": sum(1 for score in stats['scores'] if score > 0),
                    "FailedRequests": sum(1 for score in stats['scores'] if score == 0)
                })
        
        # Sort by filename
        file_details.sort(key=lambda x: x['FileName'])
        
        # Create comprehensive summary
        summary = {
            "GeneratedAt": datetime.now().isoformat(),
            "SourceFile": Path(self.jsonl_file_path).name,
            "TotalQuestions": total_questions,
            "AverageScore": round(average_score, 2),
            "OverallMetrics": {
                "SuccessfulRequests": self.analysis_metrics['successful_requests'],
                "FailedRequests": self.analysis_metrics['failed_requests'],
                "SuccessRate": round((self.analysis_metrics['successful_requests'] / total_questions * 100), 2) if total_questions > 0 else 0,
                "QuestionsWithResults": self.analysis_metrics['questions_with_results'],
                "QuestionsWithoutResults": self.analysis_metrics['questions_without_results'],
                "AverageResponseTime": round(avg_response_time, 3),
                "AverageResultCount": round(avg_result_count, 1)
            },
            "ScoreDistribution": {
                "Excellent (90-100)": sum(1 for score in relevance_scores if score >= 90),
                "Good (70-89)": sum(1 for score in relevance_scores if 70 <= score < 90),
                "Fair (50-69)": sum(1 for score in relevance_scores if 50 <= score < 70),
                "Poor (30-49)": sum(1 for score in relevance_scores if 30 <= score < 50),
                "Failed (0-29)": sum(1 for score in relevance_scores if score < 30)
            },
            "QuestionTypes": dict(self.analysis_metrics['question_types']),
            "ErrorAnalysis": dict(self.analysis_metrics['error_types']) if self.analysis_metrics['error_types'] else {},
            "FileDetails": file_details,
            "TotalFiles": len(file_details)
        }
        
        return summary
    
    def save_analysis_summary(self, output_path=None):
        """Save the analysis summary to a JSON file"""
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"search_analysis_summary_{timestamp}.json"
        
        summary = self.generate_analysis_summary()
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=4, ensure_ascii=False)
            
            print(f"✅ Analysis summary saved to: {output_path}")
            return output_path, summary
            
        except Exception as e:
            print(f"❌ Error saving analysis summary: {e}")
            return None, summary
    
    def print_summary_stats(self, summary):
        """Print key statistics to console"""
        print("\n" + "="*60)
        print("📊 SEARCH RESULTS ANALYSIS SUMMARY")
        print("="*60)
        print(f"📁 Source File: {summary['SourceFile']}")
        print(f"📝 Total Questions: {summary['TotalQuestions']:,}")
        print(f"⭐ Average Relevance Score: {summary['AverageScore']:.2f}/100")
        print(f"✅ Success Rate: {summary['OverallMetrics']['SuccessRate']:.1f}%")
        print(f"📊 Questions with Results: {summary['OverallMetrics']['QuestionsWithResults']:,}")
        print(f"❌ Questions without Results: {summary['OverallMetrics']['QuestionsWithoutResults']:,}")
        print(f"⏱️  Average Response Time: {summary['OverallMetrics']['AverageResponseTime']:.3f}s")
        print(f"🔢 Average Result Count: {summary['OverallMetrics']['AverageResultCount']:.1f}")
        
        print(f"\n📈 Score Distribution:")
        for category, count in summary['ScoreDistribution'].items():
            percentage = (count / summary['TotalQuestions'] * 100) if summary['TotalQuestions'] > 0 else 0
            print(f"   {category}: {count:,} ({percentage:.1f}%)")
        
        print(f"\n📂 Files Analyzed: {summary['TotalFiles']}")
        if summary['ErrorAnalysis']:
            print(f"\n❌ Error Types:")
            for error_type, count in summary['ErrorAnalysis'].items():
                print(f"   {error_type}: {count:,}")
        
        print("="*60)

def main():
    """Main execution function"""
    # Check command line arguments
    if len(sys.argv) > 1:
        jsonl_file = sys.argv[1]
    else:
        # Default to the specified file
        jsonl_file = r"c:\github\retail-rag-web-app\dataverse_results_20250806_225629_results.jsonl"
    
    # Verify file exists
    if not os.path.exists(jsonl_file):
        print(f"❌ File not found: {jsonl_file}")
        print("Usage: python analyze_search_results.py [path_to_jsonl_file]")
        return 1
    
    print("🚀 Search Results Analysis Tool")
    print("="*60)
    
    # Initialize analyzer
    analyzer = SearchResultsAnalyzer(jsonl_file)
    
    # Load and process the data
    if not analyzer.load_and_process_jsonl():
        return 1
    
    # Perform analysis
    if not analyzer.analyze_results():
        return 1
    
    # Generate and save summary
    output_path, summary = analyzer.save_analysis_summary()
    if output_path:
        analyzer.print_summary_stats(summary)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
