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
from dataclasses import dataclass, field
from datetime import datetime
import datetime as dtbase
from string import Template
import tzlocal
from tabulate import tabulate
import numpy as np

from . import utils

MAX_AGE_HOURS_OF_GLOBAL_RAD_DATA = 3

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
            f"forecasts={forecast_count} {'item' if forecast_count == 1 else 'items'})"
        ]
        return ", ".join(parts)

    def to_dict(self):
        """Convert Location to a dictionary."""
        return {
            "latitude": float(self.latitude),  # Explicit conversion to float
            "longitude": float(self.longitude), # Explicit conversion to float
            "name": self.name,
            "measurements": [measurement.to_dict() for measurement in self.measurements],
            "forecasts": [forecast.to_dict() for forecast in self.forecasts]
        }

@dataclass
class MeasurementEntry:
    """Class for storing DWD global radiation measurement data."""
    timestamp: float  # assuming timestamp is a Unix time float
    sis: float        # Solar Irradiance in W/m^2

    def to_dict(self):
        """Convert MeasurementEntry to a dictionary."""
        return {
            "timestamp": float(self.timestamp),  # Explicit conversion to float
            "sis": float(self.sis)               # Explicit conversion to float
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
        measurement_values_count=len(self.measurement_values)
        # Round latitude and longitude to two decimal places
        lat = round(self.grid_latitude, 2) if self.grid_latitude is not None else None
        lon = round(self.grid_longitude, 2) if self.grid_longitude is not None else None
        return (f"Measurement(grid_latitude={lat}, "
                f"grid_longitude={lon}, "
                f"distance={self.distance}, "
                f"nearest_index={self.nearest_index}, "
                f"measurement_values=Count: {measurement_values_count})")

    def to_dict(self):
        """Convert Measurement to a dictionary."""
        return {
            "grid_latitude": float(self.grid_latitude),  # Explicit conversion to float
            "grid_longitude": float(self.grid_longitude), # Explicit conversion to float
            "distance": float(self.distance),            # Explicit conversion to float
            "nearest_index": int(self.nearest_index),    # Explicit conversion to int
            "measurement_values": [entry.to_dict() for entry in self.measurement_values]
        }

    def add_measurement_value(self, timestamp, sis):
        """Method for adding retrieved measurement values as SIS"""
        self.measurement_values.append(MeasurementEntry(timestamp, sis))

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
    metadata: dict = field(default_factory=
                           lambda: {"standard_name": None, "long_name": None, "units": None})

    def __repr__(self):
        entries_count = len(self.entries)
        metadata_status = (
            "populated" if any(value is not None for value in self.metadata.values())
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
            "grid_longitude": float(self.grid_longitude), # Explicit conversion to float
            "distance": float(self.distance),            # Explicit conversion to float
            "entries": [entry.to_dict() for entry in self.entries],
            "metadata": self.metadata
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
            "sis": float(self.sis)               # Explicit conversion to float
        }

@dataclass
class IndentConfig:
    """Handles indentation settings for pretty-printing data outputs."""
    indent: str = "     "
    sub_indent: str = "        "

@dataclass
class FormatConfig:
    """Encapsulates formatting details such as date/time format and local timezone."""
    dt_format: str
    local_tz: str

@dataclass
class PrintConfig:
    """ Class for setting configuration parameters for the global radiation print service."""

    labels: dict
    format_config: FormatConfig
    indent_config: IndentConfig = field(default_factory=IndentConfig)

@dataclass
class GlobalRadiation:
    """This is the main class of the DWD Global Radiation Observation and Forecast Data Library
    It gets instantiated by every program using this library. It stores the whole dataclass
    hierarchy for storing the DWD forecast and measurement data. It also provides the main methods
    for retrieving the data from DWD servers via http file download."""

    locations: list = field(default_factory=list)
    last_measurement_fetch_date: datetime = None
    last_forecast_fetch_date: datetime = None
    measurement_health_state: str = 'green'
    forecast_health_state: str = 'green'

    def to_dict(self):
        """Convert GlobalRadiation to a dictionary."""
        return {
            "locations": [location.to_dict() for location in self.locations],
            "last_measurement_fetch_date": self.last_measurement_fetch_date.isoformat(
                ) if self.last_measurement_fetch_date else None,
            "last_forecast_fetch_date": self.last_forecast_fetch_date.isoformat(
                ) if self.last_forecast_fetch_date else None,
            "measurement_health_state": self.measurement_health_state,
            "forecast_health_state": self.forecast_health_state
        }

    def get_location_by_name(self, name):
        """Returns a location by its name, if exists."""
        for location in self.locations:
            if location.name == name:
                return location
        return None  # or raise an exception if a location is not found

    def print_data(self, language="English"):
        """
        Function for printing the data of the GlobalRadiation class and its subclasses

        This method provides a comprehensive print service to output all the retrieved
        global radiation forecast and measurement data from the queried DWD datasets.
        The default output language is English, but another supported language is German
        """
        local_tz = tzlocal.get_localzone()
        title, labels, dt_format = self._get_language_details(language)
        format_config = FormatConfig(dt_format=dt_format, local_tz=local_tz)
        config = PrintConfig(labels=labels, format_config=format_config)

        self._print_header(title)
        for location in self.locations:
            print(f"{config.labels['location']}: {location.name}")
            print(f"{config.indent_config.indent}{config.labels['latitude']}: {location.latitude}")
            print(
                f"{config.indent_config.indent}{config.labels['longitude']}: {location.longitude}")

            if location.measurements:
                self._print_measurements(location.measurements, config)
            if location.forecasts:
                self._print_forecasts(location.forecasts, config)

    def _get_language_details(self, language):
        if language == "German":
            title = "DWD Vorhersage- und Beobachtungsdaten ausgewählter Standorte"
            labels = {
                "location": "Ort",
                "latitude": "Breitengrad",
                "longitude": "Längengrad",
                "measurements": "Messungen",
                "timestamp": "Zeitstempel",
                "sis": "SIS Wert in W/m2",
                "grid_latitude": "Rasterbreitengrad",
                "grid_longitude": "Rasterlängengrad",
                "distance": "Entfernung der Lokation zum nächsten Gridpunkt in km",
                "forecasts": "Prognosen",
                "issuance_time": "Ausgabezeit",
                "metadata": "Metadaten",
                "entries": "Einträge",
            }
            dt_format = "%d.%m.%Y %H:%M:%S"
        else:
            title = "DWD Forecast and Observation Data from Selected Locations"
            labels = {
                "location": "Location",
                "latitude": "Latitude",
                "longitude": "Longitude",
                "measurements": "Measurements",
                "timestamp": "Timestamp",
                "sis": "SIS Value in W/m2",
                "grid_latitude": "Grid Latitude",
                "grid_longitude": "Grid Longitude",
                "distance": "Distance of the location to the nearest gridpoint in km",
                "forecasts": "Forecasts",
                "issuance_time": "Issuance Time",
                "metadata": "Metadata",
                "entries": "Entries",
            }
            dt_format = "%Y-%m-%d %H:%M:%S"

        return title, labels, dt_format

    def _print_header(self, title):
        print("=" * len(title))
        print(title)
        print("=" * len(title))

    def _print_measurements(self, measurements, config):
        print(f"{config.indent_config.indent}{config.labels['measurements']}:")
        for measurement in measurements:
            self._print_single_measurement(measurement, config)

    def _print_forecasts(self, forecasts, config):
        print(f"{config.indent_config.indent}{config.labels['forecasts']}:")
        for forecast in forecasts:
            self._print_single_forecast(forecast, config)

    def _print_single_measurement(self, measurement, config):
        """
        Prints a single measurement, utilizing the PrintConfig object to access
        necessary configuration like labels, date format, and additional indentation.
        """
        output = Template(
            f"{config.indent_config.sub_indent}{config.labels['grid_latitude']}: $grid_latitude\n"
            f"{config.indent_config.sub_indent}{config.labels['grid_longitude']}: $grid_longitude\n"
            f"{config.indent_config.sub_indent}{config.labels['distance']}: $distance"
        ).substitute(
            grid_latitude=measurement.grid_latitude,
            grid_longitude=measurement.grid_longitude,
            distance=measurement.distance,
        )
        print(output)
        if measurement.measurement_values:
            self._print_tabulated_data(measurement.measurement_values, config)

    def _print_tabulated_data(self, data_entries, config):
        """
        Prints data entries (either forecast entries or measurement values) in a tabulated format,
        utilizing the PrintConfig object for formatting details such as labels, date format,
        and additional indentation.
        """
        table = [
            [
                datetime.fromtimestamp(
                    entry.timestamp, config.format_config.local_tz).strftime(
                        config.format_config.dt_format),
                entry.sis  # Now consistently using `sis` for both measurements and forecasts
            ]
            for entry in data_entries
        ]

        table_output = tabulate(
            table,
            headers=[config.labels["timestamp"], config.labels["sis"]],
            tablefmt="grid"
        )

        table_output = "\n".join(
            [f"{config.indent_config.sub_indent}{line}" for line in table_output.splitlines()]
        )

        print(table_output)

    def _print_single_forecast(self, forecast, config):
        """
        Prints a single forecast, utilizing the PrintConfig object to access necessary
        configuration like labels, date format, and additional indentation.
        """
        issuance_time = datetime.fromtimestamp(
            forecast.issuance_time, config.format_config.local_tz
        ).strftime(config.format_config.dt_format)

        output = Template(
            f"{config.indent_config.sub_indent}{config.labels['issuance_time']}: $issuance_time\n"
            f"{config.indent_config.sub_indent}{config.labels['grid_latitude']}: $grid_latitude\n"
            f"{config.indent_config.sub_indent}{config.labels['grid_longitude']}: $grid_longitude\n"
            f"{config.indent_config.sub_indent}{config.labels['distance']}: $distance\n"
            f"{config.indent_config.sub_indent}{config.labels['metadata']}: $metadata"
        ).substitute(
            issuance_time=issuance_time,
            grid_latitude=forecast.grid_latitude,
            grid_longitude=forecast.grid_longitude,
            distance=forecast.distance,
            metadata=forecast.metadata,
        )
        print(output)

        if forecast.entries:
            self._print_tabulated_data(forecast.entries, config)


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
                (lat_min + lat_res, lon_min + lon_res)
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
        nearest_distance, (
            grid_latitude, grid_longitude) = find_nearest_point(
                latitude, longitude, candidate_points)
        lat_index, lon_index = get_grid_indices(
            grid_latitude, grid_longitude, all_grid_global_rad_data)

        return (
            lat_index * len(all_grid_global_rad_data.variables["lon"][:]) + lon_index,
            nearest_distance,
            round(grid_latitude, 2),
            round(grid_longitude, 2)
        )


    def _get_measurement_value_from_loaded_data(
        self, all_grid_global_rad_data, nearest_index
    ):
        lat_index = nearest_index // all_grid_global_rad_data.variables["lat"].shape[0]
        lon_index = nearest_index % all_grid_global_rad_data.variables["lat"].shape[0]
        measurement_value = all_grid_global_rad_data.variables["SIS"][:][
            0, lat_index, lon_index
        ]
        return measurement_value

    def fetch_measurements(
        self, max_hour_age_of_measurement: int = MAX_AGE_HOURS_OF_GLOBAL_RAD_DATA):
        """
        This method fetches DWD Global Radiation data from DWD OpenData servers.

        Parameters:
        max_hour_age_of_measurement:
        This parameter defines the maximum age in hours, for which
        global radiation measurement data shall be retrieved. The data provided by DWD is not actual
        measurement data, but full-grid sattelite data. Every 15min a new file is put on the DWD
        servers. The history on the http file share goes back multiple days. As a programmer you
        should adapt the queried history to your needs. If you want to record long term data,
        use this method as a basis for persisting the data into an external database.
        Use this parameter with caution, with every added hour 4 more full-grid files
        have to be downloaded and analyzed.
        The higher you choose this number, the longer the run time of your fetch operation will be.
        A reasonable default is 3h set by the MAX_AGE_HOURS_OF_GLOBAL_RAD_DATA constant.
        """
        current_date = datetime.now(dtbase.UTC)
        self.last_measurement_fetch_date = current_date
        matching_files = utils.get_matching_dwd_globalrad_data_files(
            current_date, max_hour_age_of_measurement)
        # Implementing measurement health check
        if not matching_files:
            self.measurement_health_state = 'red'
        else:
            # Check if the most recent file_time is more than 1 hour behind current_date
            latest_file_time = max(file_time for _, file_time in matching_files)
            if (current_date - latest_file_time).total_seconds() > 3600:
                self.measurement_health_state = 'yellow'
            else:
                self.measurement_health_state = 'green'
        for file, file_time in matching_files:
            self.process_file(file, file_time)

    def process_file(self, file, file_time):
        """
        Process each data file for all locations.
        """
        all_grid_global_rad_data = utils.load_sis_data(file)
        for location in self.locations:
            self.process_location(location, all_grid_global_rad_data, file_time)

    def process_location(self, location, all_grid_global_rad_data, file_time):
        """
        Process each location to handle its measurement updates.
        """
        if not location.measurements:
            self.initialize_measurement_for_location(location, all_grid_global_rad_data)
        self.update_measurement_for_location(location, all_grid_global_rad_data, file_time)

    def initialize_measurement_for_location(self, location, all_grid_global_rad_data):
        """
        Initializes measurement for a location based on the nearest grid point.
        """
        latitude, longitude = location.latitude, location.longitude
        grid_data = self._get_grid_data(all_grid_global_rad_data)
        (nearest_index, nearest_distance, grid_latitude, grid_longitude
         )= self._get_nearest_grid_point(latitude, longitude, grid_data)
        measurement = Measurement(grid_latitude, grid_longitude, nearest_distance, nearest_index)
        location.measurements = [measurement]

    def update_measurement_for_location(self, location, all_grid_global_rad_data, file_time):
        """
        Updates the measurement for a given location.
        """
        measurement = location.measurements[0]
        sis_value = self._get_measurement_value_from_loaded_data(
            all_grid_global_rad_data, measurement.nearest_index)
        measurement.add_measurement_value(file_time.timestamp(), sis_value)
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
        self.last_forecast_fetch_date = current_date
        all_grid_forecasts, _actualhoursbehind = utils.load_forecast_dataset(
            current_date
        )
        # Check forecast data availability and timeliness
        if utils.is_dataset_empty(all_grid_forecasts):
            self.forecast_health_state = 'red'
            return  # Stop processing as no data is available

        # Check the timeliness of the data
        if _actualhoursbehind > 1:
            self.forecast_health_state = 'yellow'
        else:
            self.forecast_health_state = 'green'

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

            location.forecasts.append(forecast)
