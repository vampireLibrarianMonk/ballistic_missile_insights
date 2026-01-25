# Import modules needed from arcpy
from arcpy import ApplySymbologyFromLayer_management
from arcpy import Buffer_analysis
from arcpy import CopyFeatures_management
from arcpy.da import UpdateCursor
from arcpy import Delete_management
from arcpy import Describe
from arcpy import env
from arcpy import GetCount_management
from arcpy import MakeFeatureLayer_management
from arcpy import mapping
from arcpy import Project_management
from arcpy import Rename_management
from arcpy import SaveToLayerFile_management
from arcpy import SelectLayerByAttribute_management
from arcpy import SelectLayerByLocation_management
from arcpy import SimplifyPolygon_cartography

# Import modules from ctypes
from ctypes import windll
from ctypes import wintypes

# Import needed modules from imp
from imp import load_compiled

# Import modules from os
from os import path
from os import environ

# Import modules from subprocess
from subprocess import Popen

# Import modules from time for diagnostics
from time import strftime

# Import modules from sys
from sys import argv

# Import all modules from Tkinter (import all potential modules for now)
from Tkinter import *

# Import ttk modules
import ttk

# Import ask ask save as filename modules from tk File Dialog
from tkFileDialog import asksaveasfilename

# Set variables for environment and scratch workspace and main directory
fileName =  path.basename(argv[0])
mainDirectory = argv[0]
mainDirectory = mainDirectory.replace(fileName, "")
mainDirectory += "range_ring\\"
dataPath = mainDirectory + "\\Data"
scratchPath = mainDirectory + "scratch"

# Import classification tool 
main_SRR_Var1 = mainDirectory + "code\\classificationTool.pyc"
load_compiled('classificationTool', main_SRR_Var1)
from classificationTool import classTool
classTool = classTool()

# Import range ring modules
main_SRR_Var2 = mainDirectory + "code\\rangeRingModules.pyc"
load_compiled('rangeRingModules', main_SRR_Var2)
from rangeRingModules import *

# Set environment workspace and main directory (fixes problem with spaces in directories)
dataPath = getShortFilePath(dataPath)
env.workspace = dataPath
env.scratchWorkspace = getShortFilePath(scratchPath)
mainDirectory = getShortFilePath(mainDirectory)

# Overwrite existing dataset set to true
env.overwriteOutput = True

# Variable program returns when it closes to signal to the main GUI that it has indeed closed
variable = 1

