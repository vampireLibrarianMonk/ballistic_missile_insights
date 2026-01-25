# Import modules from arcpy
from arcpy import ApplySymbologyFromLayer_management
from arcpy import CopyFeatures_management
from arcpy.da import UpdateCursor
from arcpy import Delete_management
from arcpy import Describe
from arcpy import env
from arcpy import MakeFeatureLayer_management
from arcpy import mapping
from arcpy import SaveToLayerFile_management
from arcpy import SelectLayerByAttribute_management 

# Import modules from ctypes
from ctypes import wintypes
from ctypes import windll

# Import modules from imp
from imp import load_compiled

# Import modules from os
from os import environ
from os import path
from os import system

# Import modules from subprocess
from subprocess import Popen
from subprocess import call 

# Import modules from sys
from sys import argv
from sys import executable

# Import modules from time for diagnostics
from time import strftime

# Import Modules from Tkinter
from Tkinter import *

# Import ttk modules
import ttk

# Import ask ask save as filename modules from tk File Dialog
from tkFileDialog import asksaveasfilename

# Set variables for environment workspace and main directory (move to rangeRingModules)
fileName = path.basename(argv[0])
mainDirectory = argv[0]
primeDirectory = argv[0]
mainDirectory = mainDirectory.replace(fileName, "")
mainDirectory += "\\range_ring\\"
dataPath = mainDirectory + "Data"
scratchPath = mainDirectory + "scratch"

# Import classification tool 
main_MRR_Var1 = mainDirectory + "code\\Custom_Class_Tool.pyc"
load_compiled('Custom_Class_Tool', main_MRR_Var1)
from Custom_Class_Tool import classTool
classTool = classTool()

# Import range ring modules
main_MRR_Var2 = mainDirectory + "code\\rangeRingModules.pyc"
load_compiled('rangeRingModules', main_MRR_Var2)
from rangeRingModules import *

# Set environment workspace and main directory (fixes problem with spaces in directories)
dataPath = getShortFilePath(dataPath)
env.workspace = dataPath
env.scratchWorkspace = getShortFilePath(scratchPath)
mainDirectory = getShortFilePath(mainDirectory)

# Overwrites existing dataset
env.overwriteOutput = True

# Variable program returns when it closes to signal to the main GUI that it has indeed closed
variable = 1

