# coding: utf-8

"""
Air Pollution Exposure Assessment from Traffic Emissions
--------------------------------------------------------

This script calculates the exposure of the population to air pollution 
(traffic-related air pollution - TRAP) using vehicle activity data, 
population raster, and decay parameters.

It includes:
    - Computation of distance-weighted exposure using spatial decay
    - Calculation of population exposed in different pollution bands
    - Export of a population-weighted exposure map (normalized)

INPUT:
    - Population raster (.tif)
    - List of traffic volumes (VKM) and road segments
    - Exposure thresholds and decay parameters

OUTPUT:
    - Raster maps for local emissions, distance-weighted exposure, 
      and population-weighted exposure (normalized)
    - Summary statistics for population exposed at different levels

HOW TO USE:
    1. Modify the file paths and parameters in the "Input Parameters" section.
    2. Run the script using any Python environment with `rasterio`, `numpy`, and helper functions installed.
"""

import pandas as pd
import os
import numpy as np
import rasterio
from scipy.signal import convolve2d
from shapely import wkt
from shapely.geometry import LineString, Point, shape, Polygon, box
from pyproj import Geod

def main():

    #########################################################
    ########### Input Parameters (TO BE MODIFIED) ###########
    #########################################################

    input_fleet_operation = "C:/Users/dumoulin/Documents/_CODES/gtfs4ev/examples/output/Mobility_fleet_operation.csv"
    input_travel_sequences = "C:/Users/dumoulin/Documents/_CODES/gtfs4ev/examples/output/Mobility_trip_travel_sequences.csv"

    output_local_emission_index = "air_pollution_local_emission_index.tif"
    output_distance_weighted_index = "air_pollution_distance_weighted_index.tif"     
    output_pop_exposure = "air_pollution_pop_exposure.tif"     

    pop_raster = "C:/Users/dumoulin/Documents/_CODES/gtfs4ev/examples/input/Nairobi_popraster_cropped.tif"

    buffer_distance = 300  # Buffer distance in meters
    decay_rate = 0.0064  # Decay factor (e.g. NO2 = 0.0064 per meter)

    #########################################################
    ############ Step 0: List VKM and linestrings ###########
    #########################################################

    # Get the data
    df1 = pd.read_csv(input_fleet_operation)
    df2 = pd.read_csv(input_travel_sequences)

    # 1. Extract total distance per trip_id
    distance_per_trip_df = (
        df1.groupby("trip_id")["total_distance_km"]
        .sum()
        .reset_index()
        .sort_values("trip_id")
    )

    # Extract list of total distances (only values, in trip_id order)
    total_distances = distance_per_trip_df["total_distance_km"].tolist()

    # 2. Reconstruct LINESTRING per trip_id from file1
    travelling_df = df2[df2["status"] == "travelling"].copy()
    travelling_df["geometry"] = travelling_df["location"].apply(wkt.loads)

    # Group and build full LINESTRING per trip, sorted by trip_id
    linestrings = []
    for trip_id in distance_per_trip_df["trip_id"]:  # Keep same order
        group = travelling_df[travelling_df["trip_id"] == trip_id]
        coords = []
        for geom in group["geometry"]:
            coords.extend(geom.coords)
        full_line = LineString(coords)
        linestrings.append(full_line)

    #########################################################
    ################### Step 1: Emission Index ##############
    #########################################################

    if not os.path.exists(output_local_emission_index):
        local_emission_index(total_distances, linestrings, pop_raster, output_local_emission_index)

    #########################################################
    #### Step 2: Distance-weigthed emission exposure map ####
    #########################################################

    with rasterio.open(output_local_emission_index) as src:
            # Read the raster data
            raster_data = src.read(1).astype(float) # assuming it's a single band raster
            
            # Define the convolution kernel (e.g., exponential decay)
            kernel_size = int( (buffer_distance / 100)*2 + 1 ) # distance + current pixel
            #print(kernel_size)
            decay_factor = decay_rate * 100  # NO2 = 0.0064 per meter, so 0,64 per pixel | 0.02 in some other refs

            kernel = exponential_decay_kernel(kernel_size, decay_factor)

            # Define the mask for the buffer distance
            mask = mask_within_radius(kernel_size, radius=(kernel_size-1)/2)
            
            # Apply the mask to the kernel
            kernel = kernel*mask
                
            # Distance-weigthing: perform the convolution operation 
            convolved_data = convolve2d(raster_data, kernel, mode='same', boundary='fill')
                
            # Create a new raster file with the convolved data
            profile = src.profile
            profile.update(dtype=rasterio.float32)  # Update data type to float32
            with rasterio.open(output_distance_weighted_index, 'w', **profile) as dst:
                dst.write(convolved_data.astype(rasterio.float32), 1)  # assuming it's a single band raster

    #########################################################
    ##### Step 3: Population exposure to air pollution ######
    #########################################################

    # Open the population raster file
    with rasterio.open(pop_raster) as population_src:
        # Read the population raster data
        population_data = population_src.read(1)  # assuming it's a single band raster
        population_profile = population_src.profile

    # Open the exposure raster file
    with rasterio.open(output_distance_weighted_index) as exposure_src:
        # Read the exposure raster data
        exposure_data = exposure_src.read(1)  # assuming it's a single band raster
        exposure_profile = exposure_src.profile

        # Ensure both rasters have the same shape
        if population_data.shape != exposure_data.shape:
            raise ValueError("Population raster and exposure raster do not have the same dimensions")

        # Calculate the population-weighted exposure
        popweighted_exposure = exposure_data * population_data

        # Normalize the population-weighted exposure by its maximum value
        max_value = np.max(popweighted_exposure)
        if max_value != 0:
            popweighted_exposure_normalized = popweighted_exposure / max_value
        else:
            popweighted_exposure_normalized = popweighted_exposure  # Handle case where max_value is zero

        # Update the profile for the output raster
        profile = population_profile
        profile.update(
            dtype=rasterio.float32,
            count=1,
            compress='lzw'
        )

        # Write the normalized population-weighted exposure to a new file

        with rasterio.open(output_pop_exposure, 'w', **profile) as dst:
            dst.write(popweighted_exposure_normalized.astype(rasterio.float32), 1)


