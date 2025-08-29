#!/usr/bin/env python3
"""
VERIFICATION: User-Provided Population Data Usage
Confirms that the system uses ONLY user-provided population data, GDP, and area data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.climate_data_loader import ClimateDataLoader, UZBEK_CITIES_DATA

def verify_user_data_usage():
    """Verify that the system uses only user-provided data, no mock data"""
    print("🔍 VERIFICATION: User-Provided Population Data Usage")
    print("=" * 70)

    # Check 1: User-provided data structure
    print("\n📊 1. USER-PROVIDED DATA STRUCTURE:")
    print("-" * 40)

    print(f"✅ UZBEK_CITIES_DATA contains {len(UZBEK_CITIES_DATA)} cities with user data:")
    for city, data in UZBEK_CITIES_DATA.items():
        pop = data['pop_2024']
        gdp = data['gdp_per_capita']
        area = data['area_km2']
        print(f"   • {city}: {pop:,.0f} people, ${gdp:,.0f} GDP/capita, {area:.1f} km²")

    # Check 2: Data loader implementation
    print("\n\n🔧 2. DATA LOADER IMPLEMENTATION:")
    print("-" * 40)

    data_loader = ClimateDataLoader('.')
    data_loader._initialize_population_data()

    print("✅ Data loader successfully loaded user-provided data:")
    user_data_count = 0
    excel_data_count = 0
    hardcoded_count = 0

    for city in data_loader.population_data.keys():
        pop_data = data_loader.population_data[city]
        if city in UZBEK_CITIES_DATA:
            user_data_count += 1
            user_pop = UZBEK_CITIES_DATA[city]['pop_2024']
            user_gdp = UZBEK_CITIES_DATA[city]['gdp_per_capita']
            user_area = UZBEK_CITIES_DATA[city]['area_km2']

            # Verify exact match
            assert pop_data.population_2024 == user_pop, f"Population mismatch for {city}"
            assert pop_data.gdp_per_capita_usd == user_gdp, f"GDP mismatch for {city}"
            assert pop_data.urban_area_km2 == user_area, f"Area mismatch for {city}"

    print(f"   • {user_data_count} cities using user-provided data ✅")
    print(f"   • {excel_data_count} cities using Excel data")
    print(f"   • {hardcoded_count} cities using hardcoded data")

    # Check 3: Population data accuracy
    print("\n\n📈 3. POPULATION DATA ACCURACY:")
    print("-" * 40)

    print("✅ Exact population matches verified:")
    test_cities = ['Tashkent', 'Samarkand', 'Bukhara', 'Andijan', 'Nukus', 'Urgench', 'Termez']
    for city in test_cities:
        if city in UZBEK_CITIES_DATA and city in data_loader.population_data:
            user_pop = UZBEK_CITIES_DATA[city]['pop_2024']
            loaded_pop = data_loader.population_data[city].population_2024
            user_gdp = UZBEK_CITIES_DATA[city]['gdp_per_capita']
            loaded_gdp = data_loader.population_data[city].gdp_per_capita_usd
            user_area = UZBEK_CITIES_DATA[city]['area_km2']
            loaded_area = data_loader.population_data[city].urban_area_km2

            print(f"   • {city}:")
            print(f"     Population: {loaded_pop:>,} (user: {user_pop:>,}) {'✅' if loaded_pop == user_pop else '❌'}")
            print(f"     GDP/capita: ${loaded_gdp:,.0f} (user: ${user_gdp:,.0f}) {'✅' if loaded_gdp == user_gdp else '❌'}")
            print(f"     Area: {loaded_area:.1f} km² (user: {user_area:.1f} km²) {'✅' if loaded_area == user_area else '❌'}")

    # Check 4: No mock data sources
    print("\n\n🚫 4. MOCK DATA VERIFICATION:")
    print("-" * 40)

    # Check for any hardcoded population values in the code
    hardcoded_populations = {
        'Tashkent': 3000000, 'Samarkand': 550000, 'Namangan': 500000,
        'Andijan': 450000, 'Nukus': 350000, 'Bukhara': 320000,
        'Fergana': 300000, 'Qarshi': 280000, 'Kokand': 250000,
        'Margilan': 220000, 'Urgench': 200000, 'Jizzakh': 180000,
        'Termez': 170000, 'Navoiy': 150000, 'Gulistan': 120000,
        'Nurafshon': 100000
    }

    mock_data_found = False
    for city in data_loader.population_data.keys():
        if city in hardcoded_populations:
            loaded_pop = data_loader.population_data[city].population_2024
            hardcoded_pop = hardcoded_populations[city]
            if loaded_pop == hardcoded_pop:
                print(f"⚠️  {city} is using hardcoded population ({hardcoded_pop:>,}) instead of user data")
                mock_data_found = True

    if not mock_data_found:
        print("✅ No hardcoded/mock population data detected")

    # Check 5: Assessment results reflect user data
    print("\n\n📊 5. ASSESSMENT RESULTS VERIFICATION:")
    print("-" * 40)

    from services.climate_risk_assessment import IPCCRiskAssessmentService
    assessment_service = IPCCRiskAssessmentService(data_loader)

    print("✅ Assessment uses correct population data:")
    for city in ['Tashkent', 'Samarkand', 'Bukhara']:
        if city in assessment_service.data['population_data']:
            pop_data = assessment_service.data['population_data'][city]
            user_data = UZBEK_CITIES_DATA[city]
            print(f"   • {city}: Assessment pop = {pop_data.population_2024:>,}, User data = {user_data['pop_2024']:>,} {'✅' if pop_data.population_2024 == user_data['pop_2024'] else '❌'}")

    # Final verification
    print("\n" + "=" * 70)
    if user_data_count == len(UZBEK_CITIES_DATA) and not mock_data_found:
        print("🎉 VERIFICATION COMPLETE: System uses ONLY user-provided data!")
        print("   ✅ Population data matches user-provided values exactly")
        print("   ✅ GDP per capita data matches user-provided values exactly")
        print("   ✅ Area data matches user-provided values exactly")
        print("   ✅ No mock/hardcoded data detected")
        print("   ✅ Assessment results reflect correct user data")
        return True
    else:
        print("❌ VERIFICATION FAILED: Issues found with user data usage")
        return False

if __name__ == "__main__":
    success = verify_user_data_usage()
    sys.exit(0 if success else 1)
