"""Central registry of DWD satellite radiation products.

Each :class:`RadiationProduct` bundles together the per-product details
(NetCDF variable name, filename regexes, base URLs, display labels) that
were previously hardcoded throughout the package. Internal functions
look up product metadata here via ``PRODUCTS[code]`` rather than
embedding SIS-specific strings.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RadiationProduct:
    """Metadata describing one of DWD's satellite radiation products."""

    code: str
    nc_variable: str
    measurement_filename_regex: str
    measurement_filename_capture_regex: str
    measurement_base_url: str
    forecast_base_url: Optional[str] = None
    label_de: str = ""
    label_en: str = ""

    @property
    def has_forecasts(self) -> bool:
        return self.forecast_base_url is not None


PRODUCTS = {
    "SIS": RadiationProduct(
        code="SIS",
        nc_variable="SIS",
        measurement_filename_regex=r"^SISin\d{12}DEv3\.nc$",
        measurement_filename_capture_regex=r"SISin(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})DEv3\.nc",
        measurement_base_url="https://opendata.dwd.de/weather/satellite/radiation/sis/",
        forecast_base_url="https://opendata.dwd.de/weather/satellite/radiation/sis/SISfc",
        label_de="SIS Wert in W/m²",
        label_en="SIS Value in W/m²",
    ),
}
