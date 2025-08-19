#!/usr/bin/env python3
"""
Search Engine Comparison Analysis
Compare Agentic Search vs Dataverse Search performance metrics
Generate comprehensive Excel report with detailed comparisons
"""

import json
import pandas as pd
from datetime import datetime
import os
from pathlib import Path

class SearchComparisonAnalyzer:
    def __init__(self):
        self.agentic_data = None
        self.dataverse_data = None
        self.comparison_results = {}
        
    def load_analysis_files(self, agentic_file, dataverse_file):
        """Load both analysis files"""
        print("📊 Loading analysis files...")
        
        # Load Agentic Search Results
        with open(agentic_file, 'r', encoding='utf-8') as f:
            self.agentic_data = json.load(f)
        print(f"✅ Loaded agentic search data: {len(self.agentic_data)} keys")
        
        # Load Dataverse Search Results  
        with open(dataverse_file, 'r', encoding='utf-8') as f:
            self.dataverse_data = json.load(f)
        print(f"✅ Loaded dataverse search data: {len(self.dataverse_data)} keys")
        
    def extract_key_metrics(self):
        """Extract key metrics for comparison"""
        print("🔍 Extracting key metrics...")
        
        # Performance Metrics
        agentic_perf = self.agentic_data['search_performance']
        dataverse_perf = self.dataverse_data['search_performance']
        
        # Relevance Metrics
        agentic_rel = self.agentic_data['relevance_metrics']
        dataverse_rel = self.dataverse_data['relevance_metrics']
        
        # Coverage Metrics
        agentic_cov = self.agentic_data['coverage_metrics']
        dataverse_cov = self.dataverse_data['coverage_metrics']
        
        return {
            'performance': {
                'agentic': agentic_perf,
                'dataverse': dataverse_perf
            },
            'relevance': {
                'agentic': agentic_rel,
                'dataverse': dataverse_rel
            },
            'coverage': {
                'agentic': agentic_cov,
                'dataverse': dataverse_cov
            }
        }
    
    def create_performance_comparison(self, metrics):
        """Create performance comparison dataframe"""
        print("⚡ Creating performance comparison...")
        
        agentic = metrics['performance']['agentic']
        dataverse = metrics['performance']['dataverse']
        
        performance_data = {
            'Metric': [
                'Total Searches',
                'Successful Searches', 
                'Success Rate (%)',
                'Average Response Time (ms)',
                'Median Response Time (ms)',
                'P95 Response Time (ms)',
                'P99 Response Time (ms)',
                'Min Response Time (ms)',
                'Max Response Time (ms)',
                'Zero Results Rate (%)'
            ],
            'Agentic Search': [
                agentic.get('total_searches', 0),
                agentic.get('search_execution_successful', 0),
                round(agentic.get('search_execution_success_rate', 0), 2),
                round(agentic.get('avg_response_time_ms', 0), 2),
                round(agentic.get('median_response_time_ms', 0), 2),
                round(agentic.get('p95_response_time_ms', 0), 2),
                round(agentic.get('p99_response_time_ms', 0), 2),
                round(agentic.get('min_response_time_ms', 0), 2),
                round(agentic.get('max_response_time_ms', 0), 2),
                round(self.agentic_data['coverage_metrics'].get('zero_results_rate', 0), 2)
            ],
            'Dataverse Search': [
                dataverse.get('total_searches', 0),
                dataverse.get('successful_searches', 0),
                round(dataverse.get('success_rate', 0), 2),
                round(dataverse.get('avg_response_time_ms', 0), 2),
                round(dataverse.get('median_response_time_ms', 0), 2),
                round(dataverse.get('p95_response_time_ms', 0), 2),
                round(dataverse.get('p99_response_time_ms', 0), 2),
                round(dataverse.get('min_response_time_ms', 0), 2),
                round(dataverse.get('max_response_time_ms', 0), 2),
                round(self.dataverse_data['coverage_metrics'].get('zero_results_rate', 0), 2)
            ]
        }
        
        # Calculate differences and improvements
        performance_data['Difference (A-D)'] = []
        performance_data['% Improvement'] = []
        
        for i, metric in enumerate(performance_data['Metric']):
            agentic_val = performance_data['Agentic Search'][i]
            dataverse_val = performance_data['Dataverse Search'][i]
            
            if isinstance(agentic_val, (int, float)) and isinstance(dataverse_val, (int, float)):
                diff = agentic_val - dataverse_val
                performance_data['Difference (A-D)'].append(round(diff, 2))
                
                if dataverse_val != 0:
                    improvement = ((agentic_val - dataverse_val) / dataverse_val) * 100
                    performance_data['% Improvement'].append(f"{improvement:.1f}%")
                else:
                    performance_data['% Improvement'].append("N/A")
            else:
                performance_data['Difference (A-D)'].append("N/A")
                performance_data['% Improvement'].append("N/A")
        
        return pd.DataFrame(performance_data)
    
    def create_relevance_comparison(self, metrics):
        """Create relevance metrics comparison dataframe"""
        print("🎯 Creating relevance comparison...")
        
        agentic = metrics['relevance']['agentic']
        dataverse = metrics['relevance']['dataverse']
        
        relevance_data = {
            'Metric': [
                'Precision@1',
                'Precision@3', 
                'Precision@5',
                'Precision@10',
                'Recall@1',
                'Recall@3',
                'Recall@5',
                'Recall@10',
                'F1@1',
                'F1@3',
                'F1@5',
                'F1@10',
                'NDCG@1',
                'NDCG@3',
                'NDCG@5',
                'NDCG@10',
                'MAP Score',
                'MRR Score'
            ],
            'Agentic Search': [
                round(agentic['precision_at_k']['P@1'], 4),
                round(agentic['precision_at_k']['P@3'], 4),
                round(agentic['precision_at_k']['P@5'], 4),
                round(agentic['precision_at_k']['P@10'], 4),
                round(agentic['recall_at_k']['R@1'], 4),
                round(agentic['recall_at_k']['R@3'], 4),
                round(agentic['recall_at_k']['R@5'], 4),
                round(agentic['recall_at_k']['R@10'], 4),
                round(agentic['f1_score_at_k']['F1@1'], 4),
                round(agentic['f1_score_at_k']['F1@3'], 4),
                round(agentic['f1_score_at_k']['F1@5'], 4),
                round(agentic['f1_score_at_k']['F1@10'], 4),
                round(agentic['ndcg_at_k']['NDCG@1'], 4),
                round(agentic['ndcg_at_k']['NDCG@3'], 4),
                round(agentic['ndcg_at_k']['NDCG@5'], 4),
                round(agentic['ndcg_at_k']['NDCG@10'], 4),
                round(agentic['map_score'], 4),
                round(agentic['mrr_score'], 4)
            ],
            'Dataverse Search': [
                round(dataverse['precision_at_k']['P@1'], 4),
                round(dataverse['precision_at_k']['P@3'], 4),
                round(dataverse['precision_at_k']['P@5'], 4),
                round(dataverse['precision_at_k']['P@10'], 4),
                round(dataverse['recall_at_k']['R@1'], 4),
                round(dataverse['recall_at_k']['R@3'], 4),
                round(dataverse['recall_at_k']['R@5'], 4),
                round(dataverse['recall_at_k']['R@10'], 4),
                round(dataverse['f1_score_at_k']['F1@1'], 4),
                round(dataverse['f1_score_at_k']['F1@3'], 4),
                round(dataverse['f1_score_at_k']['F1@5'], 4),
                round(dataverse['f1_score_at_k']['F1@10'], 4),
                round(dataverse['ndcg_at_k']['NDCG@1'], 4),
                round(dataverse['ndcg_at_k']['NDCG@3'], 4),
                round(dataverse['ndcg_at_k']['NDCG@5'], 4),
                round(dataverse['ndcg_at_k']['NDCG@10'], 4),
                round(dataverse['map_score'], 4),
                round(dataverse['mrr_score'], 4)
            ]
        }
        
        # Calculate differences and improvements
        relevance_data['Difference (A-D)'] = []
        relevance_data['% Improvement'] = []
        
        for i in range(len(relevance_data['Metric'])):
            agentic_val = relevance_data['Agentic Search'][i]
            dataverse_val = relevance_data['Dataverse Search'][i]
            
            diff = agentic_val - dataverse_val
            relevance_data['Difference (A-D)'].append(round(diff, 4))
            
            if dataverse_val != 0:
                improvement = ((agentic_val - dataverse_val) / dataverse_val) * 100
                relevance_data['% Improvement'].append(f"{improvement:.1f}%")
            else:
                relevance_data['% Improvement'].append("N/A")
        
        return pd.DataFrame(relevance_data)
    
    def create_question_type_comparison(self, metrics):
        """Create question type breakdown comparison"""
        print("❓ Creating question type comparison...")
        
        agentic_qtypes = metrics['relevance']['agentic']['question_type_breakdown']
        dataverse_qtypes = metrics['relevance']['dataverse']['question_type_breakdown']
        
        # Create comparison for each question type
        question_types = ['Exact word', 'Category', 'Category + Price range', 'Category + Attribute value', 'Description']
        
        comparison_data = []
        for qtype in question_types:
            if qtype in agentic_qtypes and qtype in dataverse_qtypes:
                agentic_q = agentic_qtypes[qtype]
                dataverse_q = dataverse_qtypes[qtype]
                
                comparison_data.append({
                    'Question Type': qtype,
                    'Metric': 'Precision@1',
                    'Agentic': round(agentic_q['precision_at_k']['P@1'], 4),
                    'Dataverse': round(dataverse_q['precision_at_k']['P@1'], 4),
                    'Difference': round(agentic_q['precision_at_k']['P@1'] - dataverse_q['precision_at_k']['P@1'], 4)
                })
                
                comparison_data.append({
                    'Question Type': qtype,
                    'Metric': 'Recall@10',
                    'Agentic': round(agentic_q['recall_at_k']['R@10'], 4),
                    'Dataverse': round(dataverse_q['recall_at_k']['R@10'], 4),
                    'Difference': round(agentic_q['recall_at_k']['R@10'] - dataverse_q['recall_at_k']['R@10'], 4)
                })
                
                comparison_data.append({
                    'Question Type': qtype,
                    'Metric': 'F1@5',
                    'Agentic': round(agentic_q['f1_score_at_k']['F1@5'], 4),
                    'Dataverse': round(dataverse_q['f1_score_at_k']['F1@5'], 4),
                    'Difference': round(agentic_q['f1_score_at_k']['F1@5'] - dataverse_q['f1_score_at_k']['F1@5'], 4)
                })
                
                comparison_data.append({
                    'Question Type': qtype,
                    'Metric': 'NDCG@10',
                    'Agentic': round(agentic_q['ndcg_at_k']['NDCG@10'], 4),
                    'Dataverse': round(dataverse_q['ndcg_at_k']['NDCG@10'], 4),
                    'Difference': round(agentic_q['ndcg_at_k']['NDCG@10'] - dataverse_q['ndcg_at_k']['NDCG@10'], 4)
                })
        
        return pd.DataFrame(comparison_data)
    
    def create_executive_summary(self, performance_df, relevance_df):
        """Create executive summary of key findings"""
        print("📋 Creating executive summary...")
        
        # Key performance insights
        agentic_success_rate = performance_df[performance_df['Metric'] == 'Success Rate (%)']['Agentic Search'].iloc[0]
        dataverse_success_rate = performance_df[performance_df['Metric'] == 'Success Rate (%)']['Dataverse Search'].iloc[0]
        
        agentic_avg_time = performance_df[performance_df['Metric'] == 'Average Response Time (ms)']['Agentic Search'].iloc[0]
        dataverse_avg_time = performance_df[performance_df['Metric'] == 'Average Response Time (ms)']['Dataverse Search'].iloc[0]
        
        # Key relevance insights
        agentic_map = relevance_df[relevance_df['Metric'] == 'MAP Score']['Agentic Search'].iloc[0]
        dataverse_map = relevance_df[relevance_df['Metric'] == 'MAP Score']['Dataverse Search'].iloc[0]
        
        agentic_ndcg10 = relevance_df[relevance_df['Metric'] == 'NDCG@10']['Agentic Search'].iloc[0]
        dataverse_ndcg10 = relevance_df[relevance_df['Metric'] == 'NDCG@10']['Dataverse Search'].iloc[0]
        
        summary_data = {
            'Key Insight': [
                'Search Success Rate',
                'Average Response Time',
                'Search Quality (MAP Score)',
                'Ranking Quality (NDCG@10)',
                'Precision@1 (Immediate Relevance)',
                'Recall@10 (Coverage)',
                'Throttling Impact',
                'Zero Results Rate'
            ],
            'Agentic Search': [
                f"{agentic_success_rate}%",
                f"{agentic_avg_time} ms",
                f"{agentic_map:.4f}",
                f"{agentic_ndcg10:.4f}",
                f"{relevance_df[relevance_df['Metric'] == 'Precision@1']['Agentic Search'].iloc[0]:.4f}",
                f"{relevance_df[relevance_df['Metric'] == 'Recall@10']['Agentic Search'].iloc[0]:.4f}",
                f"{self.agentic_data['search_performance'].get('throttling_rate', 0):.1f}%",
                f"{self.agentic_data['coverage_metrics'].get('zero_results_rate', 0):.1f}%"
            ],
            'Dataverse Search': [
                f"{dataverse_success_rate}%",
                f"{dataverse_avg_time} ms",
                f"{dataverse_map:.4f}",
                f"{dataverse_ndcg10:.4f}",
                f"{relevance_df[relevance_df['Metric'] == 'Precision@1']['Dataverse Search'].iloc[0]:.4f}",
                f"{relevance_df[relevance_df['Metric'] == 'Recall@10']['Dataverse Search'].iloc[0]:.4f}",
                "0.0%",
                f"{self.dataverse_data['coverage_metrics'].get('zero_results_rate', 0):.1f}%"
            ],
            'Winner': [
                'Dataverse' if dataverse_success_rate > agentic_success_rate else 'Agentic',
                'Agentic' if agentic_avg_time < dataverse_avg_time else 'Dataverse',
                'Dataverse' if dataverse_map > agentic_map else 'Agentic',
                'Dataverse' if dataverse_ndcg10 > agentic_ndcg10 else 'Agentic',
                'Dataverse' if relevance_df[relevance_df['Metric'] == 'Precision@1']['Dataverse Search'].iloc[0] > relevance_df[relevance_df['Metric'] == 'Precision@1']['Agentic Search'].iloc[0] else 'Agentic',
                'Dataverse' if relevance_df[relevance_df['Metric'] == 'Recall@10']['Dataverse Search'].iloc[0] > relevance_df[relevance_df['Metric'] == 'Recall@10']['Agentic Search'].iloc[0] else 'Agentic',
                'Dataverse',
                'Agentic' if self.agentic_data['coverage_metrics'].get('zero_results_rate', 0) < self.dataverse_data['coverage_metrics'].get('zero_results_rate', 0) else 'Dataverse'
            ]
        }
        
        return pd.DataFrame(summary_data)
    
    def generate_excel_report(self, output_file):
        """Generate comprehensive Excel report"""
        print("📊 Generating Excel report...")
        
        # Extract metrics
        metrics = self.extract_key_metrics()
        
        # Create comparison dataframes
        performance_df = self.create_performance_comparison(metrics)
        relevance_df = self.create_relevance_comparison(metrics)
        question_type_df = self.create_question_type_comparison(metrics)
        summary_df = self.create_executive_summary(performance_df, relevance_df)
        
        # Write to Excel with multiple sheets
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Executive Summary
            summary_df.to_excel(writer, sheet_name='Executive Summary', index=False)
            
            # Performance Comparison
            performance_df.to_excel(writer, sheet_name='Performance Metrics', index=False)
            
            # Relevance Comparison
            relevance_df.to_excel(writer, sheet_name='Relevance Metrics', index=False)
            
            # Question Type Breakdown
            question_type_df.to_excel(writer, sheet_name='Question Type Analysis', index=False)
            
            # Raw Data Summary
            raw_data = {
                'Data Source': [
                    'Agentic Search File',
                    'Dataverse Search File',
                    'Agentic Total Queries',
                    'Dataverse Total Queries',
                    'Agentic Successful Queries',
                    'Dataverse Successful Queries',
                    'Analysis Generated'
                ],
                'Value': [
                    'agentic_results_20250818_002606_results_agentic_analysis.json',
                    'dataverse_results_20250815_014501_results_enhanced_analysis.json',
                    self.agentic_data['search_performance']['total_searches'],
                    self.dataverse_data['search_performance']['total_searches'],
                    self.agentic_data['search_performance']['search_execution_successful'],
                    self.dataverse_data['search_performance']['successful_searches'],
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ]
            }
            pd.DataFrame(raw_data).to_excel(writer, sheet_name='Data Sources', index=False)
        
        print(f"✅ Excel report generated: {output_file}")
        return output_file

