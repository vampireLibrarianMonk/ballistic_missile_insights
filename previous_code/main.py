# Import modules from ctypes
from ctypes import windll
from ctypes import wintypes

# Import modules from sys
from sys import argv

# Import modules from imp
from imp import load_compiled

# Import modules from os
from os import listdir
from os import path

# Import modules from Tkinter
from Tkinter import *

# Import ttk modules
import ttk

# Set variables for environment workspace and main directory (move to rangeRingModules)
fileName = path.basename(argv[0])
mainDirectory = argv[0]
mainDirectory = mainDirectory.replace(fileName, "")
dataDirectory = mainDirectory + "range_ring\\Data\\"
mainDirectory += "range_ring\\code\\"

# Import range ring modules
main_RR_Var = mainDirectory + "rangeRingModules.pyc"
load_compiled('rangeRingModules', main_RR_Var)
from rangeRingModules import getShortFilePath, writeProgramInstanceOn, writeProgramInstanceOff

# Obtain short file path for main directory
mainDirectory = getShortFilePath(mainDirectory)

# Check if a tool is already running
result = writeProgramInstanceOn(mainDirectory.replace("\\code",""))

if result == 0:
    pass
else:
    errorMessage = "Main Menu is already open."
    windll.user32.MessageBoxA(0, errorMessage, "Error Loading Program", 0)
    quit()

# Function to exit program
def quitProgram():
    writeProgramInstanceOff(mainDirectory.replace("\\code",""))
    mainMenu.destroy()

# Define 01_single range ring tool
def singleRangeRingTool():
    singleButton.config(state="disabled") # disable widget tied to tool
    singleButton.update()
    
    # Import custom modules and classes
    filePath = mainDirectory + "Single_Range_Ring.pyc"
    load_compiled('Single_Range_Ring', filePath)
    from Single_Range_Ring import rangeRing
    rangeRing = rangeRing()
    number = rangeRing.singleRangeRingGenerator()

    # Return a value of 1 when tool closes in order to enable button tied to widget
    if number == 1:
        singleButton.config(state="normal")
        singleButton.update()
    else:
        pass

# Define multiple range ring tool
def multipleRangeRingTool():
    multipleButton.config(state="disabled") # disable widget tied to tool
    multipleButton.update()
    
    # Import custom modules and classes
    filePath = mainDirectory + "Multiple_Range_Ring.pyc"    
    load_compiled('Multiple_Range_Ring', filePath)
    from Multiple_Range_Ring import rangeRing
    rangeRing = rangeRing()
    number = rangeRing.multipleRangeRingGenerator()

    # Return a value of 1 when tool closes in order to enable button tied to widget
    if number == 1:
        multipleButton.config(state="normal")
        multipleButton.update()
    else:
        pass

# Define 03_reverse range ring tool function
def reverseRangeRingTool():
    reverseButton.config(state="disabled") # disable widget tied to tool
    reverseButton.update()
    
    # Import custom modules and classes
    filePath = mainDirectory + "Reverse_Range_Ring.pyc"
    load_compiled('Reverse_Range_Ring', filePath)
    from Reverse_Range_Ring import rangeRing
    rangeRing = rangeRing()
    number = rangeRing.reverseRangeRingGenerator()

    # Return a value of 1 when tool closes in order to enable button tied to widget
    if number == 1:
        reverseButton.config(state="normal")
        reverseButton.update()
    else:
        pass

# Defeine 04_minimum range ring tool function
def minimumRangeRingTool():
    minimumButton.config(state="disabled") # disable widget tied to tool
    minimumButton.update()
    
    # Import custom modules and classes
    filePath = mainDirectory + "Minimum_Range_Ring.pyc"
    load_compiled('Minimum_Range_Ring', filePath)
    from Minimum_Range_Ring import rangeRing
    rangeRing = rangeRing()    
    number = rangeRing.minimumRangeRingGenerator()

    # Return a value of 1 when tool closes in order to enable button tied to widget
    if number == 1:
        minimumButton.config(state="normal")
        minimumButton.update()
    else:
        pass

# Define custom poi tool function
def customPOITool():
    customButton.config(state="disabled") # disable widget tied to tool
    customButton.update()
    
    # Import custom modules and classes
    filePath = mainDirectory + "Custom_POI.pyc"
    load_compiled('Custom_POI', filePath)
    from Custom_POI import rangeRing
    rangeRing = rangeRing()    
    number = rangeRing.customPOIGenerator()

    # Return a value of 1 when tool closes in order to enable button tied to widget
    if number == 1:
        customButton.config(state="normal")
        customButton.update()
    else:
        pass
    
# Build main menu
mainMenu = Tk()
mainMenu.title("Main Menu")
mainMenu.attributes('-topmost', 1)
mainMenu.attributes('-topmost', 0) # put window on top of all others

# Set frame instance and configure row, column and GUI sticky
main = ttk.Frame(mainMenu, padding="3 3 25 12")
main.grid(column=0, row=0, sticky=(N, W, E, S))
main.columnconfigure(0, weight=1)
main.rowconfigure(0, weight=1)

# Tie exiting out of program "red x" to quit command
mainMenu.protocol("WM_DELETE_WINDOW", quitProgram)

# Create button for 01_single range ring tool
singleButton = ttk.Button(main, text="Single Range Ring", state="normal", command = singleRangeRingTool, width=20)
singleButton.grid(column=0, row=0, sticky=(W,E))

# Create button for multiple range ring tool
multipleButton = ttk.Button(main, text="Multiple Range Ring", state="normal", command = multipleRangeRingTool, width=20)
multipleButton.grid(column=0, row=1, sticky=(W,E))

# Create button for 03_reverse range ring tool
reverseButton = ttk.Button(main, text="Reverse Range Ring", state="normal", command = reverseRangeRingTool, width=20)
reverseButton.grid(column=0, row=2, sticky=(W,E))

# Create button for 04_minimum range ring tool
minimumButton = ttk.Button(main, text="Minimum Range Ring", state="normal", command = minimumRangeRingTool, width=20)
minimumButton.grid(column=0, row=3, sticky=(W,E))

# Create button for custom POI tool
customButton = ttk.Button(main, text="Custom POI Tool", state="normal", command = customPOITool, width=20)
customButton.grid(column=0, row=4, sticky=(W,E))

# Create butotn for quiting program
exitButton = ttk.Button(main,text="Exit Program",command=quitProgram,width=20)
exitButton.grid(column=0,row=5,sticky=(W,E))

# Determine widget spacing
for child in main.winfo_children():
    child.grid_configure(padx=20, pady=10)

# Bind escape and return keys to quit and generate map buttons 
mainMenu.bind('<Escape>', quitProgram)

mainMenu.mainloop()
