import re
import json
import plotly.graph_objects as go
import plotly.io as pio
import os

def extract_plot_data_from_html(html_file):
    """Extract plot data and layout from HTML file"""
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find Plotly.newPlot calls
    plot_pattern = r'Plotly\.newPlot\(\s*"([^"]+)",\s*(\[[^\]]*\]),\s*({[^}]*})'
    matches = re.findall(plot_pattern, content, re.DOTALL)

    plots = []
    for match in matches:
        div_id, data_str, layout_str = match

        try:
            # Clean up the data string
            data_str = data_str.strip()
            if data_str.endswith(','):
                data_str = data_str[:-1]

            # Parse the data
            data = json.loads(data_str)

            # Clean up the layout string
            layout_str = layout_str.strip()
            if layout_str.endswith(','):
                layout_str = layout_str[:-1]

            # Parse the layout
            layout = json.loads(layout_str)

            plots.append({
                'div_id': div_id,
                'data': data,
                'layout': layout
            })

        except json.JSONDecodeError as e:
            print(f"Error parsing plot data: {e}")
            continue

    return plots

def save_plots_as_png(html_file, output_dir='climate_assessment_plots'):
    """Extract plots from HTML and save as PNG files"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    plots = extract_plot_data_from_html(html_file)

    base_name = os.path.splitext(os.path.basename(html_file))[0]

    for i, plot in enumerate(plots):
        try:
            # Create the figure
            fig = go.Figure(data=plot['data'], layout=plot['layout'])

            # Save as PNG
            output_file = os.path.join(output_dir, f'{base_name}_plot_{i+1}.png')
            pio.write_image(fig, output_file, format='png', width=1600, height=1200, scale=2)

            print(f'Saved: {output_file}')

        except Exception as e:
            print(f'Error saving plot {i+1}: {e}')

# Extract plots from both HTML files
print('=== EXTRACTING PLOTS FROM HTML FILES ===')

# Main climate assessment plot
main_html = 'suhi_analysis_output/climate_assessment/ipcc_climate_risk_assessment.html'
if os.path.exists(main_html):
    print(f'Extracting plots from: {main_html}')
    save_plots_as_png(main_html)
else:
    print(f'File not found: {main_html}')

# Adaptability ranking table
table_html = 'suhi_analysis_output/climate_assessment/adaptability_ranking_table.html'
if os.path.exists(table_html):
    print(f'Extracting plots from: {table_html}')
    save_plots_as_png(table_html)
else:
    print(f'File not found: {table_html}')

print('\n=== EXTRACTION COMPLETE ===')
print('PNG files saved to: climate_assessment_plots/')