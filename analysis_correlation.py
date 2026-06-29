# -*- coding: utf-8 -*-
"""Stage 4: NDVI vs. precipitation lag correlation.

Aligns the monthly NDVI time series (Earth Engine) with monthly total
precipitation (CHIRPS) on a common grid, then computes the per-pixel
Pearson correlation between precipitation and NDVI at lags of 0-4
months — testing whether vegetation health responds to rainfall with a
delay (as reported in the original team's findings).

Run locally with:
    python analysis_correlation.py
"""

import os

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

PRECIP_PATH = "chirps_cerrado_2001-2024.nc"
NDVI_PATH = "ndvi_cerrado_monthly.nc"
MAX_LAG_MONTHS = 4
OUTPUT_DIR = "outputs"
OUTPUT_NC = "lag_correlation_maps.nc"
OUTPUT_PNG = os.path.join(OUTPUT_DIR, "lag_correlation_maps.png")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Load ---
precip_daily = xr.open_dataset(PRECIP_PATH).precip
ndvi_monthly = xr.open_dataset(NDVI_PATH).NDVI

# --- Resample precipitation to monthly totals ---
precip_monthly = precip_daily.resample(time="MS").sum()

# --- Align grids: interpolate NDVI onto the CHIRPS precipitation grid ---
# The two were exported at slightly different resolutions (CHIRPS native
# 0.25 deg vs. NDVI's ~25km Earth Engine export), so they don't share
# exact grid points even though they cover the same region.
ndvi_aligned = ndvi_monthly.interp(
    latitude=precip_monthly.latitude,
    longitude=precip_monthly.longitude,
    method="linear",
)

# --- Trim to the overlapping time range ---
precip_monthly, ndvi_aligned = xr.align(precip_monthly, ndvi_aligned, join="inner")
print(f"Aligned dataset: {precip_monthly.sizes['time']} months, "
      f"{precip_monthly.sizes['latitude']}x{precip_monthly.sizes['longitude']} grid")

# --- Lag correlation: does NDVI at time t+lag correlate with precip at time t? ---
lag_maps = []
for lag in range(MAX_LAG_MONTHS + 1):
    ndvi_shifted = ndvi_aligned.shift(time=-lag)
    r = xr.corr(precip_monthly, ndvi_shifted, dim="time")
    r = r.assign_coords(lag=lag).expand_dims("lag")
    lag_maps.append(r)
    print(f"Lag {lag} month(s): mean r = {float(r.mean(skipna=True)):.3f}")

correlation = xr.concat(lag_maps, dim="lag")
correlation.name = "pearson_r"
correlation.to_dataset().to_netcdf(OUTPUT_NC)
print(f"\nSaved correlation maps: {OUTPUT_NC}")

# --- Plot all lags side by side ---
fig, axes = plt.subplots(1, MAX_LAG_MONTHS + 1, figsize=(4 * (MAX_LAG_MONTHS + 1), 4.5))
for lag, ax in zip(range(MAX_LAG_MONTHS + 1), axes):
    im = correlation.sel(lag=lag).plot(
        ax=ax, cmap="RdBu", vmin=-1, vmax=1, add_colorbar=False
    )
    ax.set_title(f"{lag}-month lag")
    ax.set_xlabel("")
    ax.set_ylabel("")
fig.colorbar(im, ax=axes, label="Pearson r", shrink=0.8)
fig.suptitle("NDVI vs. precipitation correlation by lag")
fig.savefig(OUTPUT_PNG, dpi=150, bbox_inches="tight")
print(f"Saved plot: {OUTPUT_PNG}")
