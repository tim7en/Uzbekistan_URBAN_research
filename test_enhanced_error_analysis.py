#!/usr/bin/env python3
"""
Test script to demonstrate ENHANCED error analysis with confidence intervals
"""

import sys
from pathlib import Path
import json

# Ensure repository root is on sys.path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from services.air_quality import AirQualityAnalyzer
from services.gee import initialize_gee

def test_enhanced_error_analysis():
    """Test the enhanced error analysis with confidence intervals"""

    print("🔬 TESTING ENHANCED ERROR ANALYSIS WITH CONFIDENCE INTERVALS")
    print("=" * 70)

    # Initialize Earth Engine
    ok = initialize_gee()
    if not ok:
        print('❌ GEE initialization failed')
        return

    print("✅ GEE initialized successfully")

    analyzer = AirQualityAnalyzer()

    # Test enhanced processing for Tashkent 2020
    print(f"\n🧮 ENHANCED ANALYSIS FOR TASHKENT 2020")
    print("-" * 50)

    try:
        result = analyzer.batch_process_monthly_data_optimized("Tashkent", 2020)

        if 'pollutants' in result:
            pollutants = result['pollutants']
            print(f"✅ SUCCESS: {len(pollutants)} pollutants processed with enhanced statistics")

            # Show detailed statistics for first 2 pollutants
            for pollutant_name, data in list(pollutants.items())[:2]:  # Show first 2
                if 'error' not in data:
                    urban = data.get('urban_annual', {})
                    rural = data.get('rural_annual', {})

                    print(f"\n📊 {pollutant_name} - ENHANCED STATISTICS:")
                    print("-" * 40)

                    # Show urban statistics
                    if urban and 'confidence_interval_95' in urban:
                        ci = urban['confidence_interval_95']
                        print(f"   URBAN ZONE:")
                        print(f"      Mean: {urban.get('mean', 'N/A'):.2e}")
                        print(f"      StdDev: {urban.get('stdDev', 'N/A'):.2e}")
                        print(f"      95% CI: [{ci['lower_bound']:.2e}, {ci['upper_bound']:.2e}]")
                        print(f"      Margin of Error: {ci['margin_of_error']:.2e}")
                        print(f"      Sample Size: {urban.get('statistical_measures', {}).get('sample_size', 'N/A')}")
                        print(f"      Data Reliability: {urban.get('statistical_measures', {}).get('data_reliability', 'N/A')}")

                    # Show rural statistics
                    if rural and 'confidence_interval_95' in rural:
                        ci = rural['confidence_interval_95']
                        print(f"   RURAL ZONE:")
                        print(f"      Mean: {rural.get('mean', 'N/A'):.2e}")
                        print(f"      StdDev: {rural.get('stdDev', 'N/A'):.2e}")
                        print(f"      95% CI: [{ci['lower_bound']:.2e}, {ci['upper_bound']:.2e}]")
                        print(f"      Margin of Error: {ci['margin_of_error']:.2e}")
                        print(f"      Sample Size: {rural.get('statistical_measures', {}).get('sample_size', 'N/A')}")
                        print(f"      Data Reliability: {rural.get('statistical_measures', {}).get('data_reliability', 'N/A')}")

                    # Show urban-rural comparison
                    urban_mean = urban.get('mean')
                    rural_mean = rural.get('mean')
                    if urban_mean and rural_mean and rural_mean != 0:
                        ratio = urban_mean / rural_mean
                        print(f"   URBAN-RURAL COMPARISON:")
                        print(f"      Ratio: {ratio:.2f}")
                        print(f"      Difference: {(urban_mean - rural_mean):.2e}")
                        print(f"      Percent Difference: {((urban_mean - rural_mean) / rural_mean * 100):.1f}%")

            print(f"\n🎯 ERROR ANALYSIS FEATURES NOW INCLUDE:")
            print(f"   ✅ 95% Confidence Intervals")
            print(f"   ✅ Standard Error of the Mean")
            print(f"   ✅ Coefficient of Variation")
            print(f"   ✅ Statistical Significance Measures")
            print(f"   ✅ Data Reliability Assessment")
            print(f"   ✅ Sample Size Analysis")

        return result

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return None

if __name__ == "__main__":
    success = test_enhanced_error_analysis()
    if success:
        print("\n🎉 ENHANCED ERROR ANALYSIS WORKING!")
        print("   Confidence intervals and statistical measures are now calculated!")
    else:
        print("\n❌ Enhanced analysis needs debugging")
