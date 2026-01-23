"""
Data loaders for ORRG.
Provides loading and caching of countries, cities, and weapon systems data.
"""

import json
from pathlib import Path
from typing import Any, Optional
from functools import lru_cache

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

from app.models.inputs import RangeClassification


# Data directory path
DATA_DIR = Path(__file__).parent


class DataService:
    """
    Service class for loading and accessing ORRG data.
    Provides cached access to countries, cities, and weapons databases.
    """
    
    def __init__(self):
        """Initialize the data service."""
        self._countries_gdf: Optional[gpd.GeoDataFrame] = None
        self._cities_df: Optional[pd.DataFrame] = None
        self._weapons_df: Optional[pd.DataFrame] = None
        
        # Caches
        self._country_name_cache: dict[str, str] = {}
        self._country_geometry_cache: dict[str, BaseGeometry] = {}
        self._city_coords_cache: dict[str, tuple[float, float]] = {}
    
    def load_countries(self) -> gpd.GeoDataFrame:
        """
        Load country boundaries from shapefile.
        Uses geoBoundaries CGAZ ADM0 data.
        """
        if self._countries_gdf is not None:
            return self._countries_gdf
        
        # Look for geoBoundaries shapefile first
        shapefile = DATA_DIR / "countries" / "geoBoundariesCGAZ_ADM0.shp"
        geojson_file = DATA_DIR / "countries" / "countries.geojson"
        
        if shapefile.exists():
            self._countries_gdf = gpd.read_file(shapefile)
            # Standardize column names from geoBoundaries format
            # geoBoundaries uses: shapeGroup (ISO3), shapeName (country name)
            column_mapping = {}
            if "shapeGroup" in self._countries_gdf.columns:
                column_mapping["shapeGroup"] = "ISO3"
            if "shapeName" in self._countries_gdf.columns:
                column_mapping["shapeName"] = "NAME"
            if column_mapping:
                self._countries_gdf = self._countries_gdf.rename(columns=column_mapping)
            
            # Ensure CRS is WGS84
            if self._countries_gdf.crs is None or self._countries_gdf.crs.to_epsg() != 4326:
                self._countries_gdf = self._countries_gdf.to_crs("EPSG:4326")
                
        elif geojson_file.exists():
            self._countries_gdf = gpd.read_file(geojson_file)
        else:
            # Create sample data for testing
            self._countries_gdf = _create_sample_countries()
        
        return self._countries_gdf
    
    def load_cities(self) -> pd.DataFrame:
        """Load cities database."""
        if self._cities_df is not None:
            return self._cities_df
        
        cities_file = DATA_DIR / "cities" / "cities.csv"
        
        if cities_file.exists():
            self._cities_df = pd.read_csv(cities_file)
        else:
            # Create sample data for testing
            self._cities_df = _create_sample_cities()
        
        return self._cities_df
    
    def load_weapons(self) -> pd.DataFrame:
        """Load weapon systems database from JSON or CSV."""
        if self._weapons_df is not None:
            return self._weapons_df
        
        json_file = DATA_DIR / "weapons" / "weapons.json"
        csv_file = DATA_DIR / "weapons" / "weapons.csv"
        
        if json_file.exists():
            # Load from JSON (preferred format)
            self._weapons_df = _load_weapons_from_json(json_file)
        elif csv_file.exists():
            self._weapons_df = pd.read_csv(csv_file)
        else:
            # Create sample data for testing
            self._weapons_df = _create_sample_weapons()
        
        return self._weapons_df
    
    def get_country_list(self) -> list[str]:
        """Get list of all country names sorted alphabetically."""
        countries = self.load_countries()
        if "NAME" in countries.columns:
            return sorted(countries["NAME"].dropna().unique().tolist())
        elif "name" in countries.columns:
            return sorted(countries["name"].dropna().unique().tolist())
        return []
    
    def get_country_codes(self) -> list[str]:
        """Get list of all country ISO3 codes."""
        countries = self.load_countries()
        if "ISO3" in countries.columns:
            return sorted(countries["ISO3"].dropna().unique().tolist())
        elif "iso_a3" in countries.columns:
            return sorted(countries["iso_a3"].dropna().unique().tolist())
        return []
    
    def get_country_name(self, country_code: str) -> str:
        """Get country name from ISO3 code."""
        if country_code in self._country_name_cache:
            return self._country_name_cache[country_code]
        
        countries = self.load_countries()
        
        # Try different column name conventions
        code_col = "ISO3" if "ISO3" in countries.columns else "iso_a3"
        name_col = "NAME" if "NAME" in countries.columns else "name"
        
        match = countries[countries[code_col] == country_code]
        if not match.empty:
            name = match.iloc[0][name_col]
            self._country_name_cache[country_code] = name
            return name
        
        return country_code
    
    def get_country_code(self, country_name: str) -> Optional[str]:
        """Get ISO3 code from country name."""
        countries = self.load_countries()
        
        code_col = "ISO3" if "ISO3" in countries.columns else "iso_a3"
        name_col = "NAME" if "NAME" in countries.columns else "name"
        
        match = countries[countries[name_col] == country_name]
        if not match.empty:
            return match.iloc[0][code_col]
        
        return None
    
    def get_country_geometry(self, country_code: str) -> Optional[BaseGeometry]:
        """Get the geometry for a country by ISO3 code."""
        if country_code in self._country_geometry_cache:
            return self._country_geometry_cache[country_code]
        
        countries = self.load_countries()
        
        code_col = "ISO3" if "ISO3" in countries.columns else "iso_a3"
        
        match = countries[countries[code_col] == country_code]
        if not match.empty:
            geom = match.iloc[0].geometry
            # Make geometry valid if needed to prevent topology errors
            if not geom.is_valid:
                geom = geom.buffer(0)
            self._country_geometry_cache[country_code] = geom
            return geom
        
        return None
    
    def get_country_centroid(self, country_code: str) -> Optional[tuple[float, float]]:
        """Get the centroid of a country as (latitude, longitude)."""
        geom = self.get_country_geometry(country_code)
        if geom:
            centroid = geom.centroid
            return (centroid.y, centroid.x)
        return None
    
    def get_city_list(self, country_code: Optional[str] = None) -> list[str]:
        """Get list of city names, optionally filtered by country."""
        cities = self.load_cities()
        
        if country_code and "country_code" in cities.columns:
            cities = cities[cities["country_code"] == country_code]
        
        if "name" in cities.columns:
            return sorted(cities["name"].dropna().unique().tolist())
        elif "city_name" in cities.columns:
            return sorted(cities["city_name"].dropna().unique().tolist())
        
        return []
    
    def get_city_coordinates(self, city_name: str) -> Optional[tuple[float, float]]:
        """Get coordinates for a city as (latitude, longitude)."""
        if city_name in self._city_coords_cache:
            return self._city_coords_cache[city_name]
        
        cities = self.load_cities()
        
        name_col = "name" if "name" in cities.columns else "city_name"
        lat_col = "latitude" if "latitude" in cities.columns else "lat"
        lon_col = "longitude" if "longitude" in cities.columns else "lon"
        
        match = cities[cities[name_col] == city_name]
        if not match.empty:
            lat = match.iloc[0][lat_col]
            lon = match.iloc[0][lon_col]
            coords = (float(lat), float(lon))
            self._city_coords_cache[city_name] = coords
            return coords
        
        return None
    
    def get_weapons_for_country(self, country_code: str) -> pd.DataFrame:
        """Get all weapon systems for a specific country."""
        weapons = self.load_weapons()
        
        code_col = "country_code" if "country_code" in weapons.columns else "Country"
        
        return weapons[weapons[code_col] == country_code]
    
    def get_weapon_systems(self, country_code: Optional[str] = None) -> list[dict[str, Any]]:
        """
        Get list of weapon systems, optionally filtered by country.
        Returns list of dicts with name, range_km, classification, etc.
        """
        weapons = self.load_weapons()
        
        if country_code:
            code_col = "country_code" if "country_code" in weapons.columns else "Country"
            weapons = weapons[weapons[code_col] == country_code]
        
        results = []
        for _, row in weapons.iterrows():
            name = row.get("name") or row.get("sys_name", "Unknown")
            range_km = row.get("range_km") or row.get("Max_Range", 0)
            country = row.get("country_code") or row.get("Country", "")
            
            results.append({
                "name": name,
                "range_km": float(range_km),
                "country_code": country,
                "classification": _classify_weapon_range(float(range_km)),
            })
        
        return results
    
    def get_weapon_range(self, weapon_name: str, country_code: Optional[str] = None) -> Optional[float]:
        """Get the range in km for a specific weapon system."""
        weapons = self.load_weapons()
        
        name_col = "name" if "name" in weapons.columns else "sys_name"
        range_col = "range_km" if "range_km" in weapons.columns else "Max_Range"
        
        if country_code:
            code_col = "country_code" if "country_code" in weapons.columns else "Country"
            match = weapons[
                (weapons[name_col] == weapon_name) & 
                (weapons[code_col] == country_code)
            ]
        else:
            match = weapons[weapons[name_col] == weapon_name]
        
        if not match.empty:
            return float(match.iloc[0][range_col])
        
        return None
    
    def search_countries(self, query: str) -> list[str]:
        """Search for countries by partial name match."""
        countries = self.get_country_list()
        query_lower = query.lower()
        return [c for c in countries if query_lower in c.lower()]
    
    def search_cities(self, query: str) -> list[str]:
        """Search for cities by partial name match."""
        cities = self.get_city_list()
        query_lower = query.lower()
        return [c for c in cities if query_lower in c.lower()]
    
    def search_weapons(self, query: str) -> list[dict[str, Any]]:
        """Search for weapon systems by partial name match."""
        weapons = self.get_weapon_systems()
        query_lower = query.lower()
        return [w for w in weapons if query_lower in w["name"].lower()]


