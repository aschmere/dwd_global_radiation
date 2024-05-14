"""Module providing helper functions for the dwd-global-radiation main module"""
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import calendar
import re
from urllib.error import URLError
import requests
import numpy as np
import xarray as xr
from bs4 import BeautifulSoup
# pylint: disable=no-name-in-module
from netCDF4 import Dataset
# pylint: enable=no-name-in-module
import pytz

MAX_HOURS_TO_GO_BACK=10
HOURLY_MINUTE_TO_FETCH_NEW_FILE=15
DWD_GLOBAL_RAD_DATA_BASE_URL='https://opendata.dwd.de/weather/satellite/radiation/sis/'

@dataclass
class FileParsingContext:
    """
    A context container for storing and passing data required for parsing files
    containing global radiation data from DWD (Deutscher Wetterdienst).

    Attributes:
        regex_pattern (str): Regular expression pattern used to filter file names based
                             on expected naming conventions.
        regex_pattern_measurement_time (str): Regular expression pattern used to extract
                                              date and time information from file names.
        current_utc_date (datetime): The reference UTC date and time for calculating
                                     the age of the data files.
        max_age_hours (int): Maximum age, in hours, that a data file can be to still be considered
                             valid. Files older than this threshold will be ignored.
        file_links (list): List to store URLs of the files that match the criteria.
        file_times (list): List to store datetime objects corresponding to the times
                           extracted from the file names.

    This context is used to encapsulate the necessary state and parameters used during the
    file processing in functions such as `process_response_content`, `parse_pre_text`, and
    `process_line`. It helps streamline the passage of multiple related parameters between
    these functions and simplifies managing their state.
    """
    regex_pattern: str
    regex_pattern_measurement_time: str
    current_utc_date: datetime
    max_age_hours: int
    file_links: list
    file_times: list

