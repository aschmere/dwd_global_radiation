from setuptools import setup, find_packages

setup(
    name='dwd-global-radiation',
    version='0.1.2-b6',
    packages=find_packages(),
    description='Access and analyze DWD global radiation data and forecasts',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/aschmere/dwd-global-radiation',
    author='Arno Schmerer',
    author_email='arno@schmerer.de',
    license='MIT',
    install_requires=[
        'beautifulsoup4>=4.12.3',
        'netCDF4>=1.6.5',
        'numpy>=1.26.4',
        'pytz>=2024.1',
        'Requests>=2.31.0',
        'tabulate>=0.9.0',
        'tzlocal>=5.2',
        'xarray>=2024.3.0'
    ],
    classifiers=[
        'Development Status :: 4 - Beta',  # Change as appropriate
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.12',
    ],
    keywords=('weather meteorology radiation solar forecasting DWD data environmental data climate '
              'studies solar energy forecasting'),
)