def _load_weapons_from_json(json_file: Path) -> pd.DataFrame:
    """
    Load weapon systems from the organized JSON format.
    Converts the nested JSON structure to a flat DataFrame.
    """
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    weapons_list = []
    countries_data = data.get("countries", {})
    
    for country_code, country_info in countries_data.items():
        country_name = country_info.get("name", country_code)
        systems = country_info.get("systems", [])
        
        for system in systems:
            weapon = {
                "name": system.get("name", "Unknown"),
                "country_code": country_code,
                "country_name": country_name,
                "range_km": system.get("range_km"),
                "classification": system.get("classification", ""),
                "range_note": system.get("range_note", ""),
                "variants": ", ".join(system.get("variants", [])) if system.get("variants") else "",
            }
            # Skip weapons with no range data
            if weapon["range_km"] is not None:
                weapons_list.append(weapon)
    
    return pd.DataFrame(weapons_list)


def _classify_weapon_range(range_km: float) -> str:
    """Classify a weapon system based on its range."""
    if range_km < 300:
        return RangeClassification.CRBM.value
    elif range_km < 1000:
        return RangeClassification.SRBM.value
    elif range_km < 3000:
        return RangeClassification.MRBM.value
    elif range_km < 5500:
        return RangeClassification.IRBM.value
    else:
        return RangeClassification.ICBM.value