# Declare class that holds all functions of the range ring generator
class rangeRing:

    # Declare all variables used throughout range ring generator
    def __init__(self, *args):
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
        self.__manualEntryBoolean = False # Set boolean variable for manual entry check box selection value
        self.__justMapBoolean = False # Set boolean for clicking generate map button to speed up sequential processing of other formats for same map
        
        # Class dictionaries
        self.__weaponRangeDictionary = getWeaponRangeDictionary() # Retrieve weapon range dictionary
        self.__portionClassificationDictionary = portionClassificationDictionary() # Retrieve weapon portion classification dictionary
        self.__bannerClassificationDictionary = bannerClassificationDictionary() # Retrieve weapon banner classification dictionary
        self.__weaponSystemClassificationDictionary = getWeaponSystemSource() # Retrieve weapon source

        # Track country selection and country trigraph
        self.__currentCountrySelection = 0 
        self.__currentCountryTrigraph = ""  

        # Variables for country name and country name without special characters or spaces
        self.__countryName = ""            
        self.__countryFileName = "" 

        # Variables for system name and system name without special characters or spaces       
        self.__systemName = ""
        self.__flatSystemName = ""

        # Variable for tracking distance unit and range in km
        self.__distanceUnit = ""
        self.__kmRange = 0

        # Variable tracking system ID ("country trigraph"_"system name"), range and class (SRBM, MRBM, IRBM, ICBM)
        self.__systemID = ""
        self.__systemRange = 0
        self.__systemClass = ""

        # Variable tracking user range ring resolution choice
        self.__resolutionChoice = ""
       
        # Variables for classification variables (portion and banner marking)
        self.__classificationList = []
        self.__classificationMarkingVariable = ""

        # Variable holding path to projection file
        self.__prjFile = ""
        
        # Set Variables for world layer and saved map location
        self.__savedWorldLayerVariable = ""
        self.__saveMapVariable = ""
        
    def singleRangeRingGenerator(self):

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
            self.__classificationList = classTool.classificationTool()

            # If classification is higher than UNCLASSIFIED then count = 4 (portion and banner marking, derived from and declassify on)
            # If classification is UNCLASSIFIED then count = 3(portion and banner marking and source)
            if len(self.__classificationList) == 4 or len(self.__classificationList) == 3:
                classifyButton.config(state="disabled")
            else:
                classifyButton.config(state="normal")

            # Reenable the grab set on current tool
            root.grab_set()

        # Clears data created during process and exits program
        def quitProgram(*args):
            # Disable all widgets exept progress bar and message display
            countryName_entry.config(state = "disabled")
            sysName_entry.config(state = "disabled")
            other_entry.config(state = "disabled")
            otherSysName_entry.config(state = "disabled")
            sysRange_entry.config(state = "disabled")
            distance_entry.config(state="disabled")
            resolutionChoice.config(state="disabled")
            generateButton.config(state="disabled")
            exitButton.config(state="disabled")
            resetButton.config(state="disabled")
          
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
            Delete_management("buffer_layer")
            Delete_management("meridian_layer")
            if self.__countryName:
                Delete_management(self.__countryName)
            else:
                pass
            if self.__flatSystemName and self.__systemRange:
                rangeRing = self.__flatSystemName + "_" + self.__systemRange
                Delete_management(rangeRing)
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

        # Clears data created during process and restores program to original condition when first loaded
        def reset():
            # Disable all widgets except progress bar and message display
            countryName_entry.config(state = "disabled")
            sysName_entry.config(state = "disabled")
            other_entry.config(state = "disabled")
            otherSysName_entry.config(state = "disabled")
            sysRange_entry.config(state = "disabled")
            distance_entry.config(state="disabled")
            resolutionChoice.config(state="disabled")
            generateButton.config(state="disabled")
            classifyButton.config(state="disabled")
            exitButton.config(state="disabled")
            resetButton.config(state="disabled")
          
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
            Delete_management("buffer_layer")
            Delete_management("meridian_layer")
            if self.__countryName:
                Delete_management(self.__countryName)
            else:
                pass
            if self.__flatSystemName and self.__systemRange:
                rangeRing = self.__flatSystemName + "_" + self.__systemRange
                Delete_management(rangeRing)
            else:
                pass

            # Step progressbar up 18 units
            valueSet.set(72)
            statusBar.update()

            # Restore buttons, comboboxes and status line to their default status and value
            displayText.set("Reseting GUI...")
            statusMessage.update()
            
            # reset Cuntry name entry
            cntryName.set("")
            countryName_entry.update()
            countryName_entry.config(state="normal")
            countryName_entry.config(values=countryList)
            countryName_entry.focus()

            # Reset system name Entry
            weaponsList = []
            sysName_entry.config(values=weaponsList)            
            sysName.set("")
            sysName_entry.update()
            sysName_entry.config(state = "readonly")

            # Reset manual entry checkbox
            other_entry.deselect()
            other_entry.config(state = "normal")

            # Other system name entry
            otherSysName.set("")
            otherSysName_entry.config(state = "disabled")
            otherSysName_entry.config(values = consolidatedWeaponsList)
            otherSysName_entry.update()

            # Reset system range entry
            sysRange.set("")
            sysRange_entry.config(state = "disabled")
            sysRange_entry.update()

            # Reset system range entry
            distanceVariable.set("")
            distance_entry.update()
            distance_entry.config(state="disabled")

            # Reset range ring resolution choice
            resolutionVariable.set("")
            resolutionChoice.update()
            resolutionChoice.config(state="readonly")

            # Enable generate, exit and reset button
            generateButton.config(state="normal")
            exitButton.config(state="normal")
            resetButton.config(state="normal")

            # Reset classification list variable
            self.__classificationList = []

            # Reset boolean values for just map and manual entry
            self.__justMapBoolean = False
            self.__manualEntryBoolean = False

            # Set map variable to original mxd map instance
            self.__mapTemplate = self.__mxdDirectory + "\\range_ring_template_wo_inset.mxd"
            self.__mxd = mapping.MapDocument(self.__mapTemplate)

            # Clear message display
            displayText.set("")
            statusMessage.update()

            # Step progressbar up 18 units
            valueSet.set(90)
            statusBar.update()

            # Reset progressbar
            valueSet.set(0)
            statusBar.update()

        # Disables weapon combo box for manual entry of system name and range
        def disableWeaponCombobox():
            # Retrieve boolean value of manual system entry if checked variable = true if not checked variable = false
            self.__manualEntryBoolean = otherSysActivate.get()
            if self.__manualEntryBoolean == True:

                # Reset system name entry to avoid previous entry from interfering with process
                sysName.set("")
                sysName_entry.update()

                # Disable weapon system combobox
                weaponsList = []
                sysName_entry.config(state = "disabled")

                # Enable manual system name entry
                otherSysName_entry.config(state = "normal")            

                # Enable manual system range entry and clear it if range was already present
                sysRange_entry.config(state = "normal")
                sysRange_entry.delete(0, END)

                # Enable distance combobox
                distance_entry.config(state="readonly")
                distanceVariable.set("")
                distance_entry.update()

                # Enable classification tool
                classifyButton.config(state="normal")
            else:            
                # Enable weapon system combobox
                sysName_entry.config(state="readonly")

                # Reset manual system name entry to avoid previous entry from interfering with process
                otherSysName_entry.delete(0, END)

                # Disable manual system name entry
                otherSysName_entry.config(state = "disabled")
                otherSysName_entry.config(values = consolidatedWeaponsList)

                # Reset manual system range entry to avoid previous entry from interfering with process
                sysRange_entry.delete(0, END)

                # Disable manual system range entry
                sysRange_entry.config(state = "disabled")

                # Disable and reset distance combobox
                distanceVariable.set("")
                distance_entry.update()
                distance_entry.config(state="disabled")

                # Decision loop to run country, weapon and range match functions if there is a country entered
                if cntryName.get() != "":
                    countryWeaponsMatch()
                    rangeMatch()
                else:
                    pass

                # Disable classification tool
                classifyButton.config(state="disabled")

        # Forward arguments to dynamic match routine in range ring modules and returns a the closest country name match in country list
        def countryDynamicMatch(event):
            dynamicMatch(event, countryName_entry, countryList, cntryName)
            if self.__manualEntryBoolean == False:  
                countryWeaponsMatch()
            else:
                pass

            if countryName_entry.get() == "":
                countryName_entry.config(values=countryList)
                countryName_entry.update()
            else:
                pass

        # Returns system list under country of choice
        def countryWeaponsMatch(*args):
            # Retrieve current entry or selection from country name combobox
            self.__currentCountrySelection = countryName_entry.get()

            # Reset weaponslist
            weaponsList = []
                         
            try:
                # Retrieve current country trigraph from current country name selection from combobox or entry  
                self.__currentCountryTrigraph = countryDictionary[self.__currentCountrySelection]

                # If there is a valid country trigraph found
                if self.__currentCountryTrigraph: 

                    # Populate the weapon system in the system name combobox
                    for ID, name in weaponSystemDictionary.iteritems():
                        currentSystemID = self.__currentCountryTrigraph + "_" + name
                        if ID == currentSystemID:
                            weaponsList.append(name)
                        else:
                            pass
            except:
                pass

            # If there are weapons systems found for the country in the country name entry, sort and populate system name combobox
            if len(weaponsList) != 0:
                weaponsList.sort()
                sysName_entry.config(values=weaponsList)
                sysName.set(weaponsList[0])
                sysName_entry.update()
                        
            # Display appropriate message if no system is present
            else:
                sysName.set("No System Available In Database") 
                sysName_entry.update()
                weaponsList = []
                sysName_entry.config(values=weaponsList)

                sysRange.set("")
                sysRange_entry.update()
                
                distanceVariable.set("")
                distance_entry.update()

            # If the country name entry is blank clear system name combobox, system range entry and unit combobox
            
            if countryName_entry.get() == "":
                sysName.set("")
                weaponsList = []
                sysName_entry.config(values=weaponsList)
                sysName_entry.update()

                sysRange.set("")
                sysRange_entry.update()

                distanceVariable.set("")
                distance_entry.update()
                
        # Dynamic range match to present system name entered
        def rangeMatch(*args):
            if self.__manualEntryBoolean == True:

                # Iterate through weapon system dictionary if there is a match with the system name entry set system range to that stored in dictionary
                for key, value in self.__weaponRangeDictionary.iteritems():
                    if otherSysName.get() == key[4:]:
                        sysRange.set(value)
                        sysRange_entry.update()
                        distanceVariable.set("km") # range in database is all in kilometers
                        distance_entry.update()
                        otherSysName_entry.position = otherSysName_entry.index(END) # go to end of other system name entry(no selection)
                        break
                    else:
                        if otherSysName.get() == "":
                            pass
                        else:
                            sysRange.set("No range found for system entered") # if no system matches entry display this message
                            sysRange_entry.update()
            elif self.__manualEntryBoolean == False:
                for key, value in self.__weaponRangeDictionary.iteritems():
                    if sysName.get() == key[4:]:
                        sysRange.set(value)
                        sysRange_entry.update()
                        distanceVariable.set("km") # range in database is all in kilometers
                        distance_entry.update()
                        break
                    else:
                        if sysName.get() == "":
                            sysRange.set("")
                            sysRange_entry.update()                        
                        else:
                            if sysName.get() == "No System Available In Database": # if country does not have weapon systems in the database display this message
                                sysRange.set("")
                                sysRange_entry.update()                                
                            else:
                                sysRange.set("No range found for system entered") # if no system matches entry display this message
                                sysRange_entry.update()            
            else:
                pass

        # Forward arguments to dynamic match routine in range ring modules and returns the closest weapon system name match in list
        def weaponSystemDynamicMatch(event):
            dynamicMatch(event, otherSysName_entry, consolidatedWeaponsList, otherSysName)
            rangeMatch()

            if otherSysName_entry.get() == "":
                sysRange.set("")
                sysRange_entry.update()
                otherSysName_entry.config(values = consolidatedWeaponsList)
            else:
                pass

        # Main creation function
        def createMap(*args):
            while self.__continueProcessing == True:

                # If the function has been run beforehand skip redundant processes
                if self.__justMapBoolean == True:
                    pass
                else:
                    # Retrieve country name from country name entry 
                    try:
                        self.__countryName = countryName_entry.get() 

                        # If the user input does not pass the autocomplete function with a valid country display error message
                        if self.__countryName not in countryList:
                            errorMessage = "Entry not present in country database"
                            raise ValueError
                        else:
                            pass
                        # Convert country name into a valid file name (Delete all invalid characters (keeping "-", alphabet, "0123456789"))
                        self.__countryFileName = filter(str.isalnum, self.__countryName)
                        self.__countryFileName += ".shp"
                    except:
                        # If country name is blank display error message
                        if self.__countryName == "":
                            errorMessage = "Please enter or choose a country"
                        windll.user32.MessageBoxA(0, errorMessage, "Entry Error", 0)
                        break

                    # Retrieve country trigraph from country name validated
                    try:
                        self.__currentCountryTrigraph = countryDictionary[self.__countryName]
                    except:
                        # If there there is no matching trigraph to country validated display program error (if displayed must be fixed immediately)
                        windll.user32.MessageBoxA(0, "No matching trigraph to country entered", "Program Error", 0)
                        break
                    
                    try:
                        # If manual entry checkbox is not selected
                        if self.__manualEntryBoolean == False:

                            # Retrieve system name from combo box
                            self.__systemName = sysName.get()                        
                        else:
                            # If manual entry checkbox is selected retrieve system name from manual entry
                            self.__systemName = otherSysName.get()                
                       
                        # Convert system name into a valid file name (Delete all invalid characters (keeping "-", alphabet, "0123456789"))                
                        self.__flatSystemName = filter(str.isalnum, str(self.__systemName)) #converted to string due to unknown error out of blue (started 09 May 2015)

                        # Raise error if no system name is entered or length of system name is greater than 25 characters or if there is no match in system database
                        # for country entered
                        if self.__systemName == "":
                            errorCode = 0
                            raise ValueError
                        elif self.__systemName == "No System Available In Database":
                            errorCode = 1
                            raise ValueError
                        elif len(self.__systemName) > 25:
                            errorCode = 2
                            raise ValueError
                        else:
                            pass
                    except:

                        # Assorted codes generating error messages
                        if errorCode == 0:
                            errorMessage = "Please enter system name" 
                            windll.user32.MessageBoxA(0, errorMessage, "Entry Error", 0)
                            break
                        elif errorCode == 1:
                            errorMessage = "No System in Database. Please use Manual Entry."
                            windll.user32.MessageBoxA(0, errorMessage, "Entry Error", 0)
                            break
                        elif errorCode == 2:
                            errorMessage = "System Name cannot 25 characters" + "\n" + "Total characters entered: " + str(len(self.__systemName) - self.__systemName.count(' '))
                            windll.user32.MessageBoxA(0, errorMessage, "Entry Error", 0)
                            break
                        else:
                            pass

                    # Raises error message if selection of "No range found for system entered" or no range is entered
                    try:
                        if self.__manualEntryBoolean == False:
                            self.__systemID = self.__currentCountryTrigraph + "_" + self.__systemName
                            self.__systemRange = str(self.__weaponRangeDictionary[self.__systemID])                            
                        else:
                            # Retrieve system range
                            self.__systemRange = sysRange_entry.get()
                            self.__systemRange = self.__systemRange.replace(",", "")
                            if self.__systemRange == "No range found for system entered":
                                errorMessage = "No range found for system entered, please use manual entry."
                                raise ValueError
                            elif self.__systemRange == "":                            
                                errorMessage = "Please enter a whole numerical value for the system range" + "\nExample Range: 3500 or 3,500"
                                raise ValueError
                            elif "." in self.__systemRange:                            
                                errorMessage = "Please enter a whole numerical value for the system range" + "\nExample Range: 3500 or 3,500"
                                raise ValueError
                            else:
                                pass
                            
                        # Routine to check if entry is an integer
                        try:
                            testVariable = int(self.__systemRange)
                            testVariable += 1
                        except:
                            errorMessage = "Please enter a whole numerical value for the system range" + "\nExample Range: 3500 or 3,500"                
                            windll.user32.MessageBoxA(0, errorMessage, "Invalid Entry", 0)
                            break                       
                    except:
                        windll.user32.MessageBoxA(0, errorMessage, "Invalid Entry", 0)
                        break
                    
                    # Retrieve distance unit, return and error if nothing is selected
                    try:
                        if distance_entry.get() == "":
                            errorMessage = "Please enter a distance unit for the system range" + "\nExample Unit: km or nm"
                            raise ValueError
                        else:
                            self.__distanceUnit = distance_entry.get()
                    except:
                        windll.user32.MessageBoxA(0, errorMessage, "Distance Unit Missing", 0)
                        break

                    # Determine class of missile and km range no matter what distance unit is chosen
                    self.__systemClass, self.__kmRange = getSystemClass(self)

                    countryMaxRangeDictionary[self.__countryName]/1000

                    # If range exceeds capability of program display error (error 99999 a buffer currently cannot cover both poles)
                    maximumRange = countryMaxRangeDictionary[self.__countryName]/1000
                    try:
                        if self.__kmRange > maximumRange:
                            if self.__distanceUnit == "km":
                                errorMessage = "System range cannot exceed " + str('{:,}'.format(int(maximumRange))) + " " + self.__distanceUnit +  "." + "\nFor the country of " + self.__countryName + "."
                                raise ValueError
                            elif self.__distanceUnit == "mi":
                                maximumRange = maximumRange / 1.60934
                                errorMessage = "System range cannot exceed " + str('{:,}'.format(int(maximumRange))) + " " + self.__distanceUnit + "." + "\nFor the country of " + self.__countryName + "."
                                raise ValueError
                            elif self.__distanceUnit == "ft":
                                maximumRange = maximumRange / 0.0003048
                                errorMessage = "System range cannot exceed " + str('{:,}'.format(int(maximumRange))) + " " + self.__distanceUnit + "." + "\nFor the country of " + self.__countryName + "."
                                raise ValueError
                            elif self.__distanceUnit == "yd":
                                maximumRange = maximumRange / 0.0009144
                                errorMessage = "System range cannot exceed " + str('{:,}'.format(int(maximumRange))) + " " + self.__distanceUnit + "." + "\nFor the country of " + self.__countryName + "."
                                raise ValueError
                            elif self.__distanceUnit == "m":
                                maximumRange = maximumRange / 0.001
                                errorMessage = "System range cannot exceed " + str('{:,}'.format(int(maximumRange))) + " " + self.__distanceUnit + "." + "\nFor the country of " + self.__countryName + "."
                                raise ValueError
                            elif self.__distanceUnit == "nm":
                                maximumRange = maximumRange / 1.852
                                errorMessage = "System range cannot exceed " + str('{:,}'.format(int(maximumRange))) + " " + self.__distanceUnit + "." + "\nFor the country of " + self.__countryName + "."
                                raise ValueError
                        else:
                            pass
                    except:
                        errorMessage += "\nPlease use Custom POI Range Ring Tool."
                        windll.user32.MessageBoxA(0, errorMessage, "Program Limitation Error", 0)
                        break 

                    # Raises error if no classification entered by user in manual entry mode
                    if otherSysActivate.get() == True:
                        try:
                            if self.__classificationList == []:
                                raise ValueError
                            else:
                                pass
                        except:
                            windll.user32.MessageBoxA(0, "Please classify map.", "User Classification Required", 0)
                            break
                    else:
                        pass

                    # Get portion marking classification from dictionary if manual entry is false, if manual entry is true set portion marking to first element of self.__classificationList
                    if self.__manualEntryBoolean == False:
                        self.__classificationMarkingVariable = self.__currentCountryTrigraph + "_" + self.__systemName
                        self.__classificationList.append(self.__portionClassificationDictionary[self.__classificationMarkingVariable])
                    else:
                        pass
                    
                    # Get banner marking classification from dictionary if manual entry is false, if manual entry is true set portion marking to second element of self.__classificationList
                    if self.__manualEntryBoolean == False:
                        self.__classificationList.append(self.__bannerClassificationDictionary[self.__classificationMarkingVariable])
                    else:
                        pass

                # Get resolution choice from user, display error if not selected
                try:
                    self.__resolutionChoice = resolutionVariable.get()
                            
                    # Raise error if no output format is selected
                    if self.__resolutionChoice == "":
                        errorMessage = "Please choose range ring resolution."
                        raise ValueError                
                    else:
                        pass
                except:
                    windll.user32.MessageBoxA(0, errorMessage, "Range Ring Resolution Missing", 0)
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

                # Disable all entries except format choice when program runs
                countryName_entry.config(state = "disabled")
                sysName_entry.config(state = "disabled")
                other_entry.config(state = "disabled")
                otherSysName_entry.config(state = "disabled")
                sysRange_entry.config(state = "disabled")
                distance_entry.config(state="disabled")
                resolutionChoice.config(state="disabled")
                generateButton.config(state="disabled")
                resetButton.config(state="disabled")
                exitButton.config(state="disabled")
            
                displayText.set("Processing Input")
                statusMessage.update()

                # If the function has been run beforehand skip redundant processes
                if self.__justMapBoolean == True:
                    pass
                else:
                    # Make a layer from the world feature class
                    MakeFeatureLayer_management("world.shp", "worldLayer")
                    worldLayerVariable = "worldLayer" + ".lyr"
                    self.__savedWorldLayerVariable = self.__workingLayerDirectory + worldLayerVariable
                    SaveToLayerFile_management("worldLayer", self.__savedWorldLayerVariable, "RELATIVE")

                    # Create query string of NAME = countryName
                    nameField = "NAME"
                    queryString = '"' + nameField + '" = ' + "'" + self.__countryName + "'"

                    # Select within world feature class the target country   
                    SelectLayerByAttribute_management("worldLayer", "NEW_SELECTION", queryString)

                    # Write the selected features to a new featureclass
                    CopyFeatures_management("worldLayer", str(self.__countryFileName))

                # Step progressbar by 30 units
                valueSet.set(30)
                statusBar.update()

                # Set message display to reflect that the creation of range ring has started
                displayText.set("Creating System Range Ring")
                statusMessage.update()

                # If the function has been run beforehand skip redundant processes
                if self.__justMapBoolean == True:
                    pass
                else:                
                    bufferPolygon() # start range ring creation (buffer)

                # Step progressbar by 60
                valueSet.set(60)
                statusBar.update()

                # Set message display to reflect that map creation has started
                displayText.set("Creating Map")
                statusMessage.update()

                # If user chooses cancel for replacing product that already exists the processmap function returns a integer of 2
                messageNumber = processMap() # start map creation

                # If an integer of 2 is returned display that the user has paused the program
                if messageNumber == 2:
                    displayText.set("Paused by User")
                    statusMessage.update()                 
                else:
                    # Display that the process has completed 
                    displayText.set("Range Ring Map Created")
                    statusMessage.update()
                    valueSet.set(90)
                    statusBar.update()
                
                generateButton.config(state="normal")                
                resetButton.config(state="normal")
                exitButton.config(state="normal")
                    
                # If the function has been run beforehand skip redundant processes
                if self.__justMapBoolean == True:
                    pass
                else:
                    # Set to true so sequential outputs don't take as long
                    self.__justMapBoolean = True

                # Diagnostic time stamp print
                print strftime("%Y-%m-%d %H:%M:%S")            
                
                break
            
        def bufferPolygon(): 
            # Create variables for buffer tool
            draftBufferName = self.__flatSystemName + "_" + self.__systemRange + "_draft.shp"
            bufferFeatureName = self.__flatSystemName + "_" + self.__systemRange + ".shp"
            bufferDistance = str(int(self.__kmRange)) + " Kilometers"

            # Simplify country boundary if user selects "Low" else create range ring
            # Original data is simplified to 3 miles
            if self.__resolutionChoice == "Low":
                simplifiedPolygon = self.__countryFileName.replace(".shp", "") + "_simplified.shp"
                SimplifyPolygon_cartography(self.__countryFileName, simplifiedPolygon, "POINT_REMOVE", "9 Kilometers")
                Buffer_analysis(simplifiedPolygon, draftBufferName, bufferDistance, "", "", "", "")
            else:
                Buffer_analysis(self.__countryFileName, draftBufferName, bufferDistance, "", "", "", "")

            # Set Central Meridian variable
            self.__prjFile = adaptPRJ(self.__currentCountryTrigraph, countryCentroidDictionary[self.__currentCountryTrigraph], self.__prjDirectory)

            # Make buffer into feature layer for select by location decision loop
            MakeFeatureLayer_management(draftBufferName, "buffer_layer")

            # Make newly projected meridian feature class into feature layer for select by location decision loop
            MakeFeatureLayer_management("meridian.shp", "meridian_layer")

            # Select by location, if buffer falls within meridian then perform intersect, merge and dissolve new output feature class
            SelectLayerByLocation_management('buffer_layer','INTERSECT',"meridian_layer")

            # Set variable for decision loop determining how many intersections occur between the projected buffer and the meridian layer
            matchCount = int(GetCount_management('buffer_layer')[0])

            if matchCount > 0:
                ## Alternate Project newly created buffer feature class
                Project_management(draftBufferName, "prj_buffer.shp", self.__prjFile)
                
                # Aggregate newly created buffer feature class to get rid of anti-meridian artifacts
                from arcpy import AggregatePolygons_cartography
                AggregatePolygons_cartography("prj_buffer.shp", bufferFeatureName, "1 Centimeter")
            else:
                # Project newly created buffer feature class
                Project_management(draftBufferName, bufferFeatureName, self.__prjFile)
                
        # Function split into two sections, once generate map button is pressed the sequential presses will immediately go to section 2
        def processMap():

            if self.__justMapBoolean == True:
                pass
            else:
            
                # Section 1 create the MXD to put into the available format options
                
                # Set variable for range ring layer
                draftBufferName = self.__flatSystemName + "_" + self.__systemRange + "_draft.shp"

                # Update unprojected range ring to system name, system range and distance unit
                with UpdateCursor(draftBufferName, ['Name']) as cursor:
                # For each row, match system range up with system information (Missile 1, Missile 2, Missile 3...) 
                    for row in cursor:
                        row[0] = self.__systemName + " " + self.__systemClass + " (" + str('{:,}'.format(int(self.__systemRange)))  + " " + distanceList[distance_entry.current()] + ")"

                        # Update the cursor with updated system information
                        cursor.updateRow(row)  

                # Make and save unprojected range ring layer
                MakeFeatureLayer_management(draftBufferName, self.__countryName)
                if self.__systemClass == "":
                    rangeRingLayer_unprj = self.__countryFileName.replace(".shp","") + "_" + self.__flatSystemName + "_" + self.__systemRange + "unprj" + ".lyr" 
                else:
                    rangeRingLayer_unprj = self.__countryFileName.replace(".shp","") + "_" + self.__flatSystemName + "_" + self.__systemClass + "_" + self.__systemRange + "unprj" + ".lyr" 
                savedRangeRingLayer_unprj = self.__workingLayerDirectory + rangeRingLayer_unprj
                SaveToLayerFile_management(self.__countryName, savedRangeRingLayer_unprj, "RELATIVE")            

                # Set variable for range ring layer
                rangeRing = self.__flatSystemName + "_" + self.__systemRange + ".shp"
            
                # Make and save range ring layer
                MakeFeatureLayer_management(rangeRing, rangeRing.replace(".shp",""))
                if self.__systemClass == "":
                    rangeRingLayer = self.__countryFileName.replace(".shp","") + "_" + self.__flatSystemName + "_" + self.__systemRange + ".lyr"
                else:
                    rangeRingLayer = self.__countryFileName.replace(".shp","") + "_" + self.__flatSystemName + "_" + self.__systemClass + "_" + self.__systemRange + ".lyr" 
                savedRangeRingLayer = self.__workingLayerDirectory + rangeRingLayer
                SaveToLayerFile_management(rangeRing.replace(".shp",""), savedRangeRingLayer, "RELATIVE")

                # Set layer variables
                elementWorldlyr = mapping.Layer(self.__savedWorldLayerVariable)
                elementWorldTopoLayerVariable = self.__layerDirectory + "\\World_Topo_Map.lyr"
                elementWorldTopoLayer = mapping.Layer(elementWorldTopoLayerVariable)
                ringlyr = mapping.Layer(savedRangeRingLayer)
                ringlyr_unprj = mapping.Layer(savedRangeRingLayer_unprj)

                # Set Variables for rangeRing and elementWorldLayer variables
                if self.__kmRange > 5499:
                    symbologyRingLayer = self.__layerDirectory + "\\element_1_country_range_ring_ICBM.lyr"
                else:
                    symbologyRingLayer = self.__layerDirectory + "\\element_1_country_range_ring.lyr"
                symbologyElementWorldLayer = self.__layerDirectory + "\\element_2_world.lyr"
                symbologyRinglyr = mapping.Layer(symbologyRingLayer)
                symbologyElementWorldLayer = mapping.Layer(symbologyElementWorldLayer)
                
                # Set the legend element
                legend = mapping.ListLayoutElements(self.__mxd, "LEGEND_ELEMENT", "Legend")[0]

                # Set data frame object for element data frame
                dataFrameElement = mapping.ListDataFrames(self.__mxd, "element")[0]

                # Set data frame object for custom data frame
                self.__frame4KMZ = mapping.ListDataFrames(self.__mxd)[1]

                # Add range ring, world feature classes and world topo as layers to element dataframe
                legend.autoAdd = True
                ApplySymbologyFromLayer_management(ringlyr, symbologyRinglyr) # apply symbology
                mapping.AddLayer(dataFrameElement, ringlyr, "TOP")
                legend.autoAdd = False
                ApplySymbologyFromLayer_management(elementWorldlyr, symbologyElementWorldLayer) # apply symbology
                mapping.AddLayer(dataFrameElement, elementWorldlyr)
                mapping.AddLayer(dataFrameElement, elementWorldTopoLayer, "BOTTOM")   

                # Add points of interest and range ring to custom frame dataframe
                ApplySymbologyFromLayer_management(ringlyr_unprj, symbologyRinglyr)
                mapping.AddLayer(self.__frame4KMZ, ringlyr_unprj, "TOP")

                # Set extent of element data frame 
                if self.__kmRange < 5499:
                    dataFrameElement.extent = ringlyr.getExtent() # if range is less than 5500 km set extent to range ring
                else:
                    dataFrameElement.extent = elementWorldlyr.getExtent() # else if range is greater than 5499 km set extent to world extent
             
                # Update legend in element data frame
                styleItem = mapping.ListStyleItems("ESRI.style", "Legend Items", "Horizontal Single Symbol Label Only")[0]
                lyr = mapping.ListLayers(self.__mxd, ringlyr, dataFrameElement)[0]
                legend = mapping.ListLayoutElements(self.__mxd, "LEGEND_ELEMENT")[0]
                legend.elementPositionX = .2696
                legend.elementPositionY = .5552
                lyr.name = str('{:,}'.format(int(self.__systemRange))) + " " + self.__distanceUnit 
                legend.updateItem(lyr, styleItem)
               
                # Obtain three values for configuring Classified By:, Derived From: (Source: if UNCLASSIFIED) and Declassify On: (if not UNCLASSIFIED)

                # Obtain current username for Classified By:
                userName = environ.get("USERNAME")

                # Obtain source derived from
                if self.__manualEntryBoolean == False:
                    sourceID = self.__currentCountryTrigraph + "_" + self.__systemName
                    derivedFrom = self.__weaponSystemClassificationDictionary[sourceID]
                else:
                    derivedFrom = self.__classificationList[2]

                # Set variables for source line configuration of map
                if "EXERCISE" in self.__classificationList[1]:
                    sourceLine = "Created By: " + userName     
                else:
                    if self.__classificationList[0][0:2] == "(U" and self.__classificationList[1][0] == "U":
                        sourceLine = "Created By: " + userName + "   " + "Source: " + derivedFrom
                    else:
                        # Obtain declassifyOn
                        declassifyOn = self.__classificationList[3]
                        
                        sourceLine = "Classified By: " + userName + "   " + "Derived From: " + derivedFrom + " " + "Declassify On: " + declassifyOn       

                # Obtain projection and datum information FYI will display coordinate system of feature class not dataframe
                spatialRef = Describe(rangeRing)
                coordinateSystem = str(spatialRef.SpatialReference.Name)
                coordinateSystem = coordinateSystem.replace("_", " ")
                datum = str(spatialRef.SpatialReference.GCS.datumName)
                datum = datum.replace("_", " ")

                # Set properties of element
                # List of elements (in order to configure): 3biblio, datum:, classification, subtitle, classification, title, coordinate system:
                for elm in mapping.ListLayoutElements(self.__mxd, "TEXT_ELEMENT"):
                    if elm.text == "coordinateSystem":
                        elm.text = "Coordinate System: " + coordinateSystem + "\n" + "Datum: " + datum
                        elm.elementPositionX = 10.7039
                        elm.elementPositionY = .9697
                    elif elm.text == "3biblio":
                        elm.text = sourceLine
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
                        elm.text = self.__countryName
                    elif elm.text == "title":
                        if self.__systemClass == "":
                            if "EXERCISE" in self.__classificationList[1]:
                                 elm.text = self.__systemName
                            else:
                                elm.text = self.__classificationList[0] + " " + self.__systemName
                        else:
                            if "EXERCISE" in self.__classificationList[1]:
                                elm.text = self.__systemName + " " + self.__systemClass
                            else:
                                elm.text = self.__classificationList[0] + " " + self.__systemName + " " + self.__systemClass

                # Set variable to the MXD
                self.__saveMapVariable = self.__mxdDirectory + "\\range_ring_template_working.mxd"

                # Save copy of map
                self.__mxd.saveACopy(self.__saveMapVariable)

                # Cleanup previous mxd in instance
                del self.__mxd

                # Cleanup dataframe instances
                del dataFrameElement, self.__frame4KMZ
                
                # Delete layer variables
                del elementWorldlyr, elementWorldTopoLayer, ringlyr, ringlyr_unprj

                # Delete legend variable
                del legend

                # Delete spatial reference variable
                del spatialRef
           
            # Set mxd variable to newly saved map
            self.__mxd = mapping.MapDocument(self.__saveMapVariable)
            
            # Export map to user designated format
            messageNumber = exportMap(self.__outputFilePath, self.__mxd, self.__saveMapVariable)

            # Open Finished File
            if messageNumber == 2:
                pass
            else:
                Popen('start ' + self.__outputFilePath, shell=True)

            # Delete mxd instance
            del self.__mxd

            return messageNumber

        # Create GUI, name title of GUI and elevate window to topmost level
        root = Toplevel() 
        root.title("Single Range Ring Generator")
        root.attributes('-topmost', 1)
        root.attributes('-topmost', 0)

        # Configure GUI frame, grid, column and root weights
        mainframe = ttk.Frame(root)
        mainframe.columnconfigure(0, weight=1)
        mainframe.rowconfigure(0, weight=1)
        mainframe.grid(column=0, row=0, sticky=(N, W, E, S))

        # Tie exiting out of program "red x" to quit command
        root.protocol("WM_DELETE_WINDOW", quitProgram)

        # Create variables to pass user input to program
        cntryName = StringVar()
        sysName = StringVar()
        sysRange = StringVar()
        otherSysActivate = BooleanVar()
        otherSysName = StringVar()
        otherSysRange = StringVar()
        distanceVariable = StringVar()
        resolutionVariable = StringVar()
        valueSet = StringVar()
        displayText = StringVar()
        fmtChoice = StringVar()

        # Build dictionaries
        countryDictionary = buildCountryDictionary() # Create country dictionary (country and respective trigraph)
        weaponSystemDictionary = getWeaponSystemDictionary() # Retrieve weapon system dictionary
        countryCentroidDictionary = getCountryCentroidDictionary() # Retrieve country centroid dictionary
        distanceDictionary = {"m":"Meters", "km": "Kilometers", "ft":"Feet", "mi":"Miles", "nm": "NauticalMiles","yd": "Yards"} # Create distance dictionary
        countryMaxRangeDictionary = getCountryMaxRangeDictionary() # Retrieve country's maximum range for buffer (Fix for Error: Buffer cannot cover both poles)

        # Build lists
        weaponsMatch = [] # Initiate list variable to hold manual entry matches to system database
        weaponsList = [] # Initiate list variable to hold country system list
        consolidatedWeaponsList = consolidatedWpnsList(weaponSystemDictionary) # Create consolidated weapon system list
        countryList = buildCountryList(countryDictionary) # Create country list (country name)
        resolutionList = ["Low", "Normal"] # Create list for user choices for range ring resolution 

        # Create list to hold abbreviations for distance values
        distanceList = []
        for key, value in distanceDictionary.iteritems():
            distanceList.append(key)

        # Create combobox for country name entry
        countryName_entry = ttk.Combobox(mainframe, width=52, state="normal", textvariable=cntryName, values=countryList) 
        countryName_entry.grid(column = 2, row = 1, columnspan = 2, sticky = W)
        countryName_entry.bind('<<ComboboxSelected>>', countryDynamicMatch, add="+")
        countryName_entry.bind('<<ComboboxSelected>>', rangeMatch, add="+")
        countryName_entry.bind('<KeyRelease>', countryDynamicMatch, add="+")
        countryName_entry.bind('<KeyRelease>', rangeMatch, add="+")
        ttk.Label(mainframe, text = "Country Name:").grid(column = 1, row = 1, sticky = W)

        # Create a combobox for system name
        sysName_entry = ttk.Combobox(mainframe, width = 31, state = "readonly", textvariable = sysName, values = weaponsList)
        sysName_entry.grid(column=2, row=2, columnspan = 2, sticky = W)
        sysName_entry.bind('<<ComboboxSelected>>', rangeMatch)
        ttk.Label(mainframe, text = "System Name:").grid(column=1, row=2, sticky=W)

        # Create a checkbox for other "manual entry" option
        other_entry = Checkbutton(mainframe,width=1,variable=otherSysActivate,command=disableWeaponCombobox) 
        other_entry.grid(column=2,row=3,sticky=W)
        other_entry.bind('<<Button>>', disableWeaponCombobox)
        ttk.Label(mainframe,text="Manual Entry:").grid(column=1,row=3,sticky=W)

        # Create entry box for other system name
        otherSysName_entry = ttk.Combobox(mainframe,width=31, state="disabled",textvariable=otherSysName,values=consolidatedWeaponsList)  
        otherSysName_entry.bind('<KeyRelease>', weaponSystemDynamicMatch, add="+")
        otherSysName_entry.bind('<<ComboboxSelected>>', weaponSystemDynamicMatch, add="+")
        otherSysName_entry.grid(column=2,row=4,columnspan=2,sticky=W)
        ttk.Label(mainframe, text="Other System Name:").grid(column=1,row=4,sticky=W)

        # Create entry box for system range
        sysRange_entry = ttk.Entry(mainframe,width=34,state="disabled",textvariable=sysRange)
        sysRange_entry.grid(column=2,row=5,columnspan=2,sticky=W)
        ttk.Label(mainframe, text="System Range:").grid(column=1,row=5,sticky=W)

        # Create combobox for distance selection
        distance_entry = ttk.Combobox(mainframe,width=3,state="disabled",textvariable=distanceVariable,values=distanceList)
        distance_entry.grid(column=2,row=6,sticky=W)
        ttk.Label(mainframe, text="Distance Unit:").grid(column=1,row=6,sticky=W)

        # Create combbox for range ring resolution
        resolutionChoice = ttk.Combobox(mainframe,state="readonly",width=8,textvariable=resolutionVariable,values=resolutionList)
        resolutionChoice.grid(column=2,row=7,sticky=W)
        resolutionChoiceLabel = Label(mainframe, text="Range Ring Resolution:")
        resolutionChoiceLabel.grid(column=1,row=7,sticky=W)

        # Create progress bar
        statusBar = ttk.Progressbar(mainframe,orient=HORIZONTAL,length=180,mode='determinate',variable=valueSet,maximum=90) 
        statusBar.grid(column=1,row=10,sticky=W)

        # Create read only entry for displaying program progress updates
        statusMessage = ttk.Entry(mainframe, width=29, state="readonly", textvariable=displayText)
        statusMessage.grid(column=1,row=11,sticky=W)

        # Create button executing program
        generateButton = ttk.Button(mainframe, text="Generate Range Ring",command=createMap,width=20)
        generateButton.grid(column=2,row=10,sticky=W)

        # Create button quiting program
        exitButton = ttk.Button(mainframe,text="Exit Program",command=quitProgram,width=12)
        exitButton.grid(column=3,row=11,sticky=E)

        # Create button that triggers the classification tool
        classifyButton = ttk.Button(mainframe,text="Classify Map",state="disabled",command=classify,width=12)
        classifyButton.grid(column=2,row=9,sticky=W)
        ttk.Label(mainframe, text="Fact of country having system:").grid(column=1,row=9,sticky=W)

        # Create button reseting program
        resetButton = ttk.Button(mainframe, text="Reset", state="normal", command = reset, width=12)
        resetButton.grid(column=3,row=10,sticky=E)

        # Add 5 units of padding between all elements in the frame
        for child in mainframe.winfo_children():
            child.grid_configure(padx=5, pady=5)
        
        # Set focus to country name entry combobox
        countryName_entry.focus() 

        # Bind escape and return keys to quit button
        root.bind('<Escape>', quitProgram)
        root.bind('<Return>', createMap)

        # Make sure all mouse or keyboard events go to the root window
        root.grab_set()

        # Wait until GUI is exited 
        root.wait_window()

        # Return value of 1 that will activate main menu button selected
        return variable
