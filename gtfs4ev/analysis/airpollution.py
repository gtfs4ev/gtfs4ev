# coding: utf-8

import os
import pandas as pd
import numpy as np
import rasterio
from scipy.signal import convolve2d
from shapely import wkt
from shapely.geometry import LineString, box
from pyproj import Geod


class AirPollutionExposure:
    """
    **Traffic-related air pollution (TRAP) exposure assessment**
    based on fleet operation outputs and spatial population data.

    The `AirPollutionExposure` class estimates **relative population exposure**
    to traffic-related emissions by combining:
    - Fleet-level vehicle kilometers traveled (VKT / VKM)
    - Spatialized road geometries from travel sequences
    - A population raster
    - Distance-based exponential decay of pollutant concentration

    The exposure assessment follows a raster-based workflow and produces
    intermediate and final spatial indicators suitable for GIS analysis.

    Workflow:
        1. **Local emission index**: Spatial allocation of vehicle kilometers to raster cells based on road geometry intersection.
        2. **Distance-weighted exposure**:Application of an exponential decay kernel within a given buffer distance.
        3. **Population-weighted exposure**: Combination with population raster and normalization.
        4. **Raster export**: All outputs are written as GeoTIFF files.

    Notes:
        - The model estimates **relative exposure**, not pollutant concentration
          (e.g. NO₂, PM₂.₅).
        - Emissions are assumed proportional to vehicle kilometers traveled.
        - No background pollution or meteorology is included.
        - The decay function is isotropic and distance-based.
        - All rasters must share the same spatial resolution and CRS.

    Attributes:
        input_fleet_operation (str): Path to CSV file containing fleet operation results (trip-level VKM).
        input_travel_sequences (str): Path to CSV file containing travel sequence geometries (WKT LineStrings).
        population_raster (str): Path to population raster (GeoTIFF).
        buffer_distance (float): Maximum influence distance in meters.
        decay_rate (float): Exponential decay rate (per meter).
        output_local_emission_index (str): Path to output local emission raster.
        output_distance_weighted_index (str): Path to output distance-weighted raster.
        output_population_exposure (str): Path to output population exposure raster.

    Examples:
        >>> calculator = AirPollutionExposure(
        ...     input_fleet_operation="fleet_operation.csv",
        ...     input_travel_sequences="travel_sequences.csv",
        ...     population_raster="population.tif",
        ...     buffer_distance=300,
        ...     decay_rate=0.0064
        ... )
        >>> calculator.compute_exposure(
        ...     "local_emission.tif",
        ...     "distance_weighted.tif",
        ...     "population_exposure.tif"
        ... )
    """

    ## ============================================================
    ## Constructor
    ## ============================================================

    def __init__(
        self,
        input_fleet_operation: str,
        input_travel_sequences: str,
        population_raster: str,
        buffer_distance: float = 300,
        decay_rate: float = 0.0064,
    ):
        """
        Initialize the air pollution exposure assessment engine.

        This constructor registers all required inputs and configuration
        parameters. No computation is performed at initialization.

        Args:
            input_fleet_operation (str): Path to CSV file containing fleet
                operation outputs, including total distance traveled per trip.
            input_travel_sequences (str): Path to CSV file containing
                travel sequences with WKT geometries.
            population_raster (str): Path to population raster (GeoTIFF).
            buffer_distance (float, optional): Maximum distance of pollutant
                influence in meters. Defaults to 300 m.
            decay_rate (float, optional): Exponential decay rate of exposure
                per meter. Defaults to 0.0064.
        """
        self.input_fleet_operation = input_fleet_operation
        self.input_travel_sequences = input_travel_sequences
        self.population_raster = population_raster
        self.buffer_distance = buffer_distance
        self.decay_rate = decay_rate

        self.output_local_emission_index = None
        self.output_distance_weighted_index = None
        self.output_population_exposure = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute_exposure(
        self,
        output_local_emission_index: str,
        output_distance_weighted_index: str,
        output_population_exposure: str,
    ) -> None:
        """
        Run the full air pollution exposure assessment pipeline.

        This method executes all processing steps sequentially:
        - VKM and geometry preparation
        - Local emission index computation
        - Distance-weighted exposure convolution
        - Population-weighted exposure normalization

        All intermediate and final results are written to disk.

        Args:
            output_local_emission_index (str): Output GeoTIFF path for the
                local emission index raster.
            output_distance_weighted_index (str): Output GeoTIFF path for the
                distance-weighted exposure raster.
            output_population_exposure (str): Output GeoTIFF path for the
                normalized population exposure raster.
        """
        self.output_local_emission_index = output_local_emission_index
        self.output_distance_weighted_index = output_distance_weighted_index
        self.output_population_exposure = output_population_exposure

        vkm_list, linestrings = self._prepare_vkm_and_geometry()

        if not os.path.exists(self.output_local_emission_index):
            self._local_emission_index(
                vkm_list,
                linestrings,
                self.population_raster,
                self.output_local_emission_index,
            )

        self._distance_weighted_exposure()
        self._population_weighted_exposure()

    # ------------------------------------------------------------------
    # Step 0 – Data preparation
    # ------------------------------------------------------------------

    def _prepare_vkm_and_geometry(self):
        """
        Prepare vehicle kilometers traveled (VKM) and road geometries.

        This method:
        - Aggregates trip-level distances from fleet operation data
        - Reconstructs continuous LineStrings from travel sequence points
        - Aligns VKM values with corresponding geometries

        Returns:
            tuple:
                - vkm_list (list[float]): Total distance traveled per trip (km).
                - linestrings (list[LineString]): Reconstructed trip geometries.
        """
        df_fleet = pd.read_csv(self.input_fleet_operation)
        df_seq = pd.read_csv(self.input_travel_sequences)

        distance_per_trip = (
            df_fleet.groupby("trip_id")["total_distance_km"]
            .sum()
            .reset_index()
            .sort_values("trip_id")
        )

        vkm_list = distance_per_trip["total_distance_km"].tolist()

        travelling = df_seq[df_seq["status"] == "travelling"].copy()
        travelling["geometry"] = travelling["location"].apply(wkt.loads)

        linestrings = []
        for trip_id in distance_per_trip["trip_id"]:
            group = travelling[travelling["trip_id"] == trip_id]
            coords = []
            for geom in group["geometry"]:
                coords.extend(geom.coords)
            linestrings.append(LineString(coords))

        return vkm_list, linestrings

    # ------------------------------------------------------------------
    # Step 1 – Local emission index
    # ------------------------------------------------------------------

    def _local_emission_index(self, vkm_list, linestrings, ref_raster, output_raster, C=1):
        """
        Compute a rasterized local emission index.

        Each raster cell receives a share of vehicle kilometers traveled
        proportional to the length of road segments intersecting the cell.

        Args:
            vkm_list (list[float]): Vehicle kilometers traveled per trip.
            linestrings (list[LineString]): Trip geometries.
            ref_raster (str): Reference raster defining grid and CRS.
            output_raster (str): Output GeoTIFF path.
            C (float, optional): Scaling constant. Defaults to 1.
        """
        with rasterio.open(ref_raster) as src:
            raster = src.read(1).astype(float)
            transform = src.transform

            half_w = transform[0] / 2
            half_h = abs(transform[4]) / 2

            emission_index = np.zeros_like(raster, dtype=float)
            geod = Geod(ellps="WGS84")

            total_rows = src.height
            progress_step = max(1, total_rows // 20)  # ~5% steps

            for y in range(total_rows):

                # ---- progress message ----
                if y % progress_step == 0 or y == total_rows - 1:
                    pct = 100 * y / total_rows
                    print(
                        f"Computing local emission index: "
                        f"{pct:5.1f}% ({y}/{total_rows} rows)",
                        end="\r",
                    )

                for x in range(src.width):
                    px, py = rasterio.transform.xy(transform, y, x)
                    pixel_box = box(
                        px - half_w, py - half_h,
                        px + half_w, py + half_h
                    )

                    for j, line in enumerate(linestrings):
                        if line.intersects(pixel_box):
                            intersection = line.intersection(pixel_box)
                            if not intersection.is_empty:
                                total_len = geod.geometry_length(line) / 1000
                                inter_len = geod.geometry_length(intersection) / 1000
                                emission_index[y, x] += vkm_list[j] * (inter_len / total_len)

            print("\nLocal emission index computation completed.")

            profile = src.profile
            profile.update(dtype=rasterio.float32, count=1)

            with rasterio.open(output_raster, "w", **profile) as dst:
                dst.write((emission_index * C).astype(rasterio.float32), 1)

    # ------------------------------------------------------------------
    # Step 2 – Distance-weighted exposure
    # ------------------------------------------------------------------

    def _distance_weighted_exposure(self):
        """
        Apply distance-based exponential decay to the local emission index.

        The method convolves the local emission raster with an isotropic
        exponential decay kernel, limited to a circular buffer defined
        by `buffer_distance`.

        The result represents potential exposure intensity independent
        of population.
        """
        with rasterio.open(self.output_local_emission_index) as src:
            data = src.read(1).astype(float)

            kernel_size = int((self.buffer_distance / 100) * 2 + 1)
            decay_factor = self.decay_rate * 100

            kernel = self._exponential_decay_kernel(kernel_size, decay_factor)
            kernel *= self._mask_within_radius(kernel_size, (kernel_size - 1) / 2)

            convolved = convolve2d(data, kernel, mode="same", boundary="fill")

            profile = src.profile
            profile.update(dtype=rasterio.float32)

            with rasterio.open(self.output_distance_weighted_index, "w", **profile) as dst:
                dst.write(convolved.astype(rasterio.float32), 1)

    # ------------------------------------------------------------------
    # Step 3 – Population-weighted exposure
    # ------------------------------------------------------------------

    def _population_weighted_exposure(self):
        """
        Compute population-weighted exposure and normalize.

        The distance-weighted exposure raster is multiplied by the
        population raster and normalized by its maximum value to produce
        a relative exposure index in the range [0, 1].
        """
        with rasterio.open(self.population_raster) as pop_src:
            pop = pop_src.read(1)
            profile = pop_src.profile

        with rasterio.open(self.output_distance_weighted_index) as exp_src:
            exposure = exp_src.read(1)

        pop_exposure = exposure * pop
        max_val = np.max(pop_exposure)

        if max_val > 0:
            pop_exposure /= max_val

        profile.update(dtype=rasterio.float32, count=1, compress="lzw")

        with rasterio.open(self.output_population_exposure, "w", **profile) as dst:
            dst.write(pop_exposure.astype(rasterio.float32), 1)

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    @staticmethod
    def _exponential_decay_kernel(size, decay_factor) -> np.ndarray:
        """
        Generate a 2D exponential decay kernel.

        Args:
            size (int): Kernel size (number of pixels per dimension).
            decay_factor (float): Exponential decay factor per pixel.

        Returns:
            np.ndarray: Decay kernel.
        """
        center = (size - 1) / 2
        kernel = np.zeros((size, size))
        for i in range(size):
            for j in range(size):
                d = np.sqrt((i - center) ** 2 + (j - center) ** 2)
                d = 0.52 if d == 0 else d
                kernel[i, j] = np.exp(-decay_factor * d)
        return kernel

    @staticmethod
    def _mask_within_radius(size, radius) -> np.ndarray:
        """
        Create a circular mask to limit kernel influence.

        Args:
            size (int): Kernel size.
            radius (float): Radius of influence in pixels.

        Returns:
            np.ndarray: Binary mask array.
        """
        mask = np.zeros((size, size))
        c = size // 2
        for i in range(size):
            for j in range(size):
                if (i - c) ** 2 + (j - c) ** 2 <= radius ** 2:
                    mask[i, j] = 1
        return mask