#########################################################
###################### Helper functions #################
#########################################################

def local_emission_index(vkm_list, linestring_list, ref_raster_path, output_raster_path, C = 1):
    """ Map of local emission factor, prop. to vkm of all trips within each pixel  
    """
    # Open the reference raster
    with rasterio.open(ref_raster_path) as src:
        # Read the raster as a numpy array
        raster_array = src.read(1).astype(float)

        # Get the affine transformation matrix
        transform = src.transform

        half_pixel_width = transform[0] / 2
        half_pixel_height = transform[4] / 2

        # Create an empty emission index map
        emission_index = np.zeros_like(raster_array, dtype=np.uint8)

        # Iterate over each pixel
        i = 1
        vkm_tot = .0 # Total vkm - just to check the result in the end
        for y in range(src.height):
            for x in range(src.width):
                # Get the coordinates of the pixel
                pixel_coords = rasterio.transform.xy(transform, y, x)

                print(f"Processing pixel {i} out of {src.height*src.width}", end='\r')
                i = i+1
                
                # Calculate the coordinates of the square centered on the pixel                
                square_coords = [
                    (pixel_coords[0] - half_pixel_width, pixel_coords[1] - half_pixel_height),
                    (pixel_coords[0] + half_pixel_width, pixel_coords[1] - half_pixel_height),
                    (pixel_coords[0] + half_pixel_width, pixel_coords[1] + half_pixel_height),
                    (pixel_coords[0] - half_pixel_width, pixel_coords[1] + half_pixel_height),
                    (pixel_coords[0] - half_pixel_width, pixel_coords[1] - half_pixel_height)  # Close the polygon
                ]
                pixel_square = box(square_coords[0][0], square_coords[0][1], square_coords[2][0], square_coords[2][1])

                j = 0
                # Iterate over all linestrings and calculate the VKM within the current pixel
                for linestring in linestring_list:              

                    if linestring.intersects(pixel_square):                     
                        length = length_km(linestring)                      

                        intersection = linestring.intersection(pixel_square)
                        intersection_length = length_km(intersection)

                        vkm = vkm_list[j] # VKM of the trip associated with the linestring

                        vkm_pixel = vkm * (intersection_length/length) # VKM weigthed by the intersection length
                        vkm_tot += vkm_pixel                                    

                        emission_index[y, x] += vkm_pixel # Add contribution to the emission index (Muliplication by C is done at the end)

                    j = j + 1   

        # Write the mask to a new raster
        with rasterio.open(
            output_raster_path,
            'w',
            driver='GTiff',
            height=emission_index.shape[0],
            width=emission_index.shape[1],
            count=1,
            dtype=np.uint8,
            crs=src.crs,
            transform=transform
        ) as dst:
            dst.write(emission_index * C, 1)

    print(f"Rasterization completed successfully. Total vkm: {vkm_tot} km")

def exponential_decay_kernel(size, decay_factor):
    center = (size - 1) / 2  # Center of the kernel
    x = np.arange(size) - center
    kernel_2d = np.zeros((size, size))
    for i in range(size):
        for j in range(size):
            distance = np.sqrt((i - center) ** 2 + (j - center) ** 2)

            # Correct the distance for the center pixel to take into account that people are not at a zero distance from road 
            # We consider the average distance between 2 randomly distributed points within the square 
            if distance == .0:
                distance = 0.52 

            kernel_2d[i, j] = np.exp(-decay_factor * np.abs(distance))
    
    return kernel_2d

def length_km(linestring, geodesic = True):
    """ Calculates the lenght in km of a linestring
    """
    if geodesic: 
        geod = Geod(ellps="WGS84")
        distance = geod.geometry_length(linestring) / 1000.0
    else:
        web_mercator_projection = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
        linestring_projection = transform(web_mercator_projection, linestring)
        distance = linestring_projection.length / 1000.0

    return distance

# Define a mask for the pixel radius
def mask_within_radius(size, radius):
    mask = np.zeros((size, size))
    center = size // 2
    for i in range(size):
        for j in range(size):
            if (i - center)**2 + (j - center)**2 <= radius**2:
                mask[i, j] = 1
    return mask

def crop_raster(raster_path, bbox, output_raster_path):
    """ Creates a new raster cropped to the bbox
    """
    data_path = raster_path

    with rasterio.open(data_path) as src:
        out_image, out_transform = mask(src, [bbox], crop=True)
        out_meta = src.meta

    out_meta.update({"driver": "GTiff",
                 "height": out_image.shape[1],
                 "width": out_image.shape[2],
                 "transform": out_transform})

if __name__ == '__main__':
    main()
