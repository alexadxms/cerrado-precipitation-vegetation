# -*- coding: utf-8 -*-
"""Stage 3: stitch monthly NDVI GeoTIFFs into one time series.

Reads every ndvi_monthly_cache/ndvi_{year}_{month}.tif produced by
ndvi_monthly.py and concatenates them into a single xarray Dataset with
a proper time dimension, saved as one NetCDF file — same shape of
artifact as the CHIRPS precipitation output, ready for the alignment +
correlation step.

Safe to run before the full 2001-2024 download finishes — it just
stitches whatever months exist so far.

Run locally with:
    python ndvi_stitch.py
"""

import glob
import os
import re

import pandas as pd
import rioxarray
import xarray as xr

CACHE_DIR = "ndvi_monthly_cache"
OUTPUT_FILENAME = "ndvi_cerrado_monthly.nc"

FILENAME_RE = re.compile(r"ndvi_(\d{4})_(\d{2})\.tif$")


def parse_year_month(path):
    match = FILENAME_RE.search(os.path.basename(path))
    if not match:
        raise ValueError(f"Unexpected filename, can't parse year/month: {path}")
    year, month = match.groups()
    return int(year), int(month)


def main():
    files = sorted(glob.glob(os.path.join(CACHE_DIR, "ndvi_*_*.tif")))
    if not files:
        raise SystemExit(f"No NDVI files found in {CACHE_DIR}/ — run ndvi_monthly.py first.")

    print(f"Found {len(files)} monthly NDVI files. Stitching...")

    arrays = []
    times = []
    for path in files:
        year, month = parse_year_month(path)
        da = rioxarray.open_rasterio(path, masked=True).squeeze("band", drop=True)
        arrays.append(da)
        times.append(pd.Timestamp(year=year, month=month, day=1))

    ndvi = xr.concat(arrays, dim=pd.Index(times, name="time"))
    ndvi.name = "NDVI"

    # Match CHIRPS's coordinate naming (latitude/longitude) for the later
    # alignment step.
    ndvi = ndvi.rename({"y": "latitude", "x": "longitude"})

    ds = ndvi.to_dataset()
    ds = ds.sortby("time")

    print(ds)
    print()
    print("Time range:", ds.time.min().values, "to", ds.time.max().values)
    print("NaN fraction:", float(ds.NDVI.isnull().mean()))
    print("Mean NDVI:", float(ds.NDVI.mean(skipna=True)))

    ds.to_netcdf(OUTPUT_FILENAME)
    print(f"\nSaved: {OUTPUT_FILENAME}")


if __name__ == "__main__":
    main()
