# Import modules from arcpy
from arcpy import AddField_management
from arcpy import da
from arcpy import env
from arcpy import ListFeatureClasses

# Import modules from imp
from imp import load_compiled

# Import modules from os
from os import path

# Import modules from sys
from sys import argv

# Set overwrite existing files to True
env.overwriteOutput = True

# Set variables for Data directory
fileName =  path.basename(argv[0])
directory = argv[0]

# Set variables for Data directory
fileName =  path.basename(argv[0])
codeFileDirectory = argv[0]
codeDirectory = codeFileDirectory.replace(fileName, "")
shapefilePath = codeDirectory.replace("main code", "Experiment//shapefiles")
dataPath = codeDirectory.replace("main code", "Experiment")
compiledCodeDirectory = codeDirectory.replace("main code", "code")
RRModules = compiledCodeDirectory + "rangeRingModules.pyc"

# Import rangeRingModules getShortFilePath
load_compiled('rangeRingModules', RRModules)
from rangeRingModules import getShortFilePath

# get short filepath for datapath
shapefilePath = getShortFilePath(shapefilePath)

# Set environment (fixes problem with spaces in directories)
env.workspace = shapefilePath

# Set scratch workspaces(fixes problem with spaces in directories)
scratchPath = codeDirectory.replace("main code", "scratch")
scratchPath = getShortFilePath(scratchPath)
env.scratchWorkspace = getShortFilePath(scratchPath)

# Set path to world fcs
worldFCS = dataPath + "world.shp"

# Add new field containing system name (system range distance unit)
AddField_management(worldFCS, "Max_Range", "DOUBLE", "20", "", "25", "Max Allowed Range")

# Iterate through all feature classes and set "Max_Range" to int("NEAR_DIST"/1000) - 1
for fcs in ListFeatureClasses():
    if "boundary" in fcs:
        pass
    else:
        with da.SearchCursor(fcs, ["ISO3", "NEAR_DIST"]) as fcsCursor:
            for field in fcsCursor:          
                with da.UpdateCursor(worldFCS, ['ISO3', 'Max_Range']) as worldFCSCursor:
                    for row in worldFCSCursor:
                        if row[0] == field[0]:
                            if row[0] == 0:
                                row[1] = field[1]
                                worldFCSCursor.updateRow(row)
                                print field[1]
                            elif field[1] > row[1]:
                                row[1] = field[1]
                                worldFCSCursor.updateRow(row)
                                print field[1]
                            else:
                                pass
                        else:
                            pass

                # Delete worldfcs search cursor
                #del worldFCSCursor
        # Delete fcs searchcursor
        #del fcsCursor
