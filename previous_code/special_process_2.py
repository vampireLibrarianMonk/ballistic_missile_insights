# Import modules from arcpy
from arcpy import AddField_management
from arcpy import AggregatePolygons_cartography
from arcpy import CopyFeatures_management
from arcpy import da
from arcpy import env
from arcpy import Exists
from arcpy import GetCount_management
from arcpy import MakeFeatureLayer_management
from arcpy import Project_management
from arcpy import Rename_management
from arcpy import SelectLayerByAttribute_management
from arcpy import SelectLayerByLocation_management

# Import modules from imp
from imp import load_compiled

# Import modules from os
from os import path

# Import modules from sys
from sys import argv

# Set variables for Data directory
fileName =  path.basename(argv[0])
directory = argv[0]

# Import rangeRingModules getShortFilePath
mod1Var = directory.replace("special_process_2.pyc","rangeRingModules.pyc")
load_compiled('rangeRingModules', mod1Var)
from rangeRingModules import getShortFilePath

# Set variables for Data directory
fileName =  path.basename(argv[0])
multi_Buffer_Directory = argv[0]
multi_Buffer_Directory = multi_Buffer_Directory.replace(fileName, "")
dataPath = multi_Buffer_Directory.replace("code", "Data")

# Set environment (fixes problem with spaces in directories)
dataPath = getShortFilePath(dataPath)
env.workspace = dataPath

# Set scratch workspaces(fixes problem with spaces in directories)
scratchPath = multi_Buffer_Directory.replace("code", "scratch")
scratchPath = getShortFilePath(scratchPath)
env.scratchWorkspace = getShortFilePath(scratchPath)

# Set text file directory (multiprocessing variable carry over from multiple range ring tool)
textPath = multi_Buffer_Directory.replace("code", "txt_files")
textPath = getShortFilePath(textPath)

# Open text file with carry over variables
fileVariable = textPath + "carryOverVariables.txt" 
textFile = open(fileVariable, "r")
carryOverVariables = textFile.read().split("#")
textFile.close()

# Convert carry over variables to string and prepare it for parsing
carryOverVariables = str(carryOverVariables)
carryOverVariables = carryOverVariables.replace('["', "")
carryOverVariables = carryOverVariables.replace('"]', "")
carryOverVariables = carryOverVariables.split("?")

# Get country name
countryName = carryOverVariables[0]

# Get country trigraph
countryTrigraph = carryOverVariables[3]

# Get range list
textRangeList = carryOverVariables[4].replace("']","")
textRangeList = textRangeList.replace("['","")
textRangeList = textRangeList.replace("[","")
textRangeList = textRangeList.replace("]","")
textRangeList = textRangeList.replace(" ","")
rangeList = list(textRangeList.split(","))

# Get distance unit
distanceUnit = carryOverVariables[5]

# Get symbology value list
symbologyValueList = carryOverVariables[6]
symbologyValueList = symbologyValueList.replace("[","")
symbologyValueList = symbologyValueList.replace("]","")
symbologyValueList = symbologyValueList.replace("'","")
symbologyValueList = symbologyValueList.replace(" M","M")
symbologyValueList = symbologyValueList.split(",")

# Set projection variable
prjFile = carryOverVariables[7]

# Go through range value list and add geometries to new fcs
for rangeValue in rangeList:
    draftShapefile = "draft_" + rangeValue + ".shp"
    
    secondDraftShapefile = "second_draft_" + rangeValue + ".shp"

    thirdDraftShapefile = "third_draft_" + rangeValue + ".shp"

    finalShapefile = "final_" + rangeValue + ".shp"

    meridianLayer = "meridian_" + rangeValue

    bufferLayer = "buffer_layer" + rangeValue 

    # Project feature class
    Project_management(draftShapefile, secondDraftShapefile, prjFile)

    # Make buffer into feature layer for select by location decision loop
    MakeFeatureLayer_management(secondDraftShapefile, bufferLayer)

    # Make newly projected meridian feature class into feature layer for select by location decision loop
    MakeFeatureLayer_management("meridian.shp", meridianLayer)

    # Select by location, if buffer falls within meridian then perform intersect, merge and dissolve new output feature class
    SelectLayerByLocation_management(bufferLayer,'INTERSECT',meridianLayer)

    # Set variable for decision loop determining how many intersections occur between the projected buffer and the meridian layer
    matchCount = int(GetCount_management(bufferLayer)[0])

    # Aggregate newly created buffer feature class to get rid of anti-meridian artifacts or rename if match count is zero
    if matchCount > 0:
        AggregatePolygons_cartography(secondDraftShapefile, thirdDraftShapefile, "1 Centimeter")
    else:
        # Rename feature class
        Rename_management(secondDraftShapefile, finalShapefile)

    # If a third draft feature class exists check for multiple features if multiple features exists dissolve fcs if not rename is count is not greater than 1
    if Exists(thirdDraftShapefile):
        count = int(GetCount_management(thirdDraftShapefile)[0])

        if count > 1:
            from arcpy import Dissolve_management
            Dissolve_management(thirdDraftShapefile, finalShapefile,"FID", "", "","DISSOLVE_LINES")
        else:
            # Rename feature class
            Rename_management(thirdDraftShapefile, finalShapefile)
    else:
        pass

