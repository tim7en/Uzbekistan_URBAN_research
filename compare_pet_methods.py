#!/usr/bin/env python3
"""
Comparison of Thornthwaite vs Hargreaves PET methods for Uzbekistan
"""

import numpy as np

def compare_pet_methods():
    """Compare Thornthwaite and Hargreaves PET methods for Uzbekistan conditions"""
    print("🔬 PET Method Comparison: Thornthwaite vs Hargreaves")
    print("=" * 60)

    # Uzbekistan climate characteristics
    print("🌡️ Uzbekistan Climate Parameters:")
    print("   Summer (July): Tmean=30°C, Tmax=37°C, Tmin=23°C, Range=14°C")
    print("   Winter (January): Tmean=2°C, Tmax=6°C, Tmin=-2°C, Range=8°C")
    print("   Annual: High radiation, low humidity, continental desert")
    print()

    # Monthly temperature data (approximate for Uzbekistan)
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    t_mean = [2, 4, 10, 18, 24, 29, 31, 29, 24, 16, 9, 3]   # Mean temperature (°C)
    t_max = [6, 8, 15, 24, 30, 35, 37, 35, 30, 22, 14, 7]   # Max temperature (°C)
    t_min = [-2, 0, 5, 12, 18, 23, 25, 23, 18, 10, 4, -1]   # Min temperature (°C)

    print("📊 Monthly Temperature Comparison:")
    print("Month | Tmean | Tmax | Tmin | Range")
    print("------|-------|------|------|------")
    for i, month in enumerate(months):
        range_temp = t_max[i] - t_min[i]
        print(f"{month:5s} | {t_mean[i]:5d} | {t_max[i]:4d} | {t_min[i]:4d} | {range_temp:5d}")
    print()

    # Calculate Thornthwaite PET
    print("🌡️ Thornthwaite PET Calculation:")
    print("   Formula: PET = 16 * ((T/5)^a) * (days/30) * adjustment_factor")
    print()

    # Calculate annual heat index I (corrected Thornthwaite formula)
    I = 0
    for t in t_mean:
        if t > 0:
            I += (t / 5) ** 1.514

    # Corrected empirical coefficient calculation
    a = 6.75e-7 * I**3 - 7.71e-5 * I**2 + 1.792e-2 * I + 0.49239
    print(f"   Annual Heat Index (I): {I:.1f}")
    print(f"   Empirical Coefficient (a): {a:.3f}")
    print()

    # Monthly Thornthwaite PET
    thornthwaite_pet = []
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    for i, (t, days) in enumerate(zip(t_mean, days_in_month)):
        if t <= 0:
            pet = 0
        else:
            # Corrected Thornthwaite formula
            pet_daily = 16 * ((t / 5) ** a) * (days / 30.0) / 30  # Convert to daily then monthly
            pet = pet_daily * days  # mm/month
        thornthwaite_pet.append(pet)

    # Calculate Hargreaves PET
    print("☀️ Hargreaves PET Calculation:")
    print("   Formula: PET = 0.0023 * Ra * (Tmax - Tmin)^0.5 * (Tmean + 17.8) * days")
    print()

    # Hargreaves with proper scaling
    hargreaves_pet = []
    for i, (tmean, tmax, tmin, days) in enumerate(zip(t_mean, t_max, t_min, days_in_month)):
        if tmean + 17.8 <= 0:
            pet = 0
        else:
            # Hargreaves formula with proper units
            # Ra approximated based on latitude and season (MJ/m²/day)
            ra_seasonal = [15, 18, 22, 25, 28, 30, 29, 27, 23, 19, 16, 14][i]
            pet_daily = 0.0023 * ra_seasonal * (tmax - tmin)**0.5 * (tmean + 17.8)
            pet = pet_daily * days  # Convert to mm/month
        hargreaves_pet.append(pet)

    print("📈 Monthly PET Comparison (mm/month):")
    print("Month | Thornthwaite | Hargreaves | Ratio")
    print("------|--------------|------------|------")
    for i, month in enumerate(months):
        ratio = hargreaves_pet[i] / thornthwaite_pet[i] if thornthwaite_pet[i] > 0 else 0
        print(f"{month:5s} | {thornthwaite_pet[i]:12.1f} | {hargreaves_pet[i]:10.1f} | {ratio:5.2f}")
    print()

    # Annual totals
    annual_thornthwaite = sum(thornthwaite_pet)
    annual_hargreaves = sum(hargreaves_pet)

    print("📊 Annual PET Totals:")
    print(f"   Thornthwaite: {annual_thornthwaite:.0f} mm/year")
    print(f"   Hargreaves: {annual_hargreaves:.0f} mm/year")
    if annual_thornthwaite > 0:
        print(f"   Ratio: {annual_hargreaves/annual_thornthwaite:.2f}x")
    print()

    # Aridity index comparison
    expected_precip = 200  # mm/year for semi-arid regions of Uzbekistan

    print("🔬 Aridity Index Impact:")
    if annual_thornthwaite > 0:
        ai_thornthwaite = expected_precip / annual_thornthwaite
        print(f"   Thornthwaite AI: {ai_thornthwaite:.3f}")
        ai_classification = "arid" if ai_thornthwaite < 0.2 else "semi-arid" if ai_thornthwaite < 0.5 else "sub-humid"
        print(f"   Classification: {ai_classification}")

    ai_hargreaves = expected_precip / annual_hargreaves
    print(f"   Hargreaves AI: {ai_hargreaves:.3f}")
    ai_classification = "arid" if ai_hargreaves < 0.2 else "semi-arid" if ai_hargreaves < 0.5 else "sub-humid"
    print(f"   Classification: {ai_classification}")

    print(f"   Expected for Uzbekistan: 0.05-0.15 (arid desert)")
    print()

    print("✅ Hargreaves Advantages for Uzbekistan:")
    print("   1. Accounts for temperature range (radiation proxy)")
    print("   2. Better suited for arid continental climates")
    print("   3. More realistic PET values for desert conditions")
    print("   4. Should give AI in correct arid range (0.05-0.15)")
    print("   5. Simpler than full Penman-Monteith but more accurate")

def main():
    compare_pet_methods()

if __name__ == "__main__":
    main()
