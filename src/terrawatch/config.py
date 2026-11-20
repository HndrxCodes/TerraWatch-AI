"""Constants mirrored from the notebook (cells 1, 8, 11, 15) so cell-level results stay comparable
with the regional ones. Change them here, never inline."""

BBOX = (102.0, -4.9, 106.2, -1.6)      # west, south, east, north (same box as Giovanni/FIRMS)
CONF_MIN = 50                          # MODIS confidence minimum
SATELLITE = "Terra"                    # one satellite = consistent record from 2001

GRID_RES = 0.25                        # degrees (spec section 4.2)
MIN_INSIDE_FRAC = 0.2                  # keep a cell if >= 20% of it lies inside the province

DATA_START = "2001-01-01"              # first day with a consistent Terra record
DATA_END = "2024-12-31"
ML_START = "2003-01-01"                # leaves 2 years of fire history before the first prediction
HORIZON = 7                            # days ahead
STRIDE = 7                             # one prediction per cell per week

# Known FIRMS MODIS gaps (notebook cell 11): rows within 30 days before a gap, or inside it, are dropped
GAPS = [("2007-08-10", "2007-09-15"), ("2009-04-20", "2009-04-23")]

WF_YEARS = list(range(2010, 2025))     # walk-forward test years (notebook cell 15)
DRY_MM = 1.0                           # notebook cell 1: a day is 'dry' if rain < DRY_MM mm/day
