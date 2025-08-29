#!/usr/bin/env python3
"""
Investigation of aridity index calculation issue.
Uzbekistan should be arid (AI < 0.2) but we're getting ~0.3
"""

import json
from pathlib import Path
import numpy as np

def investigate_aridity_index():
    """Investigate why aridity index seems too high for Uzbekistan"""
    print("🔍 Investigating Aridity Index Calculation")
    print("=" * 50)

    # Load all city data
    water_dir = Path('suhi_analysis_output/water_scarcity')
    cities_data = []

    for city_dir in water_dir.iterdir():
        if city_dir.is_dir():
            city_file = city_dir / 'water_scarcity_assessment.json'
            if city_file.exists():
                with open(city_file, 'r') as f:
                    city_data = json.load(f)
                cities_data.append(city_data)

    if not cities_data:
        print("❌ No city data found")
        return

    # Extract aridity indices
    aridity_indices = [c['aridity_index'] for c in cities_data]
    cities = [c['city'] for c in cities_data]

    print("📊 Aridity Index Analysis:")
    print(f"   Average AI: {np.mean(aridity_indices):.3f}")
    print(f"   Median AI: {np.median(aridity_indices):.3f}")
    print(f"   Range: {min(aridity_indices):.3f} - {max(aridity_indices):.3f}")
    print()

    # Aridity index classification
    print("🌍 Aridity Index Classification:")
    print("   Hyper-arid: AI < 0.05")
    print("   Arid: 0.05 ≤ AI < 0.20")
    print("   Semi-arid: 0.20 ≤ AI < 0.50")
    print("   Sub-humid: 0.50 ≤ AI < 0.65")
    print("   Humid: AI ≥ 0.65")
    print()

    # Classify each city
    classifications = []
    for ai in aridity_indices:
        if ai < 0.05:
            classifications.append("Hyper-arid")
        elif ai < 0.20:
            classifications.append("Arid")
        elif ai < 0.50:
            classifications.append("Semi-arid")
        elif ai < 0.65:
            classifications.append("Sub-humid")
        else:
            classifications.append("Humid")

    print("🏙️ City Classifications:")
    for city, ai, classification in zip(cities, aridity_indices, classifications):
        print("6s")
    print()

    # Known aridity values for Uzbekistan
    print("📚 Uzbekistan Climate Facts:")
    print("   - Köppen climate classification: BWh (Hot desert)")
    print("   - Expected aridity index range: 0.03 - 0.15")
    print("   - Annual precipitation: 100-200 mm in desert regions")
    print("   - Annual PET: 1,500-2,000 mm")
    print("   - Expected AI = P/PET ≈ 0.05-0.13")
    print()

    # Calculate what AI should be
    print("🔬 Expected vs Actual:")
    print("   Expected AI range: 0.03 - 0.15 (arid)")
    print(f"   Actual AI range: {min(aridity_indices):.3f} - {max(aridity_indices):.3f}")
    print(f"   Average difference: {np.mean(aridity_indices) - 0.09:.3f}")
    print()

    # Possible causes
    print("🔍 Possible Causes of High AI:")
    print("   1. Precipitation data too high (CHIRPS overestimation)")
    print("   2. PET calculation too low (underestimating evaporative demand)")
    print("   3. Urban heat island effect not accounted for")
    print("   4. Temporal period bias (2001-2020 may be wetter than long-term)")
    print("   5. Spatial scale issues (city buffers vs regional climate)")
    print()

    # Check correlation with drought frequency
    drought_freqs = [c['drought_frequency'] for c in cities_data]
    correlation = np.corrcoef(aridity_indices, drought_freqs)[0, 1]

    print("📈 Correlation Analysis:")
    print(f"   AI vs Drought Frequency correlation: {correlation:.3f}")
    if correlation < -0.3:
        print("   ✅ Negative correlation (more arid = more drought) - physically reasonable")
    else:
        print("   ⚠️ Weak or positive correlation - may indicate calculation issues")

def check_pet_calculation():
    """Check if PET calculation might be the issue"""
    print("🔬 PET Calculation Investigation")
    print("=" * 50)

    # Thornthwaite method constants for Uzbekistan
    print("📊 Thornthwaite PET Method:")
    print("   Formula: PET = 16 * (10*T/I)^a * (N/12) * (N/N_0)")
    print("   Where:")
    print("   - T = mean monthly temperature (°C)")
    print("   - I = annual heat index")
    print("   - a = empirical coefficient")
    print("   - N = actual daylength hours")
    print("   - N_0 = maximum possible daylength")
    print()

    print("🌡️ Uzbekistan Temperature Context:")
    print("   - Summer temperatures: 35-40°C")
    print("   - Winter temperatures: -5 to +5°C")
    print("   - Annual temperature range: ~40°C")
    print("   - Should produce high PET values")
    print()

    print("💧 Expected PET Values:")
    print("   - Desert regions: 1,800-2,200 mm/year")
    print("   - Semi-desert: 1,400-1,800 mm/year")
    print("   - Oasis areas: 1,200-1,600 mm/year")
    print()

    print("🔍 Potential PET Issues:")
    print("   1. ERA5 temperature data accuracy in arid regions")
    print("   2. Daylength correction factor")
    print("   3. Urban vs rural temperature differences")
    print("   4. Monthly vs daily timestep effects")

def main():
    investigate_aridity_index()
    check_pet_calculation()

if __name__ == "__main__":
    main()
