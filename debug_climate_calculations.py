#!/usr/bin/env python3
"""
Detailed investigation of PET and precipitation calculations
to understand why aridity index is too high
"""

import json
from pathlib import Path
import numpy as np
from services.climate_data_loader import ClimateDataLoader
from services.water_scarcity_gee import WaterScarcityGEEAssessment
from services import gee

def debug_climate_calculations():
    """Debug the actual climate calculations for a specific city"""
    print("🔍 Debugging Climate Calculations")
    print("=" * 50)

    # Initialize services
    gee.initialize_gee()
    loader = ClimateDataLoader('.')
    service = WaterScarcityGEEAssessment(loader)

    # Clear cache to force fresh calculation
    import shutil
    cache_dir = Path('suhi_analysis_output/data/water_scarcity')
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Test with Bukhara (should be arid)
    test_city = 'Bukhara'
    print(f"📊 Analyzing {test_city} climate calculations...")

    # Get raw indicators (this will trigger GEE calculations)
    raw_data = service._fetch_city_indicators(test_city)

    print("📈 Raw Climate Indicators:")
    print(f"   Aridity Index: {raw_data['aridity_index']:.3f}")
    print(f"   Climatic Water Deficit: {raw_data['climatic_water_deficit']:.1f} mm/year")
    print(f"   Drought Frequency: {raw_data['drought_frequency']:.1%}")
    print()

    # Let's examine what the Thornthwaite PET calculation should produce
    print("🌡️ Thornthwaite PET Method Analysis:")
    print("   Uzbekistan temperature characteristics:")
    print("   - Summer: 35-40°C (hot)")
    print("   - Winter: -5 to +5°C (cold)")
    print("   - Annual range: ~40°C")
    print("   - Should produce high PET values")
    print()

    # Expected calculations
    print("🔬 Expected Calculations for Arid Region:")
    print("   Annual Precipitation (P): 100-200 mm")
    print("   Annual PET: 1,800-2,200 mm")
    print("   Expected AI = P/PET: 0.05-0.11")
    print("   Expected CWD = PET - P: 1,600-2,100 mm")
    print()

    # Compare with actual
    actual_ai = raw_data['aridity_index']
    actual_cwd = raw_data['climatic_water_deficit']

    print("⚖️ Comparison:")
    print(f"   Expected AI range: 0.05 - 0.11")
    print(f"   Actual AI: {actual_ai:.3f}")
    print(f"   Expected CWD range: 1,600 - 2,100 mm")
    print(f"   Actual CWD: {actual_cwd:.1f} mm")
    print()

    # Diagnosis
    print("🔍 Diagnosis:")
    if actual_ai > 0.15:
        print("   ❌ AI too high - possible causes:")
        print("      1. Precipitation overestimated")
        print("      2. PET underestimated")
        print("      3. Both factors combined")

    if actual_cwd < 1500:
        print("   ❌ CWD too low - indicates PET is underestimated")
        print("      Thornthwaite method may not be suitable for extreme arid conditions")

    print()

def investigate_pet_method_suitability():
    """Investigate if Thornthwaite method is suitable for Uzbekistan"""
    print("🔬 Thornthwaite Method Suitability Analysis")
    print("=" * 50)

    print("""
THORNTHWAITE METHOD LIMITATIONS:

1. TEMPERATURE-BASED APPROACH:
   ✅ Good for energy-limited environments
   ❌ May underestimate PET in arid regions where radiation is limiting
   ❌ Doesn't account for wind, humidity, or radiation explicitly

2. SUITABILITY FOR UZBEKISTAN:
   - Uzbekistan has extreme continental climate
   - High summer temperatures (40°C+)
   - Low humidity, high radiation
   - Thornthwaite may underestimate PET significantly

3. ALTERNATIVE METHODS:
   - Penman-Monteith: More physically based, accounts for radiation
   - Hargreaves: Simpler but better for arid regions
   - Priestley-Taylor: Good for radiation-limited environments

4. EXPECTED IMPROVEMENT:
   - Penman-Monteith would likely give 20-40% higher PET
   - AI would decrease from ~0.3 to ~0.15-0.2
   - More consistent with arid classification
    """)

def check_chirps_accuracy():
    """Check if CHIRPS precipitation data is reasonable for Uzbekistan"""
    print("🌧️ CHIRPS Precipitation Data Analysis")
    print("=" * 50)

    print("""
CHIRPS PRECIPITATION DATA:

1. DATA CHARACTERISTICS:
   ✅ Satellite-based rainfall estimates
   ✅ Bias-corrected using gauge data
   ✅ 0.05° spatial resolution
   ✅ Good performance in arid regions

2. UZBEKISTAN PRECIPITATION PATTERNS:
   - Northern regions (Tashkent): 300-500 mm/year
   - Central regions (Samarkand): 200-400 mm/year
   - Southern regions (Termez): 100-200 mm/year
   - Western desert (Nukus): 80-150 mm/year

3. VALIDATION CONCERNS:
   ⚠️ Sparse gauge network in desert regions
   ⚠️ Satellite estimates may have higher uncertainty
   ⚠️ Temporal coverage (2001-2020) may include wetter periods

4. EXPECTED ACCURACY:
   - Good: ±20% in agricultural areas
   - Moderate: ±30% in desert areas
   - May overestimate in some arid regions
    """)

def recommend_improvements():
    """Recommend improvements to the climate calculations"""
    print("💡 Recommended Improvements")
    print("=" * 50)

    print("""
IMMEDIATE IMPROVEMENTS:

1. PET METHOD UPGRADE:
   - Replace Thornthwaite with Hargreaves or Penman-Monteith
   - Hargreaves: PET = 0.0023 * Ra * (T_max - T_min)^0.5 * (T_mean + 17.8)
   - Better suited for arid regions with limited humidity data

2. ARIDITY INDEX ADJUSTMENT:
   - Apply regional correction factors
   - Use Köppen climate classification as validation
   - Cross-reference with local meteorological data

3. VALIDATION AGAINST OBSERVED DATA:
   - Compare with Uzbekistan meteorological stations
   - Validate against FAO aridity maps
   - Use GRACE satellite water storage data

4. SPATIAL CONSIDERATIONS:
   - Account for urban heat island effects
   - Consider oasis vs desert microclimates
   - Use appropriate buffer sizes for climate analysis

LONG-TERM IMPROVEMENTS:

1. MULTI-SOURCE VALIDATION:
   - Cross-validate with multiple PET methods
   - Use ensemble approach for uncertainty quantification
   - Incorporate local meteorological observations

2. DYNAMIC CALIBRATION:
   - Calibrate PET methods using local data
   - Adjust for elevation and terrain effects
   - Account for irrigation impacts on local climate
    """)

def main():
    debug_climate_calculations()
    investigate_pet_method_suitability()
    check_chirps_accuracy()
    recommend_improvements()

if __name__ == "__main__":
    main()
