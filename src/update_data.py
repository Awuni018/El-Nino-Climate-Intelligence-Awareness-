"""
El Niño Watch Ghana — Data Update Script
Run with: python -m src.update_data [--source all|oni|chirps|boundaries|faostat]

Downloads and caches all data sources.
"""

from __future__ import annotations

import argparse
import logging
import sys
import zipfile
import io
from pathlib import Path

import numpy as np
import pandas as pd
import requests

# Allow running as __main__ from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import (
    CHIRPS_BASE_URL,
    CHIRPS_END_YEAR,
    CHIRPS_START_YEAR,
    DATA_PROCESSED,
    DATA_RAW,
    FAOSTAT_CROPS_URL,
    GEOBOUNDARIES_GHA_ADM1_URL,
    GHANA_BBOX,
    GHANA_REGIONS,
    ONI_URL,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 60


def _get(url: str, stream: bool = False, **kwargs) -> requests.Response:
    logger.info("GET %s", url)
    resp = requests.get(url, timeout=REQUEST_TIMEOUT, stream=stream, **kwargs)
    resp.raise_for_status()
    return resp


# ---------------------------------------------------------------------------
# ONI
# ---------------------------------------------------------------------------

def update_oni() -> None:
    """Download and cache ONI data from NOAA."""
    logger.info("=== Updating ONI ===")
    resp = _get(ONI_URL)
    raw_path = DATA_RAW / "oni.ascii.txt"
    raw_path.write_text(resp.text, encoding="utf-8")

    from src.data_loader import _parse_oni_text
    df = _parse_oni_text(resp.text)
    out_path = DATA_PROCESSED / "oni.parquet"
    df.to_parquet(out_path, index=False)
    logger.info("ONI: saved %d rows → %s", len(df), out_path)


# ---------------------------------------------------------------------------
# Ghana Boundaries
# ---------------------------------------------------------------------------

def update_boundaries() -> None:
    """Download Ghana ADM1 boundaries from geoBoundaries."""
    import json
    logger.info("=== Updating Ghana Boundaries ===")
    meta = _get(GEOBOUNDARIES_GHA_ADM1_URL).json()
    geojson_url = meta.get("gjDownloadURL")
    if not geojson_url:
        raise RuntimeError("geoBoundaries API did not return a download URL")
    geojson = _get(geojson_url).json()
    out_path = DATA_PROCESSED / "ghana_adm1.geojson"
    out_path.write_text(json.dumps(geojson), encoding="utf-8")
    logger.info("Boundaries: saved → %s", out_path)


# ---------------------------------------------------------------------------
# CHIRPS
# ---------------------------------------------------------------------------

def update_chirps() -> None:
    """
    Download CHIRPS monthly GeoTIFFs for all years, clip to Ghana, and
    aggregate to region-level mean rainfall.
    This is a long-running operation (full 1981–present archive).
    """
    try:
        import rioxarray  # noqa: F401
        import xarray as xr
        import rasterio
        from rasterio.mask import mask as rio_mask
        import json
    except ImportError as e:
        logger.error("Missing dependency: %s. Install requirements.txt first.", e)
        return

    logger.info("=== Updating CHIRPS (%d–%d) — this may take a while ===",
                CHIRPS_START_YEAR, CHIRPS_END_YEAR)

    # Load Ghana boundaries for clipping
    bounds_path = DATA_PROCESSED / "ghana_adm1.geojson"
    if not bounds_path.exists():
        logger.info("Boundaries not cached — downloading first")
        update_boundaries()

    with open(bounds_path, encoding="utf-8") as f:
        boundaries = json.load(f)

    rows = []
    for year in range(CHIRPS_START_YEAR, CHIRPS_END_YEAR + 1):
        for month in range(1, 13):
            filename = f"chirps-v2.0.{year}.{month:02d}.tif.gz"
            url = f"{CHIRPS_BASE_URL}{filename}"
            tif_path = DATA_RAW / filename

            if not tif_path.exists():
                try:
                    resp = _get(url, stream=True)
                    with open(tif_path, "wb") as fh:
                        for chunk in resp.iter_content(chunk_size=1024 * 1024):
                            fh.write(chunk)
                    logger.info("Downloaded: %s", filename)
                except Exception as exc:
                    logger.warning("Failed %s: %s — skipping", filename, exc)
                    continue

            # Open, clip to each region
            try:
                import gzip
                import tempfile
                with gzip.open(tif_path, "rb") as gz_f:
                    tif_bytes = gz_f.read()

                with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
                    tmp.write(tif_bytes)
                    tmp_path = Path(tmp.name)

                with rasterio.open(tmp_path) as src:
                    lon_min, lat_min, lon_max, lat_max = GHANA_BBOX
                    for feature in boundaries.get("features", []):
                        region_name = feature["properties"].get("shapeName", "Unknown")
                        try:
                            out_image, _ = rio_mask(src, [feature["geometry"]], crop=True, nodata=np.nan)
                            vals = out_image[0].flatten()
                            vals = vals[~np.isnan(vals)]
                            vals = vals[vals >= 0]  # CHIRPS no-data = -9999
                            mean_rain = float(np.mean(vals)) if len(vals) else np.nan
                        except Exception:
                            mean_rain = np.nan

                        rows.append({
                            "year": year,
                            "month": month,
                            "region": region_name,
                            "rainfall_mm": mean_rain,
                            "anom_pct": np.nan,  # computed later
                            "is_mock": False,
                        })

                tmp_path.unlink(missing_ok=True)
            except Exception as exc:
                logger.warning("Could not process %s: %s", filename, exc)

        logger.info("Year %d done", year)

    df = pd.DataFrame(rows)
    df["mock_badge"] = ""
    out_path = DATA_PROCESSED / "chirps_ghana.parquet"
    df.to_parquet(out_path, index=False)
    logger.info("CHIRPS: saved %d rows → %s", len(df), out_path)


