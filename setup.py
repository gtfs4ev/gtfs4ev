from setuptools import setup, find_packages

setup(
    name="gtfs4ev",          
    version="0.2.1",                  
    description="A Python framework for simulating electric bus operations and charging demand using GTFS data",
    packages=find_packages(),
    long_description = """GTFS4EV is an open-source Python tool for planning public bus electrification using GTFS data. It provides a modular workflow that includes GTFS data pre-processing, fleet operation simulation, and scenario-based charging. Additional features include GTFS data filtering, PV integration potential, ex-post impact analysis, flexible charging strategies, spatial visualization, and dual usage as a CLI or Python library. For more information and examples, see the [GTFS4EV GitHub repository](https://github.com/gtfs4ev/gtfs4ev).""",
    long_description_content_type="text/markdown",
    author="Jérémy Dumoulin",
    author_email="jeremy.dumoulin@epfl.ch",       
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.12",
    install_requires=[
        "pandas==2.2.3",
        "numpy==2.2.4",
        "shapely==2.1.0",
        "rasterio==1.4.3",
        "osmnx==2.0.2",
        "folium==0.19.5",
        "pvlib==0.11.0",
        "timezonefinder==6.5.3",
    ],
    entry_points={
        'console_scripts': [
            'gtfs4ev=gtfs4ev.cli.gtfs4ev_cli:main',  
        ],
    }    
)