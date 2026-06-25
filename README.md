# Spatio-Temporal Correlation Between Precipitation and Vegetation Dynamics in the Brazil-Cerrado Region

A [ClimateMatch Academy](https://comptools.climatematch.io/) project (Lagoda Pod) investigating
whether changes in precipitation frequency across Brazil's Cerrado biome (2001-2024) spatially
correlate with vegetation health (NDVI).

**Team:** Alex Adams, Isaac Yameogo, Joshua Solomon Avong, Julio Montenegro Gambini, Moses Kolleh
Sesay. Mentored by Danny McCulloch (TA). See [`CMA_Project_Presentation_Logada_Precipitation.pdf`](./CMA_Project_Presentation_Logada_Precipitation.pdf)
for the team's original presentation and full findings.

This repo contains a standalone, locally-runnable rebuild of the project's data pipeline
(originally built across several Colab notebooks), written by Alex Adams.

## Research question

> How has the frequency of precipitation in Brazil's Cerrado region changed between 2001-2024,
> and how does this spatially correlate with vegetation dynamics (health)?

**Hypothesis:** A decrease in precipitation frequency in the Cerrado between 2001-2024 will show
a strong positive spatial correlation with a decline in vegetation health.

## Pipeline

Five stages, each a standalone script. Run in order — each one depends on the previous stage's
output.

| Stage | Script | What it does |
|---|---|---|
| 1 | `precipitation_download.py` | Downloads CHIRPS daily precipitation (2001-2024) from UCSB's Climate Hazards Center, clips it to the Cerrado biome shapefile |
| 2 | `ndvi_monthly.py` | Computes monthly mean MODIS NDVI over the Cerrado via Google Earth Engine, one GeoTIFF per month (288 total) |
| 3 | `ndvi_stitch.py` | Combines the 288 monthly GeoTIFFs into a single NDVI time series |
| 4 | `analysis_correlation.py` | Aligns the NDVI and precipitation grids, computes per-pixel lag correlation (0-4 months) |
| 5 | `analysis_trends.py` | Computes per-pixel Sen's slope trends by calendar month, for both variables |

`ndvi_snapshot.py` is a smaller standalone script (single-date NDVI fetch) used to validate Earth
Engine access before building the full monthly pipeline — not part of the main pipeline.

## Setup

Requires a Python environment and a free Google Earth Engine account with a registered Cloud
project (needed for stages 2 and onward; stage 1 doesn't need it).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Earth Engine project ID is set via the `EE_PROJECT` constant near the top of `ndvi_monthly.py`
and `ndvi_snapshot.py` — replace `"climatematch-cerrado"` with your own registered project ID.
The first run of `ee.Authenticate()` opens a browser sign-in; credentials are cached after that.

## Running it

```bash
python precipitation_download.py   # stage 1
python ndvi_monthly.py             # stage 2 — slow; ~288 Earth Engine requests
python ndvi_stitch.py              # stage 3
python analysis_correlation.py     # stage 4
python analysis_trends.py          # stage 5
```

Stage 2 is resumable — already-downloaded months are skipped, so it's safe to re-run if
interrupted.

## Key findings

**NDVI responds to precipitation with a delay, not immediately.** Correlating monthly
precipitation against NDVI at lags of 0-4 months shows a clear shift from strongly negative
(immediate) to strongly positive (delayed):

| Lag | 0 months | 1 month | 2 months | 3 months | 4 months |
|---|---|---|---|---|---|
| Mean correlation (r) | -0.66 | -0.21 | +0.11 | +0.41 | +0.58 |

![Lag correlation maps](./lag_correlation_maps.png)

This matches the ecological-memory interpretation from the team's original analysis: the biome's
vegetation relies on stored soil moisture rather than reacting to rainfall immediately, so the
strongest positive vegetation response shows up 3-4 months after the rain that caused it.

**Trends vary by month and aren't always coupled.** Per-pixel Sen's slope trends (2001-2024),
computed separately for each calendar month:

![NDVI trend maps](./ndvi_trend_maps.png)
![Precipitation trend maps](./precip_trend_maps.png)

January stands out: precipitation is declining there while NDVI is increasing — a vegetation
adaptation or land-use signal rather than a simple rainfall-driven response. June-August show a
comparatively flat precipitation trend (dry season), consistent with the original team's
observation that NDVI decline in that period reflects degradation/fire activity rather than
rainfall change.

## Data sources

- **Precipitation:** [CHIRPS v2.0](https://www.chc.ucsb.edu/data/chirps), UCSB Climate Hazards
  Center, daily, 0.25° resolution.
- **Vegetation:** [MODIS MOD09GA](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD09GA),
  via Google Earth Engine, NDVI computed from surface reflectance bands.
- **Cerrado boundary:** [TerraBrasilis](https://terrabrasilis.dpi.inpe.br/), INPE.

## Possible next steps

From the team's original "Future Context" findings:

- Zonal analysis by land cover (natural vs. anthropogenic greening)
- Classify zones where NDVI is stable/increasing despite declining precipitation (climate
  resilience indicator)
- Extreme rainfall indices (consecutive dry days, rainfall intensity)
- Physical mechanism investigation using reanalysis data (e.g. ERA5 — moisture recycling, wind,
  evapotranspiration)
- Compare observed trends against climate model projections (e.g. CMIP6)