# ---------------------------------------------------------------------------
# FAOSTAT
# ---------------------------------------------------------------------------

def update_faostat() -> None:
    """
    Download FAOSTAT crop production data for Ghana and cache yield data.
    Uses the FAOSTAT bulk download (Africa Production zip).
    """
    logger.info("=== Updating FAOSTAT ===")
    try:
        resp = _get(FAOSTAT_CROPS_URL, stream=True)
    except Exception as exc:
        logger.error("FAOSTAT download failed: %s", exc)
        return

    zip_path = DATA_RAW / "faostat_africa.zip"
    with open(zip_path, "wb") as fh:
        for chunk in resp.iter_content(chunk_size=1024 * 1024):
            fh.write(chunk)
    logger.info("FAOSTAT zip downloaded: %s MB", zip_path.stat().st_size // 1_000_000)

    target_items = {
        "Cocoa beans": 661,
        "Maize": 56,
        "Cassava": 125,
        "Rice, paddy": 27,
    }
    item_codes = set(target_items.values())

    rows = []
    with zipfile.ZipFile(zip_path) as zf:
        csv_names = [n for n in zf.namelist() if n.endswith(".csv") and "All_Data" not in n]
        if not csv_names:
            csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
        logger.info("Files in zip: %s", csv_names[:5])

        for name in csv_names:
            try:
                with zf.open(name) as f:
                    df_raw = pd.read_csv(f, encoding="latin-1", low_memory=False)
                    # Filter for Ghana, yield element, target crops
                    if "Area" not in df_raw.columns:
                        continue
                    sub = df_raw[
                        (df_raw["Area"] == "Ghana") &
                        (df_raw.get("Element", pd.Series()) == "Yield") &
                        (df_raw.get("Item Code", pd.Series(dtype=int)).isin(item_codes))
                    ]
                    if sub.empty:
                        continue
                    year_cols = [c for c in sub.columns if c.startswith("Y") and c[1:].isdigit()]
                    for _, row in sub.iterrows():
                        item_name = row.get("Item", "Unknown")
                        for yc in year_cols:
                            yr = int(yc[1:])
                            val = row[yc]
                            try:
                                val = float(val)
                            except (ValueError, TypeError):
                                val = np.nan
                            rows.append({
                                "year": yr,
                                "crop": item_name,
                                "yield_kg_ha": val,
                                "country": "Ghana",
                                "is_mock": False,
                            })
            except Exception as exc:
                logger.warning("Could not read %s: %s", name, exc)

    if rows:
        df = pd.DataFrame(rows).dropna(subset=["yield_kg_ha"])
        df["mock_badge"] = ""
        out_path = DATA_PROCESSED / "faostat_ghana.parquet"
        df.to_parquet(out_path, index=False)
        logger.info("FAOSTAT: saved %d rows → %s", len(df), out_path)
    else:
        logger.warning("FAOSTAT: no rows extracted — check the zip structure")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="El Niño Watch Ghana — Data Updater")
    parser.add_argument(
        "--source",
        choices=["all", "oni", "chirps", "boundaries", "faostat"],
        default="all",
        help="Which data source to update (default: all)",
    )
    args = parser.parse_args()

    updaters = {
        "oni": update_oni,
        "boundaries": update_boundaries,
        "chirps": update_chirps,
        "faostat": update_faostat,
    }

    if args.source == "all":
        for name, fn in updaters.items():
            try:
                fn()
            except Exception as exc:
                logger.error("%s update failed: %s", name, exc)
    else:
        try:
            updaters[args.source]()
        except Exception as exc:
            logger.error("%s update failed: %s", args.source, exc)
            sys.exit(1)

    logger.info("=== Update complete ===")


if __name__ == "__main__":
    main()
