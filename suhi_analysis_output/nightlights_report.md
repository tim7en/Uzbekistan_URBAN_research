# Nightlights Analysis Report
## Datasets used
- VIIRS Monthly: DATASET id = NOAA/VIIRS/DNB/MONTHLY_V1/VCMCFG
- DMSP OLS (if available): DATASET id = NOAA/DMSP-OLS/NIGHTTIME_LIGHTS

## Temporal coverage
- Years analyzed: 2016 to 2024 (annual median composites)

## Spatial resolution (typical)
- VIIRS Monthly: native ~500 m to 750 m depending on product; thumbnails exported at ~1024 px per city extent.
- DMSP OLS: coarse ~2.7 km (legacy).

## Notes
- Radiance band names may vary across collections; the script selects the first available band.
- Thumbnails are generated with a linear stretch (min/max).
