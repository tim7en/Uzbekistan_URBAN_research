#!/usr/bin/env python3
"""
Comprehensive Chart Generator for Uzbekistan URBAN Research SUHI Analysis
- Load data from multiple JSON sources (SUHI, LULC, Nightlights, Temperature, Spatial)
- Generate meaningful visualizations with confidence intervals
- Support temporal analysis across all available years
- Create publication-ready charts
"""

import json
import os
from pathlib import Path
from datetime import datetime
import warnings
from typing import Dict, List, Any, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
import plotly.express as px

# ----------------------------
# Plotly config
# ----------------------------
warnings.filterwarnings("ignore")
pio.templates.default = "plotly_white"

# Kaleido availability check (for PNG exports)
_KALEIDO_OK = True
try:
    import kaleido  # noqa: F401
except Exception:
    _KALEIDO_OK = False


def safe_write_image(fig, path, width, height, scale):
    """Write PNG if kaleido is available; otherwise skip without crashing."""
    if not _KALEIDO_OK:
        print(f"Warning: Kaleido not available, skipping PNG export for {path}")
        return False
    try:
        fig.write_image(str(path), width=width, height=height, scale=scale)
        return True
    except Exception as e:
        print(f"Warning: Failed to save PNG {path}: {e}")
        return False


# ----------------------------
# Helper Functions
# ----------------------------
def safe_get(data: dict, key: str, default=None):
    """Safely get a value from nested dictionary"""
    try:
        return data.get(key, default)
    except (AttributeError, TypeError):
        return default


def safe_float(value, default=None):
    """Safely convert value to float"""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


