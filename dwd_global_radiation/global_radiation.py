"""
This module handles the querying and parsing of global radiation observation and forecasting
data from the DWD
(German Weather Service) servers. It is designed to fetch, process, and store quarterly-hour
global radiation measurement data and hourly forecast data for user-defined locations.

Key components:
- `Location`: Manages measurement and forecast data for specific geographic locations.
- `Measurement`: Stores quarterly-hour global radiation data retrieved from DWD servers.
- `Forecast`: Manages forecast data for global radiation with hourly granularity.
- `GlobalRadiation`: The main class that orchestrates data fetching, storage, and
  representation for different locations.

The module provides tools to:
- Automatically download and parse global radiation data from DWD.
- Calculate distances from user locations to the nearest data grid points.
- Format and print the data for easy visualization and verification.
- Maintain data integrity and facilitate easy updates and retrieval of the most recent data
  according to specified constraints (like maximum age of data).

Usage of this module is suitable for applications in environmental science, meteorology, and
any system requiring precise global radiation data management and representation.
"""

import datetime as dtbase
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import tzlocal

from . import utils
from .global_radiation_printer import (
    FormatConfig,
    PrintConfig,
    get_language_details,
    print_forecasts,
    print_header,
    print_measurements,
)

# Initialize a logger for this module
_LOGGER = logging.getLogger(__name__)

MAX_AGE_HOURS_OF_GLOBAL_RAD_DATA = 3


@dataclass
class GlobalForecastData:
    """
    Holds global forecast data and its issuance time.

    Attributes:
        issuance_time (datetime): The timestamp of the last forecast data retrieval.
        all_grid_forecasts (Any): The cached forecast data.
    """

    issuance_time: float = None
    all_grid_forecasts: Any = None  # The actual forecast data cache∏


@dataclass
class GlobalMeasurementData:
    """
    Class to store cached global measurement data.

    Attributes:
        issuance_time (float): Timestamp of the last issuance of measurement data. Initially None.
        latest_file_time (datetime): The latest file time from the DWD OpenData servers.
            Initially None.
        all_grid_measurements (list): List to store arrays of measurement data from multiple files.
    """

    issuance_time: float = None
    latest_file_time: datetime = None  # New attribute to store the latest file time
    all_grid_measurements: list = field(
        default_factory=list
    )  # List to store measurement data arrays


@dataclass
class Location:
    """Class for a user-provided location for measurement and forecast data"""

    latitude: float
    longitude: float
    name: str
    measurements: list = field(default_factory=list)
    forecasts: list = field(default_factory=list)

    def __repr__(self):
        measurement_count = len(self.measurements)
        forecast_count = len(self.forecasts)
        parts = [
            f"Location(name={self.name}",
            f"latitude={self.latitude}",
            f"longitude={self.longitude}",
            f"measurements={measurement_count} {'item' if measurement_count == 1 else 'items'}",
            f"forecasts={forecast_count} {'item' if forecast_count == 1 else 'items'})",
        ]
        return ", ".join(parts)

    def to_dict(self):
        """Convert Location to a dictionary."""
        return {
            "latitude": float(self.latitude),  # Explicit conversion to float
            "longitude": float(self.longitude),  # Explicit conversion to float
            "name": self.name,
            "measurements": [
                measurement.to_dict() for measurement in self.measurements
            ],
            "forecasts": [forecast.to_dict() for forecast in self.forecasts],
        }


@dataclass
class MeasurementEntry:
    """Class for storing DWD global radiation measurement data."""

    timestamp: float  # assuming timestamp is a Unix time float
    sis: float  # Solar Irradiance in W/m^2

    def to_dict(self):
        """Convert MeasurementEntry to a dictionary."""
        return {
            "timestamp": float(self.timestamp),  # Explicit conversion to float
            "sis": float(self.sis),  # Explicit conversion to float
        }


