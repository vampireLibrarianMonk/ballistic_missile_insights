# Import modules from arcpy
from arcpy import Buffer_analysis
from arcpy import CopyFeatures_management
from arcpy import CreateFeatureclass_management
from arcpy import env
from arcpy import MakeFeatureLayer_management
from arcpy import SelectLayerByAttribute_management
from arcpy import SimplifyPolygon_cartography

# Import modules from imp
from imp import load_compiled

# Import modules from multiprocessing
from multiprocessing import Pool
from multiprocessing import cpu_count

# Import modules from os
from os import path

# Import modules from sys
from sys import argv 

# Set overwrite existing files to True
env.overwriteOutput = True

# Set variables for Data directory
fileName =  path.basename(argv[0])
directory = argv[0]

# Import rangeRingModules getShortFilePath
mod1Var = directory.replace("special_process_1.pyc","rangeRingModules.pyc")
load_compiled('rangeRingModules', mod1Var)
from rangeRingModules import getShortFilePath

# Set variables for Data directory
fileName =  path.basename(argv[0])
multi_Buffer_Directory = argv[0]
multi_Buffer_Directory = multi_Buffer_Directory.replace(fileName, "")
dataPath = multi_Buffer_Directory.replace("code", "Data")
dataPath = getShortFilePath(dataPath)

# Set environment (fixes problem with spaces in directories)
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

# Get country file name
countryFileName = carryOverVariables[1]

# Get range list
textRangeList = carryOverVariables[4].replace("']","")
textRangeList = textRangeList.replace("['","")
textRangeList = textRangeList.replace("[","")
textRangeList = textRangeList.replace("]","")
textRangeList = textRangeList.replace(" ","")
rangeList = list(textRangeList.split(","))

# Get distance unit
distanceUnit = carryOverVariables[5]

# Get range ring resolution
rangeRingResolution = carryOverVariables[8]  

def workspaceSetup(rangeList):
    # Create layer from world shapefile
    MakeFeatureLayer_management("world.shp", "countrySelection")

    # Set sql statement for selecting country from world shapefile
    nameField = "NAME"
    queryStringOne = '"' + nameField + '" = ' + "'" + countryName + "'"

    # Create layer from country selection
    lyr1 = SelectLayerByAttribute_management("countrySelection", "NEW_SELECTION", queryStringOne)

    # For each range value create feature class for individual range ring creation
    for rangeValue in rangeList:
        # Create name variable of country with range that will go into range ring (buffer)
        bufferAroundFC = countryFileName + "_" + rangeValue + ".shp"

        # Create feature class from newly created layer
        CopyFeatures_management("countrySelection", bufferAroundFC)

        # Simplify polygon if user chooses "Low" range ring resolution
        if rangeRingResolution == "Low":
            simplifiedPolygon = bufferAroundFC.replace(".shp", "") + "_simplified.shp"
            SimplifyPolygon_cartography(bufferAroundFC, simplifiedPolygon, "POINT_REMOVE", "9 Kilometers")
        else:
            pass

# Multiple buffer tool (x = range)
def multi_buffer_tool(x):
    # Create draft range ring (buffer) variable name
    draftBufferNameFC = "draft_" + x + ".shp"

    # Set distance value along with distance unit
    distanceValue = x + " " + "Kilometers"

    # Determine feature to be buffered based on range ring resolution input
    if rangeRingResolution == "Low":
        feature2BBuffered = countryFileName + "_" + x + "_simplified.shp"
    else:
        feature2BBuffered = countryFileName + "_" + x + ".shp"

    # Process the range ring according to user range ring resolution input
    Buffer_analysis(feature2BBuffered, draftBufferNameFC, distanceValue, "", "", "", "")

def startProcess():   
    # Determine how many cpus per len of range list
    if len(rangeList) > cpu_count():
        cpus = cpu_count()
    else:
        cpus = len(rangeList)

    # Set processing pool to number of cpu cores
    pool = Pool(processes = cpus)

    # Set up workspace
    workspaceSetup(rangeList)

    # Map the processing pool to the multiprocessing function along with the range list
    pool.map(multi_buffer_tool,rangeList)

    # Synchronize the main process with the job and ensure proper clean up
    pool.close()
    pool.join() 

if __name__ == '__main__':
    startProcess()
