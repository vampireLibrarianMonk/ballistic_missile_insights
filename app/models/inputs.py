"""
Input models for ORRG analytical tools.
All inputs are validated using Pydantic for type safety and consistency.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class OriginType(str, Enum):
    """Type of origin for range ring generation."""
    COUNTRY = "country"
    POINT = "point"
    CITY = "city"


class DistanceUnit(str, Enum):
    """Supported distance units for range specifications."""
    KILOMETERS = "km"
    MILES = "mi"
    NAUTICAL_MILES = "nm"
    METERS = "m"
    FEET = "ft"
    YARDS = "yd"


class RangeClassification(str, Enum):
    """Missile range classifications based on standard definitions."""
    CRBM = "CRBM"  # Close-Range Ballistic Missile (< 300 km)
    SRBM = "SRBM"  # Short-Range Ballistic Missile (300-1000 km)
    MRBM = "MRBM"  # Medium-Range Ballistic Missile (1000-3000 km)
    IRBM = "IRBM"  # Intermediate-Range Ballistic Missile (3000-5500 km)
    ICBM = "ICBM"  # Intercontinental Ballistic Missile (> 5500 km)


class PointOfInterest(BaseModel):
    """A geographic point of interest with optional metadata."""
    name: str = Field(..., description="Display name for the POI")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")
    description: Optional[str] = Field(None, description="Optional description")

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        if not -90 <= v <= 90:
            raise ValueError("Latitude must be between -90 and 90 degrees")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        if not -180 <= v <= 180:
            raise ValueError("Longitude must be between -180 and 180 degrees")
        return v


class WeaponSystemInput(BaseModel):
    """Input for a weapon system selection."""
    name: str = Field(..., description="Weapon system name")
    country_code: Optional[str] = Field(None, description="ISO3 country code")
    range_km: float = Field(..., gt=0, description="Maximum range in kilometers")
    classification: Optional[RangeClassification] = Field(
        None, description="Missile range classification"
    )


class SingleRangeRingInput(BaseModel):
    """
    Input for Single Range Ring Generator.
    Generates a single geodesic range ring from a country boundary or point of origin.
    """
    origin_type: OriginType = Field(..., description="Type of origin point")
    country_code: Optional[str] = Field(
        None, description="ISO3 country code (required if origin_type is COUNTRY)"
    )
    origin_point: Optional[PointOfInterest] = Field(
        None, description="Point of origin (required if origin_type is POINT)"
    )
    city_name: Optional[str] = Field(
        None, description="City name (required if origin_type is CITY)"
    )
    
    # Range specification
    range_value: float = Field(..., gt=0, description="Range value")
    range_unit: DistanceUnit = Field(DistanceUnit.KILOMETERS, description="Distance unit")
    
    # Weapon system (optional - for labeling)
    weapon_system: Optional[str] = Field(None, description="Weapon system name for labeling")
    weapon_source: Optional[str] = Field(None, description="Source of weapon data (e.g., '2020 Ballistic and Cruise Missile Threat Report')")
    
    # Resolution
    resolution: str = Field("normal", description="Ring resolution: 'low' or 'normal'")

    @field_validator("resolution")
    @classmethod
    def validate_resolution(cls, v: str) -> str:
        if v.lower() not in ["low", "normal", "high"]:
            raise ValueError("Resolution must be 'low', 'normal', or 'high'")
        return v.lower()


class MultipleRangeRingInput(BaseModel):
    """
    Input for Multiple Range Ring Generator.
    Generates multiple concentric range rings representing different weapon systems or ranges.
    """
    origin_type: OriginType = Field(..., description="Type of origin point")
    country_code: Optional[str] = Field(None, description="ISO3 country code")
    origin_point: Optional[PointOfInterest] = Field(None, description="Point of origin")
    city_name: Optional[str] = Field(None, description="City name")
    
    # Multiple ranges
    ranges: list[tuple[float, DistanceUnit, Optional[str]]] = Field(
        ..., 
        min_length=1,
        description="List of (range_value, unit, optional_label) tuples"
    )

    # Optional source for the weapon data (applies to the set of ranges)
    weapon_source: Optional[str] = Field(
        None,
        description="Source of weapon data (e.g., '2020 Ballistic and Cruise Missile Threat Report')",
    )
    
    # Resolution
    resolution: str = Field("normal", description="Ring resolution")


class ReverseRangeRingInput(BaseModel):
    """
    Input for Reverse Range Ring Generator.
    Computes the geographic region from which a weapon system could reach a specified target.
    """
    target_point: PointOfInterest = Field(..., description="Target point to analyze")
    
    # Range specification
    range_value: float = Field(..., gt=0, description="Weapon range value")
    range_unit: DistanceUnit = Field(DistanceUnit.KILOMETERS, description="Distance unit")
    
    # Optional weapon system for labeling
    weapon_system: Optional[str] = Field(None, description="Weapon system name")
    weapon_source: Optional[str] = Field(
        None,
        description="Source of weapon data (e.g., '2020 Ballistic and Cruise Missile Threat Report')",
    )
    
    # Resolution
    resolution: str = Field("normal", description="Ring resolution")


class MinimumRangeRingInput(BaseModel):
    """
    Input for Minimum Range Ring Generator.
    Calculates the minimum geodesic distance between two locations (countries or cities).
    """
    country_code_a: Optional[str] = Field(None, description="ISO3 code for first location (if country)")
    country_code_b: Optional[str] = Field(None, description="ISO3 code for second location (if country)")
    
    # Optional visualization options
    show_minimum_line: bool = Field(True, description="Show the minimum distance line")
    show_buffer_rings: bool = Field(False, description="Show buffer rings at key distances")


class CustomPOIRangeRingInput(BaseModel):
    """
    Input for Custom POI Range Ring Generator.
    Generates minimum/maximum "donut" range rings from one or more user-defined POIs.
    """
    points_of_interest: list[PointOfInterest] = Field(
        ..., 
        min_length=1,
        description="List of points of interest"
    )
    
    # Range specification (inner/outer for donut)
    min_range_value: Optional[float] = Field(
        None, ge=0, description="Minimum range (inner radius) - 0 or None for solid circle"
    )
    max_range_value: float = Field(..., gt=0, description="Maximum range (outer radius)")
    range_unit: DistanceUnit = Field(DistanceUnit.KILOMETERS, description="Distance unit")
    
    # Optional weapon system for labeling
    weapon_system: Optional[str] = Field(None, description="Weapon system name")
    
    # Resolution
    resolution: str = Field("normal", description="Ring resolution")

    @field_validator("min_range_value")
    @classmethod
    def validate_min_range(cls, v: Optional[float], info) -> Optional[float]:
        if v is not None and "max_range_value" in info.data:
            max_val = info.data.get("max_range_value")
            if max_val is not None and v >= max_val:
                raise ValueError("Minimum range must be less than maximum range")
        return v


# Unit conversion utilities
UNIT_TO_KM: dict[DistanceUnit, float] = {
    DistanceUnit.KILOMETERS: 1.0,
    DistanceUnit.MILES: 1.60934,
    DistanceUnit.NAUTICAL_MILES: 1.852,
    DistanceUnit.METERS: 0.001,
    DistanceUnit.FEET: 0.0003048,
    DistanceUnit.YARDS: 0.0009144,
}


def convert_to_km(value: float, unit: DistanceUnit) -> float:
    """Convert a distance value to kilometers."""
    return value * UNIT_TO_KM[unit]


def convert_from_km(value_km: float, unit: DistanceUnit) -> float:
    """Convert a distance from kilometers to the specified unit."""
    return value_km / UNIT_TO_KM[unit]


def classify_range(range_km: float) -> RangeClassification:
    """Classify a range in kilometers according to standard missile classifications."""
    if range_km < 300:
        return RangeClassification.CRBM
    elif range_km < 1000:
        return RangeClassification.SRBM
    elif range_km < 3000:
        return RangeClassification.MRBM
    elif range_km < 5500:
        return RangeClassification.IRBM
    else:
        return RangeClassification.ICBM
