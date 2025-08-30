"""
Refactored IPCC AR6 Climate Risk Assessment
Main script using modular services for data loading, risk assessment, and reporting
"""

from pathlib import Path
from services.climate_data_loader import ClimateDataLoader
from services.climate_risk_assessment import IPCCRiskAssessmentService
from services.climate_assessment_reporter import ClimateAssessmentReporter


class IPCCClimateRiskAssessment:
    """
    Main orchestrator for IPCC AR6-based urban climate risk assessment
    Uses modular services for data loading, assessment, and reporting
    """
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.output_path = self.base_path / "climate_assessment"
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize services
        self.data_loader = ClimateDataLoader(base_path)
        self.risk_assessor = None  # Initialized after data loading
        self.reporter = ClimateAssessmentReporter(str(self.output_path))
        
        self.city_risk_profiles = {}
    
    def run_comprehensive_assessment(self):
        """Run complete IPCC AR6-based climate assessment"""
        print("Starting comprehensive IPCC AR6 climate risk assessment...")
        
        # Initialize risk assessor with loaded data
        self.risk_assessor = IPCCRiskAssessmentService(self.data_loader)
        
        # Run assessment for all cities
        self.city_risk_profiles = self.risk_assessor.assess_all_cities()
        
        # Generate comprehensive reports
        self.reporter.generate_comprehensive_report(self.city_risk_profiles)
        
        print(f"\n✅ Assessment complete. Results saved to: {self.output_path}")
        return self.city_risk_profiles


def main():
    """Main execution function for climate risk assessment"""
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent
    # Candidate locations where analysis outputs/reports may reside (project-relative)
    candidates = [
        repo_root / "suhi_analysis_output",
        repo_root / "reports",
        Path.cwd() / "suhi_analysis_output",
        Path.cwd() / "reports",
        repo_root
    ]

    base_path = None
    for c in candidates:
        if c.exists():
            base_path = c
            break

    if base_path is None:
        # fallback to repo root (will likely lead to 'not found' warnings but is explicit)
        base_path = repo_root
        print(f"Warning: no suhi_analysis_output/reports folder found; using repo root: {base_path}")
    else:
        print(f"Using data base_path: {base_path}")

    # Create assessment instance
    assessment = IPCCClimateRiskAssessment(str(base_path))

    # Run comprehensive assessment
    results = assessment.run_comprehensive_assessment()
    
    # Save results to JSON file
    import json
    output_file = base_path / "climate_assessment" / "climate_risk_assessment_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        # Convert ClimateRiskMetrics objects to dictionaries
        results_dict = {}
        for city, metrics in results.items():
            results_dict[city] = {
                'city': metrics.city,
                'population': metrics.population,
                'gdp_per_capita_usd': metrics.gdp_per_capita_usd,
                'hazard_score': metrics.hazard_score,
                'exposure_score': metrics.exposure_score,
                'vulnerability_score': metrics.vulnerability_score,
                'adaptive_capacity_score': metrics.adaptive_capacity_score,
                'heat_hazard': metrics.heat_hazard,
                'dry_hazard': metrics.dry_hazard,
                'dust_hazard': metrics.dust_hazard,
                'pluvial_hazard': metrics.pluvial_hazard,
                'air_quality_hazard': metrics.air_quality_hazard,
                'population_exposure': metrics.population_exposure,
                'gdp_exposure': metrics.gdp_exposure,
                'viirs_exposure': metrics.viirs_exposure,
                'income_vulnerability': metrics.income_vulnerability,
                'veg_access_vulnerability': metrics.veg_access_vulnerability,
                'fragmentation_vulnerability': metrics.fragmentation_vulnerability,
                'bio_trend_vulnerability': metrics.bio_trend_vulnerability,
                'air_pollution_vulnerability': metrics.air_pollution_vulnerability,
                'water_access_vulnerability': metrics.water_access_vulnerability,
                'healthcare_access_vulnerability': metrics.healthcare_access_vulnerability,
                'education_access_vulnerability': metrics.education_access_vulnerability,
                'sanitation_vulnerability': metrics.sanitation_vulnerability,
                'building_age_vulnerability': metrics.building_age_vulnerability,
                'gdp_adaptive_capacity': metrics.gdp_adaptive_capacity,
                'greenspace_adaptive_capacity': metrics.greenspace_adaptive_capacity,
                'services_adaptive_capacity': metrics.services_adaptive_capacity,
                'air_quality_adaptive_capacity': metrics.air_quality_adaptive_capacity,
                'social_infrastructure_capacity': metrics.social_infrastructure_capacity,
                'water_system_capacity': metrics.water_system_capacity,
                'overall_risk_score': metrics.overall_risk_score,
                'adaptability_score': metrics.adaptability_score,
                'current_suhi_intensity': metrics.current_suhi_intensity,
                'temperature_trend': metrics.temperature_trend,
                'suhi_trend': metrics.suhi_trend,
                'built_area_percentage': metrics.built_area_percentage,
                'green_space_accessibility': metrics.green_space_accessibility,
                'economic_capacity': metrics.economic_capacity,
                'co_level': metrics.co_level,
                'no2_level': metrics.no2_level,
                'o3_level': metrics.o3_level,
                'so2_level': metrics.so2_level,
                'ch4_level': metrics.ch4_level,
                'aerosol_index': metrics.aerosol_index,
                'air_quality_trend': metrics.air_quality_trend,
                'health_risk_score': metrics.health_risk_score,
                'water_supply_risk': metrics.water_supply_risk,
                'water_demand_risk': metrics.water_demand_risk,
                'overall_water_scarcity_score': metrics.overall_water_scarcity_score,
                'water_scarcity_level': metrics.water_scarcity_level,
                'aridity_index': metrics.aridity_index,
                'climatic_water_deficit': metrics.climatic_water_deficit,
                'drought_frequency': metrics.drought_frequency,
                'surface_water_change': metrics.surface_water_change,
                'cropland_fraction': metrics.cropland_fraction
            }
        json.dump(results_dict, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Results saved to: {output_file}")
    
    return results


if __name__ == "__main__":
    main()