class SUHIChartGenerator:
    def __init__(self, data_path, output_path):
        self.data_path = Path(data_path)
        self.output_path = Path(output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)

        # containers
        self.cities_data = {}     # {city: {year: json}}
        self.temporal_data = {}   # {city: temporal_json}
        self.summary_stats = {}   # computed

        # colors
        self.colors = {
            "primary_earliest": "#1f77b4",
            "primary_latest": "#ff7f0e",
            "positive": "#d62728",
            "negative": "#2ca02c",
            "neutral": "#7f7f7f",
        }
        self.city_colors = {
            "Tashkent": "#1f77b4", "Samarkand": "#ff7f0e", "Bukhara": "#2ca02c",
            "Andijan": "#d62728", "Namangan": "#9467bd", "Fergana": "#8c564b",
            "Nukus": "#e377c2", "Urgench": "#7f7f7f", "Termez": "#bcbd22",
            "Qarshi": "#17becf", "Jizzakh": "#ff9896", "Navoiy": "#98df8a",
            "Gulistan": "#c5b0d5", "Nurafshon": "#c49c94"
        }

        # discovered years
        self.earliest_year = None
        self.latest_year = None

    # ----------------------------
    # Loading & Summary
    # ----------------------------
    def load_data(self):
        print("Scanning data folder for *_results.json and *_annual_suhi_trends.json ...")
        # Find all results files
        results = list(self.data_path.glob("*_*_results.json"))
        year_set = set()
        for fp in results:
            city, year = extract_city_year(fp.stem)
            if not city or not year:
                continue
            year_set.add(year)
            self.cities_data.setdefault(city, {})
            try:
                with open(fp, "r") as f:
                    self.cities_data[city][year] = json.load(f)
            except Exception as e:
                print(f"  ! Failed to read {fp.name}: {e}")

        # Find temporal trend files
        for tf in self.data_path.glob("*_annual_suhi_trends.json"):
            city = tf.stem.replace("_annual_suhi_trends", "")
            try:
                with open(tf, "r") as f:
                    self.temporal_data[city] = json.load(f)
            except Exception as e:
                print(f"  ! Failed to read {tf.name}: {e}")

        if not year_set:
            raise RuntimeError("No *_results.json files found in the data folder.")

        self.earliest_year = min(year_set)
        self.latest_year = max(year_set)
        print(f"Discovered years: {sorted(year_set)}")
        print(f"Using earliest={self.earliest_year}, latest={self.latest_year}")

        self._calculate_summary_stats()

    def _calculate_summary_stats(self):
        self.summary_stats = {
            "suhi_comparison": {"cities": [], "suhi_earliest": [], "suhi_latest": []},
            "urban_growth": {},  # city -> dict
            "temperature_trends": {},  # city -> dict
        }

        for city, by_year in self.cities_data.items():
            if self.earliest_year in by_year and self.latest_year in by_year:
                j0 = by_year[self.earliest_year]
                j1 = by_year[self.latest_year]

                # Flexible SUHI value extraction
                suhi0 = coalesce(
                    sget(j0, "suhi_analysis.suhi"),
                    sget(j0, "suhi.suhi"),
                    sget(j0, "suhi_intensity"),
                    default=None,
                )
                suhi1 = coalesce(
                    sget(j1, "suhi_analysis.suhi"),
                    sget(j1, "suhi.suhi"),
                    sget(j1, "suhi_intensity"),
                    default=None,
                )
                suhi0 = number_or_none(suhi0)
                suhi1 = number_or_none(suhi1)
                if suhi0 is None or suhi1 is None:
                    continue

                self.summary_stats["suhi_comparison"]["cities"].append(city)
                self.summary_stats["suhi_comparison"]["suhi_earliest"].append(suhi0)
                self.summary_stats["suhi_comparison"]["suhi_latest"].append(suhi1)

                # Urban pixels (growth)
                up0 = number_or_none(coalesce(
                    sget(j0, "suhi_analysis.urban_pixels"),
                    sget(j0, "urban.pixels"),
                    sget(j0, "urban_pixels"),
                ))
                up1 = number_or_none(coalesce(
                    sget(j1, "suhi_analysis.urban_pixels"),
                    sget(j1, "urban.pixels"),
                    sget(j1, "urban_pixels"),
                ))
                growth_rate = None
                if up0 is not None and up1 is not None and up0 != 0:
                    growth_rate = (up1 - up0) / up0 * 100.0

                self.summary_stats["urban_growth"][city] = {
                    "pixels_earliest": up0,
                    "pixels_latest": up1,
                    "growth_rate": growth_rate,
                }

        # Temperature trends (from temporal files)
        for city, temporal in self.temporal_data.items():
            trends = temporal.get("trends", temporal.get("summary", {}))
            self.summary_stats["temperature_trends"][city] = {
                "suhi_trend_per_year": number_or_none(coalesce(
                    trends.get("suhi_trend_per_year"),
                    trends.get("suhi_slope_per_year"),
                    0
                )) or 0.0,
                "urban_temp_trend": number_or_none(coalesce(
                    trends.get("urban_temp_trend_per_year"),
                    trends.get("urban_slope_per_year"),
                    0
                )) or 0.0,
                "r_squared": number_or_none(coalesce(
                    trends.get("suhi_r_squared"),
                    trends.get("r2"),
                    trends.get("r_squared"),
                    0
                )) or 0.0,
            }

    # ----------------------------
    # Charts
    # ----------------------------
    def create_suhi_comparison_chart(self):
        cities = self.summary_stats["suhi_comparison"]["cities"]
        s0 = self.summary_stats["suhi_comparison"]["suhi_earliest"]
        s1 = self.summary_stats["suhi_comparison"]["suhi_latest"]
        if not cities:
            print("No cities with both earliest & latest years. Skipping comparison chart.")
            return None

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=cities, y=s0, name=f"SUHI {self.earliest_year}",
            marker_color=self.colors["primary_earliest"], opacity=0.85,
            text=[f"{v:.2f}°C" for v in s0], textposition="auto",
        ))
        fig.add_trace(go.Bar(
            x=cities, y=s1, name=f"SUHI {self.latest_year}",
            marker_color=self.colors["primary_latest"], opacity=0.85,
            text=[f"{v:.2f}°C" for v in s1], textposition="auto",
        ))
        fig.update_layout(
            title=dict(
                text=f"SUHI Intensity Comparison: {self.earliest_year} vs {self.latest_year}<br><sub>Uzbekistan Urban Centers</sub>",
                x=0.5, font=dict(size=18)
            ),
            xaxis_title="Cities", yaxis_title="SUHI Intensity (°C)",
            barmode="group", height=600, width=1000, template="plotly_white",
            legend=dict(orientation="h", y=1.02, x=1, xanchor="right", yanchor="bottom")
        )
        fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)

        html = self.output_path / "01_suhi_comparison_earliest_vs_latest.html"
        png = self.output_path / "01_suhi_comparison_earliest_vs_latest.png"
        fig.write_html(str(html))
        safe_write_image(fig, png, width=1000, height=600, scale=2)
        print(f"Saved: {html.name}")
        return fig

    def create_suhi_change_chart(self):
        cities = self.summary_stats["suhi_comparison"]["cities"]
        s0 = self.summary_stats["suhi_comparison"]["suhi_earliest"]
        s1 = self.summary_stats["suhi_comparison"]["suhi_latest"]
        if not cities:
            print("No cities with both earliest & latest years. Skipping change chart.")
            return None

        delta = [b - a for a, b in zip(s0, s1)]
        colors = [self.colors["positive"] if d > 0 else self.colors["negative"] for d in delta]

        fig = go.Figure(go.Bar(
            x=cities, y=delta, marker_color=colors, opacity=0.85,
            text=[f"{d:+.3f}°C" for d in delta], textposition="auto",
            hovertemplate="<b>%{x}</b><br>SUHI Change: %{y:.3f}°C<extra></extra>"
        ))
        fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1)
        fig.update_layout(
            title=dict(
                text=f"SUHI Change Distribution ({self.latest_year} - {self.earliest_year})<br><sub>Red: Increase | Green: Decrease</sub>",
                x=0.5, font=dict(size=18)
            ),
            xaxis_title="Cities", yaxis_title="SUHI Change (°C)",
            height=600, width=1000, template="plotly_white"
        )

        html = self.output_path / "02_suhi_change_distribution.html"
        png = self.output_path / "02_suhi_change_distribution.png"
        fig.write_html(str(html))
        safe_write_image(fig, png, width=1000, height=600, scale=2)
        print(f"Saved: {html.name}")
        return fig

    def create_urban_growth_chart(self):
        # Only cities with growth_rate present
        rows = []
        for city, d in self.summary_stats["urban_growth"].items():
            if d.get("growth_rate") is not None:
                rows.append((city, d["growth_rate"], d.get("pixels_earliest"), d.get("pixels_latest")))
        if not rows:
            print("No urban growth data. Skipping growth chart.")
            return None

        cities, growth_rates, p0, p1 = zip(*rows)
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=("Urban Growth Rate (%)", f"Urban Area (Pixels): {self.earliest_year} vs {self.latest_year}"),
            column_widths=[0.4, 0.6]
        )
        fig.add_trace(go.Bar(
            x=list(cities), y=list(growth_rates), name="Growth Rate",
            marker_color=[self.city_colors.get(c, self.colors["neutral"]) for c in cities],
            opacity=0.85, text=[f"{v:.1f}%" for v in growth_rates], textposition="auto"
        ), row=1, col=1)

        fig.add_trace(go.Bar(
            x=list(cities), y=list(p0), name=f"Urban Pixels {self.earliest_year}",
            marker_color=self.colors["primary_earliest"], opacity=0.85
        ), row=1, col=2)
        fig.add_trace(go.Bar(
            x=list(cities), y=list(p1), name=f"Urban Pixels {self.latest_year}",
            marker_color=self.colors["primary_latest"], opacity=0.85
        ), row=1, col=2)

        fig.update_layout(
            title=dict(
                text=f"Urban Area Expansion Analysis: {self.earliest_year}-{self.latest_year}<br><sub>Growth Rates and Absolute Changes</sub>",
                x=0.5, font=dict(size=18)
            ),
            height=600, width=1200, template="plotly_white", barmode="group"
        )
        fig.update_xaxes(title_text="Cities", row=1, col=1)
        fig.update_yaxes(title_text="Growth Rate (%)", row=1, col=1)
        fig.update_xaxes(title_text="Cities", row=1, col=2)
        fig.update_yaxes(title_text="Urban Pixels", row=1, col=2)

        html = self.output_path / "03_urban_growth_analysis.html"
        png = self.output_path / "03_urban_growth_analysis.png"
        fig.write_html(str(html))
        safe_write_image(fig, png, width=1200, height=600, scale=2)
        print(f"Saved: {html.name}")
        return fig

    def create_temperature_trends_chart(self):
        rows = []
        for city, t in self.summary_stats["temperature_trends"].items():
            rows.append((
                city,
                t.get("suhi_trend_per_year", 0.0) or 0.0,
                t.get("urban_temp_trend", 0.0) or 0.0,
                t.get("r_squared", 0.0) or 0.0,
            ))
        if not rows:
            print("No temperature trend summaries. Skipping trends relationship chart.")
            return None

        cities, suhi_tr, urban_tr, r2 = zip(*rows)
        sizes = [max(10, r * 100) for r in r2]
        fig = go.Figure(go.Scatter(
            x=list(urban_tr), y=list(suhi_tr), mode="markers+text",
            text=list(cities), textposition="top center",
            marker=dict(size=sizes, color=list(r2), colorscale="Viridis",
                        showscale=True, colorbar=dict(title="R²"), line=dict(width=1, color="black"), opacity=0.85),
            hovertemplate="<b>%{text}</b><br>Urban Trend: %{x:.4f}°C/yr<br>SUHI Trend: %{y:.4f}°C/yr<br>R²: %{marker.color:.3f}<extra></extra>"
        ))
        fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)
        fig.add_vline(x=0, line_dash="dash", line_color="black", opacity=0.5)
        fig.update_layout(
            title=dict(
                text=f"Temperature Trends Relationship ({self.earliest_year}-{self.latest_year})<br><sub>Point size indicates R²</sub>",
                x=0.5, font=dict(size=18)
            ),
            xaxis_title="Urban Temperature Trend (°C/year)",
            yaxis_title="SUHI Trend (°C/year)",
            height=600, width=1000, template="plotly_white",
        )

        html = self.output_path / "04_temperature_trends_relationship.html"
        png = self.output_path / "04_temperature_trends_relationship.png"
        fig.write_html(str(html))
        safe_write_image(fig, png, width=1000, height=600, scale=2)
        print(f"Saved: {html.name}")
        return fig

    def create_temporal_analysis_charts(self):
        count = 0
        for city, temporal in self.temporal_data.items():
            data = temporal.get("data") or temporal.get("series") or temporal.get("time_series")
            if not isinstance(data, list) or not data:
                continue

            years = [d.get("year") for d in data]
            suhi_vals = [number_or_none(coalesce(d.get("suhi_intensity"), d.get("suhi"), d.get("suhi_mean"))) for d in data]
            urb = [number_or_none(coalesce(d.get("urban_temp"), d.get("urban"), d.get("urban_mean"))) for d in data]
            rur = [number_or_none(coalesce(d.get("rural_temp"), d.get("rural"), d.get("rural_mean"))) for d in data]

            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Scatter(
                x=years, y=suhi_vals, mode="lines+markers", name="SUHI Intensity",
                line=dict(color=self.city_colors.get(city, self.colors["primary_earliest"]), width=3),
                marker=dict(size=8)
            ), secondary_y=False)
            if any(v is not None for v in urb):
                fig.add_trace(go.Scatter(
                    x=years, y=urb, mode="lines+markers", name="Urban Temperature",
                    line=dict(color=self.colors["primary_latest"], width=2, dash="dash"),
                    marker=dict(size=6, symbol="square")
                ), secondary_y=True)
            if any(v is not None for v in rur):
                fig.add_trace(go.Scatter(
                    x=years, y=rur, mode="lines+markers", name="Rural Temperature",
                    line=dict(color=self.colors["negative"], width=2, dash="dash"),
                    marker=dict(size=6, symbol="triangle-up")
                ), secondary_y=True)

            # Trend line (SUHI) if enough numeric points
            xs = [x for x, y in zip(years, suhi_vals) if y is not None]
            ys = [y for y in suhi_vals if y is not None]
            if len(xs) >= 3:
                z = np.polyfit(xs, ys, 1)
                p = np.poly1d(z)
                fig.add_trace(go.Scatter(
                    x=xs, y=p(xs), mode="lines", name=f"SUHI Trend ({z[0]:.4f}°C/yr)",
                    line=dict(color="red", width=2, dash="dot"), opacity=0.7
                ), secondary_y=False)

            fig.update_xaxes(title_text="Year")
            fig.update_yaxes(title_text="SUHI Intensity (°C)", secondary_y=False)
            fig.update_yaxes(title_text="Temperature (°C)", secondary_y=True)
            fig.update_layout(
                title=dict(
                    text=f"{city} - Temporal SUHI Analysis ({self.earliest_year}-{self.latest_year})<br><sub>SUHI Evolution and Temperature Trends</sub>",
                    x=0.5, font=dict(size=16)
                ),
                height=500, width=900, template="plotly_white", hovermode="x unified"
            )

            html = self.output_path / f"05_temporal_{city.lower()}_{self.earliest_year}_{self.latest_year}.html"
            png = self.output_path / f"05_temporal_{city.lower()}_{self.earliest_year}_{self.latest_year}.png"
            fig.write_html(str(html))
            safe_write_image(fig, png, width=900, height=500, scale=2)
            count += 1

        print(f"Saved temporal charts for {count} cities")

    def create_correlation_matrix_chart(self):
        rows = []
        comp = self.summary_stats["suhi_comparison"]
        for city in comp["cities"]:
            idx = comp["cities"].index(city)
            s0 = comp["suhi_earliest"][idx]
            s1 = comp["suhi_latest"][idx]
            change = s1 - s0
            ug = self.summary_stats["urban_growth"].get(city, {})
            gr = ug.get("growth_rate")
            tr = self.summary_stats["temperature_trends"].get(city, {})
            slope = tr.get("suhi_trend_per_year", 0.0)
            rows.append({
                "SUHI_Earliest": s0,
                "SUHI_Latest": s1,
                "SUHI_Change": change,
                "Urban_Growth_Rate": gr if gr is not None else np.nan,
                "SUHI_Trend_Per_Year": slope if slope is not None else np.nan,
            })
        if not rows:
            print("No correlation data. Skipping.")
            return None

        df = pd.DataFrame(rows)
        corr = df.corr(numeric_only=True)
        fig = go.Figure(go.Heatmap(
            z=corr.values, x=corr.columns, y=corr.columns, colorscale="RdBu", zmid=0,
            text=corr.values, texttemplate="%{text:.3f}", textfont={"size": 12},
            hovertemplate="<b>%{y}</b> vs <b>%{x}</b><br>Correlation: %{z:.3f}<extra></extra>"
        ))
        fig.update_layout(
            title=dict(
                text=f"Correlation Matrix: SUHI Variables ({self.earliest_year}-{self.latest_year})",
                x=0.5, font=dict(size=18)
            ),
            height=600, width=700, template="plotly_white"
        )

        html = self.output_path / "06_correlation_matrix.html"
        png = self.output_path / "06_correlation_matrix.png"
        fig.write_html(str(html))
        safe_write_image(fig, png, width=700, height=600, scale=2)
        print(f"Saved: {html.name}")
        return fig

    def create_statistical_summary_chart(self):
        comp = self.summary_stats["suhi_comparison"]
        if not comp["cities"]:
            print("No comparison data for box plots. Skipping.")
            return None
        s0, s1 = comp["suhi_earliest"], comp["suhi_latest"]
        delta = [b - a for a, b in zip(s0, s1)]

        fig = go.Figure()
        fig.add_trace(go.Box(y=s0, name=f"SUHI {self.earliest_year}",
                             marker_color=self.colors["primary_earliest"],
                             boxpoints="all", jitter=0.3, pointpos=-1.8))
        fig.add_trace(go.Box(y=s1, name=f"SUHI {self.latest_year}",
                             marker_color=self.colors["primary_latest"],
                             boxpoints="all", jitter=0.3, pointpos=-1.8))
        fig.add_trace(go.Box(y=delta, name=f"SUHI Change ({self.latest_year}-{self.earliest_year})",
                             marker_color="#9467bd", boxpoints="all", jitter=0.3, pointpos=-1.8))
        fig.update_layout(
            title=dict(
                text=f"SUHI Statistical Distribution ({self.earliest_year}-{self.latest_year})<br><sub>Box plots with outliers</sub>",
                x=0.5, font=dict(size=18)
            ),
            yaxis_title="Temperature (°C)", height=600, width=800, template="plotly_white"
        )
        fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)

        html = self.output_path / "07_statistical_summary.html"
        png = self.output_path / "07_statistical_summary.png"
        fig.write_html(str(html))
        safe_write_image(fig, png, width=800, height=600, scale=2)
        print(f"Saved: {html.name}")
        return fig

    def create_accuracy_assessment_chart(self):
        cities, esa, ghsl, modis = [], [], [], []
        for city, by_year in self.cities_data.items():
            if self.latest_year not in by_year:
                continue
            acc = sget(by_year[self.latest_year], "accuracy_assessment", {})
            if not isinstance(acc, dict) or not acc:
                continue

            def first_number(d):
                if not isinstance(d, dict) or not d:
                    return None
                # use first numeric value found
                for v in d.values():
                    nv = number_or_none(v)
                    if nv is not None:
                        return nv
                return None

            cities.append(city)
            esa.append(first_number(acc.get("esa_agreement")))
            ghsl.append(first_number(acc.get("ghsl_agreement")))
            modis.append(first_number(acc.get("modis_lc_agreement")))

        if not cities:
            print("No accuracy data for latest year. Skipping accuracy chart.")
            return None

        fig = go.Figure()
        fig.add_trace(go.Bar(x=cities, y=esa, name="ESA Land Cover",
                             marker_color=self.colors["primary_earliest"], opacity=0.85))
        fig.add_trace(go.Bar(x=cities, y=ghsl, name="GHSL Built-up",
                             marker_color=self.colors["primary_latest"], opacity=0.85))
        fig.add_trace(go.Bar(x=cities, y=modis, name="MODIS Land Cover",
                             marker_color=self.colors["negative"], opacity=0.85))
        fig.update_layout(
            title=dict(
                text=f"Land Cover Classification Accuracy Assessment ({self.latest_year})",
                x=0.5, font=dict(size=18)
            ),
            xaxis_title="Cities", yaxis_title="Agreement Score",
            height=600, width=1000, template="plotly_white", barmode="group"
        )

        html = self.output_path / "08_accuracy_assessment_latest.html"
        png = self.output_path / "08_accuracy_assessment_latest.png"
        fig.write_html(str(html))
        safe_write_image(fig, png, width=1000, height=600, scale=2)
        print(f"Saved: {html.name}")
        return fig

    def create_comprehensive_overview_chart(self):
        comp = self.summary_stats["suhi_comparison"]
        if not comp["cities"]:
            print("No comparison data. Skipping overview dashboard.")
            return None

        cities = comp["cities"]
        s0, s1 = comp["suhi_earliest"], comp["suhi_latest"]
        delta = [b - a for a, b in zip(s0, s1)]

        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                f"SUHI Comparison ({self.earliest_year} vs {self.latest_year})",
                "Urban Growth vs SUHI Change",
                "Top 5 SUHI Increases",
                "Top 5 SUHI Improvements",
            ),
            specs=[[{"type": "bar"}, {"type": "scatter"}],
                   [{"type": "bar"}, {"type": "bar"}]]
        )

        # Panel 1
        fig.add_trace(go.Bar(x=cities[:7], y=s0[:7], name=str(self.earliest_year),
                             marker_color=self.colors["primary_earliest"], opacity=0.85),
                      row=1, col=1)
        fig.add_trace(go.Bar(x=cities[:7], y=s1[:7], name=str(self.latest_year),
                             marker_color=self.colors["primary_latest"], opacity=0.85),
                      row=1, col=1)

        # Panel 2
        growth_rates = []
        for c in cities:
            gr = self.summary_stats["urban_growth"].get(c, {}).get("growth_rate")
            growth_rates.append(gr if gr is not None else 0.0)
        fig.add_trace(go.Scatter(
            x=growth_rates[:len(delta)], y=delta, mode="markers+text",
            text=cities, textposition="top center",
            marker=dict(size=10, opacity=0.75), name="Cities", showlegend=False
        ), row=1, col=2)

        # Panel 3/4
        pairs = list(zip(cities, delta))
        top_inc = sorted(pairs, key=lambda x: x[1], reverse=True)[:5]
        top_dec = sorted(pairs, key=lambda x: x[1])[:5]
        fig.add_trace(go.Bar(x=[p[0] for p in top_inc], y=[p[1] for p in top_inc],
                             marker_color=self.colors["positive"], opacity=0.85,
                             name="Increases", showlegend=False), row=2, col=1)
        fig.add_trace(go.Bar(x=[p[0] for p in top_dec], y=[p[1] for p in top_dec],
                             marker_color=self.colors["negative"], opacity=0.85,
                             name="Improvements", showlegend=False), row=2, col=2)

        fig.update_layout(
            title=dict(
                text=f"SUHI Analysis Overview: {self.earliest_year}-{self.latest_year}",
                x=0.5, font=dict(size=20)
            ),
            height=800, width=1200, template="plotly_white", showlegend=True
        )
        fig.update_xaxes(title_text="Cities", row=1, col=1)
        fig.update_yaxes(title_text="SUHI (°C)", row=1, col=1)
        fig.update_xaxes(title_text="Urban Growth (%)", row=1, col=2)
        fig.update_yaxes(title_text="SUHI Change (°C)", row=1, col=2)
        fig.update_xaxes(title_text="Cities", row=2, col=1)
        fig.update_yaxes(title_text="SUHI Change (°C)", row=2, col=1)
        fig.update_xaxes(title_text="Cities", row=2, col=2)
        fig.update_yaxes(title_text="SUHI Change (°C)", row=2, col=2)

        html = self.output_path / "09_comprehensive_overview.html"
        png = self.output_path / "09_comprehensive_overview.png"
        fig.write_html(str(html))
        safe_write_image(fig, png, width=1200, height=800, scale=2)
        print(f"Saved: {html.name}")
        return fig

    # ----------------------------
    # Orchestration
    # ----------------------------
    def generate_all_charts(self):
        print("=" * 80)
        print("GENERATING INDIVIDUAL PLOTLY CHARTS")
        print("=" * 80)

        self.load_data()

        charts = []
        charts.append(self.create_suhi_comparison_chart())
        charts.append(self.create_suhi_change_chart())
        charts.append(self.create_urban_growth_chart())
        charts.append(self.create_temperature_trends_chart())
        self.create_temporal_analysis_charts()  # per-city charts
        charts.append(self.create_correlation_matrix_chart())
        charts.append(self.create_statistical_summary_chart())
        charts.append(self.create_accuracy_assessment_chart())
        charts.append(self.create_comprehensive_overview_chart())

        # Count outputs
        html_count = len(list(self.output_path.glob("*.html")))
        png_count = len(list(self.output_path.glob("*.png")))
        print("=" * 80)
        print("ALL CHARTS GENERATED")
        print("=" * 80)
        print(f"📁 Output: {self.output_path}")
        print(f"📊 Files: {html_count} HTML + {png_count} PNG")
        print("=" * 80)
        return charts


def main():
    # --- EDIT THESE PATHS IF NEEDED ---
    data_path = "/Users/timursabitov/Dev/Uzbekistan_URBAN_research/suhi_analysis_output/data"
    output_path = "/Users/timursabitov/Dev/Uzbekistan_URBAN_research/reporting"
    # -----------------------------------

    gen = SUHIChartGenerator(data_path, output_path)
    return gen.generate_all_charts()


if __name__ == "__main__":
    main()
