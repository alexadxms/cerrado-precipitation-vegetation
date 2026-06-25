# -*- coding: utf-8 -*-
"""Precipitation and Forest Loss — Cerrado region.

Downloads CHIRPS daily precipitation (UCSB Climate Hazards Center),
clips it to the Cerrado biome, and saves the result locally.

Run locally with:
    pip install -r requirements.txt
    python precipitation_download.py
"""

import os
import io
import zipfile

import requests
import geopandas as gpd
import xarray as xr
import rioxarray  # noqa: F401  (registers the .rio accessor)

# --- Config ---
START_YEAR = 2001
END_YEAR = 2024
CACHE_DIR = "chirps_cache"
CHIRPS_URL_TEMPLATE = (
    "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/netcdf/p25/"
    "chirps-v2.0.{year}.days_p25.nc"
)

# --- 1. Prepare the Cerrado Shapefile ---
print("--- Step 1: Preparing shapefile ---")
shapefile_url = "https://terrabrasilis.dpi.inpe.br/download/dataset/cerrado-aux/vector/states_cerrado_biome.zip"
shapefile_dir = "cerrado_shapefile"
os.makedirs(shapefile_dir, exist_ok=True)

shapefile_path = os.path.join(shapefile_dir, "states_cerrado_biome.shp")
if not os.path.exists(shapefile_path):
    response = requests.get(shapefile_url)
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        z.extractall(shapefile_dir)
cerrado_gdf = gpd.read_file(shapefile_path)
print("Shapefile is ready.")

# --- 2. Download and open CHIRPS yearly NetCDF files ---
print(f"\n--- Step 2: Downloading CHIRPS {START_YEAR}-{END_YEAR} ---")
os.makedirs(CACHE_DIR, exist_ok=True)

local_files = []
for year in range(START_YEAR, END_YEAR + 1):
    local_path = os.path.join(CACHE_DIR, f"chirps-v2.0.{year}.days_p25.nc")
    if not os.path.exists(local_path):
        url = CHIRPS_URL_TEMPLATE.format(year=year)
        print(f"  Downloading {year}...")
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
    else:
        print(f"  {year} already cached.")
    local_files.append(local_path)

ds = xr.open_mfdataset(local_files, combine="by_coords", chunks={"time": 50})
precip = ds["precip"]
precip = precip.rio.write_crs("EPSG:4326", inplace=True)

# --- 3. Clip to the Cerrado bounding box, then the precise geometry ---
print("\n--- Step 3: Clipping to Cerrado region ---")
min_lon, min_lat, max_lon, max_lat = cerrado_gdf.total_bounds

# NOTE: CHIRPS latitude is stored ascending (south -> north), so the slice
# bounds must be given as (min, max), not (max, min).
precip_subset = precip.sel(
    latitude=slice(min_lat, max_lat),
    longitude=slice(min_lon, max_lon),
)

precip_clipped = precip_subset.rio.clip(cerrado_gdf.geometry.values, drop=True)

# --- 4. Load the data into memory ---
print("\n--- Step 4: Downloading only the required data into memory ---")
precip_clipped.load()
print("Data download and processing complete.")

# --- 5. Save the final data to your computer ---
output_filename = f"chirps_cerrado_{START_YEAR}-{END_YEAR}.nc"
print(f"\n--- Step 5: Saving data to '{output_filename}' ---")
precip_clipped.to_netcdf(output_filename)
print(f"File saved successfully: {output_filename}")