def _create_sample_countries() -> gpd.GeoDataFrame:
    """Create sample country data for testing."""
    from shapely.geometry import box
    
    # Sample countries with approximate bounding boxes
    data = [
        {"NAME": "North Korea", "ISO3": "PRK", "geometry": box(124, 37.5, 131, 43)},
        {"NAME": "South Korea", "ISO3": "KOR", "geometry": box(126, 33, 130, 38.5)},
        {"NAME": "Japan", "ISO3": "JPN", "geometry": box(129, 31, 146, 46)},
        {"NAME": "China", "ISO3": "CHN", "geometry": box(73, 18, 135, 54)},
        {"NAME": "Russia", "ISO3": "RUS", "geometry": box(19, 41, 180, 82)},
        {"NAME": "Iran", "ISO3": "IRN", "geometry": box(44, 25, 64, 40)},
        {"NAME": "United States", "ISO3": "USA", "geometry": box(-125, 24, -66, 50)},
        {"NAME": "Israel", "ISO3": "ISR", "geometry": box(34, 29, 36, 34)},
        {"NAME": "India", "ISO3": "IND", "geometry": box(68, 6, 98, 36)},
        {"NAME": "Pakistan", "ISO3": "PAK", "geometry": box(60, 23, 77, 37)},
    ]
    
    return gpd.GeoDataFrame(data, crs="EPSG:4326")


