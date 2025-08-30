import json

with open('suhi_analysis_output/climate_assessment/climate_risk_assessment_results.json', 'r') as f:
    data = json.load(f)

print("HEAT AND PLUVIAL HAZARD VALUES:")
print("="*40)
for city, metrics in data.items():
    heat = metrics.get('heat_hazard', 'N/A')
    pluvial = metrics.get('pluvial_hazard', 'N/A')
    print(f'{city:12}: heat={heat}, pluvial={pluvial}')
