"""
Water Scarcity Assessment Service
Implements water scarcity and drought risk assessment for urban areas
Based on IPCC AR6 water-related hazards and GEE-derived indicators
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
import json


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
    Water Scarcity Assessment Service
    Implements comprehensive water scarcity risk assessment for urban areas
    """
    
    def __init__(self, data_loader):
        self.data_loader = data_loader
        self.water_data = {}
        self._cache = {}
        
        # Uzbekistan city coordinates and buffer definitions
        self.city_definitions = {
            "Tashkent": {"lon": 69.2401, "lat": 41.2995, "urban_radius_m": 15000, "ring_outer_m": 45000},
            "Samarkand": {"lon": 66.9597, "lat": 39.6542, "urban_radius_m": 12000, "ring_outer_m": 36000},
            "Bukhara": {"lon": 64.4286, "lat": 39.7748, "urban_radius_m": 10000, "ring_outer_m": 30000},
            "Andijan": {"lon": 72.3442, "lat": 40.7821, "urban_radius_m": 10000, "ring_outer_m": 30000},
            "Namangan": {"lon": 71.6726, "lat": 40.9983, "urban_radius_m": 10000, "ring_outer_m": 30000},
            "Fergana": {"lon": 71.7843, "lat": 40.3842, "urban_radius_m": 8000, "ring_outer_m": 24000},
            "Nukus": {"lon": 59.6103, "lat": 42.4731, "urban_radius_m": 10000, "ring_outer_m": 30000},
            "Urgench": {"lon": 60.6409, "lat": 41.5500, "urban_radius_m": 8000, "ring_outer_m": 24000},
            "Termez": {"lon": 67.2800, "lat": 37.2200, "urban_radius_m": 8000, "ring_outer_m": 24000},
            "Qarshi": {"lon": 65.8000, "lat": 38.8600, "urban_radius_m": 10000, "ring_outer_m": 30000},
            "Jizzakh": {"lon": 67.8500, "lat": 40.1200, "urban_radius_m": 8000, "ring_outer_m": 24000},
            "Navoiy": {"lon": 65.3800, "lat": 40.0800, "urban_radius_m": 8000, "ring_outer_m": 24000},
            "Gulistan": {"lon": 68.7800, "lat": 40.4800, "urban_radius_m": 6000, "ring_outer_m": 18000},
            "Nurafshon": {"lon": 69.4000, "lat": 41.2500, "urban_radius_m": 5000, "ring_outer_m": 15000}
        }
        
        # Load water scarcity data
        self._load_water_scarcity_data()
    
    def _load_water_scarcity_data(self):
        """Load water scarcity data from GEE-derived sources"""
        print("Loading water scarcity assessment data...")
        
        # For now, we'll simulate water scarcity data based on known regional patterns
        # In production, this would load from GEE exports or API calls
        self._simulate_water_scarcity_data()
        
        print(f"✓ Loaded water scarcity data for {len(self.water_data)} cities")
    
    def _simulate_water_scarcity_data(self):
        """Simulate water scarcity data based on regional patterns and known conditions"""
        # Based on Uzbekistan's regional water availability patterns
        
        # Aral Sea region (Nukus, Urgench) - severe water scarcity
        aral_region = ["Nukus", "Urgench"]
        for city in aral_region:
            self.water_data[city] = WaterScarcityMetrics(
                city=city,
                aridity_index=0.15,  # Very arid
                climatic_water_deficit=850,  # High deficit
                drought_frequency=0.35,  # 35% of months in severe drought
                surface_water_change=-45,  # Significant water loss
                cropland_fraction=0.25,  # Moderate agriculture
                population_density=85,  # Moderate density
                aqueduct_bws_score=4.2  # High water stress
            )
        
        # Southern region (Termez, Qarshi) - moderate water scarcity
        southern_region = ["Termez", "Qarshi"]
        for city in southern_region:
            self.water_data[city] = WaterScarcityMetrics(
                city=city,
                aridity_index=0.22,
                climatic_water_deficit=720,
                drought_frequency=0.28,
                surface_water_change=-25,
                cropland_fraction=0.35,  # Higher agriculture
                population_density=95,
                aqueduct_bws_score=3.8
            )
        
        # Central region (Bukhara, Navoiy) - moderate-high water scarcity
        central_region = ["Bukhara", "Navoiy"]
        for city in central_region:
            self.water_data[city] = WaterScarcityMetrics(
                city=city,
                aridity_index=0.18,
                climatic_water_deficit=780,
                drought_frequency=0.32,
                surface_water_change=-35,
                cropland_fraction=0.30,
                population_density=75,
                aqueduct_bws_score=4.0
            )
        
        # Fergana Valley (Andijan, Namangan, Fergana) - moderate water scarcity but high demand
        fergana_region = ["Andijan", "Namangan", "Fergana"]
        for city in fergana_region:
            self.water_data[city] = WaterScarcityMetrics(
                city=city,
                aridity_index=0.25,  # Less arid but high demand
                climatic_water_deficit=650,
                drought_frequency=0.25,
                surface_water_change=-15,
                cropland_fraction=0.45,  # High agriculture intensity
                population_density=180,  # High population density
                aqueduct_bws_score=3.5
            )
        
        # Tashkent region - relatively better water availability
        tashkent_region = ["Tashkent", "Nurafshon"]
        for city in tashkent_region:
            self.water_data[city] = WaterScarcityMetrics(
                city=city,
                aridity_index=0.28,
                climatic_water_deficit=580,
                drought_frequency=0.22,
                surface_water_change=-10,
                cropland_fraction=0.40,
                population_density=220,  # Very high density
                aqueduct_bws_score=3.2
            )
        
        # Other cities - mixed conditions
        other_cities = ["Samarkand", "Jizzakh", "Gulistan"]
        for city in other_cities:
            self.water_data[city] = WaterScarcityMetrics(
                city=city,
                aridity_index=0.24,
                climatic_water_deficit=680,
                drought_frequency=0.26,
                surface_water_change=-20,
                cropland_fraction=0.38,
                population_density=120,
                aqueduct_bws_score=3.6
            )
    
    def _calculate_water_scarcity_scores(self, city: str) -> WaterScarcityMetrics:
        """Calculate composite water scarcity scores for a city"""
        if city not in self.water_data:
            return WaterScarcityMetrics(city=city)
        
        metrics = self.water_data[city]
        
        # Calculate supply risk (higher values = higher risk)
        supply_indicators = [
            1.0 - metrics.aridity_index,  # Invert AI (lower AI = higher risk)
            metrics.climatic_water_deficit / 1000.0,  # Normalize CWD
            metrics.drought_frequency,  # Direct frequency
            -metrics.surface_water_change / 100.0  # Invert change (negative = higher risk)
        ]
        metrics.water_supply_risk = np.mean(supply_indicators)
        
        # Calculate demand risk (higher values = higher risk)
        demand_indicators = [
            metrics.cropland_fraction,  # Higher agriculture = higher demand
            metrics.population_density / 300.0  # Normalize population density
        ]
        metrics.water_demand_risk = np.mean(demand_indicators)
        
        # Overall water scarcity score (0-1 scale)
        # Weight supply (60%) and demand (40%) with Aqueduct benchmark (20% weight)
        supply_weight = 0.48  # 60% * 80%
        demand_weight = 0.32  # 40% * 80%
        aqueduct_weight = 0.20  # 20%
        
        metrics.overall_water_scarcity_score = (
            supply_weight * metrics.water_supply_risk +
            demand_weight * metrics.water_demand_risk +
            aqueduct_weight * (metrics.aqueduct_bws_score / 5.0)  # Normalize Aqueduct 0-5 scale
        )
        
        # Classify water scarcity level
        if metrics.overall_water_scarcity_score >= 0.7:
            metrics.water_scarcity_level = "Critical"
        elif metrics.overall_water_scarcity_score >= 0.5:
            metrics.water_scarcity_level = "High"
        elif metrics.overall_water_scarcity_score >= 0.3:
            metrics.water_scarcity_level = "Moderate"
        else:
            metrics.water_scarcity_level = "Low"
        
        return metrics
    
    def assess_city_water_scarcity(self, city: str) -> WaterScarcityMetrics:
        """Assess water scarcity risk for a specific city"""
        return self._calculate_water_scarcity_scores(city)
    
    def assess_all_cities_water_scarcity(self) -> Dict[str, WaterScarcityMetrics]:
        """Assess water scarcity for all cities"""
        results = {}
        for city in self.city_definitions.keys():
            results[city] = self.assess_city_water_scarcity(city)
        return results
    
    def get_water_scarcity_summary(self) -> Dict[str, Any]:
        """Get summary statistics for water scarcity assessment"""
        # Assess all cities to get current metrics
        assessed_data = self.assess_all_cities_water_scarcity()
        
        if not assessed_data:
            return {}
        
        scores = [metrics.overall_water_scarcity_score for metrics in assessed_data.values()]
        
        # Get risk level distribution
        risk_levels = {}
        for metrics in assessed_data.values():
            level = metrics.water_scarcity_level
            risk_levels[level] = risk_levels.get(level, 0) + 1
        
        # Get top risk cities
        top_risk_cities = sorted(
            [{"city": city, "score": metrics.overall_water_scarcity_score, "level": metrics.water_scarcity_level} 
             for city, metrics in assessed_data.items()],
            key=lambda x: x["score"], 
            reverse=True
        )[:5]
        
        return {
            "total_cities": len(assessed_data),
            "average_water_scarcity_score": float(np.mean(scores)),
            "median_water_scarcity_score": float(np.median(scores)),
            "max_water_scarcity_score": float(np.max(scores)),
            "min_water_scarcity_score": float(np.min(scores)),
            "cities_with_critical_scarcity": len([s for s in scores if s >= 0.7]),
            "cities_with_high_scarcity": len([s for s in scores if 0.5 <= s < 0.7]),
            "cities_with_moderate_scarcity": len([s for s in scores if 0.3 <= s < 0.5]),
            "cities_with_low_scarcity": len([s for s in scores if s < 0.3]),
            "risk_distribution": risk_levels,
            "most_vulnerable_city": max(assessed_data.keys(), 
                                      key=lambda x: assessed_data[x].overall_water_scarcity_score),
            "least_vulnerable_city": min(assessed_data.keys(), 
                                       key=lambda x: assessed_data[x].overall_water_scarcity_score),
            "top_risk_cities": top_risk_cities
        }
    
    def export_water_scarcity_data(self, output_path: str):
        """Export water scarcity assessment data to JSON"""
        export_data = {}
        for city, metrics in self.water_data.items():
            export_data[city] = {
                "aridity_index": metrics.aridity_index,
                "climatic_water_deficit": metrics.climatic_water_deficit,
                "drought_frequency": metrics.drought_frequency,
                "surface_water_change": metrics.surface_water_change,
                "cropland_fraction": metrics.cropland_fraction,
                "population_density": metrics.population_density,
                "aqueduct_bws_score": metrics.aqueduct_bws_score,
                "water_supply_risk": metrics.water_supply_risk,
                "water_demand_risk": metrics.water_demand_risk,
                "overall_water_scarcity_score": metrics.overall_water_scarcity_score,
                "water_scarcity_level": metrics.water_scarcity_level
            }
        
        output_file = Path(output_path) / "water_scarcity_assessment.json"
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"✓ Exported water scarcity data to {output_file}")
