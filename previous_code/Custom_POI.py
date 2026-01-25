# Import modules from arcpy
from arcpy import AddField_management
from arcpy import ApplySymbologyFromLayer_management
from arcpy import Buffer_analysis
from arcpy import ConvertCoordinateNotation_management
from arcpy import CopyFeatures_management
from arcpy import CreateTable_management
from arcpy import da 
from arcpy import Delete_management
from arcpy import Describe
from arcpy import env
from arcpy import GetCount_management
from arcpy import MakeFeatureLayer_management
from arcpy import mapping
from arcpy import Project_management
from arcpy import Rename_management
from arcpy import SaveToLayerFile_management
from arcpy import SelectLayerByLocation_management

# Import modules from ctypes
from ctypes import wintypes
from ctypes import windll

# Import modules from imp
from imp import load_compiled

# Import modules from os
from os import path
from os import environ
from os import system

# Import modules from subprocess
from subprocess import Popen

# Import modules from sys
from sys import argv

# Import modules from time for diagnostic purposes
from time import strftime

# Import modules from Tkinter
from Tkinter import *

# Import modules from ttk
import ttk

# Import ask ask save as filename modules from tk File Dialog
from tkFileDialog import asksaveasfilename

# Set variables for environment workspace and main directory (move to rangeRingModules)
fileName =  path.basename(argv[0])
mainDirectory = argv[0]
mainDirectory = mainDirectory.replace(fileName, "")
mainDirectory += "range_ring\\"
dataPath = mainDirectory + "Data"
scratchPath = mainDirectory + "scratch"

# Load compiled classification tool
main_CuPOI_Var1 = mainDirectory + "code\\classificationTool.pyc"
load_compiled('classificationTool', main_CuPOI_Var1)
from classificationTool import classTool
classTool = classTool()

# Load compiled range ring modules
main_CuPOI_Var2 = mainDirectory + "code\\rangeRingModules.pyc"
load_compiled('rangeRingModules', main_CuPOI_Var2)
from rangeRingModules import *

# Set environment workspace and main directory (fixes problem with spaces in directories)
dataPath = getShortFilePath(dataPath)
env.workspace = dataPath
env.scratchWorkspace = getShortFilePath(scratchPath)
mainDirectory = getShortFilePath(mainDirectory)

# Overwrites existing dataset
env.overwriteOutput = True

# Return Variable
variable = 1

