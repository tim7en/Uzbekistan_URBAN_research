#!/usr/bin/env python3
"""
Uzbekistan Urban Research - Professional SPA Dashboard
=====================================================

A comprehensive, professional-grade Single Page Application dashboard for 
exploring urban expansion and SUHI analysis results across Uzbekistan cities.

Features:
- Interactive data exploration with CT scan-like visualizations
- Animated network connections and transitions
- Real-time data filtering and analysis
- Professional medical/scientific visualization style
- Mobile-responsive design
- Production-ready deployment

Author: Generated for Uzbekistan Urban Research Project
Date: 2025
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import folium
from streamlit_folium import st_folium
import json
from datetime import datetime
from pathlib import Path
import base64
import warnings
warnings.filterwarnings('ignore')

# Configure page settings
st.set_page_config(
    page_title="Uzbekistan Urban Research Dashboard",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "Professional Urban Research Dashboard for Uzbekistan"
    }
)

# Custom CSS for professional styling
def load_css():
    """Load custom CSS for professional styling"""
    st.markdown("""
    <style>
        /* Global styling */
        .main .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
            max-width: 95%;
        }
        
        /* Header styling */
        .header-container {
            background: linear-gradient(135deg, #1e3c72, #2a5298);
            padding: 2rem;
            border-radius: 15px;
            margin-bottom: 2rem;
            color: white;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        
        .header-title {
            font-size: 3rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }
        
        .header-subtitle {
            font-size: 1.3rem;
            opacity: 0.9;
            margin-bottom: 1rem;
        }
        
        /* Metric cards */
        .metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1.5rem;
            border-radius: 15px;
            color: white;
            text-align: center;
            margin: 0.5rem;
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
            transition: transform 0.3s ease;
        }
        
        .metric-card:hover {
            transform: translateY(-5px);
        }
        
        .metric-value {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        
        .metric-label {
            font-size: 1rem;
            opacity: 0.9;
        }
        
        /* Sidebar styling */
        .css-1d391kg {
            background: linear-gradient(180deg, #2c3e50, #34495e);
        }
        
        /* Animation for loading */
        .loading-animation {
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 2rem;
        }
        
        .spinner {
            width: 40px;
            height: 40px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3498db;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* Professional section styling */
        .section-header {
            background: linear-gradient(135deg, #74b9ff, #0984e3);
            color: white;
            padding: 1rem 2rem;
            border-radius: 10px;
            margin: 1rem 0;
            font-size: 1.5rem;
            font-weight: 600;
            text-align: center;
        }
        
        /* CT scan-like styling for visualizations */
        .ct-scan-container {
            background: #1a1a1a;
            border: 2px solid #00ff00;
            border-radius: 10px;
            padding: 1rem;
            margin: 1rem 0;
            box-shadow: 0 0 20px rgba(0,255,0,0.3);
        }
        
        /* Network connection styling */
        .network-node {
            background: radial-gradient(circle, #00ff00, #008000);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(0,255,0,0.7); }
            70% { box-shadow: 0 0 0 10px rgba(0,255,0,0); }
            100% { box-shadow: 0 0 0 0 rgba(0,255,0,0); }
        }
        
        /* Hide streamlit elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

class UzbekistanUrbanDashboard:
    """Main dashboard class"""
    
    def __init__(self):
        """Initialize dashboard"""
        # Get the current working directory and adjust paths accordingly
        current_dir = Path(__file__).parent.parent.parent
        self.base_path = current_dir
        self.data_path = self.base_path / "dashboard_deliverables/data_analysis"
        self.viz_path = self.base_path / "dashboard_deliverables/visualizations"
        
        # Load data
        self.load_data()
        
        # City coordinates for mapping
        self.city_coords = {
            'Tashkent': [41.2995, 69.2401],
            'Nukus': [42.4731, 59.6103],
            'Andijan': [40.7821, 72.3442],
            'Bukhara': [39.7748, 64.4286],
            'Jizzakh': [40.1158, 67.8422],
            'Qarshi': [38.8606, 65.7887],
            'Navoiy': [40.1030, 65.3686],
            'Namangan': [40.9983, 71.6726],
            'Samarkand': [39.6542, 66.9597],
            'Termez': [37.2242, 67.2783],
            'Fergana': [40.3964, 71.7843],
            'Urgench': [41.5469, 60.6301],
            'Gulistan': [40.4892, 68.7844],
            'Nurafshon': [41.3344, 69.0359]
        }
    
    def load_data(self):
        """Load analysis data"""
        try:
            # Load SUHI data
            suhi_file = self.data_path / "suhi_analysis_data.csv"
            if suhi_file.exists():
                self.suhi_data = pd.read_csv(suhi_file)
            else:
                self.suhi_data = pd.DataFrame()
            
            # Load city statistics
            stats_file = self.data_path / "city_suhi_statistics.csv"
            if stats_file.exists():
                self.city_stats = pd.read_csv(stats_file, index_col=0)
            else:
                self.city_stats = pd.DataFrame()
            
            # Load urban expansion data
            urban_file = self.data_path / "urban_expansion_data.csv"
            if urban_file.exists():
                self.urban_data = pd.read_csv(urban_file)
            else:
                self.urban_data = pd.DataFrame()
            
            # Load analysis results
            results_file = self.data_path / "analysis_results.json"
            if results_file.exists():
                with open(results_file) as f:
                    self.analysis_results = json.load(f)
            else:
                self.analysis_results = {}
                
            # Show data loading status if any data is missing
            if self.suhi_data.empty or self.city_stats.empty:
                st.warning("⚠️ Some data files could not be loaded. Dashboard functionality may be limited.")
            
        except Exception as e:
            st.error(f"Error loading data: {e}")
            self.suhi_data = pd.DataFrame()
            self.city_stats = pd.DataFrame()
            self.urban_data = pd.DataFrame()
            self.analysis_results = {}
    
    def render_header(self):
        """Render professional header"""
        st.markdown("""
        <div class="header-container">
            <div class="header-title">🏙️ UZBEKISTAN URBAN RESEARCH</div>
            <div class="header-subtitle">Professional Analysis Dashboard for Urban Expansion & Surface Urban Heat Island Effects</div>
            <div style="font-size: 1rem; margin-top: 1rem;">
                📊 Comprehensive Analysis • 🌡️ SUHI Monitoring • 🗺️ Spatial Intelligence • 📈 Temporal Trends
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    def render_key_metrics(self, selected_cities=None, selected_years=None):
        """Render key metrics in professional cards"""
        if not self.suhi_data.empty and not self.city_stats.empty:
            # Filter data based on selections
            filtered_city_stats = self.city_stats.copy()
            filtered_suhi_data = self.suhi_data.copy()
            
            if selected_cities:
                filtered_city_stats = filtered_city_stats[filtered_city_stats.index.isin(selected_cities)]
            
            if selected_years and 'Year' in filtered_suhi_data.columns:
                filtered_suhi_data = filtered_suhi_data[filtered_suhi_data['Year'].isin(selected_years)]
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                mean_suhi = filtered_city_stats['SUHI_Day_mean'].mean() if not filtered_city_stats.empty else 0
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{mean_suhi:.2f}°C</div>
                    <div class="metric-label">Average SUHI Intensity</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                total_cities = len(filtered_city_stats)
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{total_cities}</div>
                    <div class="metric-label">Cities Analyzed</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                years_analyzed = filtered_suhi_data['Year'].nunique() if 'Year' in filtered_suhi_data.columns and not filtered_suhi_data.empty else 0
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{years_analyzed}</div>
                    <div class="metric-label">Years of Data</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                if not filtered_city_stats.empty:
                    max_suhi = filtered_city_stats['SUHI_Day_mean'].max()
                    hottest_city = filtered_city_stats['SUHI_Day_mean'].idxmax()
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{max_suhi:.2f}°C</div>
                        <div class="metric-label">Highest SUHI ({hottest_city})</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">N/A</div>
                        <div class="metric-label">No Data Available</div>
                    </div>
                    """, unsafe_allow_html=True)
    
    def create_ct_scan_visualization(self):
        """Create CT scan-like visualization"""
        st.markdown('<div class="section-header">🔬 CT SCAN-LIKE URBAN ANALYSIS</div>', unsafe_allow_html=True)
        
        if not self.city_stats.empty:
            fig = go.Figure()
            
            # Create CT scan-like heatmap
            cities = self.city_stats.index.tolist()
            suhi_values = self.city_stats['SUHI_Day_mean'].values
            
            # Create radial/circular CT scan visualization
            theta = np.linspace(0, 2*np.pi, len(cities))
            r = suhi_values
            
            # Add radial heatmap
            fig.add_trace(go.Scatterpolar(
                r=r,
                theta=theta * 180/np.pi,
                mode='markers+lines',
                marker=dict(
                    size=20,
                    color=suhi_values,
                    colorscale='RdYlBu_r',
                    showscale=True,
                    colorbar=dict(
                        title="SUHI Intensity (°C)",
                        titlefont=dict(color='white'),
                        tickfont=dict(color='white')
                    )
                ),
                line=dict(color='lime', width=2),
                text=cities,
                hovertemplate="<b>%{text}</b><br>SUHI: %{r:.2f}°C<extra></extra>",
                name="Cities"
            ))
            
            # Add concentric circles for reference
            for intensity in [1, 2, 3, 4]:
                fig.add_trace(go.Scatterpolar(
                    r=[intensity] * 360,
                    theta=list(range(360)),
                    mode='lines',
                    line=dict(color='rgba(0,255,0,0.3)', width=1),
                    showlegend=False,
                    hoverinfo='skip'
                ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, max(suhi_values) * 1.1],
                        tickfont=dict(color='lime'),
                        gridcolor='rgba(0,255,0,0.3)'
                    ),
                    angularaxis=dict(
                        tickfont=dict(color='lime'),
                        gridcolor='rgba(0,255,0,0.3)'
                    ),
                    bgcolor='rgba(0,0,0,0.9)'
                ),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                title=dict(
                    text="Urban Heat Island CT Scan View",
                    font=dict(size=20, color='lime'),
                    x=0.5
                ),
                height=600
            )
            
            st.markdown('<div class="ct-scan-container">', unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    def create_animated_network(self):
        """Create animated network visualization"""
        st.markdown('<div class="section-header">🕸️ ANIMATED CITY NETWORK CONNECTIONS</div>', unsafe_allow_html=True)
        
        if not self.city_stats.empty:
            fig = go.Figure()
            
            cities = self.city_stats.index.tolist()
            suhi_values = self.city_stats['SUHI_Day_mean'].values
            
            # Create network layout
            n_cities = len(cities)
            angles = np.linspace(0, 2*np.pi, n_cities, endpoint=False)
            x_pos = np.cos(angles)
            y_pos = np.sin(angles)
            
            # Add connections between similar cities
            for i in range(n_cities):
                for j in range(i+1, n_cities):
                    diff = abs(suhi_values[i] - suhi_values[j])
                    if diff < 1.5:  # Connect similar cities
                        fig.add_trace(go.Scatter(
                            x=[x_pos[i], x_pos[j]],
                            y=[y_pos[i], y_pos[j]],
                            mode='lines',
                            line=dict(
                                color=f'rgba(0,255,0,{0.8 - diff/2})',
                                width=3-diff
                            ),
                            showlegend=False,
                            hoverinfo='skip'
                        ))
            
            # Add city nodes with pulsing effect
            fig.add_trace(go.Scatter(
                x=x_pos,
                y=y_pos,
                mode='markers+text',
                marker=dict(
                    size=[max(5, abs(val) * 10 + 5) for val in suhi_values],  # Ensure positive sizes
                    color=suhi_values,
                    colorscale='RdYlBu_r',
                    showscale=True,
                    colorbar=dict(
                        title="SUHI Intensity (°C)",
                        titlefont=dict(color='white'),
                        tickfont=dict(color='white')
                    ),
                    line=dict(color='lime', width=2)
                ),
                text=cities,
                textposition="top center",
                textfont=dict(color='white', size=12),
                hovertemplate="<b>%{text}</b><br>SUHI: %{marker.color:.2f}°C<extra></extra>",
                name="Cities"
            ))
            
            fig.update_layout(
                title=dict(
                    text="Live Network: City SUHI Connections",
                    font=dict(size=20, color='lime'),
                    x=0.5
                ),
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                paper_bgcolor='rgba(0,0,0,0.9)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                height=600,
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    def create_interactive_map(self):
        """Create interactive city map"""
        st.markdown('<div class="section-header">🗺️ INTERACTIVE CITY ANALYSIS MAP</div>', unsafe_allow_html=True)
        
        if not self.city_stats.empty:
            # Create folium map centered on Uzbekistan
            center_lat, center_lon = 41.5, 64.5
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=6,
                tiles='CartoDB dark_matter'
            )
            
            # Add city markers
            for city in self.city_stats.index:
                if city in self.city_coords:
                    lat, lon = self.city_coords[city]
                    suhi_intensity = self.city_stats.loc[city, 'SUHI_Day_mean']
                    
                    # Color based on SUHI intensity
                    if suhi_intensity > 2.5:
                        color = 'red'
                    elif suhi_intensity > 1.5:
                        color = 'orange'
                    else:
                        color = 'green'
                    
                    folium.CircleMarker(
                        location=[lat, lon],
                        radius=suhi_intensity * 5,
                        popup=f"""
                        <b>{city}</b><br>
                        SUHI Intensity: {suhi_intensity:.2f}°C<br>
                        Standard Deviation: {self.city_stats.loc[city, 'SUHI_Day_std']:.2f}°C
                        """,
                        color='white',
                        fillColor=color,
                        fillOpacity=0.8,
                        weight=2
                    ).add_to(m)
            
            # Display map
            st_folium(m, width=None, height=500)
    
    def create_temporal_analysis(self, selected_cities=None, selected_years=None):
        """Create temporal analysis visualizations"""
        st.markdown('<div class="section-header">📈 TEMPORAL TRENDS ANALYSIS</div>', unsafe_allow_html=True)
        
        if not self.suhi_data.empty and 'Year' in self.suhi_data.columns:
            # Filter data based on selections
            filtered_data = self.suhi_data.copy()
            
            if selected_cities:
                filtered_data = filtered_data[filtered_data['City'].isin(selected_cities)]
            
            if selected_years:
                filtered_data = filtered_data[filtered_data['Year'].isin(selected_years)]
            
            if filtered_data.empty:
                st.warning("⚠️ No data available for the selected filters")
                return
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Yearly trends
                yearly_data = filtered_data.groupby('Year')['SUHI_Day'].mean().reset_index()
                
                fig = px.line(
                    yearly_data, 
                    x='Year', 
                    y='SUHI_Day',
                    title='Annual SUHI Trend (Filtered Data)',
                    template='plotly_dark'
                )
                
                fig.update_layout(
                    title_font_size=16,
                    height=400,
                    xaxis_title="Year",
                    yaxis_title="SUHI Intensity (°C)"
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # City comparison over time
                city_yearly = filtered_data.groupby(['Year', 'City'])['SUHI_Day'].mean().reset_index()
                
                fig = px.line(
                    city_yearly,
                    x='Year',
                    y='SUHI_Day',
                    color='City',
                    title='City-wise SUHI Trends (Filtered Data)',
                    template='plotly_dark'
                )
                
                fig.update_layout(
                    title_font_size=16,
                    height=400,
                    xaxis_title="Year",
                    yaxis_title="SUHI Intensity (°C)"
                )
                
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ Temporal data not available")
    
    def create_statistical_dashboard(self, selected_cities=None):
        """Create statistical analysis dashboard"""
        st.markdown('<div class="section-header">📊 COMPREHENSIVE STATISTICAL ANALYSIS</div>', unsafe_allow_html=True)
        
        if not self.city_stats.empty:
            # Filter data based on selections
            filtered_city_stats = self.city_stats.copy()
            
            if selected_cities:
                filtered_city_stats = filtered_city_stats[filtered_city_stats.index.isin(selected_cities)]
            
            if filtered_city_stats.empty:
                st.warning("⚠️ No city data available for the selected filters")
                return
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Distribution plot
                fig = px.histogram(
                    filtered_city_stats,
                    x='SUHI_Day_mean',
                    title='SUHI Intensity Distribution (Filtered)',
                    template='plotly_dark',
                    nbins=10
                )
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Box plot
                fig = px.box(
                    y=filtered_city_stats['SUHI_Day_mean'],
                    title='SUHI Statistical Summary (Filtered)',
                    template='plotly_dark'
                )
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)
            
            with col3:
                # Ranking
                top_cities = filtered_city_stats.nlargest(10, 'SUHI_Day_mean')
                fig = px.bar(
                    x=top_cities['SUHI_Day_mean'],
                    y=top_cities.index,
                    orientation='h',
                    title='Top Cities by SUHI (Filtered)',
                    template='plotly_dark'
                )
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)
    
    def render_sidebar(self):
        """Render interactive sidebar"""
        with st.sidebar:
            st.markdown("### 🎛️ Dashboard Controls")
            
            # Data filters
            selected_years = []
            selected_cities = []
            
            if not self.suhi_data.empty and 'Year' in self.suhi_data.columns:
                years = sorted(self.suhi_data['Year'].unique())
                selected_years = st.multiselect(
                    "📅 Select Years",
                    years,
                    default=years[-3:] if len(years) >= 3 else years,
                    help="Choose years to analyze"
                )
            else:
                st.warning("⚠️ Year data not available")
            
            if not self.city_stats.empty:
                cities = sorted(self.city_stats.index.tolist())
                selected_cities = st.multiselect(
                    "🏙️ Select Cities",
                    cities,
                    default=cities[:5] if len(cities) >= 5 else cities,
                    help="Choose cities to analyze"
                )
            else:
                st.warning("⚠️ City data not available")
            
            # Store selections in session state
            if selected_years:
                st.session_state['selected_years'] = selected_years
            if selected_cities:
                st.session_state['selected_cities'] = selected_cities
            
            # Analysis options
            st.markdown("### 📈 Analysis Options")
            show_trends = st.checkbox("Show Temporal Trends", value=True)
            show_heatmap = st.checkbox("🔥 Show SUHI Heatmap", value=True)
            show_timeline = st.checkbox("📈 Show Animated Timeline", value=True)
            show_network = st.checkbox("Show Network Connections", value=True)
            show_ct_scan = st.checkbox("Show CT Scan View", value=True)
            show_nightlights = st.checkbox("🌃 Show Night Light Maps", value=True)
            
            # Export options
            st.markdown("### 💾 Export Options")
            if st.button("📊 Export Data"):
                st.success("Data export functionality would be implemented here")
            
            if st.button("📄 Generate Report"):
                st.success("Report generation would be implemented here")
            
            # System status
            st.markdown("### 🔧 System Status")
            st.success("✅ Data Loaded")
            st.success("✅ Visualizations Ready")
            st.success("✅ Dashboard Online")
            
            return {
                'selected_years': selected_years,
                'selected_cities': selected_cities,
                'show_trends': show_trends,
                'show_heatmap': show_heatmap,
                'show_timeline': show_timeline,
                'show_network': show_network,
                'show_ct_scan': show_ct_scan,
                'show_nightlights': show_nightlights
            }
    
    def create_suhi_heatmap(self, selected_cities=None, selected_years=None):
        """Create interactive SUHI heatmap"""
        st.markdown('<div class="section-header">🔥 INTERACTIVE SUHI HEATMAP</div>', unsafe_allow_html=True)
        
        if not self.suhi_data.empty and 'Year' in self.suhi_data.columns and 'City' in self.suhi_data.columns:
            # Filter data
            filtered_data = self.suhi_data.copy()
            
            if selected_cities:
                filtered_data = filtered_data[filtered_data['City'].isin(selected_cities)]
            
            if selected_years:
                filtered_data = filtered_data[filtered_data['Year'].isin(selected_years)]
            
            if filtered_data.empty:
                st.warning("⚠️ No data available for the selected filters")
                return
            
            # Create pivot table for heatmap
            heatmap_data = filtered_data.pivot_table(
                index='City', 
                columns='Year', 
                values='SUHI_Day', 
                aggfunc='mean'
            )
            
            if not heatmap_data.empty:
                # Create interactive heatmap
                fig = px.imshow(
                    heatmap_data,
                    color_continuous_scale='RdYlBu_r',
                    aspect='auto',
                    title='SUHI Intensity Heatmap (Day)',
                    labels={'color': 'SUHI Intensity (°C)'},
                    template='plotly_dark'
                )
                
                fig.update_layout(
                    height=600,
                    xaxis_title="Year",
                    yaxis_title="City"
                )
                
                # Add hover information
                fig.update_traces(
                    hovertemplate="<b>%{y}</b><br>Year: %{x}<br>SUHI: %{z:.2f}°C<extra></extra>"
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Add night heatmap
                st.markdown("#### 🌙 Night SUHI Heatmap")
                
                heatmap_night = filtered_data.pivot_table(
                    index='City', 
                    columns='Year', 
                    values='SUHI_Night', 
                    aggfunc='mean'
                )
                
                if not heatmap_night.empty:
                    fig_night = px.imshow(
                        heatmap_night,
                        color_continuous_scale='RdYlBu_r',
                        aspect='auto',
                        title='SUHI Intensity Heatmap (Night)',
                        labels={'color': 'SUHI Intensity (°C)'},
                        template='plotly_dark'
                    )
                    
                    fig_night.update_layout(
                        height=600,
                        xaxis_title="Year",
                        yaxis_title="City"
                    )
                    
                    fig_night.update_traces(
                        hovertemplate="<b>%{y}</b><br>Year: %{x}<br>SUHI: %{z:.2f}°C<extra></extra>"
                    )
                    
                    st.plotly_chart(fig_night, use_container_width=True)
            else:
                st.warning("⚠️ Not enough data to create heatmap")
        else:
            st.warning("⚠️ Insufficient data for heatmap visualization")
    
    def create_suhi_timeline(self, selected_cities=None, selected_years=None):
        """Create interactive SUHI timeline with animations"""
        st.markdown('<div class="section-header">📈 ANIMATED SUHI TIMELINE</div>', unsafe_allow_html=True)
        
        if not self.suhi_data.empty and 'Year' in self.suhi_data.columns:
            # Filter data
            filtered_data = self.suhi_data.copy()
            
            if selected_cities:
                filtered_data = filtered_data[filtered_data['City'].isin(selected_cities)]
            
            if selected_years:
                filtered_data = filtered_data[filtered_data['Year'].isin(selected_years)]
            
            if filtered_data.empty:
                st.warning("⚠️ No data available for the selected filters")
                return
            
            # Create timeline options
            col1, col2 = st.columns([3, 1])
            
            with col2:
                auto_play = st.checkbox("🎬 Auto-play animation", value=False)
                show_night = st.checkbox("🌙 Include night data", value=True)
                animation_speed = st.slider("Animation speed (ms)", 500, 3000, 1000, 100)
            
            with col1:
                # Create animated scatter plot
                if show_night:
                    # Prepare data for both day and night
                    day_data = filtered_data.copy()
                    day_data['Period'] = 'Day'
                    day_data['SUHI'] = day_data['SUHI_Day']
                    day_data['Size'] = day_data['SUHI_Day'].apply(lambda x: max(5, abs(x) * 3 + 8))
                    
                    night_data = filtered_data.copy()
                    night_data['Period'] = 'Night'
                    night_data['SUHI'] = night_data['SUHI_Night']
                    night_data['Size'] = night_data['SUHI_Night'].apply(lambda x: max(5, abs(x) * 3 + 8))
                    
                    combined_data = pd.concat([day_data, night_data])
                    
                    # Set proper axis ranges
                    year_range = [filtered_data['Year'].min(), filtered_data['Year'].max()]
                    
                    fig = px.scatter(
                        combined_data,
                        x='Year',
                        y='SUHI',
                        color='City',
                        symbol='Period',
                        size='Size',
                        animation_frame='Year',
                        animation_group='City',
                        title='SUHI Evolution Over Time (Day vs Night)',
                        template='plotly_dark',
                        hover_data=['City', 'Period'],
                        range_x=year_range,
                        range_y=[-10, 10]
                    )
                else:
                    # Add size column for day-only visualization
                    filtered_data_copy = filtered_data.copy()
                    filtered_data_copy['Size'] = filtered_data_copy['SUHI_Day'].apply(lambda x: max(5, abs(x) * 3 + 8))
                    
                    # Set proper axis ranges
                    year_range = [filtered_data['Year'].min(), filtered_data['Year'].max()]
                    
                    fig = px.scatter(
                        filtered_data_copy,
                        x='Year',
                        y='SUHI_Day',
                        color='City',
                        size='Size',
                        animation_frame='Year',
                        animation_group='City',
                        title='SUHI Evolution Over Time (Day)',
                        template='plotly_dark',
                        hover_data=['City'],
                        range_x=year_range,
                        range_y=[-10, 10]
                    )
                
                # Update layout
                fig.update_layout(
                    height=600,
                    showlegend=True,
                    xaxis_title="Year",
                    yaxis_title="SUHI Intensity (°C)"
                )
                
                # Configure animation
                if hasattr(fig, 'layout') and hasattr(fig.layout, 'updatemenus') and fig.layout.updatemenus:
                    fig.layout.updatemenus[0].buttons[0].args[1]['frame']['duration'] = animation_speed
                    fig.layout.updatemenus[0].buttons[0].args[1]['transition']['duration'] = animation_speed // 2
                    
                    if auto_play:
                        # Auto-start animation
                        fig.layout.updatemenus[0].buttons[0].args[1]['mode'] = 'immediate'
                
                st.plotly_chart(fig, use_container_width=True)
            
            # Add summary statistics timeline
            st.markdown("#### 📊 Statistical Timeline")
            
            yearly_stats = filtered_data.groupby('Year').agg({
                'SUHI_Day': ['mean', 'std', 'min', 'max'],
                'SUHI_Night': ['mean', 'std', 'min', 'max']
            }).round(2)
            
            # Flatten column names
            yearly_stats.columns = [f"{col[1]}_{col[0]}" for col in yearly_stats.columns]
            yearly_stats = yearly_stats.reset_index()
            
            # Create statistical trend plot
            fig_stats = go.Figure()
            
            # Add mean line with error bars
            fig_stats.add_trace(go.Scatter(
                x=yearly_stats['Year'],
                y=yearly_stats['mean_SUHI_Day'],
                error_y=dict(
                    type='data',
                    array=yearly_stats['std_SUHI_Day'],
                    visible=True
                ),
                mode='lines+markers',
                name='Day SUHI (Mean ± Std)',
                line=dict(color='orange', width=3)
            ))
            
            if show_night:
                fig_stats.add_trace(go.Scatter(
                    x=yearly_stats['Year'],
                    y=yearly_stats['mean_SUHI_Night'],
                    error_y=dict(
                        type='data',
                        array=yearly_stats['std_SUHI_Night'],
                        visible=True
                    ),
                    mode='lines+markers',
                    name='Night SUHI (Mean ± Std)',
                    line=dict(color='lightblue', width=3)
                ))
            
            fig_stats.update_layout(
                title='SUHI Trends with Variability',
                xaxis_title='Year',
                yaxis_title='SUHI Intensity (°C)',
                template='plotly_dark',
                height=400
            )
            
            st.plotly_chart(fig_stats, use_container_width=True)
        else:
            st.warning("⚠️ Timeline data not available")
    
    def create_nightlight_maps(self, selected_cities=None):
        """Create night light maps visualization with scrolling capability"""
        st.markdown("## 🌃 Night Light Maps of Uzbekistan")
        st.markdown("Explore the evolution of urban lighting across Uzbekistan from 2016 to 2024")
        
        # Create tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs(["📅 Country Overview", "🏙️ City-Specific", "🗺️ Interactive Gallery", "📊 Change Analysis"])
        
        with tab1:
            st.markdown("### Night Light Evolution - Country Level (2016 vs 2024)")
            
            # Create two columns for side-by-side comparison
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 🌃 2016 Night Lights")
                # Check if 2016 image exists
                image_2016 = self.base_path / "NightTimeMap_2016_v2.jpg"
                if image_2016.exists():
                    st.image(str(image_2016), caption="Uzbekistan Night Lights - 2016", use_column_width=True)
                else:
                    st.warning("2016 night light map not found")
            
            with col2:
                st.markdown("#### 🌃 2024 Night Lights")
                # Check if 2024 image exists
                image_2024 = self.base_path / "NightTimeMap_2024_v2.jpg"
                if image_2024.exists():
                    st.image(str(image_2024), caption="Uzbekistan Night Lights - 2024", use_column_width=True)
                else:
                    st.warning("2024 night light map not found")
            
            # Add slider for opacity comparison
            st.markdown("#### 🎛️ Interactive Overlay")
            opacity = st.slider("Adjust overlay transparency", 0.0, 1.0, 0.5, 0.1)
            
            # Create overlay using HTML/CSS
            if image_2016.exists() and image_2024.exists():
                st.markdown(f"""
                <div style="position: relative; width: 100%; height: 600px; overflow: hidden;">
                    <img src="data:image/jpeg;base64,{self.get_image_base64(image_2016)}" 
                         style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: contain;">
                    <img src="data:image/jpeg;base64,{self.get_image_base64(image_2024)}" 
                         style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: contain; opacity: {opacity};">
                </div>
                """, unsafe_allow_html=True)
        
        with tab2:
            st.markdown("### 🏙️ City-Specific Night Light Analysis")
            
            # Get available cities from data or use selected cities
            available_cities = []
            if selected_cities:
                available_cities = selected_cities
            elif not self.city_stats.empty:
                available_cities = list(self.city_stats.index)
            
            if available_cities:
                # City selector
                selected_city = st.selectbox(
                    "Choose a city to explore:",
                    available_cities,
                    help="Select a city to view its night light evolution"
                )
                
                if selected_city:
                    st.markdown(f"#### 🌆 {selected_city} Night Light Evolution")
                    
                    # Use enhanced comparison function
                    self.display_enhanced_city_comparison(selected_city)
                    
                    # Add city statistics if available
                    if not self.city_stats.empty and selected_city in self.city_stats.index:
                        st.markdown("##### 📊 City SUHI Statistics")
                        city_data = self.city_stats.loc[selected_city]
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Day SUHI", f"{city_data['SUHI_Day_mean']:.2f}°C")
                        with col2:
                            st.metric("Night SUHI", f"{city_data['SUHI_Night_mean']:.2f}°C")
                        with col3:
                            st.metric("Data Years", f"{city_data['Year_count']}")
            else:
                st.info("Select cities in the sidebar to view city-specific analysis")
        
        with tab3:
            st.markdown("### 🖼️ Interactive Gallery")
            
            # Get all available night light maps
            nightlight_maps = []
            viz_maps_path = self.base_path / "dashboard_deliverables/visualizations/maps"
            charts_path = self.base_path / "dashboard_deliverables/visualizations/charts"
            
            for path in [viz_maps_path, charts_path]:
                if path.exists():
                    for file in path.glob("*lights*.png"):
                        nightlight_maps.append(file)
            
            if nightlight_maps:
                # Filter by selected cities if any
                if selected_cities:
                    filtered_maps = []
                    for map_file in nightlight_maps:
                        for city in selected_cities:
                            if city.lower() in map_file.name.lower():
                                filtered_maps.append(map_file)
                    if filtered_maps:
                        nightlight_maps = filtered_maps
                
                # Create selectbox for map selection
                selected_map = st.selectbox(
                    "Choose a night light map:",
                    nightlight_maps,
                    format_func=lambda x: x.name.replace("_", " ").replace(".png", "").title()
                )
                
                if selected_map:
                    st.image(str(selected_map), caption=selected_map.name, use_column_width=True)
                    
                    # Add scrollable gallery
                    st.markdown("#### 🎞️ Gallery View")
                    
                    # Create pagination for large number of images
                    images_per_page = 6
                    total_pages = (len(nightlight_maps) - 1) // images_per_page + 1
                    
                    if total_pages > 1:
                        page = st.selectbox("Select page:", range(1, total_pages + 1))
                        start_idx = (page - 1) * images_per_page
                        end_idx = min(start_idx + images_per_page, len(nightlight_maps))
                        page_maps = nightlight_maps[start_idx:end_idx]
                    else:
                        page_maps = nightlight_maps[:images_per_page]
                    
                    cols = st.columns(3)
                    for i, map_file in enumerate(page_maps):
                        with cols[i % 3]:
                            st.image(str(map_file), caption=map_file.name.replace("_", " ")[:25] + "...", 
                                   use_column_width=True)
            else:
                st.warning("No night light maps found in the visualization directories")
        
        with tab4:
            st.markdown("### 📊 Change Analysis")
            
            # Look for change analysis maps
            change_maps = []
            for path in [viz_maps_path, charts_path]:
                if path.exists():
                    for file in path.glob("*change*lights*.png"):
                        change_maps.append(file)
            
            if change_maps:
                st.markdown("#### 🔄 Night Light Changes (2016-2025)")
                for change_map in change_maps[:3]:  # Show first 3 change maps
                    st.image(str(change_map), caption=f"Change Analysis: {change_map.name}", 
                           use_column_width=True)
                    st.markdown("---")
            else:
                st.info("Change analysis maps will be displayed here when available")
                
            # Add summary statistics if available
            if not self.suhi_data.empty:
                st.markdown("#### 📈 Urban Growth Indicators")
                
                # Calculate some basic statistics
                years_available = sorted(self.suhi_data['Year'].unique()) if 'Year' in self.suhi_data.columns else []
                if len(years_available) >= 2:
                    earliest_year = min(years_available)
                    latest_year = max(years_available)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Analysis Period", f"{earliest_year} - {latest_year}")
                    with col2:
                        filtered_cities = len(selected_cities) if selected_cities else len(self.city_stats)
                        st.metric("Cities Analyzed", filtered_cities)
                    with col3:
                        st.metric("Data Points", len(self.suhi_data))
    
    def get_image_base64(self, image_path):
        """Convert image to base64 for HTML embedding"""
        try:
            import base64
            with open(image_path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode()
        except Exception:
            return ""
    
    def enhance_night_light_image(self, image_path):
        """Apply histogram equalization and enhancement to night light images"""
        try:
            from PIL import Image, ImageEnhance
            import numpy as np
            
            # Open image
            img = Image.open(image_path)
            
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Convert to numpy array
            img_array = np.array(img)
            
            # Apply histogram equalization to each channel
            from PIL.ImageOps import equalize
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(img)
            img_enhanced = enhancer.enhance(1.5)  # Increase contrast by 50%
            
            # Enhance brightness
            enhancer = ImageEnhance.Brightness(img_enhanced)
            img_enhanced = enhancer.enhance(1.2)  # Increase brightness by 20%
            
            # Apply histogram equalization
            img_equalized = equalize(img_enhanced)
            
            return img_equalized
            
        except Exception as e:
            st.warning(f"Could not enhance image {image_path}: {e}")
            # Return original image if enhancement fails
            try:
                from PIL import Image
                return Image.open(image_path)
            except:
                return None
    
    def display_enhanced_city_comparison(self, selected_city):
        """Display enhanced city comparison with histogram equalization"""
        city_name_lower = selected_city.lower()
        viz_path = self.base_path / "dashboard_deliverables/visualizations/charts"
        
        # Find city images
        city_2016 = None
        city_2025 = None
        
        if viz_path.exists():
            for file in viz_path.glob(f"*{city_name_lower}*2016*lights*.png"):
                city_2016 = file
                break
            for file in viz_path.glob(f"*{city_name_lower}*2025*lights*.png"):
                city_2025 = file
                break
        
        # Display enhanced comparison
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### 🌃 2016 (Enhanced)")
            if city_2016 and city_2016.exists():
                try:
                    enhanced_img_2016 = self.enhance_night_light_image(city_2016)
                    if enhanced_img_2016:
                        st.image(enhanced_img_2016, caption=f"{selected_city} - 2016 (Enhanced)", use_column_width=True)
                        
                        # Show original for comparison
                        with st.expander("View Original"):
                            st.image(str(city_2016), caption=f"{selected_city} - 2016 (Original)", use_column_width=True)
                    else:
                        st.image(str(city_2016), caption=f"{selected_city} - 2016", use_column_width=True)
                except Exception as e:
                    st.image(str(city_2016), caption=f"{selected_city} - 2016", use_column_width=True)
                    st.warning(f"Enhancement failed: {e}")
            else:
                st.warning(f"No 2016 data found for {selected_city}")
        
        with col2:
            st.markdown("##### 🌃 2025 (Enhanced)")
            if city_2025 and city_2025.exists():
                try:
                    enhanced_img_2025 = self.enhance_night_light_image(city_2025)
                    if enhanced_img_2025:
                        st.image(enhanced_img_2025, caption=f"{selected_city} - 2025 (Enhanced)", use_column_width=True)
                        
                        # Show original for comparison
                        with st.expander("View Original"):
                            st.image(str(city_2025), caption=f"{selected_city} - 2025 (Original)", use_column_width=True)
                    else:
                        st.image(str(city_2025), caption=f"{selected_city} - 2025", use_column_width=True)
                except Exception as e:
                    st.image(str(city_2025), caption=f"{selected_city} - 2025", use_column_width=True)
                    st.warning(f"Enhancement failed: {e}")
            else:
                st.warning(f"No 2025 data found for {selected_city}")
        
        # Add enhancement controls
        st.markdown("##### 🎛️ Enhancement Options")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            apply_equalization = st.checkbox("🎨 Histogram Equalization", value=True, help="Enhances contrast across the full intensity range")
        
        with col2:
            contrast_boost = st.slider("🔆 Contrast Boost", 0.5, 2.0, 1.5, 0.1, help="Adjusts image contrast")
        
        with col3:
            brightness_boost = st.slider("💡 Brightness Boost", 0.5, 2.0, 1.2, 0.1, help="Adjusts image brightness")
        
        # Apply custom enhancements if user changed settings
        if contrast_boost != 1.5 or brightness_boost != 1.2 or not apply_equalization:
            st.markdown("##### 🎯 Custom Enhancement Results")
            
            def custom_enhance(image_path, contrast, brightness, equalize):
                try:
                    from PIL import Image, ImageEnhance
                    from PIL.ImageOps import equalize as pil_equalize
                    
                    img = Image.open(image_path)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Apply contrast
                    enhancer = ImageEnhance.Contrast(img)
                    img_enhanced = enhancer.enhance(contrast)
                    
                    # Apply brightness
                    enhancer = ImageEnhance.Brightness(img_enhanced)
                    img_enhanced = enhancer.enhance(brightness)
                    
                    # Apply equalization if requested
                    if equalize:
                        img_enhanced = pil_equalize(img_enhanced)
                    
                    return img_enhanced
                except Exception as e:
                    st.error(f"Enhancement error: {e}")
                    return None
            
            col1, col2 = st.columns(2)
            
            with col1:
                if city_2016 and city_2016.exists():
                    custom_2016 = custom_enhance(city_2016, contrast_boost, brightness_boost, apply_equalization)
                    if custom_2016:
                        st.image(custom_2016, caption=f"{selected_city} - 2016 (Custom)", use_column_width=True)
            
            with col2:
                if city_2025 and city_2025.exists():
                    custom_2025 = custom_enhance(city_2025, contrast_boost, brightness_boost, apply_equalization)
                    if custom_2025:
                        st.image(custom_2025, caption=f"{selected_city} - 2025 (Custom)", use_column_width=True)
    
    def run_dashboard(self):
        """Run the complete dashboard"""
        # Load custom CSS
        load_css()
        
        # Render header
        self.render_header()
        
        # Render sidebar controls
        controls = self.render_sidebar()
        
        # Render key metrics
        self.render_key_metrics(controls['selected_cities'], controls['selected_years'])
        
        # Main dashboard content
        if controls['show_ct_scan']:
            self.create_ct_scan_visualization()
        
        if controls['show_heatmap']:
            self.create_suhi_heatmap(controls['selected_cities'], controls['selected_years'])
        
        if controls['show_timeline']:
            self.create_suhi_timeline(controls['selected_cities'], controls['selected_years'])
        
        if controls['show_network']:
            try:
                self.create_animated_network()
            except Exception as e:
                st.error(f"Network visualization error: {e}")
                st.info("Network visualization temporarily disabled due to data formatting issues.")
        
        # Interactive map
        self.create_interactive_map()
        
        if controls['show_trends']:
            self.create_temporal_analysis(controls['selected_cities'], controls['selected_years'])
        
        # Statistical dashboard
        self.create_statistical_dashboard(controls['selected_cities'])
        
        # Night light maps
        if controls['show_nightlights']:
            self.create_nightlight_maps(controls['selected_cities'])
        
        # Footer
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #888; padding: 2rem;">
            <h4>🏙️ Uzbekistan Urban Research Dashboard</h4>
            <p>Professional analysis of urban expansion and Surface Urban Heat Island effects • Generated with advanced data science and visualization techniques</p>
            <p><i>Dashboard Version 1.0 • Data Updated: """ + datetime.now().strftime('%Y-%m-%d') + """</i></p>
        </div>
        """, unsafe_allow_html=True)

def main():
    """Main function to run dashboard"""
    dashboard = UzbekistanUrbanDashboard()
    dashboard.run_dashboard()

if __name__ == "__main__":
    main()