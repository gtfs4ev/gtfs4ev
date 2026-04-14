import numpy as np
import pandas as pd
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import LineString, Point

from gtfs4ev.utils.helpers import (
    check_dataframe,
    find_closest_point,
    crop_raster,
    length_km,
    mask_within_radius,
)

# -------------------------------------------------------------------
# check_dataframe
# -------------------------------------------------------------------

def test_check_dataframe_valid():
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    assert check_dataframe(df) is True


def test_check_dataframe_nan():
    df = pd.DataFrame({"a": [1, np.nan]})
    assert check_dataframe(df) is False


def test_check_dataframe_empty_string():
    df = pd.DataFrame({"a": ["", 2]})
    assert check_dataframe(df) is False


# -------------------------------------------------------------------
# find_closest_point
# -------------------------------------------------------------------

def test_find_closest_point():
    line = LineString([(0, 0), (10, 0)])
    point = Point(5, 5)

    result = find_closest_point(line, point)

    assert isinstance(result, Point)
    assert pytest.approx(result.x, 0.001) == 5
    assert pytest.approx(result.y, 0.001) == 0


# -------------------------------------------------------------------
# crop_raster
# -------------------------------------------------------------------

def test_crop_raster(tmp_path):
    raster_path = tmp_path / "input.tif"
    output_path = tmp_path / "output.tif"

    data = np.ones((1, 10, 10), dtype=np.float32)
    transform = from_origin(0, 10, 1, 1)

    with rasterio.open(
        raster_path,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype=data.dtype,
        transform=transform,
    ) as dst:
        dst.write(data)

    bbox = {
        "type": "Polygon",
        "coordinates": [[[2, 8], [8, 8], [8, 2], [2, 2], [2, 8]]],
    }

    crop_raster(str(raster_path), bbox, str(output_path))

    with rasterio.open(output_path) as src:
        out = src.read()

    assert out is not None
    assert out.size > 0


# -------------------------------------------------------------------
# length_km
# -------------------------------------------------------------------

def test_length_km_geodesic():
    line = LineString([(0, 0), (0, 0.01)])

    result = length_km(line, geodesic=True)

    assert isinstance(result, float)
    assert result > 0


def test_length_km_projected():
    line = LineString([(0, 0), (0, 0.01)])

    result = length_km(line, geodesic=False)

    assert isinstance(result, float)
    assert result > 0


# -------------------------------------------------------------------
# mask_within_radius
# -------------------------------------------------------------------

def test_mask_within_radius_basic():
    m = mask_within_radius(5, 2)

    assert isinstance(m, np.ndarray)
    assert m.shape == (5, 5)

    # center must be 1
    assert m[2, 2] == 1

    # corners must be 0
    assert m[0, 0] == 0


def test_mask_within_radius_symmetry():
    m = mask_within_radius(7, 2)

    # symmetry check (basic sanity)
    assert m[1, 3] == m[3, 1]