#!/usr/bin/env python3
"""
Updated Search System Comparison Analysis with Unified Scoring Logic
Compares Dataverse and Agentic search systems using the new unified relevance scorer.
"""

import json
import pandas as pd
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UpdatedSearchComparisonAnalyzer:
    def __init__(self):
        self.dataverse_analysis = None
        self.agentic_analysis = None
        self.comparison_summary = {}
        
    def load_analysis_files(self, dataverse_file, agentic_file):
        """Load the analysis results from both search systems"""
        try:
            # Load dataverse analysis
            with open(dataverse_file, 'r', encoding='utf-8') as f:
                self.dataverse_analysis = json.load(f)
            logger.info(f"✅ Loaded dataverse analysis: {dataverse_file}")
            
            # Load agentic analysis  
            with open(agentic_file, 'r', encoding='utf-8') as f:
                self.agentic_analysis = json.load(f)
            logger.info(f"✅ Loaded agentic analysis: {agentic_file}")
            
        except Exception as e:
            logger.error(f"❌ Error loading analysis files: {e}")
            raise
    
    def extract_metrics(self):
        """Extract key metrics from both analyses for comparison"""
        
        # Dataverse metrics
        dv_metrics = {
            'system': 'Dataverse',
            'total_queries': self.dataverse_analysis['file_info']['total_lines'],
            'valid_results': self.dataverse_analysis['file_info']['valid_results'],
            'success_rate': self.dataverse_analysis['search_performance']['success_rate'],
            'avg_response_time': self.dataverse_analysis['search_performance']['avg_response_time_ms'],
            'p95_response_time': self.dataverse_analysis['search_performance']['p95_response_time_ms'],
            'precision_at_1': self.dataverse_analysis['relevance_metrics']['precision_at_k']['P@1'],
            'precision_at_5': self.dataverse_analysis['relevance_metrics']['precision_at_k']['P@5'],
            'precision_at_10': self.dataverse_analysis['relevance_metrics']['precision_at_k']['P@10'],
            'recall_at_1': self.dataverse_analysis['relevance_metrics']['recall_at_k']['R@1'],
            'recall_at_5': self.dataverse_analysis['relevance_metrics']['recall_at_k']['R@5'],
            'recall_at_10': self.dataverse_analysis['relevance_metrics']['recall_at_k']['R@10'],
            'map_score': self.dataverse_analysis['relevance_metrics']['map_score'],
            'mrr_score': self.dataverse_analysis['relevance_metrics']['mrr_score'],
            'zero_results_rate': 0.0  # Calculate if needed
        }
        
        # Agentic metrics
        ag_metrics = {
            'system': 'Agentic',
            'total_queries': self.agentic_analysis['file_info']['total_lines'],
            'valid_results': self.agentic_analysis['file_info']['valid_results'],
            'success_rate': self.agentic_analysis['search_performance']['search_execution_success_rate'],
            'avg_response_time': self.agentic_analysis['search_performance']['avg_response_time_ms'],
            'p95_response_time': self.agentic_analysis['search_performance']['p95_response_time_ms'],
            'precision_at_1': self.agentic_analysis['relevance_metrics']['precision_at_k']['P@1'],
            'precision_at_5': self.agentic_analysis['relevance_metrics']['precision_at_k']['P@5'],
            'precision_at_10': self.agentic_analysis['relevance_metrics']['precision_at_k']['P@10'],
            'recall_at_1': self.agentic_analysis['relevance_metrics']['recall_at_k']['R@1'],
            'recall_at_5': self.agentic_analysis['relevance_metrics']['recall_at_k']['R@5'],
            'recall_at_10': self.agentic_analysis['relevance_metrics']['recall_at_k']['R@10'],
            'map_score': self.agentic_analysis['relevance_metrics']['map_score'],
            'mrr_score': self.agentic_analysis['relevance_metrics']['mrr_score'],
            'zero_results_rate': 1.0 - (self.agentic_analysis['search_performance']['search_execution_success_rate'] / 100.0),
            'throttling_rate': self.agentic_analysis['search_performance']['throttling_rate']
        }
        
        return dv_metrics, ag_metrics
    
    def create_performance_comparison(self, dv_metrics, ag_metrics):
        """Create performance comparison DataFrame"""
        
        performance_data = {
            'Metric': [
                'Total Queries',
                'Valid Results',
                'Success Rate (%)',
                'Average Response Time (ms)',
                'P95 Response Time (ms)',
                'Zero Results Rate (%)'
            ],
            'Dataverse': [
                dv_metrics['total_queries'],
                dv_metrics['valid_results'],
                f"{dv_metrics['success_rate']:.1f}%",
                f"{dv_metrics['avg_response_time']:.1f}",
                f"{dv_metrics['p95_response_time']:.1f}",
                f"{dv_metrics['zero_results_rate']*100:.1f}%"
            ],
            'Agentic': [
                ag_metrics['total_queries'],
                ag_metrics['valid_results'],
                f"{ag_metrics['success_rate']:.1f}%",
                f"{ag_metrics['avg_response_time']:.1f}",
                f"{ag_metrics['p95_response_time']:.1f}",
                f"{ag_metrics['zero_results_rate']*100:.1f}%"
            ]
        }
        
        # Add agentic-specific metrics
        performance_data['Metric'].append('Throttling Rate (%)')
        performance_data['Dataverse'].append('N/A')
        performance_data['Agentic'].append(f"{ag_metrics['throttling_rate']:.1f}%")
        
        return pd.DataFrame(performance_data)
    
    def create_relevance_comparison(self, dv_metrics, ag_metrics):
        """Create relevance metrics comparison DataFrame"""
        
        relevance_data = {
            'Metric': [
                'Precision@1',
                'Precision@5', 
                'Precision@10',
                'Recall@1',
                'Recall@5',
                'Recall@10',
                'MAP (Mean Average Precision)',
                'MRR (Mean Reciprocal Rank)'
            ],
            'Dataverse': [
                f"{dv_metrics['precision_at_1']:.3f}",
                f"{dv_metrics['precision_at_5']:.3f}",
                f"{dv_metrics['precision_at_10']:.3f}",
                f"{dv_metrics['recall_at_1']:.3f}",
                f"{dv_metrics['recall_at_5']:.3f}",
                f"{dv_metrics['recall_at_10']:.3f}",
                f"{dv_metrics['map_score']:.3f}",
                f"{dv_metrics['mrr_score']:.3f}"
            ],
            'Agentic': [
                f"{ag_metrics['precision_at_1']:.3f}",
                f"{ag_metrics['precision_at_5']:.3f}",
                f"{ag_metrics['precision_at_10']:.3f}",
                f"{ag_metrics['recall_at_1']:.3f}",
                f"{ag_metrics['recall_at_5']:.3f}",
                f"{ag_metrics['recall_at_10']:.3f}",
                f"{ag_metrics['map_score']:.3f}",
                f"{ag_metrics['mrr_score']:.3f}"
            ],
            'Winner': []
        }
        
        # Determine winners for each metric
        numeric_comparisons = [
            ('precision_at_1', 'Higher is Better'),
            ('precision_at_5', 'Higher is Better'),
            ('precision_at_10', 'Higher is Better'),
            ('recall_at_1', 'Higher is Better'),
            ('recall_at_5', 'Higher is Better'),
            ('recall_at_10', 'Higher is Better'),
            ('map_score', 'Higher is Better'),
            ('mrr_score', 'Higher is Better')
        ]
        
        for metric, direction in numeric_comparisons:
            dv_val = dv_metrics[metric]
            ag_val = ag_metrics[metric]
            
            if dv_val > ag_val:
                winner = "🏆 Dataverse"
            elif ag_val > dv_val:
                winner = "🏆 Agentic"
            else:
                winner = "🤝 Tie"
            
            relevance_data['Winner'].append(winner)
        
        return pd.DataFrame(relevance_data)
    
    def create_question_type_comparison(self):
        """Create question type performance comparison"""
        
        comparison_data = []
        
        # Try to get question type data, but handle errors gracefully
        try:
            dv_qt_data = self.dataverse_analysis.get('question_type_breakdown', {})
            ag_qt_data = self.agentic_analysis.get('question_type_breakdown', {})
            
            question_types = ['Exact word', 'Category', 'Category + Attribute value', 'Category + Price range', 'Description']
            
            for qt in question_types:
                dv_data = dv_qt_data.get(qt, {})
                ag_data = ag_qt_data.get(qt, {})
                
                # Only add if both systems have data for this question type
                if dv_data and ag_data:
                    comparison_data.append({
                        'Question Type': qt,
                        'Dataverse P@1': f"{dv_data.get('precision_at_k', {}).get('P@1', 0):.3f}",
                        'Agentic P@1': f"{ag_data.get('precision_at_k', {}).get('P@1', 0):.3f}",
                        'Dataverse P@10': f"{dv_data.get('precision_at_k', {}).get('P@10', 0):.3f}",
                        'Agentic P@10': f"{ag_data.get('precision_at_k', {}).get('P@10', 0):.3f}",
                        'Dataverse MAP': f"{dv_data.get('map_score', 0):.3f}",
                        'Agentic MAP': f"{ag_data.get('map_score', 0):.3f}",
                        'Dataverse Queries': dv_data.get('query_count', 0),
                        'Agentic Queries': ag_data.get('query_count', 0)
                    })
        except Exception as e:
            print(f"Warning: Could not create question type comparison: {e}")
            comparison_data.append({
                'Question Type': 'Data not available',
                'Dataverse P@1': 'N/A',
                'Agentic P@1': 'N/A',
                'Dataverse P@10': 'N/A',
                'Agentic P@10': 'N/A',
                'Dataverse MAP': 'N/A',
                'Agentic MAP': 'N/A',
                'Dataverse Queries': 'N/A',
                'Agentic Queries': 'N/A'
            })
        
        return pd.DataFrame(comparison_data)
    
    def create_executive_summary(self, dv_metrics, ag_metrics):
        """Create executive summary of the comparison"""
        
        summary = {
            'Analysis Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Scoring Method': 'Unified Relevance Scorer (0-3 scale)',
            'Dataverse File': 'dataverse_results_20250815_014501_results.jsonl',
            'Agentic File': 'agentic_results_20250818_002606_results.jsonl',
            
            'Key Findings': [],
            'Performance Winners': {},
            'Relevance Winners': {},
            'Recommendations': []
        }
        
        # Performance comparison
        if dv_metrics['success_rate'] > ag_metrics['success_rate']:
            summary['Performance Winners']['Success Rate'] = 'Dataverse'
            summary['Key Findings'].append(f"Dataverse has higher success rate: {dv_metrics['success_rate']:.1f}% vs {ag_metrics['success_rate']:.1f}%")
        else:
            summary['Performance Winners']['Success Rate'] = 'Agentic'
        
        if dv_metrics['avg_response_time'] < ag_metrics['avg_response_time']:
            summary['Performance Winners']['Response Time'] = 'Dataverse'
            summary['Key Findings'].append(f"Dataverse is faster: {dv_metrics['avg_response_time']:.0f}ms vs {ag_metrics['avg_response_time']:.0f}ms")
        else:
            summary['Performance Winners']['Response Time'] = 'Agentic'
        
        # Relevance comparison
        relevance_metrics = ['precision_at_1', 'precision_at_10', 'recall_at_1', 'recall_at_10', 'map_score', 'mrr_score']
        for metric in relevance_metrics:
            if dv_metrics[metric] > ag_metrics[metric]:
                summary['Relevance Winners'][metric] = 'Dataverse'
            elif ag_metrics[metric] > dv_metrics[metric]:
                summary['Relevance Winners'][metric] = 'Agentic'
            else:
                summary['Relevance Winners'][metric] = 'Tie'
        
        # Overall winner determination
        dv_wins = sum(1 for winner in summary['Relevance Winners'].values() if winner == 'Dataverse')
        ag_wins = sum(1 for winner in summary['Relevance Winners'].values() if winner == 'Agentic')
        
        if dv_wins > ag_wins:
            summary['Key Findings'].append("🏆 Dataverse shows superior overall relevance performance")
            summary['Recommendations'].append("Consider Dataverse for production deployment")
        elif ag_wins > dv_wins:
            summary['Key Findings'].append("🏆 Agentic shows superior overall relevance performance") 
            summary['Recommendations'].append("Consider Agentic for production deployment")
        else:
            summary['Key Findings'].append("🤝 Both systems show comparable relevance performance")
        
        # Specific issues
        if ag_metrics['throttling_rate'] > 50:
            summary['Key Findings'].append(f"⚠️ Agentic system shows high throttling rate: {ag_metrics['throttling_rate']:.1f}%")
            summary['Recommendations'].append("Investigate rate limiting and capacity planning for Agentic system")
        
        return summary
    
    def generate_excel_report(self, output_file):
        """Generate comprehensive Excel comparison report"""
        
        logger.info("🔄 Generating updated Excel comparison report...")
        
        # Extract metrics
        dv_metrics, ag_metrics = self.extract_metrics()
        
        # Create comparison dataframes
        performance_df = self.create_performance_comparison(dv_metrics, ag_metrics)
        relevance_df = self.create_relevance_comparison(dv_metrics, ag_metrics)
        question_type_df = self.create_question_type_comparison()
        
        # Create executive summary
        exec_summary = self.create_executive_summary(dv_metrics, ag_metrics)
        
        # Convert summary to DataFrame for Excel
        summary_data = []
        summary_data.append(['Analysis Date', exec_summary['Analysis Date']])
        summary_data.append(['Scoring Method', exec_summary['Scoring Method']])
        summary_data.append(['Dataverse File', exec_summary['Dataverse File']])
        summary_data.append(['Agentic File', exec_summary['Agentic File']])
        summary_data.append(['', ''])
        summary_data.append(['KEY FINDINGS', ''])
        for finding in exec_summary['Key Findings']:
            summary_data.append(['', finding])
        summary_data.append(['', ''])
        summary_data.append(['RECOMMENDATIONS', ''])
        for rec in exec_summary['Recommendations']:
            summary_data.append(['', rec])
        
        summary_df = pd.DataFrame(summary_data, columns=['Category', 'Details'])
        
        # Write to Excel with multiple sheets
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            summary_df.to_excel(writer, sheet_name='Executive Summary', index=False)
            performance_df.to_excel(writer, sheet_name='Performance Comparison', index=False)
            relevance_df.to_excel(writer, sheet_name='Relevance Comparison', index=False)
            question_type_df.to_excel(writer, sheet_name='Question Type Analysis', index=False)
        
        logger.info(f"✅ Updated Excel report saved: {output_file}")
        return exec_summary

