from setuptools import setup

setup(
    name="gtfs4ev",          
    version=__version__,                  
    description="A Python framework for simulating electric bus operations and charging demand using GTFS data",
    long_description="README.md",
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
            'gtfs4ev=gtfs4ev.gtfs4ev_cli:main',  
        ],
    }    
)