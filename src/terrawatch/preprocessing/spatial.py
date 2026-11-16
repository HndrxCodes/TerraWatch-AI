"""Province polygon -> 0.25 degree grid -> detection-to-cell assignment.

The grid is only a common analysis framework. Cell-level fire counts come from MODIS detections
(about 1 km pixels), so a cell is a spatial summary, not a claim of 0.25 degree source resolution.
"""
import json
import re
from dataclasses import dataclass

import numpy as np
import pandas as pd
from matplotlib.path import Path as MPath

from ..config import GRID_RES, MIN_INSIDE_FRAC

DEFAULT_NAME = r"(sumat.*(selatan|south))|(south.*sumat)"


@dataclass(frozen=True)
class GridSpec:
    x0: float      # west edge of cell column 0
    y0: float      # south edge of cell row 0
    res: float
    nx: int
    ny: int


def load_polygons(geojson_path, name_regex=DEFAULT_NAME):
    """Returns a list of polygons; each polygon = [outer_ring, hole, hole, ...] as (lon, lat) arrays."""
    feats = json.load(open(geojson_path))["features"]
    pat = re.compile(name_regex, re.I)
    sel = [ft for ft in feats if pat.search(str(ft.get("properties", {}).get("shapeName", "")))]
    if not sel:
        if len(feats) == 1:                       # region.geojson saved by notebook cell 20
            sel = feats
        else:
            names = [ft.get("properties", {}).get("shapeName") for ft in feats]
            raise ValueError(f"South Sumatra not found. Names in file: {names}")
    polys = []
    for ft in sel:
        g = ft["geometry"]
        polys += [g["coordinates"]] if g["type"] == "Polygon" else list(g["coordinates"])
    return [[np.array(r)[:, :2] for r in poly] for poly in polys]


def inside(polys, pts):
    ok = np.zeros(len(pts), bool)
    for poly in polys:
        m = MPath(poly[0]).contains_points(pts)
        for hole in poly[1:]:
            m &= ~MPath(hole).contains_points(pts)
        ok |= m
    return ok


def build_grid(polys, res=GRID_RES, min_frac=MIN_INSIDE_FRAC, sub=5):
    """Grid anchored to multiples of `res`. A cell is kept if >= min_frac of it is inside the province
    (estimated with a sub x sub point lattice). Returns (grid DataFrame, GridSpec)."""
    xy = np.vstack([poly[0] for poly in polys])
    x0, x1 = np.floor(xy[:, 0].min() / res) * res, np.ceil(xy[:, 0].max() / res) * res
    y0, y1 = np.floor(xy[:, 1].min() / res) * res, np.ceil(xy[:, 1].max() / res) * res
    nx, ny = int(round((x1 - x0) / res)), int(round((y1 - y0) / res))
    spec = GridSpec(float(x0), float(y0), float(res), nx, ny)

    off = (np.arange(sub) + 0.5) / sub * res
    ix, iy = np.meshgrid(np.arange(nx), np.arange(ny))
    ix, iy = ix.ravel(), iy.ravel()
    px = x0 + ix[:, None] * res + off[None, :]                # (cells, sub) longitudes
    py = y0 + iy[:, None] * res + off[None, :]                # (cells, sub) latitudes
    gx = np.repeat(px[:, :, None], sub, axis=2)               # (cells, sub, sub)
    gy = np.repeat(py[:, None, :], sub, axis=1)
    pts = np.column_stack([gx.ravel(), gy.ravel()])
    frac = inside(polys, pts).reshape(len(ix), sub * sub).mean(axis=1)

    keep = frac >= min_frac
    grid = pd.DataFrame({"cell_id": (iy * nx + ix)[keep], "ix": ix[keep], "iy": iy[keep],
                         "lat": y0 + iy[keep] * res + res / 2, "lon": x0 + ix[keep] * res + res / 2,
                         "frac_inside": frac[keep]}).sort_values("cell_id").reset_index(drop=True)
    return grid, spec


def assign_cells(det: pd.DataFrame, spec: GridSpec) -> np.ndarray:
    """Cell id of each detection (-1 if outside the grid bounding box)."""
    ix = np.floor((det.longitude.values - spec.x0) / spec.res).astype(int)
    iy = np.floor((det.latitude.values - spec.y0) / spec.res).astype(int)
    ok = (ix >= 0) & (ix < spec.nx) & (iy >= 0) & (iy < spec.ny)
    return np.where(ok, iy * spec.nx + ix, -1)
