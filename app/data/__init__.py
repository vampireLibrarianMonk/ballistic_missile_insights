"""
Data package for ORRG.
Provides data loading and management for countries, cities, and weapon systems.
"""

from app.data.loaders import (
    DataService,
    get_data_service,
    load_countries,
    load_cities,
    load_weapons,
)

__all__ = [
    "DataService",
    "get_data_service",
    "load_countries",
    "load_cities",
    "load_weapons",
]
