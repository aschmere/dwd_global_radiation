DISCLAIMER: This project is a private open source project and is not affiliated with the German public meteorology service institute "Deutscher Wetterdienst" (DWD). However, it uses its publicly available data interfaces. 

# Summary
The DWD Global Radiation Observation and Forecast Data Library is a python package, which provides convenient access to forecast and observation data regarding Surface Incoming Solar Radiation (SIS) [[1]](#R1) or also known as "Global Horizontal Irradiance" (GHI) issued by the German meteorology service institute "Deutscher Wetterdienst" (DWD). The data currently used by this package covers roughly a geographical area of Germany, Austria and Switzerland. SIS or GHI is the most important input variable for determining the electrical output of photovoltaic systems. Therefore this data is particularly useful in "Smart Home"-scenarios, if you want to correlate the actual output of your photovoltaic system with measured SIS or can even help forecasting this output based on SIS forecast data. SIS data can also be helpful in regulating room heating systems, as solar irradiance can have a big impact on the room temperature as well.


For more details regarding Solar irradiance terminology and the global radiation data provided by DWD via its "Open Data" server, see [[2]](#R2).
For details on radiation terminology you can consult various resources, e.g. [[3]](#R3) and for SIS specifically [[1]](#R1).

# Installation
<ins>Note:</ins>
Complying with typical best practices for using Python it is highly recommended to create and use a python virtual environement [[4]](#R4) as installation target.
```
python3 -m pip install dwd_global_radiation
```
The listed installation command will usually install all required dependant Python packages.
As of the current version of this package the following Python packages are required:
```
beautifulsoup4==4.12.3
netCDF4==1.6.5
numpy==1.26.4
pytz==2024.1
Requests==2.31.0
tabulate==0.9.0
tzlocal==5.2
xarray==2024.3.0
```
<ins>Note:</ins>The above listed versions of dependant Python packages reflect the versions, on which this package was developed and tested. Typically you would expect, that later versions of these packages will be compatible as well. Earlier versions might also be compatible. The Python version, with which this package
was developed and tested, is 3.12.3.

The workstation, on which you use Python along with this package, needs internet access, specifically via https protocol to the Open Data server of the DWD [[5]](#R5) in order to retrieve global radiation forecasts and observations.

# Usage

## Import the Module
```
import dwd_global_radiation as dgr
```

## Instantiate Global Radiation Object
After successful import of the module a main object must be instantiated from class GlobalRadiation.
```
objGlobalRadiation=dgr.GlobalRadiation()
```

## Add Location
The object instantiated from the GlobalRadiation class in the previous step is initially empty and needs to be filled with data in order to serve a meaningful purpose.
In the first step we need to add a location, for which we want to gather either obversational or forecast data (or both). For a location to be added you need to have 3 parameters at your hand:
- The name of your location:
  This can be any name of your choice, e.g. "My Home Location"
- The latitude and longitude of your location: 
  These parameters are of type "float" and can be easily retrieved for any given location via Google Maps. We will use Berlin coordinates as an example (latitude: 52.5200, longitude: 13.4050 )

Once you have determined these parameters, you can add a location to your main object like outlined in the following code example:
```
objGlobalRadiation.add_location(name="My Home Location", latitude=52.5200, longitude=13.4050)
```

You can check, whether the location has been correctly added to your object, with the following code line:
```
objGlobalRadiation.locations
```
Example Output would be:
```
[Location(name=My Home Location, latitude=52.52, longitude=13.405, measurements=0 items, forecasts=0 items)]
```
You see from the output, that the location has been added, but there are not yet any measurements or forecasts. Note that you can add more than 1 location in order to gather measurement and forecast data, but in the following examples we will just use 1 location.
In the next steps we will fetch measurement and forecast data from the DWD OpenData servers. As outlined in the documentation of the DWD listed in the "Summary"-section, the format of the data is NetCDF full grid data. Hence adding locations to your main object will only have limited impact on compute performance/capacity, as the data is gathered for an aread of Germany/Austria/Switzerland anyway. The computing done behind the scenes is "just" to assign the nearest grid point and its forecast/measurement values to each location.
## Fetch Data from DWD OpenData Servers
### Introduction to DWD Global Radiation Measurement and Forecast Data

Strictly speaking, the term "measurements" is misleading in the context of the gathered DWD data, as the "measurements" are based on sattelite observations. However, the main advantage of satellite-based global radiation data is the comprehensive geographical coverage and the consistent retrieval of the data. The density of data cannot be achieved with pyranometer-based measurements and the accuracy of sattelite-observed global radiation data is 5 W/m2 (15 W/m2 daily average) [6].
The DWD provides via its OpenData servers observational full-grid data in a frequency of 15 minutes. The default measurement period, for which the following method retrieves this measurement data, reaches 3h into the past compared to the current timestamp at the time of executing the data retrieval function "fetch_measurements()".
Note, that the historical "data buffer" of the DWD OpenData observations is currently about 2 days [[7]](#R7), but retrieving the whole history cannot be recommended performance-wise, as with every hour going back in history 4 full-grid files must be downloaded, opened and analyzed. So the more you go back in history, the significantly longer the run time of your "fetch_measurements" call will be.<br><br>
Forecast data is fetched in a similar way to measurement data. <br>
However, there are some differences:
- You don't need to care about, how much to go back in history. Forecast data only applies to future points in time. Essentially the routines of this package filter those forecasts, which may already lie 1 or 2 hours back in time. 
- Depending on the point of time of your query, the DWD forecast data will reach 16 to 17 hours into the future.
- The forecast data has an hourly granularity and will also be updated by DWD once an hour.
- This means, that slightly depending on the current time of your forecast data retrieval you will either get 16 or 17 values of forecast.
- Each individual value of the weather forecast reflects an hourly average, not an instantaneous value.

Further details regarding the characteristics of Global Radiation forecasts and measurements using DWD Global Radiation Open Data can be looked up under [[2]](#R2).

### Fetch and Access Global Radiation Measurement Data
Listed below are sample calls of the fetch_measurements() function:
```
# Getting 3h of history for DWD Global Radiation Sattelite Observations
objGlobalRadiation.fetch_measurements()
```

To verify and check the retrieved measurement data:
```
>>> objGlobalRadiation
GlobalRadiation(locations=[Location(name=My Home Location, latitude=52.52, longitude=13.405, measurements=1 item, forecasts=0 items)], last_measurement_fetch_date=datetime.datetime(2024, 5, 14, 20, 43, 12, 610376, tzinfo=datetime.timezone.utc), last_forecast_fetch_date=None, measurement_health_state='green', forecast_health_state='green')
```
Note from the output, that objGlobalRadiation now has 1 location with 1 measurement item. The current_date of a location object is set to the date of the last data retrieval (either fetch_measurements or fetch_forecasts). From the object model, think of the measurements list object as the number of analysis runs. As we have called the fetch_measurements() function only once, there is only 1 item in the measurements list. But we will see below, that of course we have multiple "measurement entries", as 3h of measurements should result in about 10-11 entries (quarterly-hour measurement granularity) depending on the time of your query.
You can access the actual measurement entries as follows:
```
>>> # Getting the first level of measurements info
>>> objGlobalRadiation.locations[0].measurements[0]
>>> Measurement(grid_latitude=52.5, grid_longitude=13.399999618530273, distance=2.249000072479248, nearest_index=28898, measurement_values=Count: 11)
```
The 1st level of measurement info returns the following information:
- grid_latitude and grid_longitude of the nearest netCDF grid point in the underlying netCDF grid array
- The distance in kilometers(km) of the provided location to the nearest found grid point. In our example this distance is 1.631 km.
- nearest_index is the index of the nearest found grid point in the underlying one-dimensional array.
- The property measurement_values only "previews" the item count, not yet the data itself.

The 2nd level of measurement information can be accessed as follows:
```
>>> objGlobalRadiation.locations[0].measurements[0].measurement_values
[MeasurementEntry(timestamp=1715718600.0, sis=0), MeasurementEntry(timestamp=1715717700.0, sis=0), MeasurementEntry(timestamp=1715716800.0, sis=0), MeasurementEntry(timestamp=1715715900.0, sis=0), MeasurementEntry(timestamp=1715715000.0, sis=0), MeasurementEntry(timestamp=1715714100.0, sis=0), MeasurementEntry(timestamp=1715713200.0, sis=0), MeasurementEntry(timestamp=1715712300.0, sis=0), MeasurementEntry(timestamp=1715711400.0, sis=0), MeasurementEntry(timestamp=1715710500.0, sis=15), MeasurementEntry(timestamp=1715709600.0, sis=49)]

```

The 2nd leval of measurement access already provides a detailed overview of the actual measurements (list of class "MeasurementEntry"). Each MeasurementEntry has a timestamp and a sis property. Timestamp is the Unix-timestamp belonging to the measurement value and "sis", as explained already in the "Summary"-section, stands for "Solar Irradiance Shortwave Radiation" and is the measured value in W/m2 itself at the point of time of the timestamp + 11 minutes delay according to the DWD. So a timestamp of 7.30am actually contains the measured value of approximately 7.41 am. This is due to the scan delay of the sattelite data, see [[2]](#R2) for details.

Finally the 3rd level of measurement access provides the access to a single measurement value and is achieved via the following code line:
```
>>> # Getting the latest measurement value of the current measurement
>>> objGlobalRadiation.locations[0].measurements[0].measurement_values[0]
MeasurementEntry(timestamp=1715718600.0, sis=0)
>>> # Accessing the timestamp only as Unix timestamp
>>> objGlobalRadiation.locations[0].measurements[0].measurement_values[0].timestamp
1715718600.0
>>> # Convert timestamp to datetime object of local timezone
>>> import tzlocal
>>> local_tz = tzlocal.get_localzone()
>>> from datetime import datetime
>>> datetime.fromtimestamp(objGlobalRadiation.locations[0].measurements[0].measurement_values[0].timestamp,local_tz)
datetime.datetime(2024, 5, 14, 22, 30, tzinfo=zoneinfo.ZoneInfo(key='Europe/Berlin'))
>>> # Accessing the SIS value of the latest measurement
>>> objGlobalRadiation.locations[0].measurements[0].measurement_values[0].sis
0
```
### Fetch and Access Global Radiation Forecast Data
Fetching and Accessing Global Radiation forecast data is achieved by the following example code. 
```
>>> objGlobalRadiation.fetch_forecasts()
>>> GlobalRadiation(locations=[Location(name=My Home Location, latitude=52.52, longitude=13.405, measurements=1 item, forecasts=1 item)], last_measurement_fetch_date=datetime.datetime(2024, 5, 14, 20, 51, 20, 765122, tzinfo=datetime.timezone.utc), last_forecast_fetch_date=datetime.datetime(2024, 5, 14, 20, 56, 34, 971041, tzinfo=datetime.timezone.utc), measurement_health_state='green', forecast_health_state='green')
```
As you can see from the `objGlobalRadiation` output above, it displays `green` as the `forecast_health_state` and the attribute `last_forecast_fetch_date` has a datetime object with the time, when the `fetch_forecasts()` method was last run. These are all signs, that fetching forecasts has been successful.
In the next step we will dig deeper into retrieval of the fetched forecast data:
```
>>> objGlobalRadiation.locations[0].forecasts[0]
Forecast(issuance_time=1715716800.0, grid_latitude=52.5, grid_longitude=13.4, distance=2.249, entries=17, metadata=status 'populated')
```
In this level of access we see already, that we have 17 forecast entries, which looks good, as the forecasts go roughly 16 to 17 hours ahead of the current time with an hourly forecast granularity. Issuance time is the time, when DWD published or updated the forecast. It gives you an idea, how old the forecast is. With a functional DWD Open Data service at full availability the issuance time should be not more than 1h behind the current time, as the forecast is updated hourly.
Next step will be retrieve actual forecast data by digging deeper into the object hierarchy:
```
>>> objGlobalRadiation.locations[0].forecasts[0].entries
[ForecastEntry(timestamp=1715720400.0, sis=0.00024414062), ForecastEntry(timestamp=1715724000.0, sis=0.00048828125), ForecastEntry(timestamp=1715727600.0, sis=0.027832031), ForecastEntry(timestamp=1715731200.0, sis=0.0), ForecastEntry(timestamp=1715734800.0, sis=0.0), ForecastEntry(timestamp=1715738400.0, sis=0.0), ForecastEntry(timestamp=1715742000.0, sis=0.005859375), ForecastEntry(timestamp=1715745600.0, sis=17.42627), ForecastEntry(timestamp=1715749200.0, sis=113.72803), ForecastEntry(timestamp=1715752800.0, sis=259.56006), ForecastEntry(timestamp=1715756400.0, sis=420.26416), ForecastEntry(timestamp=1715760000.0, sis=572.041), ForecastEntry(timestamp=1715763600.0, sis=699.666), ForecastEntry(timestamp=1715767200.0, sis=790.8164), ForecastEntry(timestamp=1715770800.0, sis=839.0547), ForecastEntry(timestamp=1715774400.0, sis=840.1162), ForecastEntry(timestamp=1715778000.0, sis=795.8408)]
```
We see from the output above, that we have a list of 17 items of class `ForecastEntry`, each with a named tuple of `timestamp` and `sis`. `timestamp` is the time in future (maximum 17 hours ahead of current time), for which the forecast is valid, and `sis` is the actually forecasted global radiation value in W/m2.
The targeted access to specific forecast entries follows the same coding principles as already elaborated for the global radiation measurements above and hence this is not demonstrated for the forecasts again.

## Print Service
Once you have fetched all measurement or forecast data from DWD Open Data servers, you may find it convenient in order to familiarize yourself with this library or for troubleshooting and analysis purposes to just dump the gathered data in an interactive console. The following code line demonstrates the usage of the print service along with an example output:
```
>>> objGlobalRadiation.print_data()
=========================================================
DWD Forecast and Observation Data from Selected Locations
=========================================================
Location: My Home Location
     Latitude: 52.52
     Longitude: 13.405
     Measurements:
        Grid Latitude: 52.5
        Grid Longitude: 13.4
        Distance of the location to the nearest gridpoint in km: 2.249
        +---------------------+---------------------+
        | Timestamp           |   SIS Value in W/m2 |
        +=====================+=====================+
        | 2024-05-15 12:45:00 |                 857 |
        +---------------------+---------------------+
        | 2024-05-15 12:30:00 |                 854 |
        +---------------------+---------------------+
        | 2024-05-15 12:15:00 |                 848 |
        +---------------------+---------------------+
        | 2024-05-15 12:00:00 |                 840 |
        +---------------------+---------------------+
        | 2024-05-15 11:45:00 |                 828 |
        +---------------------+---------------------+
        | 2024-05-15 11:30:00 |                 814 |
        +---------------------+---------------------+
        | 2024-05-15 11:15:00 |                 797 |
        +---------------------+---------------------+
        | 2024-05-15 11:00:00 |                 777 |
        +---------------------+---------------------+
        | 2024-05-15 10:45:00 |                 755 |
        +---------------------+---------------------+
        | 2024-05-15 10:30:00 |                 730 |
        +---------------------+---------------------+
        | 2024-05-15 10:15:00 |                 703 |
        +---------------------+---------------------+
     Forecasts:
        Issuance Time: 2024-05-15 13:00:00
        Grid Latitude: 52.5
        Grid Longitude: 13.4
        Distance of the location to the nearest gridpoint in km: 2.249
        Metadata: {'standard_name': 'downwelling_shortwave_flux_in_air', 'long_name': 'solar surface irradiance', 'units': 'Watt m-2'}
        +---------------------+---------------------+
        | Timestamp           |   SIS Value in W/m2 |
        +=====================+=====================+
        | 2024-05-15 14:00:00 |        823.096      |
        +---------------------+---------------------+
        | 2024-05-15 15:00:00 |        796.442      |
        +---------------------+---------------------+
        | 2024-05-15 16:00:00 |        705.616      |
        +---------------------+---------------------+
        | 2024-05-15 17:00:00 |        567.22       |
        +---------------------+---------------------+
        | 2024-05-15 18:00:00 |        397.645      |
        +---------------------+---------------------+
        | 2024-05-15 19:00:00 |        273.018      |
        +---------------------+---------------------+
        | 2024-05-15 20:00:00 |        120.846      |
        +---------------------+---------------------+
        | 2024-05-15 21:00:00 |         22.1733     |
        +---------------------+---------------------+
        | 2024-05-15 22:00:00 |          0.0263672  |
        +---------------------+---------------------+
        | 2024-05-15 23:00:00 |          0          |
        +---------------------+---------------------+
        | 2024-05-16 00:00:00 |          0.0449219  |
        +---------------------+---------------------+
        | 2024-05-16 01:00:00 |          0.00683594 |
        +---------------------+---------------------+
        | 2024-05-16 02:00:00 |          0.0205078  |
        +---------------------+---------------------+
        | 2024-05-16 03:00:00 |          0.0424805  |
        +---------------------+---------------------+
        | 2024-05-16 04:00:00 |          0          |
        +---------------------+---------------------+
        | 2024-05-16 05:00:00 |          0.0170898  |
        +---------------------+---------------------+
        | 2024-05-16 06:00:00 |         18.5645     |
        +---------------------+---------------------+
```

# References
<a href="https://www.cmsaf.eu/SharedDocs/Literatur/document/2023/saf_cm_dwd_pum_meteosat_hel_sarah_3_3_pdf" id="R1">[1] Product User Manual Meteosat Solar Surface Radiation and Effective Cloud Albedo Climate Data Records SARAH-3<br>
<a href="https://www.dwd.de/DE/leistungen/fernerkund_globalstrahlung_sis/fernerkund_globalstrahlung_sis.html" id="R2">[2] DWD - Product Description on Global Radiation<br>
<a href="https://en.wikipedia.org/wiki/Solar_irradiance" id="R3">[3] Wikipedia - Solar Irradiance: <br>
<a href="https://docs.python.org/3/library/venv.html" id="R4">[4] Python Documentation - venv — Creation of virtual environments<br>
<a href="https://opendata.dwd.de/weather/satellite/radiation/" id="R5">[5] Global Radiation Forecast and Observation Data on the Open Data server of the DWD<br>
<a href="https://www.dwd.de/EN/ourservices/solarenergy/satellite_solarradiation.html" id="R6">[6] DWD - Satellite-based retrieval of surface solar radiation<br>
<a href="https://opendata.dwd.de/weather/satellite/radiation/sis/" id="R7">[7] DWD - Surface Incoming Solar Radiation (SIS) section of the DWD Open Data server<br>















