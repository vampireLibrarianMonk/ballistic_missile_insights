# Import modules from arcpy
from arcpy import AddField_management
from arcpy import ApplySymbologyFromLayer_management
from arcpy import Buffer_analysis
from arcpy import Clip_analysis
from arcpy import CopyFeatures_management
from arcpy.da import SearchCursor, UpdateCursor
from arcpy import Delete_management
from arcpy import Describe
from arcpy import env
from arcpy import GetCount_management
from arcpy import ListFeatureClasses
from arcpy import MakeFeatureLayer_management
from arcpy import mapping
from arcpy import Near_analysis
from arcpy import Project_management
from arcpy import SelectLayerByAttribute_management
from arcpy import SelectLayerByLocation_management
from arcpy import SaveToLayerFile_management

# Import modules from ctypes
from ctypes import windll

# Import modules from imp
from imp import load_compiled

# Import modules from os
from os import environ
from os import path

# Import modules from subprocess
from subprocess import Popen

# Import modules from sys
from sys import argv

# Import modules from Tkinter
from Tkinter import *

# Import ttk module
import ttk

# Import modules from time for diagnostics
from time import strftime

# Import ask ask save as filename modules from tk File Dialog
from tkFileDialog import asksaveasfilename

# Set variables for environment and scratch workspace and main directory
fileName =  path.basename(argv[0])
mainDirectory = argv[0]
mainDirectory = mainDirectory.replace(fileName, "")
mainDirectory += "range_ring\\"
dataPath = mainDirectory + "\\Data"
scratchPath = mainDirectory + "scratch"

