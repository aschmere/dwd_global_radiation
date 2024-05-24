"""Setup configuration for the dwd_global_radiation package.

This package provides tools to access and analyze DWD (Deutscher Wetterdienst)
global radiation data and forecasts. It is designed for applications in weather forecasting,
climate studies, and solar energy analysis, utilizing libraries like xarray for data handling
and netCDF4 for managing data formats.

Author: Arno Schmerer
License: MIT
"""
from setuptools import setup, find_packages

with open('README.md', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='dwd_global_radiation',
    version='1.0.0rc7',
    packages=find_packages(),
    description='Access and analyze DWD global radiation data and forecasts',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/aschmere/dwd_global_radiation',
    author='Arno Schmerer',
    license='MIT',
    install_requires=[
        'beautifulsoup4>=4.12.3',
        'netCDF4>=1.6.5',
        'numpy>=1.26.0',
        'pytz>=2024.1',
        'requests>=2.31.0',
        'tabulate>=0.9.0',
        'tzlocal>=5.2',
        'xarray>=2024.3.0'
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.12',
        'Topic :: Software Development :: Libraries'
    ],
    keywords=('weather meteorology radiation solar forecasting DWD data environmental data climate '
              'studies solar energy forecasting'),
)
