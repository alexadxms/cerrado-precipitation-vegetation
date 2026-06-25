# -*- coding: utf-8 -*-
"""Stage 5: Sen's slope trend maps, by calendar month.

For each calendar month (Jan-Dec), computes the Theil-Sen trend slope
across the 24 years (2001-2024) at every pixel, for both NDVI and
monthly total precipitation. Reproduces the "Monthly NDVI/Precipitation
Trends (Sen's Slope)" maps and summary table from the original deck.

Run locally with:
    python analysis_trends.py
"""

import calendar

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from scipy.stats import theilslopes

PRECIP_PATH = "chirps_cerrado_2001-2024.nc"
NDVI_PATH = "ndvi_cerrado_monthly.nc"
OUTPUT_NC = "trend_maps.nc"

# --- Load and align (same approach as analysis_correlation.py) ---
precip_daily = xr.open_dataset(PRECIP_PATH).precip
ndvi_monthly = xr.open_dataset(NDVI_PATH).NDVI

precip_monthly = precip_daily.resample(time="MS").sum()
ndvi_aligned = ndvi_monthly.interp(
    latitude=precip_monthly.latitude,
    longitude=precip_monthly.longitude,
    method="linear",
)
precip_monthly, ndvi_aligned = xr.align(precip_monthly, ndvi_aligned, join="inner")

years = np.unique(precip_monthly.time.dt.year.values)
print(f"{len(years)} years: {years.min()}-{years.max()}")


def sen_slope_1d(y):
    """Theil-Sen slope (per year) for a single pixel's time series, NaN-safe."""
    mask = ~np.isnan(y)
    if mask.sum() < 3:
        return np.nan
    x = np.arange(len(y))[mask]
    slope, _, _, _ = theilslopes(y[mask], x)
    return slope


def monthly_sen_slope(monthly_da):
    """Per-pixel Sen's slope for each calendar month, across years."""
    slopes_by_month = []
    for month in range(1, 13):
        month_data = monthly_da.sel(time=monthly_da.time.dt.month == month)
        slope = xr.apply_ufunc(
            sen_slope_1d,
            month_data,
            input_core_dims=[["time"]],
            vectorize=True,
            output_dtypes=[float],
        )
        slopes_by_month.append(slope.assign_coords(month=month).expand_dims("month"))
    return xr.concat(slopes_by_month, dim="month")


print("Computing NDVI trends (this takes a minute)...")
ndvi_trend = monthly_sen_slope(ndvi_aligned)
ndvi_trend.name = "ndvi_slope"

print("Computing precipitation trends...")
precip_trend = monthly_sen_slope(precip_monthly)
precip_trend.name = "precip_slope"

trends = xr.merge([ndvi_trend, precip_trend])
trends.to_netcdf(OUTPUT_NC)
print(f"Saved: {OUTPUT_NC}")

# --- Summary table: mean slope sign per month ---
print(f"\n{'Month':<6} {'Rain trend':<14} {'NDVI trend':<14}")
for month in range(1, 13):
    rain_mean = float(precip_trend.sel(month=month).mean(skipna=True))
    ndvi_mean = float(ndvi_trend.sel(month=month).mean(skipna=True))
    rain_dir = "Increasing" if rain_mean > 0 else "Decreasing"
    ndvi_dir = "Increasing" if ndvi_mean > 0 else "Decreasing"
    print(f"{calendar.month_abbr[month]:<6} {rain_dir:<14} {ndvi_dir:<14}")

# --- Plot: 12-panel grids ---
for var, title, fname in [
    (ndvi_trend, "Monthly NDVI trends (Sen's slope)", "ndvi_trend_maps.png"),
    (precip_trend, "Monthly precipitation trends (Sen's slope)", "precip_trend_maps.png"),
]:
    fig, axes = plt.subplots(3, 4, figsize=(13, 9))
    vmax = float(np.nanpercentile(np.abs(var.values), 95))
    for month, ax in zip(range(1, 13), axes.flat):
        im = var.sel(month=month).plot(
            ax=ax, cmap="BrBG", vmin=-vmax, vmax=vmax, add_colorbar=False
        )
        ax.set_title(calendar.month_abbr[month], fontsize=9)
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.set_xticks([])
        ax.set_yticks([])
    fig.colorbar(im, ax=axes, shrink=0.6, label="Sen's slope / year")
    fig.suptitle(title, fontsize=12)
    fig.savefig(fname, dpi=100, bbox_inches="tight")
    print(f"Saved plot: {fname}")