def get_current_solar_radiation_forecast_url(hourstogoback, current_date):
    """
    Generates a URL to fetch the solar radiation forecast from the DWD (Deutscher Wetterdienst)
    OpenData server. The URL is constructed based on a specified `current_date` adjusted by
    a certain number of hours to go back (`hourstogoback`). This function handles edge cases
    around the beginning of months, years, and midnight hours to correctly wrap the date
    and time for the forecast URL.

    Parameters:
        hourstogoback (int): Number of hours to subtract from `current_date` to get the
                             desired date and time for the forecast.
        current_date (datetime.datetime): The current datetime from which the forecast
                                          will be calculated.

    Returns:
        str: A string representing the full URL to access the forecast data for the calculated
             datetime.

    The URL is formulated to access specific hourly forecasts based on satellite data. The function
    adjusts the `current_date` by subtracting the hours specified by `hourstogoback`. It handles
    special cases at the start of months and years where the date and time would otherwise roll
    over incorrectly. Adjustments are made to ensure the date and time specified in the URL
    represent a valid and existing time, particularly just before the rollover of the day, month,
    or year at midnight. The URL follows a specific pattern to match the directory and file
    structure on the DWD OpenData server.
    """
    target_date=current_date - timedelta(hours=hourstogoback)
    target_year=target_date.year
    target_month=target_date.month
    target_day=target_date.day
    target_hour=target_date.hour
    target_minute=target_date.minute

    if (target_month == 1 and target_day == 1 and target_hour == 0 and
        target_minute < HOURLY_MINUTE_TO_FETCH_NEW_FILE):
        target_year= target_year - 1
        target_month=12
        target_day=31
        target_hour=23
    elif target_day == 1 and target_hour == 0 and target_minute < HOURLY_MINUTE_TO_FETCH_NEW_FILE:
        target_month=target_month -1
        target_hour=23
        if target_month in [1,3,5,7,8,10,12]:
            target_day=31
        elif target_month in [4,6,9,11]:
            target_day=30
        else:
            if calendar.is_leap():
                target_day=29
            else:
                target_day=28
    elif target_hour == 0 and target_minute < HOURLY_MINUTE_TO_FETCH_NEW_FILE:
        target_day = target_day - 1
        target_hour=23
    elif target_minute < HOURLY_MINUTE_TO_FETCH_NEW_FILE:
        target_hour=target_hour - 1

    str_target_year=str(target_year)
    str_target_month=f"{target_month:02d}"
    str_target_day=f"{target_day:02d}"
    str_target_hour=f"{target_hour:02d}"

    base_url='https://opendata.dwd.de/weather/satellite/radiation/sis/SISfc'
    url_suffix='_fc%2B18h-DE.nc#mode=bytes'

    url = (base_url + str_target_year + str_target_month + str_target_day +
           str_target_hour + url_suffix)

    return url

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points on the Earth's surface given their
    latitude and longitude using the Haversine formula.

    Parameters:
        lat1 (float): Latitude of the first point in decimal degrees.
        lon1 (float): Longitude of the first point in decimal degrees.
        lat2 (float): Latitude of the second point in decimal degrees.
        lon2 (float): Longitude of the second point in decimal degrees.

    Returns:
        float: The distance between the two points in kilometers.

    Notes:
        The Haversine formula is an equation important in navigation, giving distances between
        two points on a sphere from their longitudes and latitudes. It is a special case of a
        more general formula in spherical trigonometry, the law of haversines, relating the
        sides and angles of spherical "triangles".

        This implementation assumes the Earth is a sphere to calculate
        the arc between the two points.
        While this is not perfectly accurate (the Earth is slightly ellipsoidal),
        it remains a close and efficient approximation for most purposes.

    Example:
        >>> haversine(48.8566, 2.3522, 34.0522, -118.2437)
        9127.79137856901  # Distance from Paris, France to Los Angeles, USA in kilometers
    """
    # Radius der Erde in Kilometern
    r = 6371.0

    # Umwandlung von Grad in Radian
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

    # Differenz der Koordinaten
    dlon = lon2 - lon1
    dlat = lat2 - lat1

    # Haversine-Formel
    a = np.sin(dlat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2.0)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    distance = r * c
    return distance

def load_forecast_dataset(current_date, max_hours_to_go_back=MAX_HOURS_TO_GO_BACK):
    """
    Attempts to load the forecast dataset for a given number of hours
    going back from the current date.

    Args:
        current_date (datetime): The current date and time.
        max_hours_to_go_back (int): The maximum number of hours to attempt loading data for.

    Returns:
        tuple: A tuple containing the dataset and the hour offset, or (None, None)
        if unable to load.

    Raises:
        RuntimeError: If all attempts fail, the last exception is raised.
    """
    last_exception = None
    for i in range(max_hours_to_go_back):
        url = get_current_solar_radiation_forecast_url(i, current_date)
        try:
            ds = xr.open_dataset(url)
            return ds, i
        except (FileNotFoundError, PermissionError, URLError, OSError) as e:
            last_exception = e

    if last_exception:
        # We keep the try/except code block for now as a sceleton, but actually we do not want
        # to stop the program on this kind of exception. Justification: The program should handle 
        # the unavailability of the underlying cloud service and move on gracefully.
        # It's up to the class service health attributes of class GlobalRadiation to signal the 
        # the end user of this library, that there is a problem with the cloud service.
        pass

    return None, None

def get_forecast_issuance_timestamp_from_netcdf_history_attrib(history):
    """
    Extracts the forecast issuance timestamp from the 'history' attribute of a NetCDF file,
    which is formatted in a specific string pattern, and converts it to a UNIX timestamp.

    Parameters:
        history (str): The 'history' attribute string from a NetCDF file which includes
                       detailed information about the file's creation and processing steps.
                       The date-time information is embedded in this string and formatted as
                       'YYYY-MM-DD,HH:MM'.

    Returns:
        float: The UNIX timestamp representing the UTC time at which the forecast was issued.

    Example:
        history = "Generated by model run at 2021-03-15,12:25 processed on 2021-03-16"
        timestamp = get_forecast_issuance_timestamp_from_netcdf_history_attrib(history)
        print(timestamp)  # Outputs the UNIX timestamp for '2021-03-15,12:25' UTC

    Notes:
        The function assumes that the history attribute contains a date-time string formatted
        as 'YYYY-MM-DD,HH:MM'. It is designed to convert this to a datetime object in UTC and
        then to a UNIX timestamp. This timestamp can be used to reference the exact time of the
        forecast's issuance in systems that use UNIX time for scheduling or data alignment.
    """
    pattern = r'(\d{4}-\d{2}-\d{2},\d{2}:\d{2})'
    match = re.search(pattern, history)
    dt_object = datetime.strptime(match[0], '%Y-%m-%d,%H:%M')
    # Setzen der Zeitzone auf UTC
    dt_object_utc = dt_object.replace(tzinfo=timezone.utc)

    # Konvertieren des datetime-Objekts in einen Unix-Zeitstempel
    timestamp = dt_object_utc.timestamp()

    return timestamp

def get_matching_dwd_globalrad_data_files(current_utc_date=None, max_age_hours=None):
    """
    Retrieves and filters files from the DWD Global Radiation Data Base URL based on the
    provided regex pattern and the age limit defined by `max_age_hours` relative to the
    `current_utc_date`. It returns a sorted list of files that match the criteria.

    Parameters:
        current_utc_date (datetime.datetime, optional): The reference date and time in UTC
            from which the maximum age of the files is calculated. If None, the function
            will use the current UTC time.
        max_age_hours (int, optional): The maximum age in hours for the files to be considered
            relevant. Files older than this age relative to `current_utc_date` will not be included.
            If None, no age filter will be applied.

    Returns:
        list of tuples: A sorted list of tuples, where each tuple contains the URL and the
            UTC timestamp of a file that matches the criteria. The list is sorted by the timestamps
            in descending order. Returns an empty list if no files match the criteria or if there's
            an error during retrieval.
    Example:
        >>> from datetime import datetime, timedelta
        >>> current_utc_date = datetime.utcnow()
        >>> max_age_hours = 24
        >>> files = get_matching_dwd_globalrad_data_files(current_utc_date, max_age_hours)
        >>> print(files)  # This may print a list of file URLs with their timestamps.

    Notes:
        This function assumes that the files at the specified base URL conform to specific naming
        conventions suitable for regex matching as defined in the function's parameters. It utilizes
        a context object (`FileParsingContext`) to pass state across helper functions for better
        modularity and readability.
    """
    regex_pattern = r'^SISin\d{12}DEv3\.nc$'
    regex_pattern_measurement_time = r'SISin(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})DEv3\.nc'
    response = requests.get(DWD_GLOBAL_RAD_DATA_BASE_URL, timeout=(10, 10))
    if response.status_code == 200:
        context = FileParsingContext(
            regex_pattern,
            regex_pattern_measurement_time,
            current_utc_date,
            max_age_hours,
            [],
            []
        )
        file_links, file_times = process_response_content(response.content, context)
        if file_links:
            sorted_files = sorted(zip(file_links, file_times), key=lambda x: x[1], reverse=True)
            return sorted_files
        return []
    print("Error:", response.status_code)
    return []

def process_response_content(content, context):
    """
    Processes the HTML content retrieved from a URL to extract file links based on predefined
    criteria stored within a context object. This function parses the HTML, identifies `<pre>` tags,
    and extracts their contents for further processing.

    Parameters:
        content (str): HTML content as a string from which file data needs to be extracted.
        context (FileParsingContext): An object containing all necessary data and configurations
                                      for processing, including regex patterns and storage lists
                                      for file links and their timestamps.

    Returns:
        tuple: Returns two lists, one of file links and the other of their respective timestamps,
               both of which meet the specified criteria within the context object.
    """

    soup = BeautifulSoup(content, 'html.parser')
    pre_tags = soup.find_all('pre')
    for pre_tag in pre_tags:
        pre_text = pre_tag.get_text()
        parse_pre_text(pre_text, context)
    return context.file_links, context.file_times

def parse_pre_text(pre_text, context):
    """
    Parses text from `<pre>` tags to extract lines that are potentially valid file entries.
    Each line is processed to check against the context's regex pattern and other conditions.

    Parameters:
        pre_text (str): The textual content extracted from a `<pre>` tag.
        context (FileParsingContext): The context object carrying regex patterns, date-time info,
                                      and storage for valid file links and timestamps.
    """
    lines = pre_text.strip().split('\n')
    for line in lines:
        process_line(line, context)

def process_line(line, context):
    """
    Analyzes a single line from the pre-formatted text to determine if it matches the criteria
    for a valid file link. 
    If valid, extracts the date and time info, checks against the maximum age,
    and stores the link and timestamp if all conditions are met.

    Parameters:
        line (str): A single line of text potentially containing a file link.
        context (FileParsingContext): An object containing regex patterns, maximum age limits,
                                      the current reference date-time, and lists for storing
                                      valid file links and timestamps.

    Returns:
        None: This function directly modifies the context object based on the line's validity
              and relevancy as per the defined criteria.
    """
    parts = line.strip().split()
    if len(parts) < 3 or parts[0].endswith('/'):
        return
    href = parts[0]
    if not re.match(context.regex_pattern, href):
        return
    try:
        match = re.match(context.regex_pattern_measurement_time, href)
        year, month, day, hour, minute = map(int, match.groups())
        utc_file_date = datetime(year, month, day, hour, minute, tzinfo=pytz.UTC)
        if context.max_age_hours is not None and (context.current_utc_date - utc_file_date >
                                                  timedelta(hours=context.max_age_hours)):
            return
        context.file_links.append(href)
        context.file_times.append(utc_file_date)
    except (ValueError, AttributeError):
        pass  # Ignore lines that do not have a valid date/time format

def load_sis_data(filename):
    """
    Constructs a full URL for a given filename and loads the dataset from this URL using the Dataset
    class. The URL is constructed by appending a filename to the predefined base URL and adding a
    suffix to specify the mode of access.

    Parameters:
        filename (str): The name of the file to be loaded, which should
        be located at the DWD_GLOBAL_RAD_DATA_BASE_URL.

    Returns:
        Dataset: An object representing the loaded dataset, initialized with data
        from the constructed URL.


    Example:
        >>> dataset = load_sis_data("SISin20210101.nc")
        >>> print(dataset)  # Outputs the properties or contents of the dataset, dependent
        on Dataset class implementation.

    Notes:
        The function assumes the existence of a global constant 'DWD_GLOBAL_RAD_DATA_BASE_URL'
        which contains the base URL to which filenames and URL parameters are appended.
        The `url_suffix` is used to specify that the data should be accessed in byte mode,
        which is necessary for certain types of binary data files.
    """
    url_suffix="#mode=bytes"
    final_url=DWD_GLOBAL_RAD_DATA_BASE_URL + filename + url_suffix
    ds = Dataset(final_url)
    return ds

def is_dataset_empty(dataset):
    """
    Determine if the provided xarray Dataset is empty.

    This function checks if the dataset is None or if all dimensions within the dataset
    have a length of zero, indicating that there are no data entries present.

    Parameters:
    dataset (xarray.Dataset or None): The dataset to check for emptiness.

    Returns:
    bool: True if the dataset is None or all dimensions are empty, False otherwise.
    """
    if dataset is None:
        return True  # Treat None as an empty dataset
    return all(len(dataset[dim]) == 0 for dim in dataset.dims)
