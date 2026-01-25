# Import py_compile module
import py_compile

# Import modules from sys
from sys import argv

# Import modules from os
from os import listdir
from os import path

# Set variables for environment workspace and main directory
fileName = path.basename(argv[0])
mainDirectory = argv[0]
mainDirectory = mainDirectory.replace(fileName, "")
compiledDirectory = mainDirectory.replace("main code", "code")

# Get list of files in main directory
dirs = listdir(mainDirectory)

# For each file check if it is a python file then compile
for thing in dirs:
        if ".py" in thing:
                py_compile.compile(thing)
        else:
                pass