# Declare class that holds all functions of the range ring generator
class rangeRing:

    # Declare all variables used throughout range ring generator
    def __init__(self, *args):
        # Set tool name for script running
        self.__toolName = "multiple_buffer_tool"

        # Variables for storing various folder paths
        self.__layerDirectory = mainDirectory + "\\layers"
        self.__workingLayerDirectory = self.__layerDirectory + "\\workingLayers\\"
        self.__imageDirectory = mainDirectory + "\\exported_images"
        self.__pdfDirectory = mainDirectory +"\\exported_pdfs"
        self.__mxdDirectory = mainDirectory + "\\MXD"
        self.__kmzDirectory = mainDirectory + "\\exported_kmls"
        self.__prjDirectory = mainDirectory + "\\PRJ"
        self.__textPath = mainDirectory + "\\txt_files"
        self.__outputFilePath = ""

        # Set variable to mxd map instance
        self.__mapTemplate = self.__mxdDirectory + "\\range_ring_template_wo_inset.mxd" 
        self.__mxd = mapping.MapDocument(self.__mapTemplate)
        
        # Class boolean values
        self.__continueProcessing = True # Set boolean variable for loops for breaking out of processes due to errors
        self.__manualEntryBoolean = False # Set boolean variable for manual entry check box selection value
        self.__justMapBoolean = False # Set boolean for clicking generate map button to speed up sequential processing of other formats for same map
        self.__manualEntryExistsBoolean = False # Set boolean for manual user entry
        
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
        countryName = self.__countryName
        self.__countryFileName = "" 

        # Variables for system name and system name without special characters or spaces       
        self.__systemName = ""
        self.__flatSystemName = ""

        # List to track country's existing weapon name inventory
        self.__weaponsList = []

        # Variable tracking system ID ("country trigraph"_"system name"), range and class (SRBM, MRBM, IRBM, ICBM)
        self.__systemID = ""
        self.__systemRange = ""
        self.__systemClass = ""

        # Variable tracking distance unit and range in km
        self.__distanceUnit = ""
        self.__kmRange = 0

        # List for user entry list
        self.__entryList = [] 

        # List to track user input
        self.__userEntryList = []

        # List to track possible reentry of systems into main list
        self.__singularWeaponsList = []

        # List to track system ranges
        self.__rangeList = []

        # List to track default values for applying symbology
        self.__symbologyValueList = ['Missile K', 'Missile J', 'Missile I', 'Missile H', 'Missile G', 'Missile F', 'Missile E', 'Missile D', 'Missile C', 'Missile B', 'Missile A']
        self.__symbologyValueList.reverse()

        # List to track system information
        self.__infoList = []

        # Variable tracking user range ring resolution choice
        self.__resolutionChoice = ""
       
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

    def multipleRangeRingGenerator(self):
        
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
                                      filter(str.isalnum, str(''.join(userInput).split('/')[-1].replace(" ","")[:-3])) +''.join(userInput).split('/')[-1].replace(" ","_")[-4:])

        # Classification function
        def classify():
            # Load classification tool
            self.__classificationList = []
            self.__classificationList = classTool.classificationTool()
            
            # If classification is higher than UNCLASSIFIED then count = 4 (portion and banner marking, derived from and declassify on)
            # If classification is UNCLASSIFIED then count = 3(portion and banner marking and source) 
            if len(self.__classificationList) == 4:
                classifyButton.config(state="disabled")
                classifyButton.update()
                generateButton.config(state="normal")
                generateButton.update()
            elif len(self.__classificationList) == 3:
                if self.__classificationList[0][0:2] == "(U":
                    classifyButton.config(state="disabled")
                    classifyButton.update()
                    generateButton.config(state="normal")
                    generateButton.update()
                elif "EXERCISE" in self.__classificationList[1]:
                    classifyButton.config(state="disabled")
                    classifyButton.update()
                    generateButton.config(state="normal")
                    generateButton.update()
                else:
                    pass
            else:
                self.__classificationList = []
                classifyButton.config(state="normal")
                classifyButton.update()

            # Reenable the grab set on current tool
            root.grab_set()

        # Clears data created during process and exits program
        def quitProgram():
            # Disable all widgets exept progress bar and message display
            countryName_entry.config(state = "disabled")
            weaponChoiceList.config(state = "disabled")
            other_entry.deselect()
            other_entry.config(state = "disabled")
            otherSysName_entry.config(state = "disabled")
            addButton.config(state = "disabled")
            otherSysRange_entry.config(state = "disabled")
            distance_entry.config(state = "disabled")
            resolutionChoice.config(state="disabled")
            weaponSelectionList.config(state = "disabled")
            removeButton.config(state = "disabled")
            generateButton.config(state = "disabled")
            exitButton.config(state = "disabled")
            classifyButton.config(state = "disabled")
            resetButton.config(state = "disabled")

            # Reset status bar  
            valueSet.set(0)
            status.update()     

            # Clean scratch workspace
            displayText.set("Cleaning scratch workspace...")
            statusMessage.update()
            
            clearScratchWorkspace(scratchPath)

            # Step progressbar up 18 units
            valueSet.set(18)
            status.update()
            
            # Clean data folder
            displayText.set("Cleaning data folder...")
            statusMessage.update()
            
            clearWorkspace(dataPath)

            # Step progressbar up 18 units
            valueSet.set(36)
            status.update()
            
            # Clean working directory
            displayText.set("Cleaning working directory...")
            statusMessage.update()
            
            clearWorkingLayerDirectory(self.__workingLayerDirectory)

            # Step progressbar up 18 units
            valueSet.set(54)
            status.update()  

            displayText.set("Deleting temporary layers...")
            statusMessage.update()

            # Delete temporary layers
            Delete_management("worldLayer")
            Delete_management("buffer_layer")
            Delete_management("meridian_layer")
            Delete_management("multiRR_prj")
            
            if self.__countryName:
                Delete_management(self.__countryName)
            else:
                pass

            # Step progressbar up 18 units
            valueSet.set(72)
            status.update()  

            displayText.set("Exiting program...")
            statusMessage.update()

            # Step progressbar up 18 units
            valueSet.set(90)
            status.update() 
            
            # Exit Program 
            root.destroy()

        # Clears data created during process and restores program to original condition when first loaded
        def reset():
            # Disable all widgets exept progress bar and message display
            countryName_entry.config(state = "disabled")
            weaponChoiceList.config(state = "disabled")
            other_entry.deselect()
            other_entry.config(state = "disabled")
            otherSysName_entry.config(state = "disabled")
            addButton.config(state = "disabled")
            otherSysRange_entry.config(state = "disabled")
            distance_entry.config(state = "disabled")
            resolutionChoice.config(state="disabled")
            weaponSelectionList.config(state = "disabled")
            removeButton.config(state = "disabled")
            generateButton.config(state = "disabled")
            exitButton.config(state = "disabled")
            classifyButton.config(state = "disabled")
            resetButton.config(state = "disabled")

            # Reset status bar  
            valueSet.set(0)
            status.update()     
            
            # Clean scratch workspace
            displayText.set("Cleaning scratch workspace...")
            statusMessage.update()
            
            clearScratchWorkspace(scratchPath)

            # Step progressbar up 18 units
            valueSet.set(18)
            status.update()
            
            # Clean data folder
            displayText.set("Cleaning data folder...")
            statusMessage.update()
            
            clearWorkspace(dataPath)

            # Step progressbar up 18 units
            valueSet.set(36)
            status.update()
            
            # Clean working directory
            displayText.set("Cleaning working directory...")
            statusMessage.update()
            
            clearWorkingLayerDirectory(self.__workingLayerDirectory)

            # Step progressbar up 18 units
            valueSet.set(54)
            status.update()  

            displayText.set("Deleting temporary layers...")
            statusMessage.update()

            # Delete temporary layers
            Delete_management("worldlayer")
            Delete_management("meridian_layer")
            Delete_management("buffer_layer")
            Delete_management("multiRR_prj")
            
            if self.__countryName:
                Delete_management(self.__countryName)
            else:
                pass

            # Step progressbar up 18 units
            valueSet.set(72)
            status.update()

            # Restore buttons, comboboxes and status line to their default status and value
            displayText.set("Reseting GUI...")
            statusMessage.update()

            # Restore buttons, comboboxes and status line to default

            # Clear country name entry
            # Set state to normal
            # Set focus to country name entry combobox
            cntryName.set("")
            countryName_entry.config(state="normal")
            countryName_entry.config(values=countryList)
            countryName_entry.update()
            countryName_entry.focus()
            
            # Clear weapons choice list
            # Set state to normal
            weaponChoiceList.config(state="normal")
            weaponChoiceList.delete(0, END)
            weaponChoiceList.update()

            # Clear weapons selection list
            # Set state to normal
            weaponSelectionList.config(state = "normal")
            weaponSelectionList.delete(0, END)
            weaponSelectionList.update()       

            # Deselect manual entry checkbox
            # Set state to normal
            other_entry.deselect()
            other_entry.config(state = "normal")

            # For systems selected, return to consolidated weapons list
            for weapon in self.__singularWeaponsList:
                if weapon in consolidatedWeaponsList:
                    pass
                else:
                    consolidatedWeaponsList.append(weapon)

            # Sort the consolidated weapons list
            consolidatedWeaponsList.sort()

            # Clear other system name entry
            # Set values to consolidated weapons list
            otherSysName.set("")
            otherSysName_entry.config(values = consolidatedWeaponsList)

            # Clear system range entry
            # Set state to enabled
            sysRange.set("")

            # Clear entry list
            self.__entryList = []

            # Set state of add button to normal
            addButton.config(state="normal")
            addButton.update()

            # Clear distance unit choice combobox
            distanceVariable.set("")
            distance_entry.update()

            # Reset range ring resolution choice
            resolutionVariable.set("")
            resolutionChoice.update()
            resolutionChoice.config(state="readonly")
            
            # Set state of exit and reset buttons to normal
            exitButton.config(state = "normal")
            resetButton.config(state = "normal")

            # Reset classificationList
            self.__classificationList = []

            # Reset boolean values for just map and manual entry
            self.__justMapBoolean = False
            self.__manualEntryBoolean = False
            self.__manualEntryExistsBoolean = False

            # Set variable to original mxd map instance
            self.__mapTemplate = self.__mxdDirectory + "\\range_ring_template_wo_inset.mxd"
            self.__mxd = mapping.MapDocument(self.__mapTemplate)

            # Reset user entry list
            self.__userEntryList = []

            # Reset removal tracking list
            self.__singularWeaponsList = []

            # Remove list to load listboxes
            self.__weaponsList = []

            # Reset system information list
            self.__infoList = []

            # Reset status bar
            valueSet.set(90)
            status.update()

            # Clear message display
            displayText.set("")
            statusMessage.update()

            # Reset progressbar
            valueSet.set(0)
            status.update()

        # If the user has manually entered a system enable classify button for manual classification of map
        def checkIfManualEntryExists():
            if self.__userEntryList:            
                for entry in self.__userEntryList:
                    if "MANUAL" in entry:
                        self.__manualEntryExistsBoolean = True
                        classifyButton.config(state="normal")
                        classifyButton.update()
                    else:
                        self.__manualEntryExistsBoolean = False
                        classifyButton.config(state="disabled")
                        classifyButton.update()
            else:
                classifyButton.config(state="disabled")
                classifyButton.update()          

        # Disables weapon combo box for manual entry of system name and range
        def disableWeaponCombobox():
            self.__manualEntryBoolean = otherSysActivate.get()
            if self.__manualEntryBoolean == True:

                # Reset entry to avoid previous entry from interfering with process, clear and disable system name combobox
                self.__weaponsList = []  
                weaponChoiceList.config(state="disabled")
                weaponChoiceList.update()

                # Enable manual system name entry
                otherSysName_entry.config(state = "normal")            

                # Enable manual system range entry and clear it if range was already present
                otherSysRange_entry.config(state = "normal")
                otherSysRange_entry.delete(0, END)
                otherSysRange_entry.update()

                # Enable distance combobox 
                distance_entry.config(state="readonly")
                distanceVariable.set("")
                distance_entry.update()

                # Enable classification tool if no classification has been entered
                if not self.__classificationList:
                    classifyButton.config(state="normal")
                    classifyButton.update()
                else:
                    pass

                # Match weapons choice list with that of the country entered by user
                countryWeaponsMatch()

            else:            
                # Enable weapon system combobox
                weaponChoiceList.config(state="normal")
                weaponChoiceList.update()

                # Reset manual system name entry to avoid previous entry from interfering with process
                otherSysName_entry.delete(0, END)

                # Disable manual system name entry
                otherSysName_entry.config(state = "disabled")
                otherSysName_entry.update()
                
                # Reset manual system range entry to avoid previous entry from interfering with process
                otherSysRange_entry.delete(0, END)
                otherSysRange_entry.config(state="disabled")
                otherSysRange_entry.update
                
                # Disable distance combobox 
                distance_entry.config(state="disabled")
                distanceVariable.set("")
                distance_entry.update()
                
                distance_entry.config(state="disabled")
                distance_entry.update()
                
                # Decision loop to run country, weapon and range match functions if there is a country entered
                if countryName_entry.get() != "":
                    countryWeaponsMatch()
                    rangeMatch()
                else:
                    pass
               
                # Enable classify button if a manual entry exists in the user selection list
                checkIfManualEntryExists()

        # Forward arguments to dynamic match routine in range ring modules and returns a the closest country name match in country list
        def countryDynamicMatch(event):
            dynamicMatch(event, countryName_entry, countryList, cntryName)
            countryWeaponsMatch()

            if countryName_entry.get() == "":
                countryName_entry.config(values=countryList)
                countryName_entry.update()

                self.__weaponsList = []
                weaponChoiceList.delete(0, END)
                weaponChoiceList.update()
            else:
                pass

        # Returns system list under country of choice
        def countryWeaponsMatch(*args):
            self.__currentCountrySelection = countryName_entry.get()
            self.__weaponsList = []
            
            if self.__manualEntryBoolean == False:            
            
                try:
                    self.__currentCountryTrigraph = countryDictionary[self.__currentCountrySelection]
                   
                    if self.__currentCountrySelection != -1 or self.__currentCountryTrigraph:

                        for ID, name in weaponSystemDictionary.iteritems():
                            currentSystemID = self.__currentCountryTrigraph + "_" + name
                            if ID == currentSystemID:
                                self.__weaponsList.append(name)
                            else:
                                pass
                        else:
                            pass
                except:
                    pass
                
                if len(self.__weaponsList) != 0:
                    if self.__singularWeaponsList:
                        for weapon in self.__singularWeaponsList:
                            if weapon in self.__weaponsList:
                                self.__weaponsList.remove(weapon)
                            else:
                                pass
                    else:
                        pass
                    
                    if len(self.__weaponsList) == 0:
                        pass
                    else:
                        self.__weaponsList.sort()
                        weaponChoiceList.delete(0, END)
                        for weapon in self.__weaponsList:
                            weaponChoiceList.insert('end', (weapon))
                            weaponChoiceList.update()
                else:
                    weaponChoiceList.delete(0, END)
                    weaponChoiceList.insert('end', "No system available in database")                
                    weaponChoiceList.update()
            else:
                pass

        # Dynamic range match to present system name entered
        def rangeMatch(*args):        
            for key, value in self.__weaponRangeDictionary.iteritems():
                if otherSysName.get() == key[4:]:
                    sysRange.set(value)
                    otherSysRange_entry.update()
                    distanceVariable.set("km")
                    distance_entry.update()
                    otherSysName_entry.position = otherSysName_entry.index(END) # go to end (no selection)
                    break
                else:
                    if otherSysName.get() == "":
                        pass
                    else:
                        sysRange.set("No range found for system entered")                        
                        otherSysRange_entry.update()
                        if distance_entry.instate(['disabled']):
                            pass
                        else:
                            distanceVariable.set("")
                            distance_entry.update()

        # Forward arguments to dynamic match routine in range ring modules and returns a the closest weapon system name match in country list
        def weaponSystemDynamicMatch(event):
            dynamicMatch(event, otherSysName_entry, consolidatedWeaponsList, otherSysName)
            rangeMatch()

            if otherSysName_entry.get() == "":
                sysRange.set("")
                otherSysRange_entry.update()
            else:
                pass

        # Obtain weapons list relevant to country selected
        def getQuickWeaponsList():
            # Set up list variable for country's existing system list
            self.__quickWeaponsList = []

            # Get list of systems in database for country selected
            try:
                self.__currentCountryTrigraph = countryDictionary[countryName_entry.get()]
               
                if self.__currentCountryTrigraph:

                    for ID, name in weaponSystemDictionary.iteritems():
                        currentSystemID = self.__currentCountryTrigraph + "_" + name
                        if ID == currentSystemID:
                            self.__quickWeaponsList.append(name)
                        else:
                            pass
            except:
                pass

        # Function for removing selection and readding preexisting systems to their respectives lists (choicelist and consolidated weapons list)
        def removeUserSelection():
            while self.__continueProcessing == True:
                # Set list variable for passing weapon choice list contents (setting equal to contents set an uneditable tuple)
                choiceList = []

                # Get contents of weapons choice listbox
                listContents = weaponChoiceList.get(0,END)

                # Obtain current selection from user entry list
                currentSelection = [weaponSelectionList.get(index) for index in weaponSelectionList.curselection()]

                try:
                    if len(map(int, weaponSelectionList.curselection())) == 0:
                        raise ValueError
                    else:
                        pass
                except:
                    windll.user32.MessageBoxA(0, "Please select an entry to remove.", "Error Removing Selection", 0)
                    break                

                # Add systems removed from selection list back to database entry list 
                choiceList += weaponChoiceList.get(0, END)
                
                for weapon in self.__singularWeaponsList:
                    if weapon in self.__quickWeaponsList:
                        for selection in currentSelection:                        
                            if weapon in selection:
                                if weapon in listContents:
                                    pass
                                else:
                                    choiceList.append(weapon)
                        else:
                            pass
                    else:
                        pass

                # Sort choice list, delete existing contents and repopulate with subtracted user selection
                choiceList.sort()
                weaponChoiceList.delete(0, END)
                weaponChoiceList.update()
                        
                for weapon in choiceList:
                    weaponChoiceList.insert('end', weapon)
                    weaponChoiceList.update()
                else:
                    pass

                # Add weapon system selection removed back to consolidated weapons list

                # Set up list variable for consolidated weapons list
                quickConsolidatedWeaponsList = consolidatedWpnsList(weaponSystemDictionary)
                for weapon in self.__singularWeaponsList:
                    if weapon in consolidatedWeaponsList:
                        pass
                    else:
                        if weapon in quickConsolidatedWeaponsList:
                            for selection in currentSelection:
                                if weapon in selection:
                                    consolidatedWeaponsList.append(weapon)
                                    consolidatedWeaponsList.sort()
                                    
                                    otherSysName_entry.config(values=consolidatedWeaponsList)
                                    otherSysName_entry.update()
                                else:
                                    pass
                            
                        else:
                            pass

                # Delete selection singular weapons list   
                selectionList = map(int, weaponSelectionList.curselection())

                counter = 0
                
                for selection in selectionList:
                    index = int(selection) - counter
                    self.__singularWeaponsList.remove(weaponSelectionList.get(index).partition(":")[0])
                    weaponSelectionList.delete(index,index)
                    weaponSelectionList.update()
                    counter += 1
            
                for entry in self.__entryList:
                    weaponSelectionList.insert('end', entry)
                    weaponSelectionList.update()

                else:
                    pass

                # Delete selection from stored user entry list
                for selection in currentSelection:
                    for userEntry in self.__userEntryList:
                        if userEntry[3] == selection.partition(":")[0]:
                            self.__userEntryList.remove(userEntry)
                        else:                    
                            pass
            
                if len(weaponSelectionList.get(0, END)) == 0:
                    countryName_entry.config(state="normal")
                    countryName_entry.update()
                    removeButton.config(state="disabled")
                    removeButton.update()                
                    distance_entry.config(state="readonly")
                    distance_entry.update()
                    generateButton.config(state="disabled")
                    generateButton.update()

                checkIfManualEntryExists()
                    
                break           

        # Adds manual user entry into system entry list       
        def addUserSelection(*args):
            self.__continueProcessing = True
            while self.__continueProcessing == True:
                # Obtain current selection from user entry list
                currentSelection = [weaponChoiceList.get(index) for index in weaponChoiceList.curselection()]

                def deleteEntryFromConsolidatedWeaponsList(systemName):
                    if systemName in consolidatedWeaponsList:
                        otherSysName.set("")
                        consolidatedWeaponsList.remove(systemName)
                        otherSysName_entry.config(values=consolidatedWeaponsList)
                        otherSysName_entry.update()
                    else:
                        pass

                # Enables remove and generate buttons if the user has entered systems into the selection list
                def enableButtons():
                    if len(weaponSelectionList.get(0, END)) != 0:
                        removeButton.config(state="normal")
                        removeButton.update()                            
                        self.__continueProcessing = True
                        generateButton.config(state="normal")
                        generateButton.update()
                    else:
                        pass

                # Retrieve country name from country name entry    
                try:
                    self.__countryName = countryName_entry.get()

                    # If country entry is blank display error message
                    if self.__countryName == "":
                        errorMessage = "Please enter or choose a threat country"
                        countryName_entry.focus()
                        raise ValueError
                    # If country name is not in country list display error message
                    elif self.__countryName not in countryList:
                        errorMessage = "Invalid country name. Please enter a valid country name."
                        raise ValueError
                    else:
                        pass
                except:
                    windll.user32.MessageBoxA(0, errorMessage, "Country Name Entry Error", 0)
                    break

                # Obtain country trigraph from country dictionary using country name
                try:
                    self.__countryTrigraph = countryDictionary[self.__countryName]                    
                except:
                    windll.user32.MessageBoxA(0, "No matching trigraph to country entered", "Program Error", 0)
                    break         

                # Call quick weapons list function
                getQuickWeaponsList()            

                # Delete all invalid characters for country file name format (keeping "-", alphabet, "0123456789")  
                self.__countryFileName = filter(str.isalnum, self.__countryName)
                
                if self.__manualEntryBoolean != True:

                    # Set selection list to the user selection from weapon choice listbox
                    selectionList = map(int, weaponChoiceList.curselection())

                    # Obtain length of user selection
                    listContents = len(weaponChoiceList.get(0,END))

                    # Display error message if there are no more systems available to select
                    # or if list contents are equal to zero
                    # or if there is no system available in database
                    # or if "No system available in database" is chosen
                    try:
                        if listContents == 0:
                            errorMessage = "No more systems in database for selected country." + "\n" + "Please use manual entry."
                            raise ValueError
                        elif weaponChoiceList.get(0,0) == "No system available in database":
                            errorMessage = "No system available in database for selected country" + "\n" + "Please use manual entry."
                            raise ValueError                          
                        elif len(selectionList) == 0:
                            errorMessage = "Please select system name"
                            raise ValueError
                        elif weaponChoiceList.get(weaponChoiceList.curselection()[0]) == "No system available in database":
                            errorMessage = "No system available in database for selected country" + "\n" + "Please use manual entry."
                            raise ValueError
                        else:
                            pass
                    except:
                        windll.user32.MessageBoxA(0, errorMessage, "Entry Error", 0)
                        break                

                   # Iterate through user's selection and add it to the selection listbox
                    for selection in selectionList:
                        skipVariable = False
                        self.__systemName = weaponChoiceList.get(selection)
                        
                        # Delete all invalid characters for the system file name (keeping "-", alphabet, "0123456789")                
                        self.__flatSystemName = filter(str.isalnum, str(self.__systemName)) #converted to string due to unknown error out of blue (started 09 May 2015)

                        # Set system identification to the current country's trigraph and system name
                        self.__systemID = self.__currentCountryTrigraph + "_" + self.__systemName

                        # Obtain system range through system identification in the weapon range dictionary
                        self.__systemRange = self.__weaponRangeDictionary[self.__systemID]
                      
                        # Determine system class and range in km
                        self.__systemClass, self.__kmRange = getSystemClass(self)

                        # If range exceeds capability of program display error (error 99999 a buffer currently cannot cover both poles)
                        maximumRange = countryMaxRangeDictionary[self.__countryName]/1000
                        try:
                            if self.__kmRange > maximumRange:
                                errorMessage = "System range cannot exceed " + str('{:,}'.format(maximumRange)) + " " + "km." + "\nFor the country of " + self.__countryName + "."
                                raise ValueError
                            else:
                                pass
                        except:
                            errorMessage += "\nPlease use Custom POI Range Ring Tool."
                            windll.user32.MessageBoxA(0, errorMessage, "Program Limitation Error", 0)
                            continue                        

                        # If there is a duplicate range about to be entered into the program raise error message                        
                        for entry in self.__userEntryList:
                            try:
                                if entry[5] == self.__systemRange:
                                    errorMessage = "Could not add " + str(self.__systemName) + "." + "\n" + "A range of " + '{:,}'.format(self.__systemRange) + " km is already entered."
                                    skipVariable = True
                                    raise ValueError
                                else:
                                    pass           
                            except:
                                windll.user32.MessageBoxA(0, errorMessage, "Entry Error", 0)
                                self.__continueProcessing = False
                                break

                        if skipVariable == True:
                            pass
                        else:
                            tempUserEntryList = [self.__countryName, self.__countryTrigraph, self.__countryFileName, self.__systemName, self.__flatSystemName, self.__systemRange,
                                             self.__systemClass]

                            # Add entry to selection list
                            self.__userEntryList.append(tempUserEntryList)

                            userEntry = self.__systemName + ": " +  self.__systemClass + " (" + '{:,}'.format(self.__systemRange) + " km)"

                            deleteEntryFromConsolidatedWeaponsList(self.__systemName)

                            self.__singularWeaponsList.append(self.__systemName)

                            weaponSelectionList.insert('end', userEntry)
                            weaponSelectionList.update()

                    # Assemble system name list
                    systemNameList = []
                    tempWeaponsList = []

                    # Iterate through user entry list, replace unicode marker (u) with nothing and append to the system name list
                    for entry in self.__userEntryList:
                        string = str(entry[3])
                        systemNameList.append(str(string))

                    # Clear weaponChoiceList
                    weaponChoiceList.config(state="normal")
                    weaponChoiceList.delete(0, END)
                    weaponChoiceList.update()

                    # Rebuild system list for chosen country
                    for ID, name in weaponSystemDictionary.iteritems():
                        currentSystemID = self.__currentCountryTrigraph + "_" + name
                        if ID == currentSystemID:
                            tempWeaponsList.append(name)
                        else:
                            pass

                    # Take out user system choices
                    for systemName in systemNameList:
                        tempWeaponsList.remove(systemName)

                    tempWeaponsList.sort()

                    # Add systems to listbox that user did not select
                    for weapon in tempWeaponsList:
                        weaponChoiceList.insert('end', (weapon))
                        weaponChoiceList.update()                    
                            
                else:
                    skipVariable = False
                    try:
                        self.__systemName = otherSysName_entry.get()
                        
                        if self.__systemName == "No system available in database":
                            errorMessage = "No system present in database for " + self.__countryName + ", please use manual entry"
                            raise ValueError
                        elif self.__systemName == "":
                            errorMessage = "Please enter system name"
                            raise ValueError
                        else:
                            pass
                                  
                    except:
                        windll.user32.MessageBoxA(0, errorMessage, "System Name Entry Error", 0)
                        break

                    # Delete all invalid characters (keeping "-", alphabet, "0123456789")                
                    self.__flatSystemName = filter(str.isalnum, str(self.__systemName)) #converted to string due to unknown error out of blue (started 09 May 2015)

                    # Raises error message if no range is entered or an a range other than an integer is entered
                    try:                   
                        if sysRange.get() == "":
                            errorMessage = "No range entered. Please use manual entry"
                            raise ValueError
                        elif sysRange.get() == "No range found for system entered":
                            errorMessage = "No range found for system entered. Please enter range manually"
                            raise ValueError
                        else:                
                            try:
                                self.__systemRange = otherSysRange_entry.get()
                                self.__systemRange = self.__systemRange.replace(",", "")
                                self.__systemRange = int(self.__systemRange)
                            except:
                                windll.user32.MessageBoxA(0, "Please enter a whole number for the range.", "Invalid System Range Entry", 0)
                                break                    
                    except:
                        windll.user32.MessageBoxA(0, errorMessage, "Invalid System Range Entry", 0)
                        break

                    # If there is a duplicate range about to be entered into the selection list raise error
                    try:
                        for entry in self.__userEntryList:
                            if entry[5] == self.__systemRange:
                                errorMessage = "A range of " + str(self.__systemRange) + " is already entered."
                                skipVariable = True
                                raise ValueError
                            else:
                                pass           
                    except:
                        windll.user32.MessageBoxA(0, errorMessage, "Entry Error", 0)
                        break
                    
                    if skipVariable == True:
                        pass
                    else:
                        
                        # Determine class of missile
                        self.__systemClass, self.__kmRange = getSystemClass(self)
             
                        try:
                            if self.__manualEntryBoolean == False:
                                self.__distance = "km"
                            else:
                                if distance_entry.get() == "":
                                    errorMessage = "Please enter a distance unit for the system range" + "\nExample Unit: km or nm"
                                    raise ValueError
                                else:
                                    self.__distance = distance_entry.get()
                        except:
                            windll.user32.MessageBoxA(0, errorMessage, "Distance Unit Missing", 0)
                            break

                        # If range exceeds capability of program display error (error 99999 a buffer currently cannot cover both poles)
                        maximumRange = countryMaxRangeDictionary[self.__countryName]/1000
                        try:
                            if self.__kmRange > maximumRange:
                                if self.__distance == "km": 
                                    errorMessage = "System range cannot exceed " + str('{:,}'.format(maximumRange)) + " " + self.__distance +  "." + "\nFor the country of " + self.__countryName + "."
                                    raise ValueError
                                elif self.__distance == "mi":
                                    maximumRange = int(maximumRange / 1.60934)
                                    errorMessage = "System range cannot exceed " + str('{:,}'.format(maximumRange)) + " " + self.__distance + "." + "\nFor the country of " + self.__countryName + "."
                                    raise ValueError
                                elif self.__distance == "ft":
                                    maximumRange = int(maximumRange / 0.0003048)
                                    errorMessage = "System range cannot exceed " + str('{:,}'.format(maximumRange)) + " " + self.__distance + "." + "\nFor the country of " + self.__countryName + "."
                                    raise ValueError
                                elif self.__distance == "yd":
                                    maximumRange = int(maximumRange / 0.0009144)
                                    errorMessage = "System range cannot exceed " + str('{:,}'.format(maximumRange)) + " " + self.__distance + "." + "\nFor the country of " + self.__countryName + "."
                                    raise ValueError
                                elif self.__distance == "m":
                                    maximumRange = int(maximumRange / 0.001)
                                    errorMessage = "System range cannot exceed " + str('{:,}'.format(maximumRange)) + " " + self.__distance + "." + "\nFor the country of " + self.__countryName + "."
                                    raise ValueError
                                elif self.__distance == "nm":
                                    maximumRange = int(maximumRange / 1.852) 
                                    errorMessage = "System range cannot exceed " + str('{:,}'.format(maximumRange)) + " " + self.__distance + "." + "\nFor the country of " + self.__countryName + "."
                                    raise ValueError
                            else:
                                pass
                        except:
                            errorMessage += "\nPlease use Custom POI Range Ring Tool."
                            windll.user32.MessageBoxA(0, errorMessage, "Program Limitation Error", 0)
                            break
                        
                        deleteEntryFromConsolidatedWeaponsList(self.__systemName)
                        
                        otherSysName.set("")
                        other_entry.config(state="normal")
                        otherSysName_entry.update()
                        otherSysName_entry.focus()

                        # Add user selection to list for possible reentry into system lists due to removal from user entry list
                        self.__singularWeaponsList.append(self.__systemName)

                        # Set up string for display in user entry list 
                        userEntry = self.__systemName + ": " +  self.__systemClass + " (" + str('{:,}'.format(self.__systemRange)) + " " + distanceList[distance_entry.current()] + ")" 

                        # Update user entry list to reflect both the most recently added system information and updated system list
                        weaponSelectionList.insert('end', userEntry)
                        weaponSelectionList.update()

                        tempUserEntryList = [self.__countryName, self.__countryTrigraph, self.__countryFileName, self.__systemName, self.__flatSystemName, self.__systemRange,
                                             self.__systemClass, "MANUAL"]

                        # Add entry to list
                        self.__userEntryList.append(tempUserEntryList)

                        # Run check manual entry routine
                        checkIfManualEntryExists() 
                       
                # Get contents of weapons choice listbox
                listContents = weaponSelectionList.get(0,END)

                # Call function to enable remove and generate buttons if the selection box is not empty
                enableButtons()
                    
                # Reset temporary list
                tempUserEntryList = []
                
                # Disable country selection 
                countryName_entry.config(state="disabled")
                countryName_entry.update()

                # Reset system/flatsystem name variables
                self.__systemName = ""
                self.__flatSystemName = ""

                # Reset system range combobox, variable
                sysRange.set("")
                self.__systemRange = "0"
                otherSysRange_entry.update()

                # Reset distance unit entry
                distance_entry.config(state="disabled")
                distance_entry.update()
                
                break

        def calculate(*args):
            while self.__continueProcessing == True:
                
                # Get classification from user, if not display error
                try:
                    # Get user entry (portion marking, classification banner, Derived From and Declassify On)
                    if self.__manualEntryExistsBoolean == False:
                        classificationBannerList = []
                        derivedFromList = []
                        
                        for item in self.__userEntryList:
                            classificationMarkingVariable = self.__currentCountryTrigraph + "_" + item[3]                
                            classificationBanner = self.__bannerClassificationDictionary[classificationMarkingVariable]
                            classificationBannerList.append(classificationBanner)

                            sourceID = self.__currentCountryTrigraph + "_" + item[3]
                            derivedFrom = self.__weaponSystemClassificationDictionary[sourceID]
                            derivedFromList.append(derivedFrom)
                            
                        self.__classificationBanner = getClassificationBanner(classificationBannerList)

                        # Lay out derived from line for sources
                        if len(derivedFromList) > 0:
                            derivedFromLine = ""
                            spaceVariable = "                                           "
                            for item in set(derivedFromList):
                                derivedFromLine += spaceVariable
                                derivedFromLine += item
                                derivedFromLine += "\n"
                            self.__derivedFrom = derivedFromLine.rstrip()
                            self.__derivedFrom = self.__derivedFrom.lstrip()
                        else:
                            errorMessage = "No source found"
                            errorHeader = "Program Error"
                            raise ValueError
                        self.__classificationList = [self.__classificationBanner[0],self.__classificationBanner,self.__derivedFrom]
                    else:                    
                        if not self.__classificationList:
                            errorMessage = "Please classify your entries appropriately"
                            errorHeader = "Product Classification Required"
                            raise ValueError                
                        else:
                            pass
                except:
                    windll.user32.MessageBoxA(0, errorMessage, errorHeader, 0)
                    break

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

                # Create system range list for multiple range ring buffer
                self.__rangeList = []
                for item in self.__userEntryList:
                    self.__rangeList.append(item[5])

                # Get the output directory from the user
                getExportFilePath()
                
                if self.__outputFilePath.replace(" ","") == "/":
                    displayText.set("Paused by User")
                    statusMessage.update()
                    break
                else:
                    pass 

                # Sort self.__rangeList
                self.__rangeList.sort()

                # Build system information list that will update the layer reflectign each system's name and range (in chosen distance unit)
                for rangeValue in self.__rangeList:
                    for item in self.__userEntryList:                
                        if item[5] == rangeValue:
                            systemInfo = str('{:,}'.format(item[5])) + " " + distanceList[distance_entry.current()] + " " + item[3] + " " + item[6]
                            self.__infoList.append(systemInfo)
                            break
                        else:
                            pass
                # Diagnostic time stamp print
                print strftime("%Y-%m-%d %H:%M:%S")
                
                # Reset status bar
                valueSet.set(0)
                status.update()                           

                # Disable all entries except map format choice when program runs
                countryName_entry.config(state="disabled")
                countryName_entry.update()
                
                other_entry.config(state="disabled")
                other_entry.update()
                
                otherSysName_entry.config(state="disabled")
                otherSysName_entry.update()
                
                otherSysRange_entry.config(state="disabled")
                otherSysRange_entry.update()

                weaponSelectionList.config(state="disabled")
                weaponSelectionList.update()
                
                weaponChoiceList.config(state="disabled")
                weaponChoiceList.update()
                
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

                resolutionChoice.config(state="disabled")
                resolutionChoice.update()
                
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

                    # Create query string of NAME = countryName
                    nameField = "NAME"
                    queryString = '"' + nameField + '" = ' + "'" + self.__countryName + "'"

                    # Select within world feature class the target country   
                    SelectLayerByAttribute_management("worldLayer", "NEW_SELECTION", queryString)

                    # Create variable for creating country feature class
                    countryFC = str(self.__countryFileName) + ".shp"
                    
                    # Write the selected features to a new featureclass
                    CopyFeatures_management("worldLayer", countryFC)

                valueSet.set(30)
                status.update()

                displayText.set("Creating System Range Ring")
                statusMessage.update()

                if self.__justMapBoolean == True:
                    pass
                else:                
                    bufferPolygon()
                
                valueSet.set(60)
                status.update()

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
                    status.update()
                
                if self.__justMapBoolean == True:
                    pass
                else:
                    # Set boolean to true so sequential format don't take as long
                    self.__justMapBoolean = True

                # Enable generate, reset and exit button                
                generateButton.config(state="normal")
                generateButton.update()

                resetButton.config(state="normal")
                resetButton.update()

                exitButton.config(state="normal")
                exitButton.update()

                # Diagnostic time stamp print
                print strftime("%Y-%m-%d %H:%M:%S")            
                
                break
                                       
        def bufferPolygon():
            # Set Central Meridian projection file
            self.__prjFile = adaptPRJ(self.__currentCountryTrigraph, countryCentroidDictionary[self.__currentCountryTrigraph], self.__prjDirectory)
            
            # Execute Multiple Ring Buffer tool
            carryOverVariables = self.__countryName + "?" + self.__countryFileName + "?" + str(countryCentroidDictionary[self.__currentCountryTrigraph]) + "?" + self.__currentCountryTrigraph + "?" + str(self.__rangeList) + "?" + distanceDictionary[distanceList[distance_entry.current()]] + "?" + str(self.__symbologyValueList) + "?" + self.__prjFile + "?" + self.__resolutionChoice

            fileVariable = self.__textPath + "\\carryOverVariables.txt" 
            txtFile = open(fileVariable, "w")
            txtFile.write(str(carryOverVariables))
            txtFile.close()

            specialProcessFileOne = mainDirectory + "\\code\\special_process_1.pyc"
            #system(specialProcessFileOne)
            call([executable, specialProcessFileOne])
            

            specialProcessFileTwo = mainDirectory + "\\code\\special_process_2.pyc"
            #system(specialProcessFileTwo)
            call([executable, specialProcessFileTwo])

            # Update "Name" field with system name, range and distance unit
            def updateFCSField(shapefile):
                with UpdateCursor(shapefile, ['range',"NAME"]) as cursor:
                # For each row, match system range up with system information (Missile 1, Missile 2, Missile 3...)
                # self.__userEntryList: [self.__countryName, self.__countryTrigraph, self.__countryFileName, self.__systemName, self.__flatSystemName, self.__systemRange, self.__systemClass]
                    for row in cursor:
                        for item in self.__userEntryList:
                            if row[0] == str(item[5]):
                                string = item[3] + " " + item[6] + " (" + str('{:,}'.format(item[5])) + " " + distanceList[distance_entry.current()] + ")"
                                row[1] = string

                                # Update the cursor with updated system information
                                cursor.updateRow(row)
                                break
                            else:
                                pass
                    del cursor

            updateFCSField("multirangering_unprj.shp")
            updateFCSField("multirangering.shp")
             
        # Function split into two sections, once generate map button is pressed the sequential presses will immediately go to section 2
        def processMap():
            if self.__justMapBoolean == True:
                pass
            else:
            
                # Section 1 create the MXD to put into the available format options            
               
                # Make and save unprojected range ring layer
                MakeFeatureLayer_management("multirangering_unprj.shp",self.__countryName) 
                unprj_rangeRingLayer = "Multiple Range Ring Unprojected " + self.__countryName + " .lyr"
                savedunprjRangeRingLayer = self.__workingLayerDirectory + unprj_rangeRingLayer
                SaveToLayerFile_management(self.__countryName, savedunprjRangeRingLayer, "RELATIVE")            
            
                # Make and save projected range ring layer
                MakeFeatureLayer_management("multirangering.shp", "multiRR_prj")
                rangeRingLayer = "Multiple Range Ring Projected " + self.__countryName + " .lyr"
                savedRangeRingLayer = self.__workingLayerDirectory + rangeRingLayer
                SaveToLayerFile_management("multiRR_prj", savedRangeRingLayer, "RELATIVE")

                # Set layer variables
                elementWorldlyr = mapping.Layer(self.__savedWorldLayerVariable)
                elementWorldTopoLayerVariable = self.__layerDirectory + "\\World_Topo_Map.lyr"
                elementWorldTopoLayer = mapping.Layer(elementWorldTopoLayerVariable)
                ringlyr = mapping.Layer(savedRangeRingLayer)
                unprjringlyr = mapping.Layer(savedunprjRangeRingLayer)

                # Set Variables for rangeRing and elementWorldLayer variables
                symbologyRingLayer = self.__layerDirectory + "\\multi_range_ring.lyr"
                symbologyElementWorldLayer = self.__layerDirectory + "\\element_2_world.lyr"           
                symbologyRingLayer = mapping.Layer(symbologyRingLayer)
                symbologyElementWorldLayer = mapping.Layer(symbologyElementWorldLayer)
                
                # Set the legend element
                legend = mapping.ListLayoutElements(self.__mxd, "LEGEND_ELEMENT", "Legend")[0]

                # Set location of legend 
                legend.elementPositionX = .2696
                legend.elementPositionY = .5552 

                # Set data frame object for element data frame
                dataFrameElement = mapping.ListDataFrames(self.__mxd, "element")[0]

                # Set data frame object for custom data frame
                self.__frame4KMZ = mapping.ListDataFrames(self.__mxd)[1]

                # Add range ring, world feature classes and world topo as layers to element dataframe
                legend.autoAdd = True
                ApplySymbologyFromLayer_management(ringlyr, symbologyRingLayer) # apply symbology
                mapping.AddLayer(dataFrameElement, ringlyr, "TOP")
                legend.autoAdd = False
                ApplySymbologyFromLayer_management(elementWorldlyr, symbologyElementWorldLayer) # apply symbology
                mapping.AddLayer(dataFrameElement, elementWorldlyr)
                mapping.AddLayer(dataFrameElement, elementWorldTopoLayer, "BOTTOM") 

                # Add range ring to custom frame dataframe
                ApplySymbologyFromLayer_management(unprjringlyr, symbologyRingLayer)
                mapping.AddLayer(self.__frame4KMZ, unprjringlyr) 

                # Set extent of element data frame
                dataFrameElement.extent = ringlyr.getExtent()

                # Set range ring layer variables in data frames 
                prjlyr = mapping.ListLayers(self.__mxd, ringlyr, dataFrameElement)[0]

                # Update legend style in element data frame
                styleItem = mapping.ListStyleItems("ESRI.style", "Legend Items", "Horizontal Single Symbol Label Only")[0]
                legend = mapping.ListLayoutElements(self.__mxd, "LEGEND_ELEMENT")[0]
                legend.updateItem(prjlyr, styleItem)

                # If the range ring layer is set to "UNIQUE_VALUES" set class descriptions to system information list (self.__infoList)
                if prjlyr.symbologyType == "UNIQUE_VALUES":
                    prjlyr.symbology.classLabels = self.__infoList
                else:
                    windll.user32.MessageBoxA(0, 'Range ring symbology type is not set to "UNIQUE_VALUES"', "Program Error", 0)    

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
                spatialRef = Describe("multirangering.shp")
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
                        elm.text = "Multiple Range Ring Map"
                    elif elm.text == "title":
                        elm.text = self.__countryName
                        
                # Set variable to the MXD
                self.__saveMapVariable = self.__mxdDirectory + "\\range_ring_template_working.mxd"

                # Save copy of map
                self.__mxd.saveACopy(self.__saveMapVariable)

                # Cleanup previous mxd in instance
                del self.__mxd

                # Cleanup dataframe instances
                del dataFrameElement, self.__frame4KMZ
                
                # Delete layer variables
                del elementWorldlyr, elementWorldTopoLayer, ringlyr, unprjringlyr, symbologyRingLayer, symbologyElementWorldLayer, prjlyr

                # Delete legend variable
                del legend

                # Delete spatial reference variable
                del spatialRef
           
            # Set new mxd
            self.__mxd = mapping.MapDocument(self.__saveMapVariable)
            
            # Export map to user designated format
            messageNumber = exportMap(self.__outputFilePath, self.__mxd, self.__saveMapVariable)
            exportMap(self.__outputFilePath, self.__mxd, self.__saveMapVariable)
            
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
        root.title("Multiple Range Ring Generator")
        root.attributes('-topmost', 1)
        root.attributes('-topmost', 0) # put window on top of all others

        # Configure GUI frame, grid, column and root weights
        mainframe = ttk.Frame(root)
        mainframe.grid(column=0, row=0, sticky=(N,W,E,S))
        mainframe.columnconfigure(0, weight=1)
        mainframe.rowconfigure(0, weight=1)

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
        entryListName = StringVar()
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
        consolidatedWeaponsList = consolidatedWpnsList(weaponSystemDictionary) # Create consolidated weapon system list
        countryList = buildCountryList(countryDictionary) # Create country list (country name)
        resolutionList = ["Low", "Normal"] # Create list for user choices for range ring resolution 

        # Create list to hold abbreviations for distance values
        distanceList = []
        for key, value in distanceDictionary.iteritems():
            distanceList.append(key)

        # Create combobox for country name entry
        countryName_entry = ttk.Combobox(mainframe, width=59, state="normal", textvariable=cntryName, values=countryList) 
        countryName_entry.grid(column = 2, row = 1, columnspan = 2, sticky = W)
        countryName_entry.bind('<<ComboboxSelected>>', countryDynamicMatch, add="+")
        countryName_entry.bind('<KeyRelease>', countryDynamicMatch, add="+")
        ttk.Label(mainframe, text = "Country Name:").grid(column = 1, row = 1, sticky = W)

        # Create list box for system name(s) 
        weaponChoiceList = Listbox(mainframe,height=5,width=42,selectmode=EXTENDED)
        weaponChoiceList.grid(column=2,columnspan=2,row=2,sticky=W)

        # Create scroll bar for weapon choice list box
        scrollBarOne = Scrollbar(mainframe, orient=VERTICAL, command=weaponChoiceList.yview)
        scrollBarOne.grid(column=2, row=2, sticky=(N,S,E))
        weaponChoiceList['yscrollcommand'] = scrollBarOne.set

        # Create a checkbox for other "manual entry" option
        other_entry = Checkbutton(mainframe,variable=otherSysActivate,command=disableWeaponCombobox)
        other_entry.grid(column=2,row=3,sticky=W)
        other_entry.bind('<<Button>>',disableWeaponCombobox)
        Label(mainframe,text="Manual Entry:").grid(column=1,row=3,sticky=W)

        # Create entry box for alternate system name
        otherSysName_entry = ttk.Combobox(mainframe,width=30,state="disabled",textvariable = otherSysName, values = consolidatedWeaponsList)  
        otherSysName_entry.bind('<KeyRelease>', weaponSystemDynamicMatch, add="+")
        otherSysName_entry.bind('<<ComboboxSelected>>', weaponSystemDynamicMatch, add="+")
        otherSysName_entry.grid(column=2,row=4,sticky=W)
        ttk.Label(mainframe, text="Other System Name:").grid(column=1,row=4,sticky=W)

        # Create button adding user entry (system name, range and distance unit) to system list
        addButton = Button(mainframe,text="Add",state="normal",command=addUserSelection,width=4)
        addButton.grid(column=3,row=3,sticky=W)

        # Create entry box for system range
        otherSysRange_entry = ttk.Entry(mainframe,width=31,state="disabled",textvariable = sysRange)
        otherSysRange_entry.grid(column=2,row=5,columnspan=2,sticky=W)
        ttk.Label(mainframe, text="System Range:").grid(column=1,row=5,sticky=W)

        # Create combobox for distance selection
        distance_entry = ttk.Combobox(mainframe,width=3,state="disabled",textvariable=distanceVariable, values=distanceList)
        distance_entry.grid(column=2,row=6,sticky=W)
        ttk.Label(mainframe,text="Distance Unit:").grid(column=1,row=6,sticky=W)

        # Create progress bar
        status = ttk.Progressbar(mainframe,orient=HORIZONTAL,length=180,mode='determinate',variable=valueSet,maximum=90) 
        status.grid(column=1,row=15,sticky=W)

        # Create read only entry for displaying program progress updates
        statusMessage = ttk.Entry(mainframe,width=29,state="readonly",textvariable=displayText)
        statusMessage.grid(column=1,row=16,sticky=W)

        # Create list box for user entry
        weaponSelectionList = Listbox(mainframe, height=5,width=60,selectmode=EXTENDED)
        weaponSelectionList.grid(column=2,columnspan=2,row=8,sticky=W)

        # Create scroll bar for user entry list box
        scrollBarTwo = Scrollbar(mainframe, orient=VERTICAL, command=weaponSelectionList.yview)
        scrollBarTwo.grid(column=2,columnspan=2,row=8,sticky=(N,S,E))
        weaponSelectionList['yscrollcommand'] = scrollBarTwo.set

        # Create button removing user entry(system name, range and distance unit) to system list
        removeButton = ttk.Button(mainframe,text="Remove",state="disabled",command=removeUserSelection,width=8)
        removeButton.grid(column=4,row=8,sticky=W) 

        # Create button executing program
        generateButton = ttk.Button(mainframe,text="Generate Map", state="disabled",command=calculate,width=13)
        generateButton.grid(column=2,row=15,sticky=W)

        # Create label for classify tool
        classifyLabel = ttk.Label(mainframe, text="Fact of country having said system(s):")
        classifyLabel.grid(column=1,row=11,sticky=E)

        # Create button that triggers the classification tool
        classifyButton = ttk.Button(mainframe,text="Classify Map",state="disabled",command=classify,width=12)
        classifyButton.grid(column=2,row=11,sticky=W)

        # Create label for range ring resolution selection
        resolutionChoice = ttk.Combobox(mainframe,state="readonly",width=5,textvariable=resolutionVariable,values=resolutionList)
        resolutionChoice.grid(column=2,row=12,sticky=W)

        # Create combbox for range ring resolution
        resolutionChoiceLabel = Label(mainframe, text="Range Ring Resolution:")
        resolutionChoiceLabel.grid(column=1,row=12,sticky=W)

        # Create button reseting program
        resetButton = ttk.Button(mainframe,text="Reset Menu",state="normal",command=reset,width=12)
        resetButton.grid(column=3,columnspan=2,row=15,sticky=E)

        # Create button quiting program
        exitButton = ttk.Button(mainframe,text="Exit Program",command=quitProgram,width=12)
        exitButton.grid(column=3,columnspan=2,row=16,sticky=E)

        # Add 5 units of padding between all elements in the frame
        for child in mainframe.winfo_children():
            child.grid_configure(padx=5, pady=5)

        # Set focus to country name entry combobox
        countryName_entry.focus() 

        # Bind escape and return keys to quit and generate map buttons 
        root.bind('<Escape>', quitProgram)
        root.bind('<Return>', calculate)

        # Make sure all mouse or keyboard events go to the root window
        root.grab_set()

        # Wait until GUI is exited 
        root.wait_window()

        # Return value of 1 that will activate main menu button selected
        return variable