@dataclass
class Measurement:
    """Class for hosting various quarterly hour global radiation measurement
    data from DWD servers"""

    grid_latitude: float
    grid_longitude: float
    distance: float
    nearest_index: int
    measurement_values: list[MeasurementEntry] = field(default_factory=list)

    def __repr__(self):
        measurement_values_count = len(self.measurement_values)
        # Round latitude and longitude to two decimal places
        lat = round(self.grid_latitude, 2) if self.grid_latitude is not None else None
        lon = round(self.grid_longitude, 2) if self.grid_longitude is not None else None
        return (
            f"Measurement(grid_latitude={lat}, "
            f"grid_longitude={lon}, "
            f"distance={self.distance}, "
            f"nearest_index={self.nearest_index}, "
            f"measurement_values=Count: {measurement_values_count})"
        )

    def to_dict(self):
        """Convert Measurement to a dictionary."""
        return {
            "grid_latitude": float(self.grid_latitude),  # Explicit conversion to float
            "grid_longitude": float(
                self.grid_longitude
            ),  # Explicit conversion to float
            "distance": float(self.distance),  # Explicit conversion to float
            "nearest_index": int(self.nearest_index),  # Explicit conversion to int
            "measurement_values": [
                entry.to_dict() for entry in self.measurement_values
            ],
        }

    def add_measurement_value(self, timestamp, sis):
        """Method for adding retrieved measurement values as SIS."""
        if not any(entry.timestamp == timestamp for entry in self.measurement_values):
            self.measurement_values.append(MeasurementEntry(timestamp, sis))
        else:
            _LOGGER.warning(
                "Duplicate timestamp %s found. Measurement value not added.", timestamp
            )

    def get_measurement_values(self):
        """Method to retrieve all measurement values"""
        return self.measurement_values


@dataclass
class Forecast:
    """Class for storing Forecast data retrieved in hourly granularity from DWD servers"""

    issuance_time: str
    grid_latitude: float = None
    grid_longitude: float = None
    distance: float = None
    entries: list = field(default_factory=list)
    metadata: dict = field(
        default_factory=lambda: {
            "standard_name": None,
            "long_name": None,
            "units": None,
        }
    )

    def __repr__(self):
        entries_count = len(self.entries)
        metadata_status = (
            "populated"
            if any(value is not None for value in self.metadata.values())
            else "empty"
        )
        # Round latitude and longitude to two decimal places
        lat = round(self.grid_latitude, 2) if self.grid_latitude is not None else None
        lon = round(self.grid_longitude, 2) if self.grid_longitude is not None else None
        return (
            f"Forecast(issuance_time={self.issuance_time}, "
            f"grid_latitude={lat}, grid_longitude={lon}, "
            f"distance={self.distance}, entries={entries_count}, "
            f"metadata=status '{metadata_status}')"
        )

    def to_dict(self):
        """Convert Forecast to a dictionary."""
        return {
            "issuance_time": float(self.issuance_time),  # Explicit conversion to float
            "grid_latitude": float(self.grid_latitude),  # Explicit conversion to float
            "grid_longitude": float(
                self.grid_longitude
            ),  # Explicit conversion to float
            "distance": float(self.distance),  # Explicit conversion to float
            "entries": [entry.to_dict() for entry in self.entries],
            "metadata": self.metadata,
        }

    def set_metadata(self, standard_name=None, long_name=None, units=None):
        """Function for writing global radiation metadata of the DWD data file"""
        self.metadata["standard_name"] = standard_name
        self.metadata["long_name"] = long_name
        self.metadata["units"] = units

    def set_distance(self, latitude=None, longitude=None):
        """Method to calculate and set the distance between the user provided location
        and the nearest grid point of the DWD data"""
        self.distance = round(
            utils.haversine(
                self.grid_latitude, self.grid_longitude, latitude, longitude
            ),
            3,
        )

    def add_entry(self, timestamp, sis):
        """Method to add a forecast entry from a retrieved DWD file"""
        entry = ForecastEntry(timestamp, sis)
        self.entries.append(entry)


@dataclass
class ForecastEntry:
    """Class for storing DWD global radiation forecast data"""

    timestamp: str
    sis: float

    def to_dict(self):
        """Convert ForecastEntry to a dictionary."""
        return {
            "timestamp": float(self.timestamp),  # Explicit conversion to float
            "sis": float(self.sis),  # Explicit conversion to float
        }
