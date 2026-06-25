# -*- coding: utf-8 -*-
"""Monthly NDVI time series — Cerrado region, 2001-2024.

Stage 2 of the rebuild. For each month, computes the mean MODIS NDVI
over the Cerrado server-side in Earth Engine, then downloads one small
GeoTIFF per month (coarse ~25km scale, close to CHIRPS's resolution —
exact grid alignment with CHIRPS happens later via xarray.interp_like).

Resumable: already-downloaded months are skipped, so this can be killed
and re-run safely.

Run locally with:
    pip install -r requirements.txt
    python ndvi_monthly.py
"""

import os
import time

import ee
import geemap
import geopandas as gpd
import requests

EE_PROJECT = "climatematch-cerrado"
SHAPEFILE_PATH = "cerrado_shapefile/states_cerrado_biome.shp"
CACHE_DIR = "ndvi_monthly_cache"
START_YEAR = 2001
END_YEAR = 2024
SCALE_METERS = 25000  # ~25km, close to CHIRPS's 0.25-degree resolution
MAX_RETRIES = 3
RETRY_WAIT_SECONDS = 10
REQUEST_PAUSE_SECONDS = 1  # be polite to Earth Engine's rate limits

# --- Authenticate ---
ee.Authenticate(auth_mode="localhost")
ee.Initialize(project=EE_PROJECT)

# --- Load and simplify the Cerrado shapefile ---
shp = gpd.read_file(SHAPEFILE_PATH)
shp["geometry"] = shp.geometry.simplify(0.01)
aoi = geemap.gdf_to_ee(shp)
region = aoi.geometry().bounds()


def get_ndvi(img):
    ndvi = img.normalizedDifference(["sur_refl_b02", "sur_refl_b01"]).rename("NDVI")
    return img.addBands(ndvi)


def month_date_range(year, month):
    start = ee.Date.fromYMD(year, month, 1)
    end = start.advance(1, "month")
    return start, end


def download_month(year, month, out_path):
    start, end = month_date_range(year, month)
    monthly_mean = (
        ee.ImageCollection("MODIS/061/MOD09GA")
        .filterDate(start, end)
        .map(get_ndvi)
        .select("NDVI")
        .mean()
        .clip(aoi)
    )

    url = monthly_mean.getDownloadURL(
        {"scale": SCALE_METERS, "region": region, "format": "GEO_TIFF"}
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            with open(out_path, "wb") as f:
                f.write(response.content)
            return
        except Exception as e:
            print(f"    attempt {attempt}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_WAIT_SECONDS)
            else:
                raise


# --- Main loop ---
os.makedirs(CACHE_DIR, exist_ok=True)

months = [(y, m) for y in range(START_YEAR, END_YEAR + 1) for m in range(1, 13)]
print(f"Fetching {len(months)} monthly NDVI composites ({START_YEAR}-{END_YEAR})...")

for i, (year, month) in enumerate(months, start=1):
    out_path = os.path.join(CACHE_DIR, f"ndvi_{year}_{month:02d}.tif")
    if os.path.exists(out_path):
        continue
    print(f"  [{i}/{len(months)}] {year}-{month:02d}")
    download_month(year, month, out_path)
    time.sleep(REQUEST_PAUSE_SECONDS)

print("All months downloaded.")
