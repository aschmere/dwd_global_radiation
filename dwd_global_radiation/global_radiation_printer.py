"""
global_radiation_printer.py

This module provides functions and classes for printing the data related to
global radiation forecasts and measurements. It is part of the GlobalRadiation
package and is responsible for the formatted output of the data, ensuring clear
and readable presentation.

Classes:
    IndentConfig: Handles indentation settings for pretty-printing data outputs.
    FormatConfig: Encapsulates formatting details such as date/time format and
        local timezone.
    PrintConfig: Class for setting configuration parameters for the global
        radiation print service.

Functions:
    print_header(title): Prints the header for the output.
    print_measurements(measurements, config): Prints the measurements data.
    print_forecasts(forecasts, config): Prints the forecasts data.
    print_single_measurement(measurement, config): Prints a single measurement
        with configuration details.
    print_tabulated_data(data_entries, config): Prints data entries (either
        forecast entries or measurement values) in a tabulated format.
    print_single_forecast(forecast, config): Prints a single forecast with
        configuration details.
    get_language_details(language): Returns the title, labels, and date-time
        format based on the specified language.

The module separates the printing logic from the core data management, adhering
to the Single Responsibility Principle (SRP). This makes the codebase more
modular, maintainable, and easier to understand.
"""

from dataclasses import dataclass, field
from datetime import datetime
from string import Template

from tabulate import tabulate


@dataclass
class IndentConfig:
    """Handles indentation settings for pretty-printing data outputs."""
    indent: str = "    "
    sub_indent: str = "        "

@dataclass
class FormatConfig:
    """Encapsulates formatting details such as date/time format and local timezone."""
    dt_format: str
    local_tz: str

@dataclass
class PrintConfig:
    """Class for setting configuration parameters for the global radiation print service."""
    labels: dict
    format_config: FormatConfig
    indent_config: IndentConfig = field(default_factory=IndentConfig)

def print_header(title):
    """Prints the header for the output."""
    print("=" * len(title))
    print(title)
    print("=" * len(title))

def print_measurements(measurements, config):
    """Prints the measurements data."""
    print(f"{config.indent_config.indent}{config.labels['measurements']}:")
    for measurement in measurements:
        print_single_measurement(measurement, config)

def print_forecasts(forecasts, config):
    """Prints the forecasts data."""
    print(f"{config.indent_config.indent}{config.labels['forecasts']}:")
    for forecast in forecasts:
        print_single_forecast(forecast, config)

def print_single_measurement(measurement, config):
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
        print_tabulated_data(measurement.measurement_values, config)

def print_tabulated_data(data_entries, config):
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
            entry.sis,
        ]
        for entry in data_entries
    ]

    table_output = tabulate(
        table,
        headers=[config.labels["timestamp"], config.labels["sis"]],
        tablefmt="grid",
    )

    table_output = "\n".join(
        [f"{config.indent_config.sub_indent}{line}" for line in table_output.splitlines()]
    )

    print(table_output)

def print_single_forecast(forecast, config):
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
        print_tabulated_data(forecast.entries, config)

def get_language_details(language):
    """
    Returns the title, labels, and date-time format based on the specified language.
    """
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
