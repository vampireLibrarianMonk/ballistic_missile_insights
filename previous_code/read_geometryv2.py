# Import modules from arcpy
##from arcpy import Array
##from arcpy import CopyFeatures_management
from arcpy import da
##from arcpy import DefineProjection_management
##from arcpy import Describe
from arcpy import env
##from arcpy import GetParameterAsText
from arcpy import Point
from arcpy import Polygon

# Import modules from decimal
from decimal import Decimal

# Import modules from math
from math import asin, atan, atan2, cos, degrees, pi, radians, sin, sqrt, tan

# Import numpy module
import numpy as np

# Import modules from time for diagnostics
from time import strftime

# Overwrites existing dataset
env.overwriteOutput = True

print strftime("%Y-%m-%d %H:%M:%S")

pointList = np.array([])
##infc = r"C:\showcase_other_stash\Experiment\BermudaUnitedKingdom_upper.shp"
infc = r'C:\showcase_other_stash\Experiment\shapefiles\China_lower.shp'
#spatialRef = Describe(infc)

# Enter for loop for each feature
for row in da.SearchCursor(infc, ["SHAPE@"]):

    # Step through each part of the feature
    for part in row[0]:
        
        # Step through each vertex in the feature
        for pnt in part:
            pointList = np.append(pointList, np.array([np.float64(pnt.X), np.float64(pnt.Y)]))

print np.size(pointList, 0)
print strftime("%Y-%m-%d %H:%M:%S")