# Declare class that holds all functions of the range ring generator
class rangeRing:

    # Declare all variables used throughout range ring generator
    def __init__(self, *args):
        # Set tool name for script running
        self.__toolName = "custom_POI_tool"

        # Set variable for current workspace of geodatabase
        self.__gdbWorkspace = dataPath

        # Variables for storing various folder paths
        self.__layerDirectory = mainDirectory + "\\layers"
        self.__workingLayerDirectory = self.__layerDirectory + "\\workingLayers\\"
        self.__imageDirectory = mainDirectory + "\\exported_images"
        self.__pdfDirectory = mainDirectory +"\\exported_pdfs"
        self.__mxdDirectory = mainDirectory + "\\MXD"
        self.__kmzDirectory = mainDirectory + "\\exported_kmls"
        self.__prjDirectory = mainDirectory + "\\PRJ"
        self.__outputFilePath = ""

        # Set variable to mxd map instance
        self.__mapTemplate = self.__mxdDirectory + "\\range_ring_template_wo_inset.mxd" 
        self.__mxd = mapping.MapDocument(self.__mapTemplate)
        
        # Class boolean values
        self.__continueProcessing = True # Set boolean variable for loops for breaking out of processes due to errors
        self.__justMapBoolean = False # Set boolean for clicking generate map button to speed up sequential processing of other formats for same map
        
        # Class dictionaries
        self.__weaponRangeDictionary = getWeaponRangeDictionary() # Retrieve weapon range dictionary
        self.__portionClassificationDictionary = portionClassificationDictionary() # Retrieve weapon portion classification dictionary
        self.__bannerClassificationDictionary = bannerClassificationDictionary() # Retrieve weapon banner classification dictionary
        self.__weaponSystemClassificationDictionary = getWeaponSystemSource() # Retrieve weapon source  

        # Variable for map title
        self.__mapTitle = ""

        # Variables for system name and system name without special characters or spaces       
        self.__systemName = ""
        self.__flatSystemName = ""

        # Variable for tracking distance unit and range in km
        self.__distanceUnit = ""
        self.__kmRange = 0
        
        # Variable tracking system ID ("country trigraph"_"system name"), range and class (SRBM, MRBM, IRBM, ICBM)
        self.__systemID = ""
        self.__systemMinRange = 0
        self.__systemMaxRange = 0
        self.__systemClass = ""

        # Variable tracking distance unit
        self.__distanceUnit = ""

        # List for user entry list
        self.__comboboxList = [] # custom list due to ttk combobox error wont take list of lists
        self.__entryList = [] 

        # List to track the two system ranges (min/max)
        self.__rangeList = []
        
        # Variables for classification variables and variables holding system name and type
        self.__classificationList = []
        self.__classificationMarkingVariable = ""
        self.__classificationPortionMarking = ""
        self.__classificationBanner = ""
        self.__declassifyOn = ""

        # Variable holding path to projection file
        self.__prjFile = ""
        
        # Set Variables for world layer and saved map location
        self.__savedWorldLayerVariable = ""
        self.__saveMapVariable = ""
        
    def customPOIGenerator(self):

        # Function asking user to choose where they want to save the file in the following formats (.jpg, .kmz or .pdf)
        def getExportFilePath():            
            file_opt = options = {}
            options['defaultextension'] = '.jpg'
            options['filetypes'] = [('JPEG', '.jpg'), ("KMZ",'.kmz'), ("PDF", '.pdf')]
            options['initialdir'] = self.__imageDirectory
            options['parent'] = mainframe
            options['title'] = 'Choose output format'

            userInput = list(asksaveasfilename(**file_opt))            

            self.__outputFilePath = (getShortFilePath(''.join(userInput).rpartition("/")[0]) + "/" +
                                      filter(str.isalnum, str(''.join(userInput).split('/')[-1].replace(" ","")[:-3])) + ''.join(userInput).split('/')[-1].replace(" ","_")[-4:])

        # Classification function
        def classify():
            # Load classification tool
            self.__classificationList = []
            self.__classificationList = classTool.classificationTool()

            # Decision loop for user classification selection

            # Manual classification higher than UNCLASSIFIED
            if len(self.__classificationList) == 4:
                classifyButton.config(state="disabled")
                classifyButton.update()

            # Manual classification UNCLASSIFIED
            elif len(self.__classificationList) == 3:
                if self.__classificationList[0] == "U":
                    classifyButton.config(state="disabled")
                    classifyButton.update()
                elif "EXERCISE" in self.__classificationList[1]:
                    classifyButton.config(state="disabled")
                    classifyButton.update()              
                else:
                    pass
                
            # Clear classification list, return classify button to normal status if no classification is selected
            else:
                self.__classificationList = []
                classifyButton.config(state="normal")
                classifyButton.update()            

            # Reenable the grab set on current tool
            root.grab_set()
  
        def quitProgram():
            # Disable all widgets exept progress bar and message display
            lat_entry.config(state="disabled")
            long_entry.config(state="disabled")
            POI_entry.config(state="disabled")
            pointList_entry.config(state="disabled")
            addButton.config(state="disabled")
            removeButton.config(state="disabled")
            classifyButton.config(state="disabled")
            generateButton.config(state="disabled")
            resetButton.config(state="disabled")
            exitButton.config(state="disabled")
            mapTitle_entry.config(state="disabled")
            sysName_entry.config(state="disabled")
            sysMinRange_entry.config(state="disabled")
            sysMaxRange_entry.config(state="disabled")
            distance_entry.config(state="disabled")
            
            # Reset status bar  
            valueSet.set(0)
            statusBar.update()     

            # Clean scratch workspace
            displayText.set("Cleaning scratch workspace...")
            statusMessage.update()
            
            clearScratchWorkspace(scratchPath)

            # Step progressbar up 18 units
            valueSet.set(18)
            statusBar.update()
            
            # Clean data folder
            displayText.set("Cleaning data folder...")
            statusMessage.update()
            
            clearWorkspace(dataPath)

            # Step progressbar up 18 units
            valueSet.set(36)
            statusBar.update()
            
            # Clean working directory
            displayText.set("Cleaning working directory...")
            statusMessage.update()
            
            clearWorkingLayerDirectory(self.__workingLayerDirectory)

            # Step progressbar up 18 units
            valueSet.set(54)
            statusBar.update()  

            displayText.set("Deleting temporary layers...")
            statusMessage.update()

            # Delete temporary layers
            Delete_management("worldLayer")
            Delete_management("donut_layer")
            Delete_management("meridian_layer")
            Delete_management("minMaxRangeRing")
            Delete_management("Points of Interest")

            if self.__systemName and self.__systemClass and self.__systemMinRange and self.__distanceUnit and self.__systemMaxRange and self.__distanceUnit:
                rangeRing_unprj = self.__systemName + " " + self.__systemClass + " : Min range: " + str('{:,}'.format(self.__systemMinRange)) + " " + self.__distanceUnit + " Max range: " + str('{:,}'.format(self.__systemMaxRange)) + " " + self.__distanceUnit
                Delete_management(rangeRing_unprj)
            else:
                pass

            # Step progressbar up 18 units
            valueSet.set(72)
            statusBar.update()  

            displayText.set("Exiting program...")
            statusMessage.update()

            # Step progressbar up 18 units
            valueSet.set(90)
            statusBar.update() 
                    
            # Exit Program 
            root.destroy()

        def reset():
            # Disable all widgets exept progress bar and message display
            lat_entry.config(state="disabled")
            long_entry.config(state="disabled")
            POI_entry.config(state="disabled")
            pointList_entry.config(state="disabled")
            addButton.config(state="disabled")
            removeButton.config(state="disabled")
            classifyButton.config(state="disabled")
            generateButton.config(state="disabled")
            resetButton.config(state="disabled")
            exitButton.config(state="disabled")
            mapTitle_entry.config(state="disabled")
            sysName_entry.config(state="disabled")
            sysMinRange_entry.config(state="disabled")
            sysMaxRange_entry.config(state="disabled")
            distance_entry.config(state="disabled")
            
            # Reset status bar  
            valueSet.set(0)
            statusBar.update()     

            # Clean scratch workspace
            displayText.set("Cleaning scratch workspace...")
            statusMessage.update()
            
            clearScratchWorkspace(scratchPath)

            # Step progressbar up 18 units
            valueSet.set(18)
            statusBar.update()
            
            # Clean data folder
            displayText.set("Cleaning data folder...")
            statusMessage.update()
            
            clearWorkspace(dataPath)

            # Step progressbar up 18 units
            valueSet.set(36)
            statusBar.update()
            
            # Clean working directory
            displayText.set("Cleaning working directory...")
            statusMessage.update()
            
            clearWorkingLayerDirectory(self.__workingLayerDirectory)

            # Step progressbar up 18 units
            valueSet.set(54)
            statusBar.update()  

            displayText.set("Deleting temporary layers...")
            statusMessage.update()

            # Delete temporary layers
            Delete_management("worldLayer")
            Delete_management("donut_layer")
            Delete_management("meridian_layer")
            Delete_management("minMaxRangeRing")
            Delete_management("Points of Interest")

            if self.__systemName and self.__systemClass and self.__systemMinRange and self.__distanceUnit and self.__systemMaxRange and self.__distanceUnit:
                rangeRing_unprj = self.__systemName + " " + self.__systemClass + " : Min range: " + str('{:,}'.format(self.__systemMinRange)) + " " + self.__distanceUnit + " Max range: " + str('{:,}'.format(self.__systemMaxRange)) + " " + self.__distanceUnit
                Delete_management(rangeRing_unprj)
            else:
                pass

            # Step progressbar up 18 units
            valueSet.set(72)
            statusBar.update()  

            # Restore buttons, comboboxes and status line to their default status and value
            displayText.set("Reseting GUI...")
            statusMessage.update()
            
            latEntry.set("")
            lat_entry.config(state="normal")
            lat_entry.update()
            
            longEntry.set("")
            long_entry.config(state="normal")
            long_entry.update()

            POIText.set("")
            POI_entry.config(state="normal")
            POI_entry.update()

            mapTitle.set("")
            mapTitle_entry.config(state="normal")
            mapTitle_entry.update()

            sysName.set("")
            sysName_entry.config(state="normal")
            sysName_entry.config(values = consolidatedWeaponsList)
            sysName_entry.update()
            
            sysMinRange.set("")
            sysMinRange_entry.config(state="normal")
            sysMinRange_entry.update()
            
            sysMaxRange.set("")
            sysMaxRange_entry.config(state="normal")
            sysMaxRange_entry.update()

            self.__entryList = []
            entryListName.set("")
            pointList_entry.config(values=self.__entryList)
            pointList_entry.config(state="normal")
            pointList_entry.update()

            addButton.config(state="normal")
            addButton.update()

            removeButton.config(state="disabled")
            removeButton.update()
            
            distanceVariable.set("")
            distance_entry.config(state="readonly")
            distance_entry.update()

            classifyButton.config(state="readonly")
            classifyButton.update()

            generateButton.config(state="normal")
            resetButton.config(state="normal")
            exitButton.config(state="normal")

            # Reset variables to their original values
            self.__classificationList = []

            # Reset boolean values for just map and manual entry
            self.__justMapBoolean = False
            self.__manualEntryBoolean = False

            # Set variable to original mxd map instance
            self.__mapTemplate = self.__mxdDirectory + "\\range_ring_template_wo_inset.mxd"
            self.__mxd = mapping.MapDocument(self.__mapTemplate)

            # Set focus to system name entry
            lat_entry.focus()

            # Step progressbar up 18 units
            valueSet.set(90)
            statusBar.update()

            # Clear message display
            displayText.set("")
            statusMessage.update()

            # Reset progressbar
            valueSet.set(0)
            statusBar.update()

        # Dynamic range match to present system name entered
        def rangeMatch(*args):        
            for key, value in self.__weaponRangeDictionary.iteritems():
                if sysName.get() == key[4:]:
                    sysMaxRange.set(value)
                    sysMaxRange_entry.update()
                    distanceVariable.set("km")
                    distance_entry.update()
                    sysName_entry.position = sysName_entry.index(END) # go to end (no selection)
                    break
                else:
                    if sysName.get() == "":
                        pass
                    else:
                        sysMaxRange.set("No range found for system entered")                        
                        sysMaxRange_entry.update()
                        if distance_entry.instate(['disabled']):
                            pass
                        else:
                            distanceVariable.set("")
                            distance_entry.update()

        # Forward arguments to dynamic match routine in range ring modules and returns a the closest weapon system name match in country list
        def weaponSystemDynamicMatch(event):
            dynamicMatch(event, sysName_entry, consolidatedWeaponsList, sysName)
            rangeMatch()

            if sysName_entry.get() == "":
                sysMaxRange.set("")
                sysMaxRange_entry.update()
                sysName_entry.config(values=consolidatedWeaponsList)
            else:
                pass

        # Remove user selection from point entry list
        def removeUserSelection():
            # Remove values from list that goes into combobox and list used for creating points
            userChoice = pointList_entry.get()
            self.__comboboxList.remove(userChoice)
            self.__entryList.remove([userChoice[0:7],userChoice[9:17],userChoice[19:]])

            entryListName.set("")
            pointList_entry.config(values=self.__comboboxList)
            pointList_entry.update()
            
        # Adds user entry into system entry list       
        def addUserSelection():
            while self.__continueProcessing == True:
                try:
                    lattitude = lat_entry.get()
                    
                    if lattitude == "":
                        errorMessage = "Please enter a value for lattitude"
                        raise ValueError
                    else:
                        pass

                    if len(lattitude) != 7:
                        errorMessage = "Lattitude value must be 7 characters long (ex. 905959N)"
                        raise ValueError                              
                    elif int(lattitude[0:2]) >= 90:
                        errorMessage = "Degrees cannot equal or exceed 90"
                        raise ValueError
                    elif lattitude[2:4] == "":
                        errorMessage = "Please enter value for Minutes"
                        raise ValueError                
                    elif int(lattitude[2:4]) >= 60:
                        errorMessage = "Minutes cannot equal or exceed 60"
                        raise ValueError
                    elif lattitude[4:6] == "":
                        errorMessage = "Please enter value for Seconds"
                        raise ValueError
                    elif int(lattitude[4:6]) >= 60:
                        errorMessage = "Seconds cannot equal or exceed 60"
                        raise ValueError
                    elif lattitude[6] != "N" and lattitude[6] != "S":
                        errorMessage = 'Last character must be either "N" (North) or "S" (South)'
                        raise ValueError
                    else:
                        pass
                except:
                    windll.user32.MessageBoxA(0, errorMessage, "Lattitude Entry Error", 0)
                    break

                try:
                    longitude = long_entry.get()
                    
                    if longitude == "":
                        errorMessage = "Please enter a value for longitude"
                        raise ValueError
                    elif len(longitude) != 8:
                        errorMessage = "Longitude value must be 8 characters long (ex. 1805959E)"
                        raise ValueError                
                    elif int(longitude[0:3]) >= 180:
                        errorMessage = "Degrees cannot equal or exceed 180"
                        raise ValueError
                    elif longitude[3:5] == "":
                        errorMessage = "Please enter value for Minutes"
                        raise ValueError                
                    elif int(longitude[3:5]) >= 60:
                        errorMessage = "Minutes cannot equal or exceed 60"
                        raise ValueError
                    elif longitude[5:7] == "":
                        errorMessage = "Please enter value for Seconds"
                        raise ValueError
                    elif int(longitude[5:7]) >= 60:
                        errorMessage = "Seconds cannot equal or exceed 60"
                        raise ValueError
                    elif longitude[7] != "E" and longitude[7] != "W":
                        errorMessage = 'Last character must be either "E" (East) or "W" (West)'
                        raise ValueError
                    else:
                        pass
                except:
                    windll.user32.MessageBoxA(0, errorMessage, "Longitude Entry Error", 0)
                    break

                # Retrieve name of place
                try:
                    POIName = POI_entry.get()

                    if POIName == "":
                        errorMessage = "Please enter a name for the coordinates entered."
                        raise ValueError
                    elif len(POIName) > 30:
                        errorMessage = "Please keep length of name to 30 characters." + "\n" + "Number of characters entered: " + str(len(POIName))
                        raise ValueError                
                    else:
                        pass
                except:
                    windll.user32.MessageBoxA(0, errorMessage, "POI Name Entry Error", 0)
                    break
               
                # Update point entry list with user entry
                userEntry = str(lattitude) + ", " + str(longitude) + ", " + POIName
                self.__comboboxList.append(userEntry)
                
                entryListName.set(userEntry)
                
                self.__entryList.append([lattitude,longitude,POIName])
                pointList_entry.config(values=self.__comboboxList)
                pointList_entry.update()

                # Clear lattitude and longitude entry
                latEntry.set("")
                lat_entry.update()

                longEntry.set("")
                long_entry.update()

                POIText.set("")
                POI_entry.update()

                if removeButton.instate(['disabled']):
                    removeButton.config(state="normal")
                    removeButton.update()
                else:
                    pass

                break

        def calculate(*args):
            while self.__continueProcessing == True:
                
                if self.__justMapBoolean == True:
                    pass
                else:
                    # Retrieve title of map
                    try:
                        self.__mapTitle = mapTitle_entry.get()

                        if self.__mapTitle == "":
                            errorMessage = "Please enter a map title."
                            raise ValueError
                        elif len(self.__mapTitle) > 45:
                            errorMessage = "Map title cannot exceed 45 characters."
                            raise ValueError
                        else:
                            pass                
                    except:
                        windll.user32.MessageBoxA(0, errorMessage, "Map Title Entry Error", 0)
                        break

                    # Retrieve system name
                    try:
                        self.__systemName = sysName_entry.get()
                        if self.__systemName == "":
                            errorMessage = "Please enter system name"
                            raise ValueError                
                    except:
                        windll.user32.MessageBoxA(0, errorMessage, "System Name Entry Error", 0)
                        break
                    
                    # Delete all invalid characters (keeping "-", alphabet, "0123456789")                
                    self.__flatSystemName = filter(str.isalnum, str(self.__systemName)) #converted to string due to unknown error out of blue (started 09 May 2015)
                    
                    # Raises error message if no 04_minimum range is entered or an a range other than an integer is entered
                    try:
                        self.__systemMinRange = sysMinRange_entry.get()
                        self.__systemMinRange = self.__systemMinRange.replace(",", "")
                        self.__systemMinRange = int(self.__systemMinRange)
                    except:
                        windll.user32.MessageBoxA(0, "Please enter a whole number for the 04_minimum range.", "Invalid System Range Entry", 0)
                        break

                    # Raises error message if no maximum range is entered or an a range other than an integer is entered
                    try:
                        self.__systemMaxRange = sysMaxRange_entry.get()
                        self.__systemMaxRange = self.__systemMaxRange.replace(",", "")
                        self.__systemMaxRange = int(self.__systemMaxRange)
                    except:
                        windll.user32.MessageBoxA(0, "Please enter a whole number for the maximum range.", "Invalid System Range Entry", 0)
                        break      

                    # Determine class of missile
                    self.__systemRange = self.__systemMaxRange
                    self.__systemClass, self.__kmRange = getSystemClass(self)
         
                    try:
                        if distance_entry.get() == "":
                            errorMessage = "Please enter a distance unit for the system range" + "\nExample Unit: km or nm"
                            raise ValueError
                        else:
                            self.__distanceUnit = distance_entry.get()
                    except:
                        windll.user32.MessageBoxA(0, errorMessage, "Distance Unit Missing", 0)
                        break   

                    # Get classification from user, if not display error
                    try:
                        # Get user entry (portion marking, classification banner, Derived From and Declassify On)                  
                        if not self.__classificationList:
                            errorMessage = "Please classify your entries appropriately"
                            errorHeader = "Product Classification Required"
                            raise ValueError                
                        else:
                            pass
                    except:
                        windll.user32.MessageBoxA(0, errorMessage, errorHeader, 0)
                        break

                # Get the output directory from the user
                getExportFilePath()
                
                if self.__outputFilePath.replace(" ","") == "/":
                    displayText.set("Paused by User")
                    statusMessage.update()
                    break
                else:
                    pass
                
                # Diagnostic time stamp print
                print strftime("%Y-%m-%d %H:%M:%S")
                
                # Reset status bar
                valueSet.set(0)
                statusBar.update()                           

                # Disable all entries except map format choice when program runs
                latEntry.set("")
                lat_entry.config(state="disabled")
                lat_entry.update()
                
                longEntry.set("")
                long_entry.config(state="disabled")
                long_entry.update()
                
                POIText.set("")
                POI_entry.config(state="disabled")
                POI_entry.update()

                mapTitle_entry.config(state="disabled")
                mapTitle_entry.update()

                sysMinRange_entry.config(state="disabled")
                sysMinRange_entry.update()
                
                sysMaxRange_entry.config(state="disabled")
                sysMaxRange_entry.update()

                sysName_entry.config(state="disabled")
                sysName_entry.update()
                
                pointList_entry.config(state="disabled")
                pointList_entry.update()
                
                distance_entry.config(state="disabled")
                distance_entry.update()

                classifyButton.config(state="disabled")
                classifyButton.update()

                addButton.config(state="disabled")
                addButton.update()

                removeButton.config(state="disabled")
                removeButton.update()

                generateButton.config(state="disabled")
                generateButton.update()
                
                resetButton.config(state="disabled")
                resetButton.update()
                
                exitButton.config(state="disabled")
                exitButton.update()            
                
                displayText.set("Processing Input")
                statusMessage.update()

                if self.__justMapBoolean == True:
                    pass
                else:
                    # Make a layer from the world feature class
                    MakeFeatureLayer_management("world.shp", "worldLayer")
                    worldLayerVariable = "worldLayer" + ".lyr"
                    self.__savedWorldLayerVariable = self.__workingLayerDirectory + worldLayerVariable
                    SaveToLayerFile_management("worldLayer", self.__savedWorldLayerVariable, "RELATIVE")

                valueSet.set(30)
                statusBar.update()

                displayText.set("Creating System Range Ring")
                statusMessage.update()

                if self.__justMapBoolean == True:
                    pass
                else:                
                    bufferPolygon()
                
                valueSet.set(60)
                statusBar.update()

                displayText.set("Creating Map")
                statusMessage.update()

                messageNumber = processMap()
                
                if messageNumber == 2:
                    displayText.set("Paused by User")
                    statusMessage.update()                 
                else:                    
                    displayText.set("Range Ring Map Created")
                    statusMessage.update()
                    valueSet.set(90)
                    statusBar.update()

                generateButton.config(state="normal")
                generateButton.update()
                
                resetButton.config(state="normal")
                resetButton.update()
                
                exitButton.config(state="normal")
                exitButton.update()  
                
                if self.__justMapBoolean == True:
                    pass
                else:
                    # Set boolean to true so sequential format don't take as long
                    self.__justMapBoolean = True

                # Diagnostic time stamp print
                print strftime("%Y-%m-%d %H:%M:%S")            
                
                break
                            
        def bufferPolygon():
            # Create temporary table
            CreateTable_management(env.workspace, "tempTable.dbf")

            # Create lattitude and longitude fields
            AddField_management("tempTable.dbf","LATTITUDE","TEXT","","",7,"Lattitude","NON_NULLABLE","REQUIRED")
            AddField_management("tempTable.dbf","LONGITUDE","TEXT","","",8,"Longitude","NON_NULLABLE","REQUIRED")
            AddField_management("tempTable.dbf","POI_NAME","TEXT","","",30,"POI Name","NON_NULLABLE","REQUIRED")

            # Start an edit seesion
            edit = da.Editor(env.workspace)
            edit.startEditing()
            edit.startOperation()

            # Insert user input into table
            POI_Name_List = []
            with da.InsertCursor("tempTable.dbf",("LATTITUDE", "LONGITUDE", "POI_NAME")) as cursor:
                for entry in self.__entryList:
                    cursor.insertRow(entry)
                    POI_Name_List.append(entry[2])

            # Stop edit operation
            edit.stopOperation()

            # Stop edit session and save changes
            edit.stopEditing(True)

            # Create the point feature class
            ConvertCoordinateNotation_management("tempTable.dbf","POI_FCS",'LONGITUDE','LATTITUDE')

            # Delete temporary table
            Delete_management("tempTable.dbf")
            
            # Find centroid of points created
            XCoordinateList = []
            
            # Add centroid x coordinate to the x coordinate list    
            for row in da.SearchCursor("POI_FCS.shp", ["SHAPE@X"]):
                XCoordinateList.append(row[0])
                
            # Set Central Meridian variable and adapt projection to center on points of interest
            centroid = int(sum(XCoordinateList)/len(XCoordinateList))        
            self.__prjFile = adaptPRJ("POI", centroid, self.__prjDirectory)        
            
            # Create variables for buffer tool
            draftMinBufferName = self.__flatSystemName + "_" + str(self.__systemMinRange) + "_draft.shp"
            draftMaxBufferName = self.__flatSystemName + "_" + str(self.__systemMaxRange) + "_draft.shp"
            
            bufferMinFeatureName = self.__flatSystemName + "_" + str(self.__systemMinRange) + ".shp"
            bufferMaxFeatureName = self.__flatSystemName + "_" + str(self.__systemMaxRange) + ".shp"
            
            minBufferDistance = str(self.__systemMinRange) + " " + str(distanceDictionary[distanceVariable.get()])
            maxBufferDistance = str(self.__systemMaxRange) + " " + str(distanceDictionary[distanceVariable.get()]) 

            # Execute buffer tool for 04_minimum range
            Buffer_analysis("POI_FCS.shp", draftMinBufferName, minBufferDistance, "", "", "", "")        

            # Execute buffer tool for maximum range
            Buffer_analysis("POI_FCS.shp", draftMaxBufferName, maxBufferDistance, "", "", "", "")

            # Set up variables for erase equivalent processing
            maxArrayList = []
            minArrayList = []
            donutArrayList = []
            count = 0

            # Record polygon geometries in maximum range buffer
            for maxLayer in da.SearchCursor(draftMaxBufferName, ["SHAPE@"]):
                    maxArrayList.append(maxLayer[0])

            # Record polygon geometries in 04_minimum range buffer
            for minLayer in da.SearchCursor(draftMinBufferName, ["SHAPE@"]):
                    minArrayList.append(minLayer[0])

            # Erase 04_minimum range from maximum range buffer and add to list
            for polygon in maxArrayList:
                    donut = polygon.difference(minArrayList[count])
                    count += 1
                    donutArrayList.append(donut)           

            # Create feature class containing erased polygons
            CopyFeatures_management(donutArrayList, "donut.shp")

            # Make buffer into feature layer for select by location decision loop
            MakeFeatureLayer_management("donut.shp", "donut_layer")

            # Make newly projected meridian feature class into feature layer for select by location decision loop
            MakeFeatureLayer_management("meridian.shp", "meridian_layer")

            # Select by location, if buffer falls within meridian then perform intersect, merge and dissolve new output feature class
            SelectLayerByLocation_management('donut_layer','INTERSECT',"meridian_layer")

            # Set variable for decision loop determining how many intersections occur between the projected buffer and the meridian layer
            matchCount = int(GetCount_management('donut_layer')[0])

            if matchCount > 0:
                ## Alternate Project newly created 04_minimum range buffer feature class
                Project_management("donut.shp", "prj_buffer.shp", self.__prjFile)

                # Aggregate newly created 04_minimum range buffer feature class to get rid of anti-meridian artifacts
                # Only if the range is less than 5499 km (avoids anti-meridian error (to replicate take this out and put SS-18 Mod 5
                # or TD-2 2 stage and look to east of anti-meridian))
                if self.__kmRange > 5499:
                    Rename_management("prj_buffer.shp", "minMaxRangeRing.shp", "FeatureClass")
                else:
                    from arcpy import AggregatePolygons_cartography
                    AggregatePolygons_cartography("prj_buffer.shp", "minMaxRangeRing.shp", "1 Centimeter")
            else:
                # Project newly created 04_minimum range buffer feature class
                Project_management("donut.shp", "minMaxRangeRing.shp", self.__prjFile)

            # Add POI_NAME field to minMaxRangeRing feature class
            AddField_management("minMaxRangeRing.shp","POI_Name","TEXT","","",30,"POI_NAME","NULLABLE","REQUIRED")

            # Update unprojected range ring to system name, system range and distance unit
            # Add field name "Name"
            AddField_management("donut.shp","Name","TEXT","","",30,"Place Name","NULLABLE","REQUIRED")
            
            with da.UpdateCursor("donut.shp", ['Name']) as cursor:
            # For each row, match system range up with system information (Missile 1, Missile 2, Missile 3...)
                count = 0
                for row in cursor:
                    row[0] = POI_Name_List[count]
                    count += 1

                    # Update the cursor with updated system information
                    cursor.updateRow(row)

            # Insert place names into projected range ring feature class
            count = 0
            cursor =  da.UpdateCursor("minMaxRangeRing.shp", "POI_NAME")
            for row in cursor:
                row[0] = POI_Name_List[count]
                cursor.updateRow(row)
                count +=1
                if count < len(POI_Name_List):
                    pass
                else:
                    break

        # Function split into two sections, once generate map button is pressed the sequential presses will immediately go to section 2
        def processMap():

            if self.__justMapBoolean == True:
                pass
            else:
            
                # Section 1 create the MXD to put into the available format options

                # Make and save POI_FCS layer
                #layerName = self.__mapTitle + " " + self.__systemName + " " + self.__systemClass
                MakeFeatureLayer_management("POI_FCS.shp", "Points of Interest")
                POILayer = self.__mapTitle + ".lyr"
                savedPOILayer = self.__workingLayerDirectory + POILayer
                SaveToLayerFile_management("Points of Interest", savedPOILayer, "RELATIVE")

                # Set variable for unprojected range ring layer
                rangeRing_unprj = self.__systemName + " " + self.__systemClass + " : Min range: " + str('{:,}'.format(self.__systemMinRange)) + " " + self.__distanceUnit + " Max range: " + str('{:,}'.format(self.__systemMaxRange)) + " " + self.__distanceUnit
            
                # Make and save unprojected range ring layer
                MakeFeatureLayer_management("donut.shp", rangeRing_unprj)
                rangeRingLayer_unprj = "minMaxRangeRing_unprj.lyr"
                savedRangeRingLayer_unprj = self.__workingLayerDirectory + rangeRingLayer_unprj
                SaveToLayerFile_management(rangeRing_unprj, savedRangeRingLayer_unprj, "RELATIVE")        

                # Set variable for range ring layer
                rangeRing = "minMaxRangeRing.shp"
            
                # Make and save range ring layer
                MakeFeatureLayer_management(rangeRing, "minMaxRangeRing")
                rangeRingLayer = "minMaxRangeRing.lyr"
                savedRangeRingLayer = self.__workingLayerDirectory + rangeRingLayer
                SaveToLayerFile_management("minMaxRangeRing", savedRangeRingLayer, "RELATIVE")

                # Set layer variables
                POIlyr = mapping.Layer(savedPOILayer)            
                ringlyr = mapping.Layer(savedRangeRingLayer)
                ringlyr_unprj = mapping.Layer(savedRangeRingLayer_unprj) 
                elementWorldlyr = mapping.Layer(self.__savedWorldLayerVariable)
                elementWorldTopoLayerVariable = self.__layerDirectory + "\\World_Topo_Map.lyr"
                elementWorldTopoLayer = mapping.Layer(elementWorldTopoLayerVariable)

                # Set Variables for rangeRing and elementWorldLayer variables
                symbologyPOILayer = self.__layerDirectory + "\\POI.lyr"
                symbologyRingLayerVariable = self.__layerDirectory + "\\min_max_range_ring.lyr"
                symbologyElementWorldLayer = self.__layerDirectory + "\\element_2_world.lyr"           
                symbologyRingLayer = mapping.Layer(symbologyRingLayerVariable)
                symbologyElementWorldLayer = mapping.Layer(symbologyElementWorldLayer)
                
                # Set the legend element
                legend = mapping.ListLayoutElements(self.__mxd, "LEGEND_ELEMENT", "Legend")[0]

                # Set data frame object for element data frame
                dataFrameElement = mapping.ListDataFrames(self.__mxd, "element")[0]

                # Set data frame object for custom data frame
                self.__frame4KMZ = mapping.ListDataFrames(self.__mxd)[1] 

                # Add points of interest, range ring, world feature classes and world topo as layers to element dataframe
                legend.autoAdd = True
                ApplySymbologyFromLayer_management(ringlyr, symbologyRingLayer) # apply symbology
                mapping.AddLayer(dataFrameElement, ringlyr, "TOP")
                ApplySymbologyFromLayer_management(POIlyr, symbologyPOILayer) # apply symbology
                mapping.AddLayer(dataFrameElement, POIlyr)
                legend.autoAdd = False            
                ApplySymbologyFromLayer_management(elementWorldlyr, symbologyElementWorldLayer) # apply symbology
                mapping.AddLayer(dataFrameElement, elementWorldlyr)
                mapping.AddLayer(dataFrameElement, elementWorldTopoLayer, "BOTTOM")

                # Add points of interest and range ring to custom frame dataframe
                ApplySymbologyFromLayer_management(ringlyr_unprj, symbologyRingLayer)
                mapping.AddLayer(self.__frame4KMZ, ringlyr_unprj, "TOP")
                mapping.AddLayer(self.__frame4KMZ, POIlyr)            

                # Set extent of element data frame
                dataFrameElement.extent = ringlyr.getExtent()

                # Update legend style in element data frame
                styleItem = mapping.ListStyleItems("ESRI.style", "Legend Items", "Horizontal Single Symbol Label Only")[0]
                lyr = mapping.ListLayers(self.__mxd, ringlyr, dataFrameElement)[0]
                legend = mapping.ListLayoutElements(self.__mxd, "LEGEND_ELEMENT")[0]
                legend.updateItem(lyr, styleItem)
                
                # Set location of legend if position has been changed
                legend.elementPositionX = .2696
                legend.elementPositionY = .5552

                # Set "multiRR_prj" layer symbology set show other values to False and set value field to "System_Information"
                lyr = mapping.ListLayers(self.__mxd, "minMaxRangeRing")[0]
                lyr.name = "Min range: " + str('{:,}'.format(self.__systemMinRange)) + " " + self.__distanceUnit + " Max range: " + str('{:,}'.format(self.__systemMaxRange)) + " " + self.__distanceUnit

                # Obtain current username for Classified By (Created by if UNCLASSIFIED)
                userName = environ.get("USERNAME")

                # Set variables for element configuration of map
                if "UNCLASSIFIED" in self.__classificationList[1]:
                    threeBibliography = "Created By: " + userName + " Source: " + self.__classificationList[2]
                elif "EXERCISE" in self.__classificationList[1]:
                    threeBibliography = "Created By: " + userName 
                else:
                    threeBibliography = "Classified By: " + userName + " Derived From: " + self.__classificationList[2]  + " Declassify On: " + self.__classificationList[3]

                # Obtain projection and datum information FYI will display coordinate system of feature class not dataframe
                spatialRef = Describe(rangeRing)
                coordinateSystem = str(spatialRef.SpatialReference.Name)
                coordinateSystem = coordinateSystem.replace("_", " ")
                datum = str(spatialRef.SpatialReference.GCS.datumName)
                datum = datum.replace("_", " ")

                # Set properties of element dataframe
                # List of elements (in order to configure): 3biblio, datum:, classification, subtitle, classification, title, coordinate system:
                for elm in mapping.ListLayoutElements(self.__mxd, "TEXT_ELEMENT"):
                    if elm.text == "coordinateSystem":
                        elm.text = "Coordinate System: " + coordinateSystem + "\n" + "Datum: " + datum
                        elm.elementPositionX = 10.7039
                        elm.elementPositionY = .9697
                    elif elm.text == "3biblio":
                        elm.text = threeBibliography
                        elm.elementPositionX = 10.7437
                        elm.elementPositionY = 8.1284
                    elif elm.text == "classification1":
                        elm.text = self.__classificationList[1]
                        elm.elementPositionX = 10.7739
                        elm.elementPositionY = 8.3779
                    elif elm.text == "classification2":
                        elm.text = self.__classificationList[1]
                        elm.elementPositionX = .2317
                        elm.elementPositionY = .1254
                    elif elm.text == "subtitle":
                        elm.text = self.__mapTitle 
                    elif elm.text == "title":
                        if "EXERCISE" in self.__classificationList[1]:
                            elm.text = self.__systemName + " " + self.__systemClass
                        else:
                            elm.text = self.__classificationList[0] + " " + self.__systemName + " " + self.__systemClass

                # Set variable to the MXD
                self.__saveMapVariable = self.__mxdDirectory + "\\range_ring_template_working.mxd"

                self.__mxd.saveACopy(self.__saveMapVariable)

                # Cleanup previous mxd in instance
                del self.__mxd

                # Cleanup dataframe instances
                del dataFrameElement, self.__frame4KMZ

                # Delete layer variables
                del POIlyr, ringlyr, ringlyr_unprj, elementWorldlyr, elementWorldTopoLayer, symbologyRingLayer, symbologyElementWorldLayer

                # Delete legend variable
                del legend

                # Delete spatial reference variable
                del spatialRef
           
            # Set mxd variable to newly saved map
            self.__mxd = mapping.MapDocument(self.__saveMapVariable)
            
            # Export map to user designated format
            messageNumber = exportMap(self.__outputFilePath, self.__mxd, self.__saveMapVariable)
            
            # Cleanup mxd instance
            del self.__mxd

            # Open Finished File
            if messageNumber == 2:
                pass
            else:
                Popen('start ' + self.__outputFilePath, shell=True)

            return messageNumber

        # Create GUI, name title of GUI and elevate window to topmost level
        root = Toplevel() 
        root.title("Custom Point(s) of Interest Range Ring Generator")
        root.attributes('-topmost', 1)
        root.attributes('-topmost', 0) # put window on top of all others

        # Configure GUI frame, grid, column and root weights
        mainframe = ttk.Frame(root, padding="3 3 12 12")
        mainframe.grid(column=0, row=0, sticky=(N, W, E, S))
        mainframe.columnconfigure(0, weight=1)
        mainframe.rowconfigure(0, weight=1)

        # Tie exiting out of program "red x" to quit command
        root.protocol("WM_DELETE_WINDOW", quitProgram)

        # Create variables to pass user input to program
        latEntry = StringVar()
        longEntry = StringVar()
        POIText = StringVar()
        mapTitle = StringVar()
        sysMaxRange = StringVar()
        sysName = StringVar()
        sysMinRange = StringVar()
        sysMaxRange = StringVar()
        distanceVariable = StringVar()
        entryListName = StringVar()
        valueSet = StringVar()
        displayText = StringVar()
        fmtChoice = StringVar()

        # Build dictionaries
        weaponSystemDictionary = getWeaponSystemDictionary() # Retrieve weapon system dictionary
        countryCentroidDictionary = getCountryCentroidDictionary() # Retrieve country centroid dictionary
        distanceDictionary = {"m":"Meters", "km": "Kilometers", "ft":"Feet", "mi":"Miles", "nm": "NauticalMiles","yd": "Yards"} # Create distance dictionary

        # Build lists
        weaponsMatch = [] # Initiate list variable to hold manual entry matches to system database
        consolidatedWeaponsList = consolidatedWpnsList(weaponSystemDictionary) # Create consolidated weapon system list

        # Create list to hold abbreviations for distance values
        distanceList = []
        for key, value in distanceDictionary.iteritems():
            distanceList.append(key)

        # Create entry box for lattitude
        lat_entry = ttk.Entry(mainframe,width=8,state="normal",textvariable=latEntry) 
        lat_entry.grid(column=2,row=1,columnspan=2,sticky=W)
        latLabel = ttk.Label(mainframe,text="Enter lattitude (ex. 895959N):")
        latLabel.grid(column=1,row=1,sticky=W) 

        # Create entry box for longitude
        long_entry = ttk.Entry(mainframe,width=9,state="normal",textvariable=longEntry)
        long_entry.grid(column=2,row=2,columnspan=2,sticky=W)
        longLabel = ttk.Label(mainframe,text="Enter longitude (ex. 1795959E):")
        longLabel.grid(column=1,row=2,sticky=W) 

        # Create entry box for point of interest name
        POI_entry = ttk.Entry(mainframe,width=30,state="normal",textvariable=POIText)
        POI_entry.grid(column=2,row=3,columnspan=2,sticky=W)
        POI_entryLabel = ttk.Label(mainframe,text="Enter point of interest name:")
        POI_entryLabel.grid(column=1,row=3,sticky=W)

        # Create combo box for user entry
        pointList_entry = ttk.Combobox(mainframe,width=45,state = "readonly",textvariable=entryListName)
        pointList_entry.grid(column=2,row=4,columnspan=2,sticky=W)
        ttk.Label(mainframe, text="Point Entry List:").grid(column=1,row=4,sticky=W)

        # Create button adding user entry (system name, range and distance unit) to system list
        addButton = ttk.Button(mainframe,text="Add Point",state="normal",command=addUserSelection,width=9)
        addButton.grid(column=3,row=3,sticky=E)

        # Create button removing user entry(system name, range and distance unit) to system list
        removeButton = ttk.Button(mainframe,text="Remove Point",state="disabled",command=removeUserSelection,width=13)
        removeButton.grid(column=4,row=4,sticky=E) 

        # Create name for map
        mapTitle_entry = ttk.Entry(mainframe,width=45,state="normal",textvariable=mapTitle)
        mapTitle_entry.grid(column=2,row=5,columnspan=2,sticky=W)
        mapTitle_entryLabel = ttk.Label(mainframe,text="Enter map title (i.e. Missile Garrisons):")
        mapTitle_entryLabel.grid(column=1,row=5,sticky=W)

        # Create entry box for alternate system name
        sysName_entry = ttk.Combobox(mainframe,width=30,state="normal",textvariable=sysName,values=consolidatedWeaponsList)  
        sysName_entry.bind('<KeyRelease>',weaponSystemDynamicMatch,add="+")
        sysName_entry.bind('<<ComboboxSelected>>',weaponSystemDynamicMatch, add="+")
        sysName_entry.grid(column=2,row=6,columnspan=2,sticky=W)
        sysName_entryLabel = ttk.Label(mainframe,text="System Name:")
        sysName_entryLabel.grid(column=1,row=6,sticky=W)

        # Create entry box for 04_minimum system range
        sysMinRange_entry = ttk.Entry(mainframe,width=31,state="normal",textvariable=sysMinRange)
        sysMinRange_entry.grid(column=2,row=7,columnspan=2,sticky=W)
        sysMinRangeLabel = ttk.Label(mainframe,text="System Minimum Range:")
        sysMinRangeLabel.grid(column=1,row=7,sticky=W)

        # Create entry box for maximum system range
        sysMaxRange_entry = ttk.Entry(mainframe,width=31,state="normal",textvariable=sysMaxRange)
        sysMaxRange_entry.grid(column=2,row=8,columnspan=2,sticky=W)
        sysMaxRangeLabel = ttk.Label(mainframe,text="System Maximum Range:")
        sysMaxRangeLabel.grid(column=1,row=8,sticky=W)

        # Create combobox for distance selection
        distance_entry = ttk.Combobox(mainframe,width=3,state="readonly",textvariable=distanceVariable, values=distanceList)
        distance_entry.grid(column=2,row=9,sticky=W)
        distanceEntryLabel = ttk.Label(mainframe,text="Distance Unit:")
        distanceEntryLabel.grid(column=1,row=9,sticky=W)

        # Create button that triggers the classification tool
        classifyButton = ttk.Button(mainframe,text="Classify Map",state="normal",command=classify,width=11)
        classifyButton.grid(column=2,columnspan=2, row=10,sticky=E)
        classifyLabel = ttk.Label(mainframe, text="Fact of system, at location(s) entered, having said min/max range:")
        classifyLabel.grid(column=1,columnspan=3,row=10,sticky=W)

        # Create progress bar
        statusBar = ttk.Progressbar(mainframe,orient=HORIZONTAL,length=180,mode='determinate',variable=valueSet,maximum=90) 
        statusBar.grid(column=1,row=15,sticky=W)

        # Create button for executing program
        generateButton = ttk.Button(mainframe,text="Generate Map", command=calculate)
        generateButton.grid(column=2,row=15,sticky=W)

        # Create read only entry for displaying program progress updates
        statusMessage = ttk.Entry(mainframe,width=29,state="readonly",textvariable=displayText)
        statusMessage.grid(column=1,row=16,sticky=W)

        # Create button reseting program
        resetButton = ttk.Button(mainframe,text="Reset Menu",state="normal",command=reset,width=12)
        resetButton.grid(column=4,row=15,sticky=E)

        # Create button for exiting program
        exitButton = ttk.Button(mainframe,text="Exit Program",command=quitProgram,width=12)
        exitButton.grid(column=4,row=16,sticky=E)

        # Add 5 units of padding between all elements in the frame
        for child in mainframe.winfo_children():
            child.grid_configure(padx=5, pady=5)

        # Set focus to country name entry combobox
        lat_entry.focus() 

        # Bind escape and return keys to quit and generate map buttons 
        root.bind('<Escape>', quitProgram)
        root.bind('<Return>', calculate)

        root.grab_set()
        root.wait_window()
        return variable
