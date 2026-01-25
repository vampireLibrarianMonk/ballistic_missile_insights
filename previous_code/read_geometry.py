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

# Import modules from time for diagnostics
from time import strftime

# Overwrites existing dataset
env.overwriteOutput = True

print strftime("%Y-%m-%d %H:%M:%S")

pointList = []
infc = r"C:\showcase_other_stash\Experiment\BermudaUnitedKingdom_upper.shp"
#spatialRef = Describe(infc)

# Enter for loop for each feature
for row in da.SearchCursor(infc, ["SHAPE@"]):

    # Step through each part of the feature
    for part in row[0]:
        
        # Step through each vertex in the feature
        for pnt in part:
            pointList.append([pnt.X, pnt.Y])

print len(pointList)

# Semi major, minor axis and flattening (in meters)
semi_major = 6378137
semi_minor = 6356752.314140
flattening = (semi_major - semi_minor) / semi_major

featureList = []

# Obtain lattitude/longitude of point 
for point in pointList:
    inputLat = point[1]
    inputLong = point[0]
    inputBearing = 0
    recordCount = 0
    distance = 100000

    # Given an origin point (in decimal degrees) and bearing (in degrees)
    lat1, lng1, bearing = list(map(radians, [inputLat, inputLong, inputBearing]))

    partList = []

    while inputBearing < Decimal("359.9"):
        # Direct Problem:
        # Given an initial point and initial bearing and distance along the geodesic find the end point
        tan_reduced1 = (1 - flattening) * tan(lat1) # reduced latitude
        cos_reduced1 = 1 / sqrt(1 + tan_reduced1 **2)
        sin_reduced1 = tan_reduced1 * cos_reduced1
        sin_bearing, cos_bearing = sin(bearing), cos(bearing)
        sigma1 = atan2(tan_reduced1, cos_bearing)
        sin_alpha = cos_reduced1 * sin_bearing
        cos_sq_alpha = 1 - sin_alpha ** 2
        u_sq = cos_sq_alpha * (semi_major ** 2 - semi_minor ** 2) / semi_minor ** 2
        

        A = 1 + u_sq / 16384. * (4096 + u_sq * (-768 + u_sq * (320 - 175 * u_sq)))
        B = u_sq / 1024. * (256 + u_sq * (-128 + u_sq * (74 - 47 * u_sq)))

        sigma = distance / (semi_minor * A)
        sigma_prime = 2 * pi

        while abs(sigma - sigma_prime) > 10e-12:
            cos2_sigma_m = cos(2 * sigma1 + sigma)
            sin_sigma, cos_sigma = sin(sigma), cos(sigma)
            delta_sigma = B * sin_sigma * (
                cos2_sigma_m + B / 4. * (
                    cos_sigma * (
                        -1 + 2 * cos2_sigma_m
                    ) - B / 6. * cos2_sigma_m * (
                        -3 + 4 * sin_sigma ** 2) * (
                        -3 + 4 * cos2_sigma_m ** 2
                    )
                )
            )

            sigma_prime = sigma
            sigma = distance / (semi_minor * A) + delta_sigma

        sin_sigma, cos_sigma = sin(sigma), cos(sigma)

        lat2 = atan2(
            sin_reduced1 * cos_sigma + cos_reduced1 * sin_sigma * cos_bearing,
            (1 - flattening) * sqrt(
                sin_alpha ** 2 + (
                    sin_reduced1 * sin_sigma -
                    cos_reduced1 * cos_sigma * cos_bearing
                ) ** 2
            )
        )

        lamda_lng = atan2(
            sin_sigma * sin_bearing,
            cos_reduced1 * cos_sigma - sin_reduced1 * sin_sigma * cos_bearing
            )

        C = flattening / 16. * cos_sq_alpha * (4 + flattening * (4 - 3 * cos_sq_alpha))

        delta_lng = (
            lamda_lng - (1-C) * flattening * sin_alpha * (
                sigma + C * sin_sigma * (
                    cos2_sigma_m + C * cos_sigma * (
                        -1 + 2 * cos2_sigma_m ** 2
                    )
                )
            )
        )

        lng2 = lng1 + delta_lng

        endLat2, endLng2 = list(map(degrees, [lat2, lng2]))

        # Substitute decision loop for equation
        if distance <= 100000:
            inputBearing = inputBearing + Decimal(str(1.139240506329114))
        elif distance > 100000 and distance <= 10000000:
            inputBearing = inputBearing + Decimal(str(.5113636363636364))
        elif distance > 10000000 and distance <= 20037500:            
            inputBearing = inputBearing + Decimal(str(0.1616524472384374))
        else:
            print "Error in distance"

        partList.append(Point(endLng2, endLat2))
        
    featureList.append(partList)

##features = []
##
##for feature in featureList:
##    # Create a Polygon object based on the array of points
##    # Append to the list of Polygon objects
##    features.append(
##        arcpy.Polygon(
##            arcpy.Array([arcpy.Point(*coords) for coords in feature])))
##
##CopyFeatures_management(features, r"C:\Users\Mr. P\Desktop\showcase\range_ring\Experiment\test.shp")
##
##DefineProjection_management(r"C:\Users\Mr. P\Desktop\showcase\range_ring\Experiment\test.shp", spatialRef.SpatialReference)

print len(featureList)
print strftime("%Y-%m-%d %H:%M:%S")
