"""
Models package for ORRG.
Contains Pydantic models for inputs and outputs.
"""

from app.models.inputs import (
    OriginType,
    DistanceUnit,
    RangeClassification,
    PointOfInterest,
    SingleRangeRingInput,
    MultipleRangeRingInput,
    ReverseRangeRingInput,
    MinimumRangeRingInput,
    CustomPOIRangeRingInput,
)

from app.models.outputs import (
    RangeRingOutput,
    AnalyticalResult,
    ExportMetadata,
)

__all__ = [
    "OriginType",
    "DistanceUnit",
    "RangeClassification",
    "PointOfInterest",
    "SingleRangeRingInput",
    "MultipleRangeRingInput",
    "ReverseRangeRingInput",
    "MinimumRangeRingInput",
    "CustomPOIRangeRingInput",
    "RangeRingOutput",
    "AnalyticalResult",
    "ExportMetadata",
]
