# Import modules from arcpy
from arcpy import CopyFeatures_management
from arcpy.da import SearchCursor
from arcpy import env

### Import modules from imp
##from imp import load_compiled

# Import modules from multiprocessing
from multiprocessing import Pool
from multiprocessing import cpu_count

### Import modules from os
##from os import path
##
### Import modules from sys
##from sys import argv
##
### Set variables for Data directory
##fileName =  path.basename(argv[0])
##data_directory = argv[0]
##
### Import rangeRingModules getShortFilePath
##mod1Var = data_directory.replace("special_process_3.pyc","rangeRingModules.pyc")
##load_compiled('rangeRingModules', mod1Var)
##from rangeRingModules import getShortFilePath
##
### Set variables for Data directory
##data_directory = data_directory.replace(fileName, "")
##dataPath = data_directory.replace("code", "Data")
##dataPath = getShortFilePath(dataPath)

# Set environment (fixes problem with spaces in directories)
env.workspace = r"C:\Users\Mr. P\Desktop\showcase\range_ring\Data\data store"

# Erase 04_minimum range buffer from maximum range buffer
def donutMaker(polygonPair):
    donut = polygonPair[0].difference(polygonPair[1])

    return donut

# Function enabling multiprocessing of Custom POIs
def multiPOI():
    # Set up variables for erase equivalent processing
    draftMaxBufferName = r"C:\Users\Mr. P\Desktop\showcase\range_ring\Data\data store\max_buffer.shp"
    draftMinBufferName = r"C:\Users\Mr. P\Desktop\showcase\range_ring\Data\data store\min_buffer.shp"
##    maxArrayList = []
##    minArrayList = []
    arrayList = []
    count = 0

    # Record polygon geometries in maximum range buffer
    for maxLayer in SearchCursor(draftMaxBufferName, ["SHAPE@"]):
            arrayList.append([maxLayer[0]])

   # Record polygon geometries in 04_minimum range buffer
    for minLayer in SearchCursor(draftMinBufferName, ["SHAPE@"]):
            arrayList[count].append(minLayer[0])
            count += 1

##    # Erase 04_minimum range from maximum range buffer and add to list
##    for polygon in maxArrayList:
##            donut = polygon.difference(minArrayList[count])
##            count += 1
##            donutArrayList.append(donut)
##    
    # Determine how many cpus per length of range list
    if len(arrayList) > int(cpu_count()):
        cpus = int(cpu_count())
    else:
        cpus = len(arrayList)

    # Set processing pool to number of cpu cores
    pool = Pool(processes = cpus)
    
    # Map the processing pool to the multiprocessing function along with the range list
    donutArrayList = pool.map(donutMaker,arrayList)

    # Flatten the list of lists
    donutArrayList = [ent for sublist in donutArrayList for ent in donutArrayList]

    for item in donutArrayList:
        print item
        print item.extent
        break

    #CopyFeatures_management(newList, r"C:\Users\Mr. P\Desktop\showcase\range_ring\Data\data store\donut.shp")

    # Synchronize the main process with the job and ensure proper clean up
    pool.close()
    pool.join()

if __name__ == '__main__':
    multiPOI()
