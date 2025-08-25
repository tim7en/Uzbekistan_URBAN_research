"""
Climate assessment reporting and visualization service
Generates dashboards, tables, and reports for IPCC AR6 climate risk assessments
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from typing import Dict, List, Optional, Any

from .climate_risk_assessment import ClimateRiskMetrics


class ClimateAssessmentReporter:
    """Service for generating climate assessment reports and visualizations"""
    
    def __init__(self, output_path: str):
        self.output_path = Path(output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)
    
    def generate_comprehensive_report(self, city_risk_profiles: Dict[str, ClimateRiskMetrics]):
        """Generate all reports and visualizations"""
        if not city_risk_profiles:
            print("No assessment data available for reporting")
            return
        
        print("Generating comprehensive climate assessment report...")
        
        # Generate visualizations
        self.create_risk_assessment_dashboard(city_risk_profiles)
        self.create_adaptability_ranking_table(city_risk_profiles)
        
        # Generate text report
        self.generate_assessment_summary(city_risk_profiles)
        
        print(f"[SUCCESS] Reports generated and saved to: {self.output_path}")
    
    def create_risk_assessment_dashboard(self, city_risk_profiles: Dict[str, ClimateRiskMetrics]):
        """Create comprehensive climate risk assessment dashboard"""
        if not city_risk_profiles:
            print("No risk assessment data available")
            return None
        
        # Prepare data for visualization
        cities = list(city_risk_profiles.keys())
        hazard_scores = [city_risk_profiles[city].hazard_score for city in cities]
        exposure_scores = [city_risk_profiles[city].exposure_score for city in cities]
        vulnerability_scores = [city_risk_profiles[city].vulnerability_score for city in cities]
        adaptive_capacity_scores = [city_risk_profiles[city].adaptive_capacity_score for city in cities]
        overall_risk_scores = [city_risk_profiles[city].overall_risk_score for city in cities]
        adaptability_scores = [city_risk_profiles[city].adaptability_score for city in cities]
        populations = [city_risk_profiles[city].population or 0 for city in cities]
        
        # Create comprehensive dashboard
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                "IPCC AR6 Risk Components by City",
                "Risk vs Adaptability Matrix",
                "Population-Weighted Risk Assessment",
                "Adaptive Capacity vs Overall Risk",
                "Climate Risk Classification",
                "Priority Action Matrix"
            ),
            specs=[[{"type": "bar"}, {"type": "scatter"}],
                   [{"type": "scatter"}, {"type": "scatter"}],
                   [{"type": "bar"}, {"type": "scatter"}]]
        )
        
        # Panel 1: Risk components with professional styling
        fig.add_trace(go.Bar(x=cities, y=hazard_scores, name="Hazard", 
                            marker_color='#DC143C', opacity=0.8, 
                            hovertemplate="<b>%{x}</b><br>Hazard Score: %{y:.3f}<extra></extra>"), row=1, col=1)
        fig.add_trace(go.Bar(x=cities, y=exposure_scores, name="Exposure", 
                            marker_color='#FF8C00', opacity=0.8,
                            hovertemplate="<b>%{x}</b><br>Exposure Score: %{y:.3f}<extra></extra>"), row=1, col=1)
        fig.add_trace(go.Bar(x=cities, y=vulnerability_scores, name="Vulnerability", 
                            marker_color='#FFD700', opacity=0.8,
                            hovertemplate="<b>%{x}</b><br>Vulnerability Score: %{y:.3f}<extra></extra>"), row=1, col=1)
        fig.add_trace(go.Bar(x=cities, y=adaptive_capacity_scores, name="Adaptive Capacity", 
                            marker_color='#32CD32', opacity=0.8,
                            hovertemplate="<b>%{x}</b><br>Adaptive Capacity Score: %{y:.3f}<extra></extra>"), row=1, col=1)
        
        # Panel 2: Risk vs Adaptability Matrix - Professional styling with risk-based colors
        # Create risk-based color mapping
        def get_risk_adaptability_color(risk, adaptability):
            """Determine color based on risk level and adaptability"""
            if risk > 0.6:
                return '#8B0000' if adaptability < 0.4 else '#DC143C'  # Dark red to red
            elif risk > 0.4:
                return '#FF8C00' if adaptability < 0.4 else '#FFA500'  # Dark orange to orange
            elif risk > 0.2:
                return '#FFD700' if adaptability < 0.4 else '#FFFF00'  # Gold to yellow
            else:
                return '#32CD32' if adaptability < 0.4 else '#00FF00'  # Lime to green
        
        risk_adapt_colors = [get_risk_adaptability_color(r, a) for r, a in zip(overall_risk_scores, adaptability_scores)]
        
        fig.add_trace(go.Scatter(
            x=overall_risk_scores, y=adaptability_scores,
            mode='markers+text', 
            text=[f"<b>{city}</b>" for city in cities], 
            textposition='top center',
            textfont=dict(size=10, color='black'),
            marker=dict(
                size=18, 
                color=risk_adapt_colors, 
                opacity=0.8,
                line=dict(width=2, color='white'),
                symbol='circle'
            ),
            name="Risk-Adaptability", showlegend=False,
            hovertemplate="<b>%{text}</b><br>" +
                         "Risk Score: %{x:.3f}<br>" +
                         "Adaptability: %{y:.3f}<br>" +
                         "<extra></extra>"
        ), row=1, col=2)
        
        # Panel 3: Population-weighted risk with normalized marker sizing and professional styling
        pop_array = np.array(populations, dtype=float)
        # replace zeros with median to avoid tiny markers
        if np.nanmax(pop_array) == 0:
            pop_array = np.ones_like(pop_array)
        pop_array = np.where(pop_array <= 0, np.nanmax(pop_array), pop_array)
        pop_sqrt = np.sqrt(pop_array)
        min_s, max_s = float(np.nanmin(pop_sqrt)), float(np.nanmax(pop_sqrt))
        if max_s == min_s:
            sizes = np.full_like(pop_sqrt, 15.0)
        else:
            sizes = np.interp(pop_sqrt, (min_s, max_s), (10.0, 50.0))

        fig.add_trace(go.Scatter(
            x=populations, y=overall_risk_scores,
            mode='markers+text', 
            text=[f"<b>{city}</b>" for city in cities], 
            textposition='top center',
            textfont=dict(size=9, color='black'),
            marker=dict(
                size=sizes.tolist(),
                color=overall_risk_scores,
                colorscale='Reds',
                showscale=True,
                colorbar=dict(title="Risk Score", x=0.48, len=0.3, y=0.65),
                opacity=0.8,
                line=dict(width=2, color='white'),
                symbol='circle'
            ),
            name="Population Risk", showlegend=False,
            hovertemplate="<b>%{text}</b><br>" +
                         "Population: %{x:,}<br>" +
                         "Risk Score: %{y:.3f}<br>" +
                         "<extra></extra>"
        ), row=2, col=1)
        
        # Panel 4: Adaptive capacity vs risk - Color coded by risk level with professional styling
        fig.add_trace(go.Scatter(
            x=adaptive_capacity_scores, y=overall_risk_scores,
            mode='markers+text', 
            text=[f"<b>{city}</b>" for city in cities], 
            textposition='top center',
            textfont=dict(size=10, color='black'),
            marker=dict(
                size=16, 
                color=overall_risk_scores,
                colorscale='RdYlGn_r',  # Red-Yellow-Green reversed (high risk = red)
                showscale=True,
                colorbar=dict(title="Risk Score", x=1.02, len=0.3, y=0.35),
                opacity=0.8,
                line=dict(width=2, color='white'),
                symbol='diamond'
            ),
            name="Capacity vs Risk", showlegend=False,
            hovertemplate="<b>%{text}</b><br>" +
                         "Adaptive Capacity: %{x:.3f}<br>" +
                         "Risk Score: %{y:.3f}<br>" +
                         "<extra></extra>"
        ), row=2, col=2)
        
        # Panel 5: Risk classification with professional styling
        # Compute categorical risk labels using canonical function
        risk_categories = self._compute_risk_categories(overall_risk_scores)
        category_counts = pd.Series(risk_categories).value_counts()
        # Ensure consistent ordering
        ordered_cats = [c for c in ['Very High Risk', 'High Risk', 'Medium Risk', 'Low Risk'] if c in category_counts.index]
        colors_cat = {'Low Risk': '#32CD32', 'Medium Risk': '#FFD700', 'High Risk': '#FF8C00', 'Very High Risk': '#DC143C'}

        fig.add_trace(go.Bar(
            x=ordered_cats, y=[category_counts[c] for c in ordered_cats],
            marker_color=[colors_cat[cat] for cat in ordered_cats],
            opacity=0.8, name="Risk Categories", showlegend=False,
            text=[category_counts[c] for c in ordered_cats],
            textposition='auto',
            textfont=dict(size=14, color='white', family='Arial Black'),
            hovertemplate="<b>%{x}</b><br>Cities: %{y}<extra></extra>"
        ), row=3, col=1)

        # Panel 6: Priority action matrix with enhanced styling
        priority_scores = self._calculate_priority_scores(city_risk_profiles)
        priority_labels = self._get_priority_labels(priority_scores)

        color_map = {"Urgent":"#8B0000","High":"#DC143C","Medium":"#FF8C00","Low":"#32CD32"}
        urgency_colors = [color_map[label] for label in priority_labels]

        # Create symbol mapping for priority levels
        symbol_map = {"Urgent":"diamond","High":"square","Medium":"circle","Low":"triangle-up"}
        urgency_symbols = [symbol_map[label] for label in priority_labels]

        fig.add_trace(go.Scatter(
            x=priority_scores, y=populations,
            mode='markers+text', 
            text=[f"<b>{city}</b>" for city in cities], 
            textposition='top center',
            textfont=dict(size=9, color='black'),
            marker=dict(
                size=18, 
                color=urgency_colors, 
                opacity=0.8,
                line=dict(width=2, color='white'),
                symbol=urgency_symbols
            ),
            name="Action Priority", showlegend=False,
            hovertemplate="<b>%{text}</b><br>" +
                         "Priority Score: %{x:.3f}<br>" +
                         "Population: %{y:,}<br>" +
                         "Priority Level: " + "%{customdata}<br>" +
                         "<extra></extra>",
            customdata=priority_labels
        ), row=3, col=2)
        
        # Add reference lines
        fig.add_hline(y=0.5, line_dash="dash", line_color="black", opacity=0.5, row=1, col=2)
        fig.add_vline(x=0.5, line_dash="dash", line_color="black", opacity=0.5, row=1, col=2)
        fig.add_vline(x=0.5, line_dash="dash", line_color="black", opacity=0.5, row=2, col=2)
        fig.add_hline(y=0.5, line_dash="dash", line_color="black", opacity=0.5, row=2, col=2)
        
        # Update layout with professional styling
        fig.update_layout(
            title=dict(
                text="<b>IPCC AR6 Urban Climate Risk Assessment Dashboard</b><br><sub>Uzbekistan Cities - Climate Change Adaptability Analysis</sub>",
                x=0.5, 
                font=dict(size=20, color='#2E4057'),
                pad=dict(t=20, b=20)
            ),
            height=1200, width=1600,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            plot_bgcolor='white',
            paper_bgcolor='#F8F9FA',
            font=dict(family="Arial, sans-serif", size=12, color='#2E4057')
        )
        
        # Update axes labels with professional styling
        fig.update_xaxes(title_text="<b>Cities</b>", row=1, col=1, showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig.update_yaxes(title_text="<b>Risk Component Score</b>", row=1, col=1, showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig.update_xaxes(title_text="<b>Overall Risk Score</b>", row=1, col=2, showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig.update_yaxes(title_text="<b>Adaptability Score</b>", row=1, col=2, showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig.update_xaxes(title_text="<b>Population</b>", row=2, col=1, showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig.update_yaxes(title_text="<b>Overall Risk Score</b>", row=2, col=1, showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig.update_xaxes(title_text="<b>Adaptive Capacity Score</b>", row=2, col=2, showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig.update_yaxes(title_text="<b>Overall Risk Score</b>", row=2, col=2, showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig.update_xaxes(title_text="<b>Risk Categories</b>", row=3, col=1, showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig.update_yaxes(title_text="<b>Number of Cities</b>", row=3, col=1, showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig.update_xaxes(title_text="<b>Priority Score</b>", row=3, col=2, showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig.update_yaxes(title_text="<b>Population</b>", row=3, col=2, showgrid=True, gridwidth=1, gridcolor='lightgray')
        
        # Save
        html_file = self.output_path / "ipcc_climate_risk_assessment.html"
        png_file = self.output_path / "ipcc_climate_risk_assessment.png"
        fig.write_html(str(html_file))
        
        try:
            fig.write_image(str(png_file), width=1600, height=1200, scale=2)
        except Exception as e:
            print(f"Warning: Could not save PNG: {e}")
        
        print(f"✓ Saved climate risk assessment dashboard: {html_file.name}")
        return fig
    
    def create_adaptability_ranking_table(self, city_risk_profiles: Dict[str, ClimateRiskMetrics]):
        """Create detailed adaptability ranking table"""
        if not city_risk_profiles:
            return None
        
        # Calculate priority scores
        priority_scores = self._calculate_priority_scores(city_risk_profiles)
        priority_labels = self._get_priority_labels(priority_scores)
        
        # Prepare comprehensive data
        table_data = []
        for i, (city, metrics) in enumerate(city_risk_profiles.items()):
            # Use canonical risk category for table and charts so labels are consistent
            risk_level = self.risk_category_from_score(metrics.overall_risk_score)
            adaptability_level = self._get_adaptability_level(metrics.adaptability_score)
            
            table_data.append({
                'City': city,
                'Population': f"{metrics.population:,}" if metrics.population else "N/A",
                'Overall Risk': f"{metrics.overall_risk_score:.3f}",
                'Risk Level': risk_level,
                'Adaptability Score': f"{metrics.adaptability_score:.3f}",
                'Adaptability Level': adaptability_level,
                'Hazard Score': f"{metrics.hazard_score:.3f}",
                'Exposure Score': f"{metrics.exposure_score:.3f}",
                'Vulnerability Score': f"{metrics.vulnerability_score:.3f}",
                'Adaptive Capacity': f"{metrics.adaptive_capacity_score:.3f}",
                'Current SUHI (°C)': f"{metrics.current_suhi_intensity:.2f}",
                'Temp Trend (°C/yr)': f"{metrics.temperature_trend:.4f}",
                # keep numeric priority score for sorting and also formatted string for display
                'Priority Score (num)': priority_scores[i],
                'Priority Score': f"{priority_scores[i]:.3f}",
                'Action Priority': priority_labels[i]
            })
        
        # Sort by numeric priority score (descending) then remove the numeric column
        df = pd.DataFrame(table_data).sort_values("Priority Score (num)", ascending=False)
        df = df.drop(columns=["Priority Score (num)"])  # Remove helper column from display
        
        # Create color-coded table
        cell_colors = self._create_table_cell_colors(df)
        
        fig = go.Figure(data=[go.Table(
            header=dict(
                values=list(df.columns),
                fill_color='lightblue',
                align='center',
                font=dict(size=12, color='black'),
                height=40
            ),
            cells=dict(
                values=[df[col] for col in df.columns],
                fill_color=cell_colors,
                align='center',
                font=dict(size=10),
                height=35
            )
        )])
        
        fig.update_layout(
            title=dict(
                text="Urban Climate Change Adaptability Assessment Results<br><sub>IPCC AR6 Methodology - Ranked by Climate Risk</sub>",
                x=0.5, font=dict(size=16)
            ),
            height=600 + len(df) * 35,
            width=1600
        )
        
        # Save
        html_file = self.output_path / "adaptability_ranking_table.html"
        png_file = self.output_path / "adaptability_ranking_table.png"
        fig.write_html(str(html_file))
        
        try:
            fig.write_image(str(png_file), width=1600, height=600 + len(df) * 35, scale=2)
        except Exception as e:
            print(f"Warning: Could not save PNG: {e}")
        
        print(f"✓ Saved adaptability ranking table: {html_file.name}")
        return fig
    
    def generate_assessment_summary(self, city_risk_profiles: Dict[str, ClimateRiskMetrics]):
        """Generate comprehensive assessment text report"""
        if not city_risk_profiles:
            print("No assessment data available")
            return
        
        print("\n" + "="*80)
        print("IPCC AR6 URBAN CLIMATE RISK ASSESSMENT REPORT")
        print("="*80)
        
        # Summary statistics
        risk_scores = [metrics.overall_risk_score for metrics in city_risk_profiles.values()]
        adapt_scores = [metrics.adaptability_score for metrics in city_risk_profiles.values()]
        
        print(f"\n📊 ASSESSMENT SUMMARY:")
        print(f"   Cities Assessed: {len(city_risk_profiles)}")
        print(f"   Average Risk Score: {np.mean(risk_scores):.3f}")
        print(f"   Average Adaptability Score: {np.mean(adapt_scores):.3f}")
        print(f"   Highest Risk City: {max(city_risk_profiles.keys(), key=lambda x: city_risk_profiles[x].overall_risk_score)}")
        print(f"   Most Adaptable City: {max(city_risk_profiles.keys(), key=lambda x: city_risk_profiles[x].adaptability_score)}")
        
        # Risk categories
        high_risk = [city for city, metrics in city_risk_profiles.items() if metrics.overall_risk_score > 0.6]
        low_adaptability = [city for city, metrics in city_risk_profiles.items() if metrics.adaptability_score < 0.4]
        urgent_action = list(set(high_risk) & set(low_adaptability))
        
        print(f"\n🚨 HIGH PRIORITY CITIES (Risk > 0.6): {len(high_risk)}")
        for city in high_risk:
            risk = city_risk_profiles[city].overall_risk_score
            adapt = city_risk_profiles[city].adaptability_score
            print(f"   {city}: Risk={risk:.3f}, Adaptability={adapt:.3f}")
        
        print(f"\n⚠️  URGENT ACTION NEEDED: {len(urgent_action)}")
        for city in urgent_action:
            print(f"   {city}: High risk + Low adaptability")
        
        print(f"\n📈 CLIMATE TRENDS:")
        temp_trends = [metrics.temperature_trend for metrics in city_risk_profiles.values() if metrics.temperature_trend != 0]
        if temp_trends:
            print(f"   Average Temperature Trend: {np.mean(temp_trends):.4f} °C/year")
            warming_cities = [city for city, metrics in city_risk_profiles.items() if metrics.temperature_trend > 0.05]
            print(f"   Rapidly Warming Cities (>0.05°C/yr): {len(warming_cities)}")
        
        print("="*80)
        
        # Save text report
        report_file = self.output_path / "climate_assessment_report.txt"
        with open(report_file, 'w') as f:
            f.write("IPCC AR6 URBAN CLIMATE RISK ASSESSMENT REPORT\n")
            f.write("="*80 + "\n\n")
            f.write(f"Assessment Date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Cities Assessed: {len(city_risk_profiles)}\n")
            f.write(f"Average Risk Score: {np.mean(risk_scores):.3f}\n")
            f.write(f"Average Adaptability Score: {np.mean(adapt_scores):.3f}\n\n")
            
            # Detailed city results
            for city, metrics in sorted(city_risk_profiles.items(), 
                                      key=lambda x: x[1].overall_risk_score, reverse=True):
                f.write(f"\n{city}:\n")
                f.write(f"  Overall Risk: {metrics.overall_risk_score:.3f}\n")
                f.write(f"  Adaptability: {metrics.adaptability_score:.3f}\n")
                f.write(f"  Hazard: {metrics.hazard_score:.3f}\n")
                f.write(f"  Exposure: {metrics.exposure_score:.3f}\n")
                f.write(f"  Vulnerability: {metrics.vulnerability_score:.3f}\n")
                f.write(f"  Adaptive Capacity: {metrics.adaptive_capacity_score:.3f}\n")
                f.write(f"  Population: {metrics.population:,}\n" if metrics.population else "  Population: N/A\n")
                f.write(f"  Temperature Trend: {metrics.temperature_trend:.4f} °C/year\n")
        
        print(f"✓ Saved detailed text report: {report_file.name}")
    
    def _calculate_priority_scores(self, city_risk_profiles: Dict[str, ClimateRiskMetrics]) -> List[float]:
        """Calculate priority scores for cities using quantile-based approach"""
        cities = list(city_risk_profiles.keys())
        overall_risk_scores = [city_risk_profiles[city].overall_risk_score for city in cities]
        adaptive_capacity_scores = [city_risk_profiles[city].adaptive_capacity_score for city in cities]
        populations = [city_risk_profiles[city].population or 0 for city in cities]
        
        def qscale(series, x, lo=0.1, hi=0.9):
            s = pd.Series(series)
            a, b = s.quantile(lo), s.quantile(hi)
            if a == b: 
                return 0.5
            return float(np.clip((x - a) / (b - a), 0, 1))

        risk_q  = [qscale(overall_risk_scores, r) for r in overall_risk_scores]
        ac_gap  = [1 - a for a in adaptive_capacity_scores]  # low AC => high gap
        ac_q    = [qscale(ac_gap, g) for g in ac_gap]
        pop_q   = [qscale(populations, p) for p in populations]

        # priority scoring (geometric-ish mix)
        alpha, beta = 0.8, 0.6   # emphasis on risk, then AC gap
        priority_scores = [
            (rq ** alpha) * (aq ** beta) * (max(0.2, pq) ** 0.4)  # ensure small cities not zeroed
            for rq, aq, pq in zip(risk_q, ac_q, pop_q)
        ]
        
        return priority_scores
    
    def _get_priority_labels(self, priority_scores: List[float]) -> List[str]:
        """Convert priority scores to categorical labels"""
        q80 = float(pd.Series(priority_scores).quantile(0.80))
        q50 = float(pd.Series(priority_scores).quantile(0.50))
        q20 = float(pd.Series(priority_scores).quantile(0.20))

        def bucket(p):
            if p >= q80: return "Urgent"
            if p >= q50: return "High"
            if p >= q20: return "Medium"
            return "Low"

        return [bucket(p) for p in priority_scores]

    def _compute_risk_categories(self, overall_risk_scores: List[float]) -> List[str]:
        """Compute categorical risk labels using absolute thresholds based on IPCC AR6 standards"""
        return [self.risk_category_from_score(risk) for risk in overall_risk_scores]

    def risk_category_from_score(self, risk_score: float) -> str:
        """Canonical mapping from numeric risk score to category label.

        This centralizes thresholds so all UI elements and summaries use the same buckets.
        Thresholds (inclusive/exclusive as below) are:
          risk < 0.2 -> 'Low Risk'
          0.2 <= risk < 0.4 -> 'Medium Risk'
          0.4 <= risk < 0.6 -> 'High Risk'
          risk >= 0.6 -> 'Very High Risk'
        """
        if risk_score is None:
            return "N/A"
        try:
            r = float(risk_score)
        except Exception:
            return "N/A"

        if r < 0.2:
            return "Low Risk"
        elif r < 0.4:
            return "Medium Risk"
        elif r < 0.6:
            return "High Risk"
        else:
            return "Very High Risk"
    
    def _get_risk_level(self, risk_score: float) -> str:
        """Convert risk score to categorical level"""
        if risk_score > 0.7:
            return "Very High"
        elif risk_score > 0.5:
            return "High"
        elif risk_score > 0.3:
            return "Medium"
        else:
            return "Low"
    
    def _get_adaptability_level(self, adaptability_score: float) -> str:
        """Convert adaptability score to categorical level"""
        if adaptability_score > 0.7:
            return "Very High"
        elif adaptability_score > 0.5:
            return "High"
        elif adaptability_score > 0.3:
            return "Medium"
        else:
            return "Low"
    
    def _create_table_cell_colors(self, df: pd.DataFrame) -> List[List[str]]:
        """Create color matrix for table cells"""
        def get_cell_color(value, column):
            if column in ['Risk Level', 'Action Priority']:
                if 'Very High' in value or 'Urgent' in value:
                    return 'rgba(255, 0, 0, 0.3)'
                elif 'High' in value:
                    return 'rgba(255, 165, 0, 0.3)'
                elif 'Medium' in value:
                    return 'rgba(255, 255, 0, 0.3)'
                else:
                    return 'rgba(0, 255, 0, 0.3)'
            elif column == 'Adaptability Level':
                if 'Very High' in value:
                    return 'rgba(0, 255, 0, 0.3)'
                elif 'High' in value:
                    return 'rgba(255, 255, 0, 0.3)'
                elif 'Medium' in value:
                    return 'rgba(255,165, 0, 0.3)'
                else:
                    return 'rgba(255, 0, 0, 0.3)'
            return 'white'
        
        # Create cell colors matrix
        cell_colors = []
        for col in df.columns:
            col_colors = [get_cell_color(str(val), col) for val in df[col]]
            cell_colors.append(col_colors)
        
        return cell_colors