### Semi major, minor axis and flattening (in meters)
##semi_major = np.float64(6378137)
##semi_minor = np.float64(6356752.314140)
##flattening = np.float64((semi_major - semi_minor) / semi_major)
##
##featureList = np.array([])
##
##inputBearing = np.float64(0)
##recordCount = np.float64(0)
##distance = np.float64(100000)
##
### Given an origin point (in decimal degrees) and bearing (in degrees)
##lat1 = np.float64(np.radians(inputLat))
##lng1 = np.float64(np.radians(inputLong))
##bearing = np.float64(np.radians(inputBearing)) 
##
##bearAddOne = np.float64(np.radians(Decimal(str(1.139240506329114))))
##bearAddTwo = np.float64(np.radians(Decimal(str(.5113636363636364))))
##bearAddThree = np.float64(np.radians(Decimal(str(0.1616524472384374))))
##
##npOne = np.float64(1)
##npNegOne = np.float64(-1)
##npTwo = np.float64(2)
##npNegThree = np.float64(-3)
##npFour = np.float64(4)
##npSix = np.float64(6)
##np16 = np.float64(16)
##np47 = np.float(47)
##np74 = np.float64(np74)
##np175 = np.float64(175)
##npNeg128 = np.float64(-128)
##np256 = np.float64(256)
##np320 = np.float64(320)
##np360 = np.float64(np.radians(360))
##npNeg768 = np.float64(-768)
##np1024 = np.float64(1024)
##np4096 = np.float64(4096)
##np16384 = np.float64(16384)
##
##limit = np.float64(10e-12)
##
##limitOne = np.float64(100000)
##limitTwo = np.float64(10000000)
##limitThree = np.float64(20037500)
##
### Obtain lattitude/longitude of point 
##for point in pointList:
##    inputLat = np.float64(point[1])
##    inputLong = np.float64(point[0])
##    partList = np.array([])
##
##    while bearing < np360:
##        # Direct Problem:
##        # Given an initial point and initial bearing and distance along the geodesic find the end point
##        tan_reduced1 = (npOne - flattening) * np.tan(lat1) # reduced latitude
##        cos_reduced1 = npOne / np.sqrt(npOne + tan_reduced1 **npTwo)
##        sin_reduced1 = tan_reduced1 * cos_reduced1
##        sin_bearing, cos_bearing = np.sin(bearing), np.cos(bearing)
##        sigma1 = np.arctan2(tan_reduced1, cos_bearing)
##        sin_alpha = cos_reduced1 * sin_bearing
##        cos_sq_alpha = npOne - sin_alpha ** npTwo
##        u_sq = cos_sq_alpha * (semi_major ** npTwo - semi_minor ** npTwo) / semi_minor ** npTwo
##        
##
##        A = npOne + u_sq / np16384 * (np4096 + u_sq * (npNeg768 + u_sq * (np320 - np175 * u_sq)))
##        B = u_sq / np1024 * (np256 + u_sq * (npNeg128 + u_sq * (np74 - np47 * u_sq)))
##
##        sigma = distance / (semi_minor * A)
##        sigma_prime = npTwo * np.pi
##
##        while abs(sigma - sigma_prime) > limit:
##            cos2_sigma_m = cos(npTwo * sigma1 + sigma)
##            sin_sigma, cos_sigma = sin(sigma), cos(sigma)
##            delta_sigma = B * sin_sigma * (
##                cos2_sigma_m + B / npFour * (
##                    cos_sigma * (
##                        npNegOne + npTwo * cos2_sigma_m
##                    ) - B / np.Six * cos2_sigma_m * (
##                        npNegThree + npFour * sin_sigma ** npTwo) * (
##                        npNegThree + npFour * cos2_sigma_m ** npTwo
##                    )
##                )
##            )
##
##            sigma_prime = sigma
##            sigma = distance / (semi_minor * A) + delta_sigma
##
##        sin_sigma, cos_sigma = sin(sigma), cos(sigma)
##
##        lat2 = np.arctan2(
##            sin_reduced1 * cos_sigma + cos_reduced1 * sin_sigma * cos_bearing,
##            (npOne - flattening) * np.sqrt(
##                sin_alpha ** npTwo + (
##                    sin_reduced1 * sin_sigma -
##                    cos_reduced1 * cos_sigma * cos_bearing
##                ) ** npTwo
##            )
##        )
##
##        lamda_lng = np.arctan2(
##            sin_sigma * sin_bearing,
##            cos_reduced1 * cos_sigma - sin_reduced1 * sin_sigma * cos_bearing
##            )
##
##        C = flattening / np16 * cos_sq_alpha * (npfour + flattening * (npFour - npThree * cos_sq_alpha))
##
##        delta_lng = (
##            lamda_lng - (npOne-C) * flattening * sin_alpha * (
##                sigma + C * sin_sigma * (
##                    cos2_sigma_m + C * cos_sigma * (
##                        npNegOne + npTwo * cos2_sigma_m ** npTwo
##                    )
##                )
##            )
##        )
##
##        lng2 = lng1 + delta_lng
##
##        endLat2, endLng2 = np.degrees(lat2), np.degrees(lng2)
##
##        # Substitute decision loop for equation
##        if distance <= limitOne:
##            bearing = bearing + bearAddOne
##        elif distance > limitOne and distance <= limitTwo:
##            bearing = bearing + bearAddTwo
##        elif distance > limitTwo and distance <= limitThree:            
##            bearing = bearing + bearAddThree
##        else:
##            print "Error in distance"
##
##        partList = np.append(partList,[endLng2, endLat2]) 
##        
##    featureList = np.append(featureList, partList)
##
####features = []
####
####for feature in featureList:
####    # Create a Polygon object based on the array of points
####    # Append to the list of Polygon objects
####    features.append(
####        arcpy.Polygon(
####            arcpy.Array([arcpy.Point(*coords) for coords in feature])))
####
####CopyFeatures_management(features, r"C:\Users\Mr. P\Desktop\showcase\range_ring\Experiment\test.shp")
####
####DefineProjection_management(r"C:\Users\Mr. P\Desktop\showcase\range_ring\Experiment\test.shp", spatialRef.SpatialReference)
##
##print np.size(featureList, 0)
##print strftime("%Y-%m-%d %H:%M:%S")
