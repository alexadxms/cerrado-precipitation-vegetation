# -*- coding: utf-8 -*-
"""NDVI snapshot — Cerrado region.

Local rewrite of NDVI_maps.ipynb (originally Colab-only). Pulls a single
MODIS NDVI snapshot for the Cerrado, clipped to the same shapefile used
by the precipitation script.

Stage 1 of the rebuild: just confirm Earth Engine auth + a single NDVI
fetch works locally. The real monthly 2001-2024 time series comes next.

Run locally with:
    pip install -r requirements.txt
    python ndvi_snapshot.py
"""

import datetime
import os

import ee
import geemap
import geopandas as gpd
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import rasterio
import requests

EE_PROJECT = "climatematch-cerrado"
SHAPEFILE_PATH = "cerrado_shapefile/states_cerrado_biome.shp"
DATE_STR = "2010-05-01"  # change this date as needed

# --- Authenticate (opens a browser the first time; cached after that) ---
ee.Authenticate(auth_mode="localhost")
ee.Initialize(project=EE_PROJECT)

# --- Load the Cerrado shapefile (already downloaded by precipitation_download.py) ---
assert os.path.exists(SHAPEFILE_PATH), (
    f"Shapefile not found at {SHAPEFILE_PATH}. Run precipitation_download.py "
    "first, or update SHAPEFILE_PATH."
)
shp = gpd.read_file(SHAPEFILE_PATH)
# Simplify the polygon — the raw state-boundary shapefile has too many
# vertices and blows past Earth Engine's request-size limit once embedded
# in the clip/download request.
shp["geometry"] = shp.geometry.simplify(0.01)
aoi = geemap.gdf_to_ee(shp)

# --- NDVI computation ---
date = datetime.datetime.strptime(DATE_STR, "%Y-%m-%d")


def get_ndvi(img):
    ndvi = img.normalizedDifference(["sur_refl_b02", "sur_refl_b01"]).rename("NDVI")
    return img.addBands(ndvi)


modis = (
    ee.ImageCollection("MODIS/061/MOD09GA")
    .filterDate(DATE_STR, (date + datetime.timedelta(days=1)).strftime("%Y-%m-%d"))
    .map(get_ndvi)
    .first()
)

ndvi_img = modis.select("NDVI").clip(aoi)

# --- Export NDVI to a local GeoTIFF ---
url = ndvi_img.getDownloadURL(
    {
        "scale": 800,  # coarser scale keeps the download small
        "region": aoi.geometry().bounds(),
        "format": "GEO_TIFF",
    }
)

response = requests.get(url)
if response.status_code != 200:
    print("Failed to download NDVI GeoTIFF.")
    print("Status code:", response.status_code)
    print("Response:", response.text)
    raise SystemExit(1)

with open("ndvi.tif", "wb") as f:
    f.write(response.content)
print("NDVI GeoTIFF downloaded successfully: ndvi.tif")

# --- Plot it ---
with rasterio.open("ndvi.tif") as src:
    ndvi_array = src.read(1).astype(float)
    ndvi_array[ndvi_array == src.nodata] = float("nan")

    fig, ax = plt.subplots(figsize=(8, 6))
    cmap = plt.cm.YlGn
    norm = mcolors.Normalize(vmin=-0.2, vmax=0.9)
    im = ax.imshow(ndvi_array, cmap=cmap, norm=norm)
    fig.colorbar(im, ax=ax, label="NDVI")
    ax.set_title(f"NDVI map on {DATE_STR}")
    ax.axis("off")
    fig.savefig("ndvi_preview.png", dpi=150, bbox_inches="tight")
    print("Saved preview image: ndvi_preview.png")
