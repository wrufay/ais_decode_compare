"""
This script processes the 5 decoded data sources and produces a 24 hour plot,
of each side by side for the entire day of 2025-12-30 UTC.

The data used is extracted after running extract.py on all 5 decoded data sources.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT  = Path(__file__).parent.parent
DATA_DIR   = REPO_ROOT / "data"
PLOTS_DIR  = DATA_DIR / "plots"
CACHE_PATH = DATA_DIR / "plot_cache.npz"

BBOX = {
    "lon_min": -68,
    "lon_max": -55,
    "lat_min": 42,
    "lat_max": 48,
}

SOURCES = [
    "original_nm4",
    "original_streaming",
    "aisdb_nm4",
    "aisdb_streaming",
    "reference_csv",
]


def make_plot(cache: np.lib.npyio.NpzFile, bounds: dict | None, out_png: Path) -> None:
    n_src = len(SOURCES)
    fig, axes = plt.subplots(1, n_src, figsize=(5 * n_src, 5), constrained_layout=True)
    fig.suptitle("Vessel positions — 00h-24h UTC  (2025-12-30)", fontsize=13)

    for ax, src_name in zip(axes, SOURCES):
        lons = cache[f"{src_name}_lons"]
        lats = cache[f"{src_name}_lats"]
        n = len(lons)
        ax.scatter(lons, lats, s=0.3, alpha=0.4, linewidths=0)
        ax.set_title(f"{src_name}\n{n:,} pts", fontsize=8)
        ax.set_xlabel("Longitude", fontsize=7)
        ax.set_ylabel("Latitude", fontsize=7)
        ax.tick_params(labelsize=6)
        if bounds:
            ax.set_xlim(bounds["lon_min"], bounds["lon_max"])
            ax.set_ylim(bounds["lat_min"], bounds["lat_max"])

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=150)
    plt.close()
    print(f"Saved: {out_png}")


def main():
    cache = np.load(CACHE_PATH)

    make_plot(cache, bounds=None, out_png=PLOTS_DIR / "routes_00h-24h_global.png")
    make_plot(cache, bounds=BBOX,  out_png=PLOTS_DIR / "routes_00h-24h_scotian.png")


if __name__ == "__main__":
    main()
