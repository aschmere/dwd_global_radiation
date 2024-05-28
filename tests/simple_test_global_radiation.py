"""
This example program demonstrates the basic usage of the DWD Global Radiation Observation
and Forecast Data Python Library.
It showcases how to configure and use the library to fetch global radiation data
for specified locations based on configuration settings provided in a coordinates.ini file.

Functions:
    read_configurations_from_file(file_path):
        Reads package path and location data from a given INI configuration file (coordinates.ini).
        It extracts the package path required for
        module imports and a list of locations where radiation data will be collected.

        Parameters:
            file_path (str): The path to the configuration file in INI format.

        Returns:
            tuple: A tuple containing:
                - package_path (str): The file path to the package required for the project.
                - locations (list of tuples): A list where each tuple contains latitude (float),
                  longitude (float), and a descriptive name (str) of a location.

Main Execution:
    When executed as the main program, the module performs the following operations:
        - Measures the runtime of the program from start to finish.
        - Reads the configuration from 'tests/coordinates.ini'
          to obtain necessary paths and location data.
        - Updates the system path with the package path to allow imports from the specified package.
        - Initializes a GlobalRadiation object using the dwd_global_radiation package.
        - Adds each location from the configuration file to the GlobalRadiation object.
        - Fetches radiation forecasts and measurements for the registered locations.
        - Displays the fetched data in German and prints the total execution time of the program.

This example serves to illustrate the practical implementation and operational flow of the
DWD library in a real-world application, guiding users through the process of setting up, fetching,
and displaying radiation data.
"""
import sys
import configparser
import time  # Import the time module
import logging

logging.basicConfig(
    level=logging.DEBUG,  # Set the logging level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Set the log message format
    handlers=[
        logging.StreamHandler(),  # Log to standard output (console)
        logging.FileHandler('global_radiation.log'),  # Additionally log to a file
    ]
)

def read_configurations_from_file(file_path):
    """See module docstring for further information"""
    config = configparser.ConfigParser()
    config.read(file_path)

    # Read package path
    cfg_package_path = config['Package']['path']

    # Read locations
    cfg_locations = []
    location_prefix = "Location"

    for section in config.sections():
        if section.startswith(location_prefix) and section[len(location_prefix):].isdigit():
            cfg_latitude = float(config[section]['latitude'])
            cfg_longitude = float(config[section]['longitude'])
            cfg_name = config[section]['name']
            cfg_locations.append((cfg_latitude, cfg_longitude, cfg_name))

    return cfg_package_path, cfg_locations

if __name__ == '__main__':
    start_time = time.time()  # Record the start time

    # Path to the external file containing configurations
    CONFIG_FILE_PATH = 'tests/coordinates.ini'  # Update with your file path

    # Read configurations from the external file
    main_package_path, main_locations = read_configurations_from_file(CONFIG_FILE_PATH)

    # Update sys.path with the package path
    sys.path.insert(0, main_package_path)

    import dwd_global_radiation

    # Create GlobalRadiation object
    objGlobalRadiation = dwd_global_radiation.GlobalRadiation()

    # Add each location and fetch forecasts
    for lat, lon, loc_name in main_locations:
        objGlobalRadiation.add_location(latitude=lat, longitude=lon, name=loc_name)

    objGlobalRadiation.fetch_forecasts()
    objGlobalRadiation.fetch_forecasts() #test caching
    objGlobalRadiation.fetch_measurements(max_hour_age_of_measurement=1)
    objGlobalRadiation.fetch_measurements(max_hour_age_of_measurement=1) #test caching

    objGlobalRadiation.print_data(language="German")

    end_time = time.time()  # Record the end time
    print(f"Program execution time: {end_time - start_time:.2f} seconds")
    