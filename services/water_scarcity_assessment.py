"""
Water Scarcity Assessment Service - REMOVED
This module has been removed as it contained simulated/mock data.
Only real satellite data from Google Earth Engine is now used.
"""

# This file is kept for backwards compatibility but the simulator has been removed
# All water scarcity assessments now use only real GEE data

# Import the metrics class from GEE service for compatibility
try:
    from services.water_scarcity_gee import WaterScarcityMetrics
except ImportError:
    # Fallback dataclass if GEE service not available
    from dataclasses import dataclass

    @dataclass
    class WaterScarcityMetrics:
        """Water scarcity assessment metrics for a city"""
        city: str

        # Supply-side indicators (hydroclimate)
        aridity_index: float = 0.0  # AI = P/PET (lower = drier baseline)
        climatic_water_deficit: float = 0.0  # CWD (higher = greater unmet demand)
        drought_frequency: float = 0.0  # Fraction of months with PDSI ≤ -2

        # Surface water indicators
        surface_water_change: float = 0.0  # JRC GSW change_abs (negative = loss)

        # Demand proxies
        cropland_fraction: float = 0.0  # ESA WorldCover cropland %
        population_density: float = 0.0  # GPW population density

        # External benchmark
        aqueduct_bws_score: float = 0.0  # WRI Aqueduct Baseline Water Stress

        # Composite scores
        water_supply_risk: float = 0.0
        water_demand_risk: float = 0.0
        overall_water_scarcity_score: float = 0.0

        # Risk classification
        water_scarcity_level: str = "Unknown"


class WaterScarcityAssessmentService:
    """
    DEPRECATED: This simulator has been removed.
    Only real GEE data is now used for water scarcity assessment.
    """

    def __init__(self, data_loader):
        raise RuntimeError(
            "WaterScarcityAssessmentService (simulator) has been removed. "
            "Only real satellite data from Google Earth Engine is now supported. "
            "Please ensure GEE is properly configured and use WaterScarcityGEEAssessment instead."
        )

    def assess_city_water_scarcity(self, city: str):
        """DEPRECATED: This method is no longer available."""
        raise RuntimeError("This simulator has been removed. Use WaterScarcityGEEAssessment instead.")

    def assess_all_cities_water_scarcity(self):
        """DEPRECATED: This method is no longer available."""
        raise RuntimeError("This simulator has been removed. Use WaterScarcityGEEAssessment instead.")