def main():
    """Main function to run the comparison analysis"""
    print("🔍 Search Engine Comparison Analysis")
    print("="*50)
    
    # Initialize analyzer
    analyzer = SearchComparisonAnalyzer()
    
    # File paths
    agentic_file = "test_case_acs_analysis/agentic_results_20250818_002606_results_agentic_analysis.json"
    dataverse_file = "test_case_analysis/dataverse_results_20250815_014501_results_enhanced_analysis.json"
    
    # Check if files exist
    if not os.path.exists(agentic_file):
        print(f"❌ Agentic file not found: {agentic_file}")
        return
    
    if not os.path.exists(dataverse_file):
        print(f"❌ Dataverse file not found: {dataverse_file}")
        return
    
    # Load data
    analyzer.load_analysis_files(agentic_file, dataverse_file)
    
    # Generate output filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"search_comparison_analysis_{timestamp}.xlsx"
    
    # Generate Excel report
    report_file = analyzer.generate_excel_report(output_file)
    
    print("\n📊 Analysis Complete!")
    print(f"📄 Report saved as: {report_file}")
    print("\n🔍 Key Findings:")
    print("- Performance metrics comparison between Agentic and Dataverse search")
    print("- Relevance metrics breakdown by question type")
    print("- Executive summary with winner analysis")
    print("- Detailed question type performance analysis")
    
    return report_file

if __name__ == "__main__":
    main()
