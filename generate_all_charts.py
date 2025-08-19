#!/usr/bin/env python3
"""
Chart Generation Launcher
=========================

Quick launcher to generate all individual Plotly charts for SUHI analysis.

This script runs both the individual chart generator and dashboard chart extractor
to create a complete set of standalone charts in the reporting folder.

Usage:
    python generate_all_charts.py

Author: GitHub Copilot
Date: August 19, 2025
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Run all chart generation scripts."""
    print("🚀 SUHI CHART GENERATION SUITE")
    print("=" * 60)
    
    # Get the Python executable path
    python_exe = sys.executable
    
    try:
        # Run individual chart generator
        print("📊 Generating individual analysis charts...")
        result1 = subprocess.run([python_exe, "individual_chart_generator.py"], 
                                capture_output=True, text=True, check=True)
        print("✅ Individual charts generated successfully!")
        
        print("\\n" + "-" * 60)
        
        # Run dashboard chart extractor
        print("🎛️ Extracting dashboard components...")
        result2 = subprocess.run([python_exe, "dashboard_chart_extractor.py"], 
                                capture_output=True, text=True, check=True)
        print("✅ Dashboard charts extracted successfully!")
        
        print("\\n" + "=" * 60)
        print("🎉 ALL CHARTS GENERATED!")
        print("=" * 60)
        print("📁 Check the 'reporting' folder for all charts:")
        print("   📈 Individual charts: 22 HTML + 22 PNG")
        print("   🎛️ Dashboard charts: 6 HTML + 6 PNG")
        print("   📋 Total: 28 HTML + 28 PNG files")
        print("=" * 60)
        
        # Count actual files
        reporting_path = Path("reporting")
        if reporting_path.exists():
            html_files = list(reporting_path.rglob("*.html"))
            png_files = list(reporting_path.rglob("*.png"))
            print(f"📊 Actual files created: {len(html_files)} HTML + {len(png_files)} PNG")
        
        print("\\n🌟 Open 'reporting/README.md' for chart index and navigation!")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running chart generation: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        return False
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