# Gather geometries from separate range ring feature classes (unprojected)
geometryList_unprj = []
for rangeValue in rangeList:
    draftShapefile = "draft_" + rangeValue + ".shp"
    for row in da.SearchCursor(draftShapefile, ["SHAPE@"]):
        geometryList_unprj.append(row[0])

# Create empty 02_multiple range ring feature class (unprojected)
CopyFeatures_management(geometryList_unprj, "multirangering_unprj.shp")

# Add new field containing system name (system range distance unit)
AddField_management("multirangering_unprj.shp", "ISO3", "TEXT", "", "", "3", "Country Trigraph")

# Add new field containing system name (system range distance unit)
AddField_management("multirangering_unprj.shp", "cntry_name", "TEXT", "", "", "50", "Country Name")

# Add new field containing system name (system range distance unit)
AddField_management("multirangering_unprj.shp", "range", "TEXT", "", "", "8", "System Range")

# Add new field containing system name (system range distance unit)
AddField_management("multirangering_unprj.shp", "sys_info", "TEXT", "", "", "10", "System Information")

# Add new field containing system name (system range distance unit)
AddField_management("multirangering_unprj.shp", "NAME", "TEXT", "", "", "50", "System Summary")

# For each row, match system range up with country and system layer symbology information
with da.UpdateCursor("multirangering_unprj.shp", ['ISO3', 'cntry_name', 'range', 'sys_info']) as cursor:
    count = 0

    for row in cursor:
        row[0] = countryTrigraph
        row[1] = countryName
        row[2] = rangeList[count]
        row[3] = symbologyValueList[count].replace("'","")

        count += 1
        
        # Update the cursor with new system information
        cursor.updateRow(row)

    del cursor

# Gather geometries from separate range ring feature classes (projected)
geometryList_prj = []
for rangeValue in rangeList:
    finalShapefile = "final_" + rangeValue + ".shp"
    for row in da.SearchCursor(finalShapefile, ["SHAPE@"]):
        geometryList_prj.append(row[0])

# Create empty 02_multiple range ring feature class (projected)
CopyFeatures_management(geometryList_prj, "multirangering.shp")

# Add new field containing system name (system range distance unit)
AddField_management("multirangering.shp", "ISO3", "TEXT", "", "", "3", "Country Trigraph")

# Add new field containing system name (system range distance unit)
AddField_management("multirangering.shp", "cntry_name", "TEXT", "", "", "50", "Country Name")

# Add new field containing system name (system range distance unit)
AddField_management("multirangering.shp", "range", "TEXT", "", "", "8", "System Range")

# Add new field containing system name (system range distance unit)
AddField_management("multirangering.shp", "sys_info", "TEXT", "", "", "10", "System Information")

# Add new field containing system name (system range distance unit)
AddField_management("multirangering.shp", "NAME", "TEXT", "", "", "50", "System Summary")

# For each row, match system range up with country and system layer symbology information
with da.UpdateCursor("multirangering.shp", ['ISO3', 'cntry_name', 'range', 'sys_info']) as cursor:
    count = 0

    for row in cursor:
        row[0] = countryTrigraph
        row[1] = countryName
        row[2] = rangeList[count]
        row[3] = symbologyValueList[count].replace("'","")

        count += 1
        
        # Update the cursor with new system information
        cursor.updateRow(row)

    del cursor