def _create_sample_cities() -> pd.DataFrame:
    """Create sample city data for testing."""
    data = [
        {"name": "Pyongyang", "country_code": "PRK", "latitude": 39.0392, "longitude": 125.7625},
        {"name": "Seoul", "country_code": "KOR", "latitude": 37.5665, "longitude": 126.9780},
        {"name": "Tokyo", "country_code": "JPN", "latitude": 35.6762, "longitude": 139.6503},
        {"name": "Beijing", "country_code": "CHN", "latitude": 39.9042, "longitude": 116.4074},
        {"name": "Moscow", "country_code": "RUS", "latitude": 55.7558, "longitude": 37.6173},
        {"name": "Tehran", "country_code": "IRN", "latitude": 35.6892, "longitude": 51.3890},
        {"name": "Washington D.C.", "country_code": "USA", "latitude": 38.9072, "longitude": -77.0369},
        {"name": "Tel Aviv", "country_code": "ISR", "latitude": 32.0853, "longitude": 34.7818},
        {"name": "New Delhi", "country_code": "IND", "latitude": 28.6139, "longitude": 77.2090},
        {"name": "Islamabad", "country_code": "PAK", "latitude": 33.6844, "longitude": 73.0479},
        {"name": "Guam", "country_code": "USA", "latitude": 13.4443, "longitude": 144.7937},
        {"name": "Honolulu", "country_code": "USA", "latitude": 21.3069, "longitude": -157.8583},
        {"name": "Los Angeles", "country_code": "USA", "latitude": 34.0522, "longitude": -118.2437},
        {"name": "New York", "country_code": "USA", "latitude": 40.7128, "longitude": -74.0060},
    ]
    
    return pd.DataFrame(data)


def _create_sample_weapons() -> pd.DataFrame:
    """Create sample weapon systems data for testing."""
    data = [
        # North Korea
        {"name": "Hwasong-12", "country_code": "PRK", "range_km": 4500},
        {"name": "Hwasong-14", "country_code": "PRK", "range_km": 10000},
        {"name": "Hwasong-15", "country_code": "PRK", "range_km": 13000},
        {"name": "Hwasong-17", "country_code": "PRK", "range_km": 15000},
        {"name": "KN-23", "country_code": "PRK", "range_km": 690},
        {"name": "Scud-B", "country_code": "PRK", "range_km": 300},
        {"name": "Scud-C", "country_code": "PRK", "range_km": 500},
        {"name": "Nodong", "country_code": "PRK", "range_km": 1300},
        # Iran
        {"name": "Shahab-3", "country_code": "IRN", "range_km": 2000},
        {"name": "Sejjil", "country_code": "IRN", "range_km": 2500},
        {"name": "Emad", "country_code": "IRN", "range_km": 1700},
        {"name": "Fateh-110", "country_code": "IRN", "range_km": 300},
        # Russia
        {"name": "Iskander-M", "country_code": "RUS", "range_km": 500},
        {"name": "Topol-M", "country_code": "RUS", "range_km": 11000},
        {"name": "RS-28 Sarmat", "country_code": "RUS", "range_km": 18000},
        # China
        {"name": "DF-21", "country_code": "CHN", "range_km": 2150},
        {"name": "DF-26", "country_code": "CHN", "range_km": 4000},
        {"name": "DF-31", "country_code": "CHN", "range_km": 8000},
        {"name": "DF-41", "country_code": "CHN", "range_km": 15000},
        # Pakistan
        {"name": "Shaheen-III", "country_code": "PAK", "range_km": 2750},
        {"name": "Ghauri", "country_code": "PAK", "range_km": 1500},
        # India
        {"name": "Agni-V", "country_code": "IND", "range_km": 5000},
        {"name": "Prithvi-II", "country_code": "IND", "range_km": 350},
        # Israel
        {"name": "Jericho III", "country_code": "ISR", "range_km": 4800},
    ]
    
    return pd.DataFrame(data)


# Global data service instance
_data_service: Optional[DataService] = None


def get_data_service() -> DataService:
    """Get the global data service instance."""
    global _data_service
    if _data_service is None:
        _data_service = DataService()
    return _data_service


# Convenience functions
def load_countries() -> gpd.GeoDataFrame:
    """Load countries GeoDataFrame."""
    return get_data_service().load_countries()


def load_cities() -> pd.DataFrame:
    """Load cities DataFrame."""
    return get_data_service().load_cities()


def load_weapons() -> pd.DataFrame:
    """Load weapons DataFrame."""
    return get_data_service().load_weapons()
