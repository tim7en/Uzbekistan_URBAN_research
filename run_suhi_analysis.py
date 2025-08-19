#!/usr/bin/env python3
"""
SUHI Analysis Runner
===================

Quick runner script to generate comprehensive SUHI analysis reports and visualizations.

Usage:
    python run_suhi_analysis.py

This script will:
1. Generate professional gridded visualizations
2. Create detailed markdown reports  
3. Export comprehensive data tables
4. Generate interactive dashboards
5. Provide temporal analysis charts

All outputs are saved to the suhi_analysis_output directory.

Author: GitHub Copilot
Date: August 19, 2025
"""

import sys
from pathlib import Path

# Add the current directory to the path
sys.path.append(str(Path(__file__).parent))

from professional_suhi_reporter import ProfessionalSUHIReporter
from comprehensive_suhi_analyzer import SUHIAnalyzer

def main():
    """Run both analysis tools."""
    print("🌟 SUHI ANALYSIS SUITE")
    print("=" * 50)
    
    data_path = "suhi_analysis_output/data"
    
    try:
        # Run Professional Reporter (static visualizations)
        print("🎨 Running Professional Reporter...")
        reporter = ProfessionalSUHIReporter(data_path)
        professional_results = reporter.run_complete_analysis()
        
        print("\\n" + "=" * 50)
        
        # Run Comprehensive Analyzer (interactive dashboard)
        print("📊 Running Comprehensive Analyzer...")
        analyzer = SUHIAnalyzer(data_path)
        comprehensive_results = analyzer.run_complete_analysis()
        
        print("\\n" + "🎉 ALL ANALYSIS COMPLETE!")
        print("=" * 50)
        print("📁 Check the following directories for outputs:")
        print("   📈 Visualizations: suhi_analysis_output/visualizations/")
        print("   📋 Reports: suhi_analysis_output/reports/")
        print("=" * 50)
        
        return {
            'professional': professional_results,
            'comprehensive': comprehensive_results
        }
        
    except Exception as e:
        print(f"❌ Error running analysis: {e}")
        return None

if __name__ == "__main__":
    results = main()
