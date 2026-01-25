# Import modules from arcpy
from arcpy import CopyFeatures_management
from arcpy import da
from arcpy import env
from arcpy import MakeFeatureLayer_management
from arcpy import Near_analysis
from arcpy import SaveToLayerFile_management
from arcpy import SelectLayerByAttribute_management

# Import modules from imp
from imp import load_compiled

# Import modules from multiprocessing
from multiprocessing import Pool
from multiprocessing import cpu_count

# Import modules from os
from os import path

# Import modules from sys
from sys import argv

# Import modules from time for diagnostics
from time import strftime

# Set overwrite existing files to True
env.overwriteOutput = True

# Set variables for Data directory
fileName =  path.basename(argv[0])
directory = argv[0]

# Set variables for Data directory
fileName =  path.basename(argv[0])
codeFileDirectory = argv[0]
codeDirectory = codeFileDirectory.replace(fileName, "")
featureLayerPath = codeDirectory.replace("main code", "Experiment//feature_layers")
shapefilePath = codeDirectory.replace("main code", "Experiment//shapefiles")
dataPath = codeDirectory.replace("main code", "Experiment")
compiledCodeDirectory = codeDirectory.replace("main code", "code")
RRModules = compiledCodeDirectory + "rangeRingModules.pyc"

# Import rangeRingModules getShortFilePath
load_compiled('rangeRingModules', RRModules)
from rangeRingModules import getShortFilePath

# get short filepath for datapath
dataPath = getShortFilePath(dataPath)

# Set environment (fixes problem with spaces in directories)
env.workspace = dataPath

# Set scratch workspaces(fixes problem with spaces in directories)
scratchPath = codeDirectory.replace("main code", "scratch")
scratchPath = getShortFilePath(scratchPath)
env.scratchWorkspace = getShortFilePath(scratchPath)

# Create list of countries from world feature class
countryList = []

worldFeatureClass = da.SearchCursor("world.shp", ["NAME"])

for row in worldFeatureClass:
    if "dispute" in row[0]: # if the territory is disputed exclude from list
        pass
    else:
        countryList.append(row[0])
        
def workspaceSetup(countryList):
    # Create layer from world shapefile
    print strftime("%Y-%m-%d %H:%M:%S")
    
    worldLayerPath = featureLayerPath + "worldLayer"
    MakeFeatureLayer_management("world.shp", "worldLayer")

    MakeFeatureLayer_management("Border_Upper.shp", "Border_Upper")

    MakeFeatureLayer_management("Border_Lower.shp", "Border_Lower")

    for countryName in countryList:
        # Set sql statement for selecting country from world shapefile
        nameField = "NAME"
        queryString = '"' + nameField + '" = ' + "'" + countryName + "'"

        # Save layer from country selection
        lyr1 = SelectLayerByAttribute_management("worldLayer", "NEW_SELECTION", queryString)
        MakeFeatureLayer_management("worldLayer", countryName)
        countryLayerVariable = featureLayerPath + countryName + ".lyr"
        SaveToLayerFile_management(countryName, countryLayerVariable, "RELATIVE")

        firstBoundaryLayerPath = featureLayerPath + countryName + "_Border_Upper.lyr"
        SaveToLayerFile_management("Border_Upper", firstBoundaryLayerPath, "RELATIVE")

        secondBoundaryLayerPath = featureLayerPath + countryName + "_Border_Lower.lyr"
        SaveToLayerFile_management("Border_Lower", secondBoundaryLayerPath, "RELATIVE")
        
    ##    countryFileName = filter(str.isalnum, str(countryName))
    ##    countryShapefileVariable = shapefilePath + countryFileName + ".shp"
    ##    CopyFeatures_management(countryName, countryShapefileVariable)

    print strftime("%Y-%m-%d %H:%M:%S")

# Multiple buffer tool (x = range)
def obtain_max_distance(x):
    # create country layer variable
    countryLayerVariable = featureLayerPath + x + ".lyr"
    countryFileName = filter(str.isalnum, str(x))

    # Create feature class to measure distance between upper boundary
    firstFCSVariable = shapefilePath + countryFileName + "_upper.shp"
    CopyFeatures_management(countryLayerVariable, firstFCSVariable)

    # Create feature class to measure distance between lower boundary
    secondFCSVariable = shapefilePath + countryFileName + "_lower.shp"
    CopyFeatures_management(countryLayerVariable, secondFCSVariable)

    # Create feature class to measure distance between lower boundary
    firstBoundaryFCSVariable = shapefilePath + countryFileName + "_lower_boundary.shp"
    CopyFeatures_management("Border_Upper.shp", firstBoundaryFCSVariable)

    # Create feature class to measure distance between lower boundary
    secondBoundaryFCSVariable = shapefilePath + countryFileName + "_upper_boundary.shp"
    CopyFeatures_management("Border_Lower.shp", secondBoundaryFCSVariable)

    # Find the distance between country and upper boundary (put value in upper country fcs)
    Near_analysis(firstFCSVariable,firstBoundaryFCSVariable,"","","","GEODESIC")

    # Find the distance between country and lower boundary (put value in lower country fcs)
    Near_analysis(secondFCSVariable, secondBoundaryFCSVariable,"","","","GEODESIC")
    
def startProcess():   
    # Determine how many cpus per len of range list
    if len(countryList) > int(cpu_count()):
        cpus = int(cpu_count())
    else:
        cpus = len(countryList)

    # Set processing pool to number of cpu cores
    pool = Pool(processes = cpus)

    # Set up workspace
    workspaceSetup(countryList)
    
    # Map the processing pool to the multiprocessing function along with the range list
    pool.map(obtain_max_distance,countryList)

    # Synchronize the main process with the job and ensure proper clean up
    pool.close()
    pool.join()

if __name__ == '__main__':
    startProcess()
