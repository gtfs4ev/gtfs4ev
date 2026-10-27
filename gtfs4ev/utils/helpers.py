# coding: utf-8

""" 
Some useful generic functions for gtfs4ev classes.
"""

import numpy as np
import re
import rasterio
import pyproj
from rasterio.mask import mask
from pyproj import Geod, Transformer
from shapely.geometry import LineString, Point
from shapely.ops import transform

def check_dataframe(df):
	""" 
    Returns false if a dataframe contains neither NaN nor empty values.	  
	"""

	# Check for NaN values in the entire DataFrame
	if df.isna().any().any():
		return False
	# Check for empty cells in the entire DataFrame
	elif df.apply(lambda x: x == '').any().any():
		return False
	else:
		return True
        
def find_closest_point(line, point):
    """
    Returns the closest point on the LineString to the given Point.
    """
    return line.interpolate(line.project(point))

def crop_raster(raster_path, bbox, output_raster_path):
    """ 
    Creates a new raster cropped to the bbox
    """
    data_path = raster_path

    with rasterio.open(data_path) as src:
        out_image, out_transform = mask(src, [bbox], crop=True)
        out_meta = src.meta

    out_meta.update({"driver": "GTiff",
                 "height": out_image.shape[1],
                 "width": out_image.shape[2],
                 "transform": out_transform})

    with rasterio.open(output_raster_path, "w", **out_meta) as dest:
        dest.write(out_image) 

def length_km(linestring, geodesic = True):
    """ 
    Calculates the lenght in km of a linestring
    """
    if geodesic: 
    	geod = Geod(ellps="WGS84")
    	distance = geod.geometry_length(linestring) / 1000.0
    else:
    	web_mercator_projection = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
    	linestring_projection = transform(web_mercator_projection, linestring)
    	distance = linestring_projection.length / 1000.0

    return distance

def mask_within_radius(size, radius):
    """ Defines a mask for the pixel radius
    """
    mask = np.zeros((size, size))
    center = size // 2
    for i in range(size):
        for j in range(size):
            if (i - center)**2 + (j - center)**2 <= radius**2:
                mask[i, j] = 1
    return mask

def gtfs_time_to_seconds(time_str: str) -> int:
    """ 
    Converts a GTFS time string to seconds since the
    beginning of the service day.
    Supports extended GTFS times such as 25:30:00.
    """
    if not isinstance(time_str, str):
        raise ValueError(f"Invalid GTFS time: {time_str!r}")

    match = re.fullmatch(
        r"([0-9]{1,2}):([0-5][0-9]):([0-5][0-9])",
        time_str,
    )

    if match is None:
        raise ValueError(f"Invalid GTFS time: {time_str!r}")

    hours, minutes, seconds = map(int, match.groups())

    return hours * 3600 + minutes * 60 + seconds


def seconds_to_gtfs_time(total_seconds: int) -> str:
    """
    Converts service-day seconds to a GTFS time string 
    without wrapping at midnight.
    """
    if (
        isinstance(total_seconds, bool)
        or not isinstance(total_seconds, (int, np.integer))
        or total_seconds < 0
    ):
        raise ValueError(
            "total_seconds must be a non-negative integer."
        )

    hours, remainder = divmod(int(total_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
