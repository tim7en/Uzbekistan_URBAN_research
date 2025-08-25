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

    return results


if __name__ == "__main__":
    main()
