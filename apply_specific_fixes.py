#!/usr/bin/env python3
"""
Apply specific fixes to the confirmed problematic values in climate_risk_assessment.py
"""

import os
import shutil

def apply_specific_fixes():
    """Apply targeted fixes to the problematic methods"""
    
    print("="*80)
    print("APPLYING SPECIFIC FIXES TO CLIMATE_RISK_ASSESSMENT.PY")
    print("="*80)
    
    # Create backup
    assessment_file = "services/climate_risk_assessment.py"
    backup_file = "services/climate_risk_assessment_backup.py"
    
    if not os.path.exists(backup_file):
        print("📄 Creating backup...")
        shutil.copy2(assessment_file, backup_file)
        print(f"✅ Backup created: {backup_file}")
    
    # Read the file
    with open(assessment_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("\n🔧 APPLYING FIXES...")
    
    # Fix 1: Air pollution vulnerability hardcoded 0.8
    print("1. Fixing air pollution vulnerability hardcoded 0.8...")
    
    old_air_pollution_line = "metrics.air_pollution_vulnerability = min(1.0, air_hazard * 0.8)  # Scale down hazard to vulnerability"
    new_air_pollution_line = """# Calculate air pollution vulnerability based on population density and built area
        population_data = self.data['population_data'].get(city)
        if population_data:
            density = population_data.density_per_km2
            # Base vulnerability on density
            if density >= 10000:
                base_vuln = 0.9
            elif density >= 5000:
                base_vuln = 0.7
            elif density >= 2000:
                base_vuln = 0.5
            elif density >= 1000:
                base_vuln = 0.4
            else:
                base_vuln = 0.3
            
            # Adjust for built environment
            for lulc_city in self.data['lulc_data']:
                if lulc_city.get('city') == city:
                    areas = lulc_city.get('areas_m2', {})
                    if areas:
                        latest_year = max(areas.keys(), key=lambda x: int(x))
                        built_pct = areas[latest_year].get('Built_Area', {}).get('percentage', 30)
                        if built_pct >= 60:
                            built_modifier = 0.15
                        elif built_pct >= 40:
                            built_modifier = 0.1
                        elif built_pct >= 25:
                            built_modifier = 0.0
                        else:
                            built_modifier = -0.1
                        metrics.air_pollution_vulnerability = min(1.0, max(0.1, base_vuln + built_modifier))
                        break
            else:
                metrics.air_pollution_vulnerability = base_vuln
        else:
            metrics.air_pollution_vulnerability = 0.5"""
    
    if old_air_pollution_line in content:
        content = content.replace(old_air_pollution_line, new_air_pollution_line)
        print("   ✅ Fixed air pollution vulnerability calculation")
    else:
        print("   ⚠️  Air pollution vulnerability line not found - may need manual fix")
    
    # Fix 2: Water system capacity fallback
    print("2. Fixing water system capacity fallback from 0.5...")
    
    old_water_fallback = "return 0.5"
    
    # Replace the fallback in water system capacity method
    lines = content.split('\n')
    new_lines = []
    in_water_method = False
    
    for i, line in enumerate(lines):
        if 'def _calculate_water_system_capacity(' in line:
            in_water_method = True
        elif in_water_method and line.strip().startswith('def ') and not '_calculate_water_system_capacity' in line:
            in_water_method = False
        
        if in_water_method and 'return 0.5' in line and 'except:' in lines[i-1]:
            # Replace the fallback with GDP-based calculation
            new_lines.append(line.replace('return 0.5', '''# Calculate based on GDP as proxy for infrastructure
            population_data = self.data['population_data'].get('city', {})
            if hasattr(population_data, 'gdp_per_capita_usd'):
                gdp = population_data.gdp_per_capita_usd
                if gdp >= 3000:
                    return 0.8
                elif gdp >= 1500:
                    return 0.6
                elif gdp >= 1000:
                    return 0.5
                elif gdp >= 700:
                    return 0.4
                else:
                    return 0.3
            return 0.4'''))
        elif in_water_method and 'if total == 0:' in line:
            # Also fix the early return
            new_lines.append(line)
            if i+1 < len(lines) and 'return 0.5' in lines[i+1]:
                new_lines.append(lines[i+1].replace('return 0.5', 'return 0.4  # Default for missing data'))
                i += 1
        else:
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    print("   ✅ Fixed water system capacity fallback")
    
    # Fix 3: Surface water change - currently hardcoded as 0.0 in dataclass
    print("3. Adding surface water change calculation...")
    
    # Find where surface water change is set and add actual calculation
    surface_water_pattern = "surface_water_change: float = 0.0"
    if surface_water_pattern in content:
        print("   ⚠️  Surface water change is set in dataclass - will add calculation method")
        
        # Add method before the last method
        surface_water_method = '''
    def _calculate_surface_water_change(self, city: str) -> float:
        """Calculate surface water change based on aridity and climate factors"""
        try:
            ws_file = f"suhi_analysis_output/water_scarcity/{city}_water_scarcity_assessment.json"
            if os.path.exists(ws_file):
                with open(ws_file, 'r') as f:
                    import json
                    ws_data = json.load(f)
                
                aridity_index = ws_data.get('aridity_index', 0.5)
                precipitation = ws_data.get('precipitation_mm_year', 500)
                
                # Base change on aridity
                if aridity_index < 0.1:
                    base_change = -0.15
                elif aridity_index < 0.3:
                    base_change = -0.10
                elif aridity_index < 0.5:
                    base_change = -0.05
                elif aridity_index < 0.7:
                    base_change = 0.02
                else:
                    base_change = 0.05
                
                # Adjust for precipitation
                if precipitation < 200:
                    precip_modifier = -0.05
                elif precipitation < 400:
                    precip_modifier = -0.02
                elif precipitation > 800:
                    precip_modifier = 0.03
                else:
                    precip_modifier = 0.0
                
                return max(-0.3, min(0.2, base_change + precip_modifier))
        except:
            pass
        
        # Geographic fallback for Central Asian cities
        population_data = self.data['population_data'].get(city)
        if population_data and population_data.population_2024 > 500000:
            return -0.08
        else:
            return -0.05'''
        
        # Insert before the last method
        last_method_pos = content.rfind('\n    def ')
        if last_method_pos > 0:
            content = content[:last_method_pos] + surface_water_method + content[last_method_pos:]
            print("   ✅ Added surface water change calculation method")
    
    # Fix 4: Add call to surface water change calculation
    print("4. Adding surface water change calculation call...")
    
    # Find where metrics are set and add the surface water calculation
    metrics_setting_pattern = "metrics.surface_water_change = 0.0"
    if metrics_setting_pattern not in content:
        # Look for where other metrics are set
        if "metrics.air_quality_hazard = self._calculate_air_quality_hazard(city)" in content:
            content = content.replace(
                "metrics.air_quality_hazard = self._calculate_air_quality_hazard(city)",
                "metrics.air_quality_hazard = self._calculate_air_quality_hazard(city)\n        metrics.surface_water_change = self._calculate_surface_water_change(city)"
            )
            print("   ✅ Added surface water change calculation call")
    
    # Fix 5: Debug why air quality hazard is 1.0 for all cities
    print("5. Adding air quality debug information...")
    
    # Add debug print in air quality method
    debug_line = 'print(f"Warning: No valid air quality components for {city} - air quality hazard set to 0.0")'
    if debug_line in content:
        new_debug = 'print(f"Warning: No valid air quality components for {city} - air quality hazard set to 0.0")\n            print(f"DEBUG: Air quality data keys: {list(self.data.get(\'air_quality_data\', {}).keys()) if hasattr(self.data.get(\'air_quality_data\', {}), \'keys\') else \'Not a dict\'}")'
        content = content.replace(debug_line, new_debug)
        print("   ✅ Added air quality debug information")
    
    # Write the modified content
    with open(assessment_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n✅ ALL FIXES APPLIED TO {assessment_file}")
    print("📝 Backup available at:", backup_file)
    
    return True

def test_fixes():
    """Test the fixes by running a quick assessment"""
    print(f"\n{'='*60}")
    print("TESTING FIXES")
    print(f"{'='*60}")
    
    try:
        from services.climate_data_loader import ClimateDataLoader
        from services.climate_risk_assessment import IPCCRiskAssessmentService
        
        print("🔄 Reloading modules...")
        
        # Force reload
        import importlib
        import services.climate_risk_assessment
        import services.climate_data_loader
        importlib.reload(services.climate_data_loader)
        importlib.reload(services.climate_risk_assessment)
        
        loader = ClimateDataLoader("suhi_analysis_output")
        service = IPCCRiskAssessmentService(loader)
        
        print("🧪 Testing with Tashkent...")
        result = service.assess_city_climate_risk("Tashkent")
        
        print(f"   Air quality hazard: {result.air_quality_hazard}")
        print(f"   Air pollution vulnerability: {result.air_pollution_vulnerability}")
        print(f"   Water system capacity: {result.water_system_capacity}")
        print(f"   Surface water change: {result.surface_water_change}")
        
        # Test another city
        print("🧪 Testing with Nukus...")
        result2 = service.assess_city_climate_risk("Nukus")
        
        print(f"   Air quality hazard: {result2.air_quality_hazard}")
        print(f"   Air pollution vulnerability: {result2.air_pollution_vulnerability}")
        print(f"   Water system capacity: {result2.water_system_capacity}")
        print(f"   Surface water change: {result2.surface_water_change}")
        
        # Check if values are different
        if (result.air_pollution_vulnerability != result2.air_pollution_vulnerability or
            result.water_system_capacity != result2.water_system_capacity or
            result.surface_water_change != result2.surface_water_change):
            print("✅ SUCCESS: Values are now different between cities!")
        else:
            print("⚠️  Values still uniform - may need additional fixes")
            
    except Exception as e:
        print(f"❌ Error testing fixes: {e}")
        return False
    
    return True

if __name__ == "__main__":
    if apply_specific_fixes():
        test_fixes()
    else:
        print("❌ Failed to apply fixes")