@dataclass
class GlobalRadiation:
    """This is the main class of the DWD Global Radiation Observation and Forecast Data Library
    It gets instantiated by every program using this library. It stores the whole dataclass
    hierarchy for storing the DWD forecast and measurement data. It also provides the main methods
    for retrieving the data from DWD servers via http file download."""

    locations: list = field(default_factory=list)
    last_measurement_fetch_date: datetime = None
    last_forecast_fetch_date: datetime = None
    measurement_health_state: str = "green"
    forecast_health_state: str = "green"
    forecast_data: GlobalForecastData = field(default_factory=GlobalForecastData)
    measurement_data: GlobalMeasurementData = field(
        default_factory=GlobalMeasurementData
    )

    def to_dict(self):
        """Convert GlobalRadiation to a dictionary."""
        return {
            "locations": [location.to_dict() for location in self.locations],
            "last_measurement_fetch_date": (
                self.last_measurement_fetch_date.isoformat()
                if self.last_measurement_fetch_date
                else None
            ),
            "last_forecast_fetch_date": (
                self.last_forecast_fetch_date.isoformat()
                if self.last_forecast_fetch_date
                else None
            ),
            "measurement_health_state": self.measurement_health_state,
            "forecast_health_state": self.forecast_health_state,
        }

    def get_location_by_name(self, name):
        """Returns a location by its name, if exists."""
        for location in self.locations:
            if location.name == name:
                return location
        return None  # or raise an exception if a location is not found

    def print_data(self, language="English"):
        """
        Function for printing the data of the GlobalRadiation class and its subclasses.
        """
        local_tz = tzlocal.get_localzone()
        title, labels, dt_format = get_language_details(language)
        format_config = FormatConfig(dt_format=dt_format, local_tz=local_tz)
        config = PrintConfig(labels=labels, format_config=format_config)

        print_header(title)
        for location in self.locations:
            print(f"{config.labels['location']}: {location.name}")
            print(f"{config.indent_config.indent}{config.labels['latitude']}: {location.latitude}")
            print(
                f"{config.indent_config.indent}{config.labels['longitude']}: {location.longitude}")

            if location.measurements:
                print_measurements(location.measurements, config)
            if location.forecasts:
                print_forecasts(location.forecasts, config)

    def add_location(self, *, latitude=None, longitude=None, name=None):
        """
        With this method a user-provided location can be handed over to the main class.
        For all defined locations global radiation data will be retrieved and parsed.
        Checks for the uniqueness of the location name before adding to prevent duplicates.
        """
        # Validate mandatory parameters
        if latitude is None or longitude is None or name is None:
            raise ValueError("latitude, longitude, and name must be specified")

        # Validate latitude range
        if not 46.0 <= latitude <= 57.0:
            raise ValueError("latitude must be in the range 46.0 to 57.0")

        # Validate longitude range
        if not 5.0 <= longitude <= 16.0:
            raise ValueError("longitude must be in the range 5.0 to 16.0")

        # Check for unique location name
        if any(loc.name == name for loc in self.locations):
            raise ValueError(f"A location with the name '{name}' already exists.")

        # If all checks pass, create and add the new location
        location = Location(latitude, longitude, name)
        self.locations.append(location)

    def remove_location(self, name):
        """Removes a location by its name."""
        for i, location in enumerate(self.locations):
            if location.name == name:
                del self.locations[i]
                return
        raise ValueError(f"Location with name '{name}' not found")

    def _get_grid_data(self, all_grid_global_rad_data):

        ndlats = all_grid_global_rad_data.variables["lat"][:].filled()
        ndlons = all_grid_global_rad_data.variables["lon"][:].filled()
        long_grid, lat_grid = np.meshgrid(ndlons, ndlats)
        coordinates = np.dstack((lat_grid, long_grid)).reshape(-1, 2)
        return all_grid_global_rad_data, coordinates

    def _get_nearest_grid_point(self, latitude, longitude, grid_data):
        def calculate_candidate_points(lat, lon, lat_res=0.05, lon_res=0.05):
            lat_min = np.floor(lat / lat_res) * lat_res
            lon_min = np.floor(lon / lon_res) * lon_res
            return [
                (lat_min, lon_min),
                (lat_min, lon_min + lon_res),
                (lat_min + lat_res, lon_min),
                (lat_min + lat_res, lon_min + lon_res),
            ]

        def find_nearest_point(lat, lon, candidate_points):
            distances = [
                utils.haversine(lat, lon, c_lat, c_lon)
                for c_lat, c_lon in candidate_points
            ]
            nearest_idx = np.argmin(distances)
            return round(distances[nearest_idx], 3), candidate_points[nearest_idx]

        def get_grid_indices(grid_lat, grid_lon, grid_data):
            lat_var = grid_data.variables["lat"][:]
            lon_var = grid_data.variables["lon"][:]
            lat_idx = np.argmin(np.abs(lat_var - grid_lat))
            lon_idx = np.argmin(np.abs(lon_var - grid_lon))
            return lat_idx, lon_idx

        all_grid_global_rad_data, _ = grid_data
        candidate_points = calculate_candidate_points(latitude, longitude)
        nearest_distance, (grid_latitude, grid_longitude) = find_nearest_point(
            latitude, longitude, candidate_points
        )
        lat_index, lon_index = get_grid_indices(
            grid_latitude, grid_longitude, all_grid_global_rad_data
        )

        return (
            lat_index * len(all_grid_global_rad_data.variables["lon"][:]) + lon_index,
            nearest_distance,
            round(grid_latitude, 2),
            round(grid_longitude, 2),
        )

    def _get_measurement_value_from_loaded_data(
        self, all_grid_global_rad_data, nearest_index
    ):
        lat_index = nearest_index // all_grid_global_rad_data.variables["lat"].shape[0]
        lon_index = nearest_index % all_grid_global_rad_data.variables["lat"].shape[0]
        measurement_value = all_grid_global_rad_data.variables["SIS"][:][
            0, lat_index, lon_index
        ]
        units_string = all_grid_global_rad_data.variables["time"].units
        time_value = all_grid_global_rad_data.variables["time"][0].data.item()

        # Parse the base date from the units string and set it to UTC
        base_date_str = units_string.split(" since ")[1]
        base_date = datetime.strptime(base_date_str, "%Y-%m-%d %H:%M:%S")

        # Ensure the base_date is in UTC
        base_date = base_date.replace(tzinfo=timezone.utc)

        # Convert the base date to a timestamp
        base_timestamp = base_date.timestamp()

        # Add the time value to the base timestamp
        real_timestamp = base_timestamp + time_value

        return real_timestamp, measurement_value

    def fetch_measurements(
        self, max_hour_age_of_measurement: int = MAX_AGE_HOURS_OF_GLOBAL_RAD_DATA
    ):
        """
        Fetches DWD Global Radiation data from DWD OpenData servers.

        Parameters:
        max_hour_age_of_measurement:
            Defines the maximum age in hours for which global radiation measurement data
            shall be retrieved. The data provided by DWD is not actual measurement data, but
            full-grid satellite data. Every 15 minutes a new file is put on the DWD servers.
            The history on the HTTP file share goes back multiple days. As a programmer,
            you should adapt the queried history to your needs. If you want to record
            long-term data, use this method as a basis for persisting the data into an
            external database. Use this parameter with caution; with every added hour,
            4 more full-grid files have to be downloaded and analyzed. The higher you choose
            this number, the longer the run time of your fetch operation will be.
            A reasonable default is 3h set by the MAX_AGE_HOURS_OF_GLOBAL_RAD_DATA constant.
        """
        current_date = datetime.now(timezone.utc)
        self.last_measurement_fetch_date = current_date

        # Check if cached data is older than 15 minutes
        if self.measurement_data.issuance_time and (
            (current_date.timestamp() - self.measurement_data.issuance_time)
            < timedelta(minutes=15).total_seconds()
        ):
            use_cached_data = True
        else:
            matching_files = utils.get_matching_dwd_globalrad_data_files(
                current_date, max_hour_age_of_measurement
            )

            # Implementing measurement health check
            if not matching_files:
                self.measurement_health_state = "red"
                _LOGGER.warning(
                    "No matching files found. Setting measurement health state to red."
                )
                return

            latest_file_time = max(file_time for _, file_time in matching_files)
            if (current_date - latest_file_time).total_seconds() > 3600:
                self.measurement_health_state = "yellow"
            else:
                self.measurement_health_state = "green"

            # Check if the server data is newer than the cached data
            use_cached_data = (
                self.measurement_data.latest_file_time
                and self.measurement_data.latest_file_time >= latest_file_time
            )

        if use_cached_data:
            _LOGGER.info(
                "Using cached measurement data as it is less than 15 minutes old or server data "
                "is not newer."
            )
            self.process_measurements(
                self.measurement_data.all_grid_measurements, is_cached=True
            )
        else:
            self.reset_all_measurements()
            self.measurement_data = GlobalMeasurementData()  # Reset the cache

            # Process each file
            for file, _ in matching_files:  # file_time is no longer needed
                all_grid_global_rad_data = utils.load_sis_data(file)
                self.measurement_data.all_grid_measurements.append(
                    all_grid_global_rad_data
                )
                current_issuance_time = (
                    utils.get_measurement_timestamp_from_netcdf_history_attrib(
                        all_grid_global_rad_data.history
                    )
                )

                # Update cached issuance time and latest file time if they are newer
                if (self.measurement_data.issuance_time is None) or (
                    current_issuance_time > self.measurement_data.issuance_time
                ):
                    self.measurement_data.issuance_time = current_issuance_time
                    self.measurement_data.latest_file_time = latest_file_time

                self.process_measurements([all_grid_global_rad_data], is_cached=False)

    def reset_all_measurements(self):
        """
        Reset the measurements for all locations.
        """
        for location in self.locations:
            location.measurements = []

    def process_measurements(self, all_grid_measurements, is_cached):
        """
        Process measurement data for all locations.
        """
        for all_grid_global_rad_data in all_grid_measurements:
            for location in self.locations:
                if is_cached and location.measurements:
                    continue  # Do not overwrite existing measurements with cached data
                self.process_location(location, all_grid_global_rad_data)

    def process_location(self, location, all_grid_global_rad_data):
        """
        Process each location to handle its measurement updates.
        """
        if not location.measurements:
            self.initialize_measurement_for_location(location, all_grid_global_rad_data)
        self.update_measurement_for_location(location, all_grid_global_rad_data)

    def initialize_measurement_for_location(self, location, all_grid_global_rad_data):
        """
        Initializes measurement for a location based on the nearest grid point.
        """
        latitude, longitude = location.latitude, location.longitude
        grid_data = self._get_grid_data(all_grid_global_rad_data)
        (nearest_index, nearest_distance, grid_latitude, grid_longitude) = (
            self._get_nearest_grid_point(latitude, longitude, grid_data)
        )
        measurement = Measurement(
            grid_latitude, grid_longitude, nearest_distance, nearest_index
        )
        location.measurements = [measurement]

    def update_measurement_for_location(self, location, all_grid_global_rad_data):
        """
        Updates the measurement for a given location.
        """
        measurement = location.measurements[0]
        timestamp, sis_value = self._get_measurement_value_from_loaded_data(
            all_grid_global_rad_data, measurement.nearest_index
        )
        measurement.add_measurement_value(timestamp, sis_value)

    def fetch_forecasts(self):
        """
        Fetches and processes global radiation forecast data for each location stored
        in the object's locations list.

        This function retrieves forecast data from a dataset for the current date,
        processes each location's data by selecting the nearest forecast point
        (based on latitude and longitude), and appends a
        processed forecast object to each location's forecast list.

        The function retrieves the forecast data using utility functions that handle
        dataset loading and
        timestamp extraction. Each forecast includes metadata such as standard names, long names,
        and units, and forecasts are only added if their timestamp is greater than
        the current timestamp.
        """
        current_date = datetime.now(dtbase.UTC)

        # Check if we need to fetch new forecasts
        if (
            self.forecast_data.issuance_time
            and (current_date.timestamp() - self.forecast_data.issuance_time)
            < timedelta(hours=1).total_seconds()
        ):
            _LOGGER.info("Using cached forecast data as it is less than 1 hour old.")
            all_grid_forecasts = self.forecast_data.all_grid_forecasts
        else:
            self.last_forecast_fetch_date = current_date
            all_grid_forecasts, _actualhoursbehind = utils.load_forecast_dataset(
                current_date
            )

            # Check forecast data availability and timeliness
            if utils.is_dataset_empty(all_grid_forecasts):
                self.forecast_health_state = "red"
                _LOGGER.warning(
                    "Forecast data is empty. Setting forecast health state to red."
                )
                return  # Stop processing as no data is available

            # Check the timeliness of the data
            if _actualhoursbehind > 1:
                self.forecast_health_state = "yellow"
                _LOGGER.warning(
                    "Forecast data is %s hours behind. "
                    "Setting forecast health state to yellow.",
                    _actualhoursbehind,
                )
            else:
                self.forecast_health_state = "green"
                _LOGGER.info(
                    "Forecast data is up to date. Setting forecast health state to green."
                )

            # Update the cached forecast data
            global_issuance_time = (
                utils.get_forecast_issuance_timestamp_from_netcdf_history_attrib(
                    all_grid_forecasts.history
                )
            )
            self.forecast_data.issuance_time = global_issuance_time
            self.forecast_data.all_grid_forecasts = all_grid_forecasts

        for location in self.locations:
            latitude = location.latitude
            longitude = location.longitude
            selected_data = all_grid_forecasts.sel(
                lon=longitude, lat=latitude, method="nearest"
            )

            issuance_time = (
                utils.get_forecast_issuance_timestamp_from_netcdf_history_attrib(
                    selected_data.history
                )
            )
            forecast = Forecast(
                issuance_time,
                grid_latitude=round(selected_data.lat.item(), 2),
                grid_longitude=round(selected_data.lon.item(), 2),
            )
            forecast.set_metadata(
                standard_name=selected_data.SIS.standard_name,
                long_name=selected_data.SIS.long_name,
                units=selected_data.SIS.units,
            )
            forecast.set_distance(latitude, longitude)

            for timestamp, value in zip(
                selected_data.time.values, selected_data.SIS.values
            ):
                timestamp_of_entry = timestamp.astype("datetime64[s]").astype("float")
                if timestamp_of_entry > current_date.timestamp():
                    forecast.add_entry(timestamp_of_entry, value)

            location.forecasts = [forecast]
