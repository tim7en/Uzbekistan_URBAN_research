# Tashkent SO2 source identification report

Analysis window: 2025-10-01 to 2026-03-12
Spatial domain: 150 km by 150 km centered on Tashkent.

## Executive summary
- The strongest persistent regional SO2 source signal is Almalyk smelter complex. Its seasonal median is 802.8 umol/m2, compared with a domain median of 317.3 umol/m2.
- Angren is the main secondary regional source area. It is weaker than Almalyk in raw SO2 intensity, but its east-of-city position is often more consistent with observed westward transport.
- The Tashkent urban or CHP corridor shows a persistent local elevation, but the satellite pixel size does not support separate attribution to CHP-1 versus CHP-2.
- Chirchiq appears as a weaker intermittent source area. Its transport geometry toward the city is plausible, but the regional SO2 signal is not dominant.
- December 2025 and January 2026 standard-band coverage is too sparse for confident monthly attribution in the Tashkent domain. Those months should not be interpreted as meaningful source minima.

## Revised method
- Use the standard Sentinel-5P SO2 total-column band in Earth Engine and keep OFFL as the primary source, using NRTI only after the latest available OFFL day.
- Restrict to nominal product quality and treat the product as relative evidence of column enhancement, not a direct emission rate.
- Aggregate local Tashkent thermal sources into one urban or CHP corridor because separate CHP attribution is not supported by the sensor footprint.
- Report monthly domain coverage and downgrade months with sparse valid pixels instead of forcing values.
- Separate regional source strength from transport plausibility. Wind consistency is used only as supporting evidence.

## Seasonal source summary
```
                            source    category median_umol_m2 mean_umol_m2 p90_umol_m2 hotspot_share_p90 mean_transport_alignment regional_evidence transport_plausibility
           Almalyk smelter complex     smelter          802.8        810.3      1034.3             1.000                    0.396              high                    low
Angren power / industrial corridor       power          434.2        408.5       622.7             0.000                    0.713            medium                 medium
     Tashkent urban / CHP corridor urban_power          346.5        346.8       425.6             0.000                       NA            medium                  local
          Chirchiq industrial area    chemical          226.4        233.8       344.4             0.000                    0.825               low                   high
```

## Monthly domain coverage
```
   month valid_grid_cells valid_fraction median_umol_m2 coverage_status
Oct 2025            400.0          1.000          249.8        reliable
Nov 2025            400.0          1.000         1001.9        reliable
Dec 2025            0.000          0.000             NA    insufficient
Jan 2026           15.000          0.037          113.9    insufficient
Feb 2026            378.0          0.945          229.4        reliable
Mar 2026            371.0          0.927          112.1        reliable
```

## Interpretation for Tashkent city
- Almalyk is the clearest regional SO2 hotspot and should be treated as the dominant regional point-source signal in this domain.
- Angren is the most credible secondary contributor to Tashkent exposure because it combines elevated SO2 with frequent east-to-west transport geometry.
- The Tashkent urban or CHP corridor represents local background and heating-system influence, but the available satellite data cannot isolate individual stacks inside the city.
- Chirchiq remains a plausible intermittent contributor, especially during north-east to westward flow, but its seasonal SO2 signal is materially weaker.

## Limitations
- Sentinel-5P SO2 is a total-column retrieval, not a source-resolved emission inventory.
- ERA5-Land 10 m wind is not a full back-trajectory model and does not resolve plume height.
- Winter low-sun and masking effects strongly reduce valid standard-band SO2 coverage over parts of the study period.
- This analysis supports relative source identification and city-impact plausibility, not percent source apportionment.

## Event maps generated
- 15 Nov 2025: `so2_transport_event_2025-11-15.png`
- 17 Feb 2026: `so2_transport_event_2026-02-17.png`

## Data references
- Earth Engine OFFL SO2 catalog: https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S5P_OFFL_L3_SO2
- Earth Engine NRTI SO2 catalog: https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S5P_NRTI_L3_SO2
- Sentinel-5P SO2 product readme: https://sentinels.copernicus.eu/documents/247904/3541451/Sentinel-5P-Sulfur-Dioxide-Level-2-Product-Readme-File
- Earth Engine ERA5-Land hourly catalog: https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_HOURLY

## Snapshot transport rows
```
 date_label                             source source_mean_umol_m2 city_mean_umol_m2 domain_coverage_fraction flow_to_bearing_deg mean_transport_alignment
15 Oct 2025            Almalyk smelter complex               420.3            -6.411                    1.000               229.5                    0.000
15 Oct 2025 Angren power / industrial corridor               296.1            -6.411                    1.000               229.5                    0.380
15 Oct 2025           Chirchiq industrial area               114.8            -6.411                    1.000               229.5                    0.992
15 Oct 2025      Tashkent urban / CHP corridor              -6.411            -6.411                    1.000               229.5                       NA
15 Nov 2025            Almalyk smelter complex              2006.4            1869.9                    0.775               254.4                    0.266
15 Nov 2025 Angren power / industrial corridor               518.6            1869.9                    0.775               254.4                    0.734
15 Nov 2025           Chirchiq industrial area               226.1            1869.9                    0.775               254.4                    0.953
15 Nov 2025      Tashkent urban / CHP corridor              1869.9            1869.9                    0.775               254.4                       NA
15 Dec 2025            Almalyk smelter complex                  NA                NA                    0.000               221.9                    0.000
15 Dec 2025 Angren power / industrial corridor                  NA                NA                    0.000               221.9                    0.254
15 Dec 2025           Chirchiq industrial area                  NA                NA                    0.000               221.9                    0.966
15 Dec 2025      Tashkent urban / CHP corridor                  NA                NA                    0.000               221.9                       NA
15 Jan 2026            Almalyk smelter complex                  NA                NA                    0.000               279.6                    0.651
15 Jan 2026 Angren power / industrial corridor                  NA                NA                    0.000               279.6                    0.953
15 Jan 2026           Chirchiq industrial area                  NA                NA                    0.000               279.6                    0.733
15 Jan 2026      Tashkent urban / CHP corridor                  NA                NA                    0.000               279.6                       NA
 7 Feb 2026            Almalyk smelter complex               392.1             174.3                    0.865               282.2                    0.685
 7 Feb 2026 Angren power / industrial corridor               788.2             174.3                    0.865               282.2                    0.966
 7 Feb 2026           Chirchiq industrial area               136.7             174.3                    0.865               282.2                    0.702
 7 Feb 2026      Tashkent urban / CHP corridor               174.3             174.3                    0.865               282.2                       NA
17 Feb 2026            Almalyk smelter complex               681.0             232.1                    0.925               289.9                    0.776
17 Feb 2026 Angren power / industrial corridor               420.3             232.1                    0.925               289.9                    0.992
17 Feb 2026           Chirchiq industrial area               185.4             232.1                    0.925               289.9                    0.601
17 Feb 2026      Tashkent urban / CHP corridor               232.1             232.1                    0.925               289.9                       NA
12 Mar 2026            Almalyk smelter complex               479.4             176.2                    0.578                  NA                       NA
12 Mar 2026 Angren power / industrial corridor                  NA             176.2                    0.578                  NA                       NA
12 Mar 2026           Chirchiq industrial area             -34.839             176.2                    0.578                  NA                       NA
12 Mar 2026      Tashkent urban / CHP corridor               176.2             176.2                    0.578                  NA                       NA
```