# Import range ring modules
main_RRR_Var1 = mainDirectory + "code\\rangeRingModules.pyc"
load_compiled('rangeRingModules', main_RRR_Var1)
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
        self.__toolName = "reverseRangeRing"
        
        # Set variable for current workspace of geodatabase
        self.__gdbWorkspace = dataPath 

        # Variables for storing various folder paths
        self.__layerDirectory = mainDirectory + "\\layers"
        self.__workingLayerDirectory = self.__layerDirectory + "\\workingLayers\\"
        self.__mxdDirectory = mainDirectory + "\\MXD"
        self.__imageDirectory = mainDirectory + "\\exported_images"
        self.__pdfDirectory = mainDirectory +"\\exported_pdfs"
        self.__kmzDirectory = mainDirectory + "\\exported_kmls"
        self.__prjDirectory = mainDirectory + "\\PRJ"
        self.__outputFilePath = ""

        # Set variable to mxd map instance
        self.__mapTemplate = self.__mxdDirectory + "\\range_ring_template_wo_inset.mxd" 
        self.__mxd = mapping.MapDocument(self.__mapTemplate)

        # Class boolean values
        self.__continueProcessing = True # Set boolean variable for breaking out of processes
        self.__justMapBoolean = False # Set boolean for clicking generate map button to speed up sequential processing of other formats for same map

        # Class dictionaries
        self.__portionClassificationDictionary = portionClassificationDictionary() # Retrieve weapon portion classification dictionary
        self.__bannerClassificationDictionary = bannerClassificationDictionary() # Retrieve weapon banner classification dictionary
        self.__weaponSystemSourceDictionary = getWeaponSystemSource() # Retrieve weapon source

        # Variable for dynamic country swap
        self.__swapCountryName = ""

        # Variables for city name and city name without special characters
        self.__cityName = ""            
        self.__cityFileName = ""

        # Variable for military base name and military base name without special characters
        self.__baseName = ""
        self.__componentName = ""
        self.__baseFileName = ""

        # Variables for country name, country name without special characters and current country trigraph
        self.__countryName = ""
        self.__countryFileName = ""
        self.__targetCountryName = ""
        self.__currentCountryTrigraph = ""

        # Variables for system name and system name without special characters
        self.__systemName = ""
        self.__flatSystemName = ""

        # Variable for storing feature name to be buffered
        self.__variableName = ""
        self.__featureName = ""

        # Variable for tracking distance unit and range in km
        self.__distanceUnit = ""
        self.__kmRange = 0

        # Variable for keeping track of matching weapon system list                        
        self.__matchingWeaponsList = []

        # Variable tracking only weapons
        self.__weaponOnlyList = []

        # Variable to display threat system number count
        self.__displayVariable = ""

        # Variable for distance measurement between target city and shooter country
        self.__minimumRange = 0.0

        # Variables for system name and system name without special characters or spaces     
        self.__systemClass = ""

        # Variable holding path to projection file
        self.__prjFile = ""

        # Variable for storing how many intersections occur over the anti-meridian
        self.__matchCount = 0

        # Variable tracking user format choice
        self.__userFormatChoice = ""

        # Variables for obtaining classification of product
        self.__portionMarkingVariable = ""
        self.__classificationPortionMarking = ""
        self.__classificationBanner = ""

        # Variables for storing map variables
        self.__countryQueryString = ""
        self.__savedLayer = ""
        self.__countryLayer = ""
        self.__saveMapVariable = ""

        # Set variable to original mxd map instance
        self.__mapTemplate = self.__mxdDirectory + "\\range_ring_template_wo_inset.mxd" 
        self.__mxd = mapping.MapDocument(self.__mapTemplate)
        
    def reverseRangeRingGenerator(self):
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
            
        # Clears data created during process and exits program
        def quitProgram():
            # Disable all widgets except progress bar and message display
            cityName_entry.config(state = "disabled")
            baseName_entry.config(state = "disabled")
            other_entry.deselect()
            other_entry.config(state="disabled")
            countryName_entry.config(state = "disabled")
            system_entry.config(state = "disabled")
            calculateButton.config(state = "disabled")
            generateMapButton.config(state = "disabled")
            resetButton.config(state = "disabled")
            exitButton.config(state = "disabled")
          
            # Reset status bar  
            valueSet.set(0)
            statusBar.update()     

            # Clean scratch workspace
            displayText.set("Cleaning scratch workspace...")
            statusMessage.update()
            
            clearScratchWorkspace(scratchPath)

            # Step progressbar up 6 units
            valueSet.set(6)
            statusBar.update()
            
            # Clean data folder
            displayText.set("Cleaning data folder...")
            statusMessage.update()
            
            clearWorkspace(dataPath)

            # Step progressbar up 12 units
            valueSet.set(12)
            statusBar.update()
            
            # Clean working directory
            displayText.set("Cleaning working directory...")
            statusMessage.update()
            
            clearWorkingLayerDirectory(self.__workingLayerDirectory)

            # Step progressbar up 18 units
            valueSet.set(18)
            statusBar.update()  

            displayText.set("Deleting temporary layers...")
            statusMessage.update()

            # Delete temporary layers
            Delete_management("citiesLayer")
            Delete_management("baseLayer")
            Delete_management("worldLayer")
            Delete_management("meridian_layer")
            Delete_management("country_lyr")
            if self.__flatSystemName and self.__systemRange:
                rangeRing = self.__flatSystemName + "_" + str(self.__systemRange)
                Delete_management(rangeRing)
            else:
                pass

            # Step progressbar up 24 units
            valueSet.set(24)
            statusBar.update()  

            displayText.set("Exiting program...")
            statusMessage.update()

            # Step progressbar up 30 units
            valueSet.set(30)
            statusBar.update() 
            
            # Exit Program 
            root.destroy()
            
        def reset():
            # Disable all widgets except progress bar and message display
            cityName_entry.config(state = "disabled")
            baseName_entry.config(state = "disabled")
            other_entry.deselect()
            other_entry.config(state="disabled")
            countryName_entry.config(state = "disabled")
            system_entry.config(state = "disabled")
            calculateButton.config(state = "disabled")
            generateMapButton.config(state = "disabled")
            resetButton.config(state = "disabled")
            exitButton.config(state = "disabled")
          
            # Reset status bar  
            valueSet.set(0)
            statusBar.update()

            # Clean scratch workspace
            displayText.set("Cleaning scratch workspace...")
            statusMessage.update()
            
            clearScratchWorkspace(scratchPath)

            # Step progressbar up 6 units
            valueSet.set(6)
            statusBar.update()
            
            # Clean data folder
            displayText.set("Cleaning data folder...")
            statusMessage.update()
            
            clearWorkspace(dataPath)

            # Step progressbar up 12 units
            valueSet.set(12)
            statusBar.update()
            
            # Clean working directory
            displayText.set("Cleaning working directory...")
            statusMessage.update()
            
            clearWorkingLayerDirectory(self.__workingLayerDirectory)

            # Step progressbar up 18 units
            valueSet.set(18)
            statusBar.update()  

            displayText.set("Deleting temporary layers...")
            statusMessage.update()

            # Delete temporary layers
            Delete_management("citiesLayer")
            Delete_management("baseLayer")
            Delete_management("worldLayer")
            Delete_management("meridian_layer")
            Delete_management("country_lyr")
            if self.__flatSystemName and self.__systemRange:
                rangeRing = self.__flatSystemName + "_" + str(self.__systemRange)
                Delete_management(rangeRing)
            else:
                pass
            if self.__featureName:
                Delete_management(self.__featureName.replace(".shp", ""))

            # Step progressbar up 24 units
            valueSet.set(24)
            statusBar.update()  

            displayText.set("Reseting GUI...")
            statusMessage.update()
          
            # Set variable to mxd map instance
            self.__mapTemplate = self.__mxdDirectory + "\\range_ring_template_wo_inset.mxd" 
            self.__mxd = mapping.MapDocument(self.__mapTemplate)

            # Reset shortcut to map variable
            self.__justMapBoolean = False

            # Reset country swap variable
            self.__swapCountryName = ""

            # Reset weapons list variable
            self.__weaponOnlyList = []

            # Reset match count variable
            self.__matchCount = 0

            # Reset city name entry
            cityName.set("")
            cityName_entry.config(state="normal")
            cityName_entry.config(values=cityList)
            cityName_entry.update()

            # Reset target selection switch
            other_entry.config(state="normal")
            other_entry.update()

            # Reset military base name entry
            baseName.set("")
            baseName_entry.config(state = "disabled")
            baseName_entry.update()

            # Reset country name entry
            cntryName.set("")
            countryName_entry.config(state="normal")
            if self.__swapCountryName == "":
                pass
            else:
                countryList.append(self.__swapCountryName)
            countryList.sort()
            countryName_entry.config(values=countryList)
            countryName_entry.update()

            # Add removed country back to country list (code would not take other list values a reset of countryList)
            systemName.set("")
            self.__matchingWeaponsList = []
            system_entry.config(values=self.__matchingWeaponsList)
            system_entry.config(state="disabled")
            system_entry.update()

            # Reset calculate button
            calculateButton.config(state="normal")
            calculateButton.update()

            # Reset generate button
            generateMapButton.config(state="disabled")
            generateMapButton.update()

            # Reset reset button
            resetButton.config(state = "normal")
            resetButton.update()

            # Reset exit button 
            exitButton.config(state = "normal")
            exitButton.update()

            # Step progressbar up 30 units
            valueSet.set(30)
            statusBar.update()

            # Reset message display
            displayText.set("")
            statusMessage.update()

            # Reset progress bar
            valueSet.set(0)
            statusBar.update()

            # Set focus to city name entry
            cityName_entry.focus()

        # Function to switch target selection from cities to US military bases
        def switchTargetSelection():
            if otherEntry.get() == True:
                cityName_entry.config(state= "disabled")
                baseName_entry.config(state= "normal")
            else:
                cityName_entry.config(state= "normal")
                baseName_entry.config(state= "disabled")                

        # Function to take presently selected target city's host country out of the shooter country name selection list
        def valueHandler(*args):
            if self.__swapCountryName != "":
                countryList.append(self.__swapCountryName)
            else:
                pass
            
            countryTrigraph = ""
            current = cityName_entry.get()

            for key, value in cityDictionary.iteritems():
                if key[4:] == current:
                    countryTrigraph = key[:3]
                    for key, value in countryDictionary.iteritems():
                        if value == countryTrigraph:
                            self.__swapCountryName = key
                        else:
                            pass
                else:
                    pass
                
            if self.__swapCountryName in countryList:
                cntryName.set("")
                countryList.remove(self.__swapCountryName)
                countryName_entry.config(values=countryList)
                countryName_entry.config(state="normal")
                countryName_entry.update()
            else:
                pass

        # Forward arguments to dynamic match routine in range ring modules and returns the closest city name match in city list
        def cityDynamicMatch(event):
            dynamicMatch(event, cityName_entry, cityList, cityName)

            if cityName_entry.get() == "":
                cityName_entry.config(values=cityList)
            else:
                pass

        # Forward arguments to dynamic match routine in range ring modules and return the closest military name match in military base list
        def baseDynamicMatch(event):
            dynamicMatch(event, baseName_entry, militaryBaseList, baseName) 

            if baseName_entry.get() == "":
                baseName_entry.config(values=militaryBaseList)
            else:
                pass          
        
        # Forward arguments to dynamic match routine in range ring modules and returns a the closest country name match in country list
        def countryDynamicMatch(event):
            dynamicMatch(event, countryName_entry, countryList, cntryName)

            if countryName_entry.get() == "":
                countryName_entry.config(values=countryList)
            else:
                pass
            
        def calculate(*args):
            while self.__continueProcessing == True:
                if otherEntry.get() == True:
                    # Retrieve military base name entered
                    try:
                        self.__baseName = baseName_entry.get()
                        self.__baseFileName = filter(str.isalnum, self.__baseName)
                        
                        if self.__baseName == "":
                            errorMessage = "Please choose a target military base."
                            raise ValueError
                        elif self.__baseName not in militaryBaseList:
                            errorMessage = "Military base entry invalid."
                            raise ValueError
                        else:
                            pass                
                    except:
                        windll.user32.MessageBoxA(0, errorMessage, "Entry Error", 0)
                        break

                    # Remove country name in "()" if present # http://stackoverflow.com/questions/14716342/how-do-i-find-the-string-between-two-special-characters
                    if "(" in self.__baseName:
                        additionalMatch = True
                        removeVariable = " (" + self.__baseName.partition('(')[-1].rpartition(')')[0] + ")"
                        self.__baseName = self.__baseName.replace(removeVariable, "")
                        self.__componentName = removeVariable.partition('(')[-1].rpartition(')')[0]
                    else:
                        additionalMatch = False

                    # Create query string of city name
                    # Example: SITE_NAME = 'MCB Quantico' and/or COMPONENT = 'MC Active' 
                    baseNameField = "SITE_NAME"
                    if additionalMatch == True:                
                        componentNameField = "COMPONENT"
                        baseQueryString = '"' + baseNameField + '" = ' + "'" + self.__baseName + "'" + " AND " + '"' + componentNameField + '" = ' + "'" + self.__componentName + "'"
                    else:
                        baseQueryString = '"' + baseNameField + '" = ' + "'" + self.__baseName + "'"

                    shapefile = "military_bases_US.shp"
                    layer = "baseLayer"
                    queryString = baseQueryString
                    self.__variableName = str(self.__baseFileName) + ".shp"           
                else:
                    # Retrieve city name entered
                    try:
                        self.__cityName = cityName_entry.get()
                        self.__cityFileName = filter(str.isalnum, self.__cityName)
                        
                        if self.__cityName == "":
                            errorMessage = "Please choose a target city."
                            raise ValueError
                        elif self.__cityName not in cityList:
                            errorMessage = "City entry invalid."
                            raise ValueError
                        else:
                            pass                
                    except:
                        windll.user32.MessageBoxA(0, errorMessage, "Entry Error", 0)
                        break

                    # Remove country name in "()" if present # http://stackoverflow.com/questions/14716342/how-do-i-find-the-string-between-two-special-characters
                    if "(" in self.__cityName:
                        additionalMatch = True
                        removeVariable = " (" + self.__cityName.partition('(')[-1].rpartition(')')[0] + ")"
                        self.__cityName = self.__cityName.replace(removeVariable, "")
                        self.__targetCountryName = removeVariable.partition('(')[-1].rpartition(')')[0]
                    else:
                        additionalMatch = False

                    # Create query string of city name
                    # CITY_NAME = 'Hamilton' AND ADMIN_NAME = 'Bermuda (United Kingdom)' example
                    cityNameField = "CITY_NAME"
                    if additionalMatch == True:                
                        adminNameField = "ADMIN_Name"
                        cityQueryString = '"' + cityNameField + '" = ' + "'" + self.__cityName + "'" + " AND " + '"' + adminNameField + '" = ' + "'" + self.__targetCountryName + "'"
                    else:
                        cityQueryString = '"' + cityNameField + '" = ' + "'" + self.__cityName + "'"

                    shapefile = "cities.shp"
                    layer = "citiesLayer"
                    queryString = cityQueryString
                    self.__variableName = str(self.__cityFileName) + ".shp"

                # Retrieve country name entered
                try:
                    self.__countryName = countryName_entry.get()
                    self.__countryFileName = filter(str.isalnum, self.__countryName)

                    if self.__countryName == "":
                        errorMessage = "Please choose a threat country."
                        raise ValueError
                    elif self.__countryName not in countryList:
                        errorMessage = "Country entry invalid."
                        raise ValueError
                    else:
                        pass                
                except:
                    windll.user32.MessageBoxA(0, errorMessage, "Country Entry Error", 0)
                    break
                
                # Look for a valid trigraph matching country entered
                try:
                    self.__currentCountryTrigraph = countryDictionary[self.__countryName]
                except:
                    windll.user32.MessageBoxA(0, "No matching trigraph for country entered", "Program Error", 0)
                    break

                #Diagnostic time stamp print
                print strftime("%Y-%m-%d %H:%M:%S")

                # Disable city combobox
                cityName_entry.config(state="disabled")
                cityName_entry.update()

                # Disable switch target selection checkbutton
                other_entry.config(state="normal")
                other_entry.update()
                
                # Disable city combobox
                baseName_entry.config(state="disabled")
                baseName_entry.update()                

                # Disable country combobox
                countryName_entry.config(state="disabled")
                countryName_entry.update()

                # Disable calculate button
                calculateButton.config(state="disabled")
                calculateButton.update()

                displayText.set("Processing Input")
                statusMessage.update()

                # Make a layer from the choice target feature class
                MakeFeatureLayer_management(shapefile, layer)
                layerName = layer + ".lyr"
                self.__savedLayer = self.__workingLayerDirectory + layerName

                # Select within target feature class the target point
                SelectLayerByAttribute_management(layer, "NEW_SELECTION", queryString) 
                SaveToLayerFile_management(layer, self.__savedLayer, "RELATIVE")

                # Write the selected features to a new featureclass
                CopyFeatures_management(layer, self.__variableName)

                # If the name was not present with the city name find city's home country
                if otherEntry.get() == True:
                        self.__targetCountryName = "United States"
                else:
                    cityNameVariable = str(self.__cityFileName) + ".shp"
                    countrySearch = SearchCursor(cityNameVariable, ["ADMIN_NAME"])

                    for name in countrySearch:
                        self.__targetCountryName = name[0]

                # Make a layer from the world feature class
                MakeFeatureLayer_management("world.shp", "worldLayer")
                worldLayer = "worldLayer" + ".lyr"
                self.__savedWorldLayer = self.__workingLayerDirectory + worldLayer
                SaveToLayerFile_management("worldLayer", self.__savedWorldLayer, "RELATIVE")

                # Create query string of country name
                countryNameField = "NAME"
                self.__countryQueryString = '"' + countryNameField + '" = ' + "'" + self.__countryName + "'"

                # Select within world feature class the shooter country
                SelectLayerByAttribute_management("worldLayer", "NEW_SELECTION", self.__countryQueryString)
                
                # Write the selected features to a new featureclass
                countryNameVariable = str(self.__countryFileName) + ".shp"
                CopyFeatures_management("worldLayer", countryNameVariable)

                statusBar.step(15)
                statusBar.update()

                displayText.set("Calculating Minimum Range")
                statusMessage.update()

                Near_analysis(self.__variableName,countryNameVariable,"", "","" ,"GEODESIC")       

                # Create list to hold country choices
                fcs = ListFeatureClasses(self.__variableName)
                curObj = SearchCursor(self.__variableName, ["NEAR_DIST"])

                for row in curObj:
                    self.__minimumRange = row[0]

                self.__minimumRange = int(self.__minimumRange/1000)

                weaponsMatch()

                statusBar.step(15)
                statusBar.update()

                displayText.set("Minimum Range = " + str('{:,}'.format(self.__minimumRange)) + " km")
                statusMessage.update()           

                system_entry.config(state="readonly")
                system_entry.update()
                
                if system_entry.get() == "No systems within range in database":
                    pass
                else:
                    generateMapButton.config(state="normal")
                    generateMapButton.update()
                    
                #Diagnostic time stamp print
                print strftime("%Y-%m-%d %H:%M:%S")

                break

        # Populate threat system combobox with threat systems that match or surpass the required 04_minimum range bewteen target city and shooter country
        def weaponsMatch():
            weaponDBF = SearchCursor("Weapon_List.dbf", ["sys_name", "Max_Range", "Country"])

            for entry in weaponDBF:
                if entry[2] == countryDictionary[self.__countryName]:
                    if entry[1] >= self.__minimumRange:
                        entryVariable = entry[0] + " (" + str('{:,}'.format(entry[1])) + " km" + ")" 
                        self.__matchingWeaponsList.append(entryVariable)
                        self.__weaponOnlyList.append(entry[0])
                    else:
                        pass
                else:
                    pass
            if len(self.__matchingWeaponsList) == 0:
                self.__displayVariable = "No systems within range in database" 
                systemName.set(self.__displayVariable)
                system_entry.update() 
                generateMapButton.config(state="disabled")
                generateMapButton.update() 
            else:
                self.__matchingWeaponsList.sort()
                self.__weaponOnlyList.sort()
                system_entry.config(state="readonly")
                self.__displayVariable = "Systems within range: " + str(len(self.__matchingWeaponsList))
                systemName.set(self.__displayVariable)
                system_entry.config(values=self.__matchingWeaponsList)
                system_entry.update()   

        def generateMap():
            stopLoop = False
            while stopLoop == False:
                # Get system selection from user if there are systems available, if not selected prompt to choose
                try:                   
                    if system_entry.get() == self.__displayVariable:
                        errorMessage = "Please select threat system"
                        raise ValueError
                    else:
                        pass
                except:
                    windll.user32.MessageBoxA(0, errorMessage, "Threat System Entry Error", 0)
                    break

                # Get the output directory from the user
                getExportFilePath()
                
                if self.__outputFilePath.replace(" ","") == "/":
                    displayText.set("Paused by User")
                    statusMessage.update()
                    break
                else:
                    pass

                if self.__justMapBoolean == False:
                    # Set variable for system name
                    self.__systemName = self.__weaponOnlyList[system_entry.current()]

                    # Delete all invalid characters for a system file name
                    self.__flatSystemName = filter(str.isalnum, str(self.__systemName))

                    # Set variable for country trigraph and system name for find the system's range via the weapon system dictionary
                    findRangeVariable = self.__currentCountryTrigraph + "_" + self.__systemName            
                    self.__systemRange = systemRangeDictionary[findRangeVariable]

                    # Retrieve system class and range in km
                    self.__systemClass, self.__kmRange = getSystemClass(self)

                    # Get portion marking classification from weapon database via established classification dictionaries
                    self.__classificationMarkingVariable = self.__currentCountryTrigraph + "_" + self.__systemName
                    self.__classificationPortionMarking = self.__portionClassificationDictionary[self.__classificationMarkingVariable]
                    
                    # Get banner marking classification from weapon database via established classification dictionaries
                    self.__classificationBanner = self.__bannerClassificationDictionary[self.__classificationMarkingVariable]
                else:
                    pass

                #Diagnostic time stamp print
                print strftime("%Y-%m-%d %H:%M:%S")

                # Disable other_entry checkbutton, generate, reset, quit buttons and format combobox
                other_entry.config(state="disabled")
                other_entry.update()

                generateMapButton.config(state="disabled")
                generateMapButton.update()

                resetButton.config(state="disabled")
                resetButton.update()
                
                exitButton.config(state="disabled")
                exitButton.update()

                system_entry.config(state="disabled")
                system_entry.update()

                # Set progressbar to 0 units
                valueSet.set(0)
                statusBar.update()

                # Set display message to display 
                displayText.set("Creating Range Ring")
                statusMessage.update()

                valueSet.set(10)
                statusBar.update()

                if self.__justMapBoolean == False:
                    # Run main range ring function
                    bufferCity()
                else:
                    pass

                displayText.set("Creating Map")
                statusMessage.update()

                valueSet.set(20)
                statusBar.update()

                if self.__justMapBoolean == False:
                    processMap()
                else:
                    pass

                displayText.set("Creating Map")
                statusMessage.update()

                valueSet.set(20)
                statusBar.update()
                
                # Set new mxd instance for exporting map
                self.__mxd = mapping.MapDocument(self.__saveMapVariable)
       
                # Export map to user designated format
                messageNumber = exportMap(self.__outputFilePath, self.__mxd, self.__saveMapVariable)

                # Cleanup mxd instance
                del self.__mxd
                
                # Open Finished File
                if messageNumber == 2:
                    displayText.set("Paused by User")
                    statusMessage.update()
                    pass
                else:
                    valueSet.set(30)
                    displayText.set("Range Ring Map Created")
                    statusMessage.update() 
                    statusBar.update()
                    Popen('start ' + self.__outputFilePath, shell=True)

                # Enable generate, reset, quit buttons and format combobox
                generateMapButton.config(state="normal")
                generateMapButton.update()

                resetButton.config(state="normal")
                resetButton.update()
                
                exitButton.config(state="normal")
                exitButton.update()
                
                #Diagnostic time stamp print
                print strftime("%Y-%m-%d %H:%M:%S")
                break

        def bufferCity():
            # Create variables for buffer tool depending on target entered
            if otherEntry.get() == True:
                self.__featureName = self.__baseFileName + "_" + str(self.__systemRange) + ".shp"
            else:
                self.__featureName = self.__cityFileName + "_" + str(self.__systemRange) + ".shp"
                
            draftBufferName = "draft_" + self.__featureName

            # Set Central Meridian variable
            self.__prjFile = adaptPRJ(self.__currentCountryTrigraph, countryCentroidDictionary[self.__currentCountryTrigraph], self.__prjDirectory)

            # Execute Buffer Tool
            distanceVariable = str(self.__systemRange) + " " + "Kilometers"
            cityNameVariable = str(self.__cityFileName) + ".shp"
            Buffer_analysis(self.__variableName, "fcs_buffer.shp", distanceVariable, "", "", "", "")

            # Clip buffer by the input country
            countryNameVariable = str(self.__countryFileName) + ".shp"
            Clip_analysis("fcs_buffer.shp", countryNameVariable, draftBufferName) 

            # Make newly projected meridian feature class into feature layer for select by location decision loop
            MakeFeatureLayer_management("meridian.shp", "meridian_layer")

            # Project newly created buffer feature class
            Project_management(draftBufferName, self.__featureName, self.__prjFile)

            # Create layer for threat country
            MakeFeatureLayer_management(countryNameVariable, "country_lyr")

            # Select by location, if buffer falls within meridian then perform intersect, merge and dissolve new output feature class
            SelectLayerByLocation_management("country_lyr",'INTERSECT',"meridian_layer")

            # Set variable for decision loop determining how many intersections occur between the projected buffer and the meridian layer
            self.__matchCount = int(GetCount_management("country_lyr")[0])

            if self.__matchCount > 0:
                # Alternate Project newly created buffer feature class
                Project_management(countryNameVariable, "country_prj.shp", self.__prjFile)            

                # Aggregate newly created buffer feature class to get rid of anti-meridian artifacts
                from arcpy import AggregatePolygons_cartography
                AggregatePolygons_cartography("country_prj.shp", "country_aggregate.shp", "1 Centimeter")
            else:
                pass

        # Function to assemble and export map in the user's chosen format
        def processMap():
            if otherEntry.get() == True:
                # Add new field containing military base name (component)
                AddField_management(self.__featureName, "NAME", "TEXT", "", "", "60", "Base Name")

                # Update unprojected buffer feature class with "NAME" field for display in Google Earth kmz file
                with UpdateCursor(self.__featureName, ['SITE_NAME',"COMPONENT", "NAME"]) as cursor:
                    for row in cursor:
                        string = row[0] + " (" + row[1] + ")"
                        row[2] = string

                        # Update cursor to reflect change in name
                        cursor.updateRow(row)
                    del cursor
            else:
                pass
            
            # Make and save range ring layer
            MakeFeatureLayer_management(self.__featureName, self.__featureName.replace(".shp", ""))
            if otherEntry.get() == True:
                rangeRingLayer = self.__baseFileName + "_" + self.__countryFileName + "_" + self.__flatSystemName + "_" + str(self.__systemRange) + ".lyr"
            else:
                rangeRingLayer = self.__cityFileName + "_" + self.__countryFileName + "_" + self.__flatSystemName + "_" + str(self.__systemRange) + ".lyr"
            savedRangeRingLayer = self.__workingLayerDirectory + rangeRingLayer
            SaveToLayerFile_management(self.__featureName.replace(".shp", ""), savedRangeRingLayer, "RELATIVE")

            # Make a layer from the world feature class
            if self.__matchCount > 0:
                MakeFeatureLayer_management("country_aggregate.shp", "country_lyr")
                self.__countryLayer = self.__workingLayerDirectory + "country_lyr.lyr"
                SaveToLayerFile_management("country_lyr", self.__countryLayer, "RELATIVE")
            else:
                countryNameVariable = str(self.__countryFileName) + ".shp"
                MakeFeatureLayer_management(countryNameVariable, "country_lyr")
                self.__countryLayer = self.__workingLayerDirectory + "country_lyr.lyr"
                SaveToLayerFile_management("country_lyr", self.__countryLayer, "RELATIVE")

            # Set layer variables
            countrylyr = mapping.Layer(self.__countryLayer)
            elementWorldlyr = mapping.Layer(self.__savedWorldLayer)
            elementWorldTopoLayerVariable = self.__layerDirectory + "\World_Topo_Map.lyr"
            elementWorldTopoLayer = mapping.Layer(elementWorldTopoLayerVariable)
            ringlyr = mapping.Layer(savedRangeRingLayer)

            # Set Variables for rangeRing and elementWorldLayer variables
            symbologyRingLayer = self.__layerDirectory + "\\reverse_range_ring.lyr"
            symbologyElementWorldLayer = self.__layerDirectory + "\\element_2_world.lyr"           
            symbologyRingLayer = mapping.Layer(symbologyRingLayer)
            symbologyElementWorldLayer = mapping.Layer(symbologyElementWorldLayer)

            # Set the legend element
            legend = mapping.ListLayoutElements(self.__mxd, "LEGEND_ELEMENT", "Legend")[0]

            # Set data frame object for custom data frame
            self.__frame4KMZ = mapping.ListDataFrames(self.__mxd)[1]

            # Set data frame object for element and inset data frames
            dataFrameElement = mapping.ListDataFrames(self.__mxd, "element")[0]

            # Add range ring, world feature classes and world topo as layers to element dataframe
            legend.autoAdd = True
            ApplySymbologyFromLayer_management(ringlyr, symbologyRingLayer) # apply symbology
            mapping.AddLayer(dataFrameElement, ringlyr, "TOP")
            legend.autoAdd = False
            ApplySymbologyFromLayer_management(elementWorldlyr, symbologyElementWorldLayer) # apply symbology
            mapping.AddLayer(dataFrameElement, elementWorldlyr)
            mapping.AddLayer(dataFrameElement, elementWorldTopoLayer, "BOTTOM")   

            # Add points of interest and range ring to custom frame dataframe
            mapping.AddLayer(self.__frame4KMZ, ringlyr, "TOP")

            # Set extent of element data frame to choosen threat country
            dataFrameElement.extent = countrylyr.getSelectedExtent()
         
            # Update legend in element data frame
            styleItem = mapping.ListStyleItems("ESRI.style", "Legend Items", "Horizontal Single Symbol Label Only")[0] # Legend Style
            lyr = mapping.ListLayers(self.__mxd, ringlyr, dataFrameElement)[0]
            legend = mapping.ListLayoutElements(self.__mxd, "LEGEND_ELEMENT")[0]
            legend.elementPositionX = .2696 # Legend X position
            legend.elementPositionY = .5552 # Legend Y position

            # Change layer name in legend to target name
            if otherEntry.get() == True:
                lyr.name = self.__baseName + " (" + self.__componentName + ")"
                legend.updateItem(lyr, styleItem)
            else:
                if "`" in self.__cityName:
                    lyr.name = self.__cityName.replace("`", "'")
                else:
                    lyr.name = self.__cityName
                    legend.updateItem(lyr, styleItem)                    

            # Obtain two values for configuring Created By: and Source:

            # Obtain current username for Classified By:
            userName = environ.get("USERNAME")

            # Obtain source derived from
            sourceID = self.__currentCountryTrigraph + "_" + self.__systemName
            spaceVariable = "                                             "
            if otherEntry.get() == True:
                source = self.__weaponSystemSourceDictionary[sourceID] + "\n" + spaceVariable + "DoS, Simplified World Polygons, March 2013" +  "\n" + spaceVariable + "DOD, Military Installations, Ranges, and Training Areas, 21 November 2013"
            else:
                source = self.__weaponSystemSourceDictionary[sourceID] + "\n" + spaceVariable + "DoS, Simplified World Polygons, March 2013"

            # Set variables for element configuration of map
            twoBibliography = "Created By: " + userName + "   " + "Source: " + source 

            # Obtain projection and datum information FYI will display coordinate system of feature class not dataframe
            spatialRef = Describe(self.__featureName)
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
                    elm.text = twoBibliography
                    elm.elementPositionX = 10.7437
                    elm.elementPositionY = 8.1284
                elif elm.text == "classification1":
                    elm.text = self.__classificationBanner
                    elm.elementPositionX = 10.7739
                    elm.elementPositionY = 8.3779
                elif elm.text == "classification2":
                    elm.text = self.__classificationBanner
                    elm.elementPositionX = .2317
                    elm.elementPositionY = .1254
                elif elm.text == "subtitle":
                    elm.text = self.__systemName + " " + self.__systemClass + " " + "(" + str('{:,}'.format(self.__systemRange)) + " km" + ")"
                elif elm.text == "title":
                    elm.text = self.__classificationPortionMarking + " Threat to " + self.__targetCountryName

            # Set variable to the MXD
            self.__saveMapVariable = self.__mxdDirectory + "\\range_ring_template_working.mxd"

            self.__mxd.saveACopy(self.__saveMapVariable)

            # Cleanup previous mxd in instance
            del self.__mxd

            # Cleanup dataframe instances
            del dataFrameElement, self.__frame4KMZ
            
            # Delete layer variables
            del countrylyr, elementWorldlyr, elementWorldTopoLayer, ringlyr, symbologyRingLayer, symbologyElementWorldLayer

            # Delete legend variable
            del legend

            # Delete spatial reference variable
            del spatialRef

            # Set to true so sequential format don't take as long
            self.__justMapBoolean = True

        # Create GUI, name title of GUI and elevate window to topmost level
        root = Toplevel()
        root.title("Reverse Range Ring Generator")
        root.attributes('-topmost', 1)
        root.attributes('-topmost', 0) # put window on top of all others

        # Configure GUI frame, grid, column and root weights
        mainframe = ttk.Frame(root)
        mainframe.grid(column=0, row=0, sticky=(N, W, E, S))
        mainframe.columnconfigure(0, weight=1)
        mainframe.rowconfigure(0, weight=1)

        # Tie exiting out of program "red x" to quit command
        root.protocol("WM_DELETE_WINDOW", quitProgram)        

        # Create variables to pass user input to program
        cityName = StringVar()
        baseName = StringVar()
        cntryName = StringVar()
        systemName = StringVar()
        displayText = StringVar()
        valueSet = StringVar()
        fmtChoice = StringVar()

        otherEntry = BooleanVar()

        # Build dictionaries
        cityDictionary = buildCityDictionary()[1]# Create city dictionary (city trigraph + city name)
        countryDictionary = buildCountryDictionary() # Create country dictionary (country and respective trigraph)
        systemDictionary = getWeaponSystemDictionary() # Retrieve weapon system dictionary
        systemRangeDictionary = getWeaponRangeDictionary() # Retrieve weapon system range dictionary
        countryCentroidDictionary = getCountryCentroidDictionary() # Retrieve country centroid dictionary

        # Build lists
        cityList = buildCityDictionary()[0] # Create city list (city name)
        countryList = buildCountryList(countryDictionary) # Create country list (country name)
        militaryBaseList = buildMilitaryBaseList() # Create military base list (site name)

        # Create combobox for city name entry
        cityName_entry = ttk.Combobox(mainframe,width=60,state="normal",textvariable=cityName,values=cityList) 
        cityName_entry.grid(column=2,row=1,columnspan=2,sticky=W)
        cityName_entry.bind('<KeyRelease>',cityDynamicMatch, add="+")
        cityName_entry.bind('<KeyRelease>',valueHandler, add="+")
        cityName_entry.bind('<<ComboboxSelected>>',valueHandler, add="+")
        ttk.Label(mainframe,text="City Name (Target):").grid(column=1,row=1,sticky=W)

        # Create checkbutton for switchihng between city or military base target selection
        other_entry = Checkbutton(mainframe,variable=otherEntry, command=switchTargetSelection)
        other_entry.grid(column=2,row=2,sticky=W)
        ttk.Label(mainframe,text="Switch Target Set:").grid(column=1,row=2,sticky=W)

        # Create combobox for military base entry 
        militaryBaseList.sort()
        baseName_entry = ttk.Combobox(mainframe,width=60,state="disabled",textvariable=baseName,values=militaryBaseList) 
        baseName_entry.grid(column=2,row=3,columnspan=2,sticky=W)
        baseName_entry.bind('<KeyRelease>',baseDynamicMatch)
        ttk.Label(mainframe,text="Military Base Name (Target):").grid(column=1,row=3,sticky=W)        

        # Create combobox for country name entry
        countryName_entry = ttk.Combobox(mainframe,width=60,state="normal",textvariable=cntryName,values=countryList) 
        countryName_entry.grid(column=2,row=4,columnspan=2,sticky=W)
        countryName_entry.bind('<KeyRelease>',countryDynamicMatch,add="+")
        ttk.Label(mainframe,text="Country Name (Shooter):").grid(column=1,row=4,sticky=W)

        # Create combobox for threat system availability
        system_entry = ttk.Combobox(mainframe,width=40,state="disabled",textvariable=systemName) 
        system_entry.grid(column=2,row=8,columnspan=2,sticky=W)
        ttk.Label(mainframe,text="Threat System(s) Availability:").grid(column=1,row=8,sticky=W)

        # Create progress bar
        statusBar = ttk.Progressbar(mainframe,orient=HORIZONTAL,length=175,mode='determinate',variable=valueSet,maximum=30)
        statusBar.grid(column=1,row=11,sticky=W)

        # Create read only entry for displaying program progress updates
        statusMessage = ttk.Entry(mainframe,width=28,state="readonly",textvariable=displayText)
        statusMessage.grid(column=1,row=12,sticky=W)

        # Create button calculating 04_minimum distance between target city and shooter country
        calculateButton = ttk.Button(mainframe,text="Calculate",state="normal",command=calculate,width=9)
        calculateButton.grid(column=2, row=11, sticky=W)

        # Create button that will generate the map
        generateMapButton = ttk.Button(mainframe,text="Generate Map",state="disabled",command=generateMap,width=14)
        generateMapButton.grid(column=2,row=12,sticky=W)

        # Create button that will reset the program
        resetButton = ttk.Button(mainframe,text="Reset",state="normal",command=reset,width=5) 
        resetButton.grid(column=4,row=11,sticky=W)

        # Create button that will quit the program
        exitButton = ttk.Button(mainframe,text="Exit",command=quitProgram,width=5)
        exitButton.grid(column=4,row=12,sticky=W)

        # Add 5 units of padding between all elements in the frame
        for child in mainframe.winfo_children():
            child.grid_configure(padx=5, pady=5)

        # Set focus to country name entry combobox
        cityName_entry.focus() 

        # Bind escape and return keys to quit and generate map buttons 
        root.bind('<Escape>', quitProgram)
        root.bind('<Return>', calculate)

        # Make sure all mouse or keyboard events go to the root window
        root.grab_set()

        # Wait until GUI is exited 
        root.wait_window()

        # Return value of 1 that will activate main menu button selected
        return variable
