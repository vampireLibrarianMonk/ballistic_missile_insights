print "Importing Modules"

# Import modules from arcpy
from arcpy import env

# Import modules from sys
from sys import argv

# Import modules from imp
from imp import load_compiled

# Import modules from os
from os import listdir
from os import path

print "Obtaining file paths"

# Set variables for environment workspace and main directory (move to rangeRingModules)
fileName = path.basename(argv[0])
mainDirectory = argv[0]
mainDirectory = mainDirectory.replace(fileName, "")
dataDirectory = mainDirectory + "range_ring\\Data"
scratchDirectory = mainDirectory + "range_ring\\scratch\\scratch.gdb"
textPath = mainDirectory + "range_ring\\txt_files\\programRunning.txt"
mainDirectory += "range_ring\\code\\"

# Import range ring modules
main_RR_Var = mainDirectory + "rangeRingModules.pyc"
load_compiled('rangeRingModules', main_RR_Var)
from rangeRingModules import clearWorkspace, clearScratchWorkspace, writeProgramInstanceOff

print "Clearing workspace"

# Clear workspace
clearWorkspace(dataDirectory)

print "Clearing scratch workspace"

# Clear scratch workspace
clearScratchWorkspace(scratchDirectory)

print "Reseting program"

# Write program off
mainDirectory = mainDirectory.replace("code","")
writeProgramInstanceOff(mainDirectory)
