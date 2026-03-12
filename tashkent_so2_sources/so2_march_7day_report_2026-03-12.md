# March 2026 SO2 daily 7-day composite report

## Method
- Each March day is represented by a 7-day rolling SO2 composite centered on that day where possible.
- Latest SO2 day available in the Tashkent domain: 2026-03-11.
- Latest ERA5-Land day available in the Tashkent domain: 2026-03-05.
- Windows after the latest available SO2 day are right-truncated and should be interpreted as recent rolling composites, not true centered windows.

## Key findings
- Full centered SO2 windows are available through 2026-03-08.
- For the most recent city issue window, the Tashkent urban / CHP corridor is the most defensible city-level source candidate.
- Angren is strongest in the earliest March composites, but Almalyk becomes the dominant regional hotspot through the recent issue window.
- Wind-based attribution weakens sharply after early March because ERA5-Land availability ends on 2026-03-05 in this environment.
- The wind-supported windows do not show positive transport support for an external source overtaking the local Tashkent corridor signal.

## Daily window overview
```
center_date effective_start effective_end so2_support_days wind_support_days domain_valid_fraction city_mean_umol_m2            likely_city_source            regional_hotspot_source transport_screened_external_source
 2026-03-01      2026-02-26    2026-03-04            7.000             7.000                 0.927            33.667 Tashkent urban / CHP corridor Angren power / industrial corridor       no supported external source
 2026-03-02      2026-02-27    2026-03-05            7.000             7.000                 0.927            33.667 Tashkent urban / CHP corridor Angren power / industrial corridor       no supported external source
 2026-03-03      2026-02-28    2026-03-06            7.000             6.000                 0.920            76.573 Tashkent urban / CHP corridor Angren power / industrial corridor       no supported external source
 2026-03-04      2026-03-01    2026-03-07            7.000             5.000                 0.922             4.829 Tashkent urban / CHP corridor            Almalyk smelter complex       no supported external source
 2026-03-05      2026-03-02    2026-03-08            7.000             4.000                 0.925           -65.448 Tashkent urban / CHP corridor            Almalyk smelter complex       no supported external source
 2026-03-06      2026-03-03    2026-03-09            7.000             3.000                 0.925            83.441 Tashkent urban / CHP corridor            Almalyk smelter complex       no supported external source
 2026-03-07      2026-03-04    2026-03-10            7.000             2.000                 0.922            83.441 Tashkent urban / CHP corridor            Almalyk smelter complex                   wind unavailable
 2026-03-08      2026-03-05    2026-03-11            7.000             1.000                 0.922            49.003 Tashkent urban / CHP corridor            Almalyk smelter complex                   wind unavailable
 2026-03-09      2026-03-06    2026-03-11            6.000             0.000                 0.922            49.003 Tashkent urban / CHP corridor            Almalyk smelter complex                   wind unavailable
 2026-03-10      2026-03-07    2026-03-11            5.000             0.000                 0.922            37.199 Tashkent urban / CHP corridor            Almalyk smelter complex                   wind unavailable
 2026-03-11      2026-03-08    2026-03-11            4.000             0.000                 0.907            83.289 Tashkent urban / CHP corridor            Almalyk smelter complex                   wind unavailable
 2026-03-12      2026-03-09    2026-03-11            3.000             0.000                 0.578             176.2 Tashkent urban / CHP corridor            Almalyk smelter complex                   wind unavailable
```

## Recent issue window
```
center_date so2_support_days wind_support_days city_mean_umol_m2 almalyk_mean_umol_m2 angren_mean_umol_m2 chirchiq_mean_umol_m2            likely_city_source regional_hotspot_source
 2026-03-08            7.000             1.000            49.003                475.5               209.0               -84.290 Tashkent urban / CHP corridor Almalyk smelter complex
 2026-03-09            6.000             0.000            49.003                475.5               209.0               -84.290 Tashkent urban / CHP corridor Almalyk smelter complex
 2026-03-10            5.000             0.000            37.199                420.2               201.6                -142.8 Tashkent urban / CHP corridor Almalyk smelter complex
 2026-03-11            4.000             0.000            83.289                526.6               311.5                -193.9 Tashkent urban / CHP corridor Almalyk smelter complex
 2026-03-12            3.000             0.000             176.2                479.4                  NA               -34.839 Tashkent urban / CHP corridor Almalyk smelter complex
```

## Interpretation
- On 2026-03-12, the rolling composite city signal is 176.2 umol/m2.
- The same composite still shows a stronger regional hotspot over Almalyk (479.4 umol/m2), but this does not by itself prove city impact.
- The strongest statement supported by the current data is: the recent March city SO2 issue is more consistent with a local Tashkent urban / CHP signal than with a clearly wind-supported external transport episode.
- Almalyk should still be monitored as the dominant regional hotspot, especially once fresh wind data become available for the latest days.