def main():
    """Main execution function"""
    
    # Initialize analyzer
    analyzer = UpdatedSearchComparisonAnalyzer()
    
    # File paths
    dataverse_analysis_file = "test_case_analysis/dataverse_results_20250815_014501_results_enhanced_analysis.json"
    agentic_analysis_file = "test_case_acs_analysis/agentic_results_20250818_002606_results_agentic_analysis.json"
    
    # Generate timestamp for output files
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    excel_file = f"updated_search_comparison_analysis_{timestamp}.xlsx"
    
    try:
        # Load analysis files
        analyzer.load_analysis_files(dataverse_analysis_file, agentic_analysis_file)
        
        # Generate Excel report
        exec_summary = analyzer.generate_excel_report(excel_file)
        
        # Print summary to console
        print("\n" + "="*80)
        print("🔬 UPDATED SEARCH SYSTEM COMPARISON SUMMARY")
        print("="*80)
        print(f"📅 Analysis Date: {exec_summary['Analysis Date']}")
        print(f"📊 Scoring Method: {exec_summary['Scoring Method']}")
        print(f"📁 Dataverse File: {exec_summary['Dataverse File']}")
        print(f"📁 Agentic File: {exec_summary['Agentic File']}")
        print("\n🔍 KEY FINDINGS:")
        for finding in exec_summary['Key Findings']:
            print(f"   • {finding}")
        print(f"\n💡 RECOMMENDATIONS:")
        for rec in exec_summary['Recommendations']:
            print(f"   • {rec}")
        print(f"\n📊 Detailed comparison saved to: {excel_file}")
        print("="*80)
        
    except Exception as e:
        logger.error(f"❌ Error in main execution: {e}")
        raise

if __name__ == "__main__":
    main()
