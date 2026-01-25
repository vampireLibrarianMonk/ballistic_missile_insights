# Import modules from arcpy
from arcpy import ApplySymbologyFromLayer_management
from arcpy import Buffer_analysis
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
from arcpy import SaveToLayerFile_management
from arcpy import SelectLayerByAttribute_management
from arcpy import SelectLayerByLocation_management

# Import modules form ctypes
from ctypes import windll
from ctypes import wintypes

# Import needed modules from imp
from imp import load_compiled

# Import modules from os
from os import path
from os import environ

# Import modules from subprocess
from subprocess import Popen

# Import modules from sys
from sys import argv

# Import all modules from Tkinter (import all potential modules for now)
from Tkinter import *

# Import modules from time for diagnostics
from time import strftime

# Import ttk module
import ttk

# Import ask ask save as filename modules from tk File Dialog
from tkFileDialog import asksaveasfilename

# Set variables for environment workspace and main directory (move to rangeRingModules)
fileName = path.basename(argv[0])
mainDirectory = argv[0]
mainDirectory = mainDirectory.replace(fileName, "")
mainDirectory += "range_ring\\"
dataPath = mainDirectory + "Data"
scratchPath = mainDirectory + "scratch"

# Import range ring modules
main_MuRR_Var1 = mainDirectory + "code\\rangeRingModules.pyc"
load_compiled('rangeRingModules', main_MuRR_Var1)
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
    def __init__(self, *args):
        # Set variable for current workspace of geodatabase
        self.__toolName = "minimum_Range"
        self.__systemName = self.__toolName
        
        self.__gdbWorkspace = dataPath # Set variable for current workspace of geodatabase

        # Class boolean values
        self.__justMapBoolean = False # Set boolean for clicking generate map button to speed up sequential processing of other formats for same map
        self.__continueProcessing = True # Set boolean variable for loops for breaking out of processes due to errors

        # Variables for first/second country name and country name without special characters or spaces
        self.__countryName = ""            
        self.__countryFileName = ""
        self.__secondCountryName = ""
        self.__secondCountryFileName= ""

        # Variable for current country's trigraph
        self.__currentCountryTrigraph = ""
        
        self.__variableName = "minrnge"
        self.__featureName = ""

        # Variable for tracking system range, range in km, system classification and distance unit
        self.__systemRange = 0
        self.__kmRange = 0
        self.__systemClass = ""
        self.__distanceUnit = "km"

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

        # Set Variables for world layer and saved map location
        self.__savedWorldLayer = ""
        self.__saveMapVariable = ""

        # Variable tracking user range ring resolution choice
        self.__resolutionChoice = ""

        # Variable holding path to projection file
        self.__prjFile = ""

        # Variable for tracking country swap value
        self.__swapCountryValue = ""
        
    def minimumRangeRingGenerator(self):

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
            combobox.config(state="disabled")
            combobox2.config(state="disabled")
            createMapButton.config(state="disabled")
            calculateButton.config(state="disabled")
            quitButton.config(state="disabled")
            resolutionChoice.config(state="disabled")
            resetButton.config(state="disabled")
          
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
            Delete_management("worldLayer")
            Delete_management("buffer_layer")
            Delete_management("meridian_layer")
            Delete_management("firstCountryLayer")
            Delete_management("secondCountryLayer")
            
            if self.__systemName and self.__systemRange:
                rangeRing = self.__systemName + "_" + str(self.__systemRange)
                Delete_management(rangeRing)
            else:
                pass
            if self.__systemName and self.__systemRange and self.__distanceUnit:
                layerName = "Minimum Range from " + self.__countryName + " (" + str('{:,}'.format(self.__systemRange)) + " " + self.__distanceUnit + ") to"
                Delete_management(layerName)
            else:
                pass
            if self.__featureName:
                Delete_management(self.__featureName.replace(".shp",""))
            else:
                pass

            # Step progressbar up 24 units
            valueSet.set(24)
            statusBar.update()

            # Restore buttons, comboboxes and status line to their default status and value
            displayText.set("Reseting GUI...")
            statusMessage.update()
           
            # Step progressbar up 30 units
            valueSet.set(30)
            statusBar.update()
            
            # Clear message display
            displayText.set("")
            statusMessage.update()

            # Reset progressbar
            valueSet.set(0)
            statusBar.update()
     
            # Exit program
            root.destroy()

        def reset():
            # Disable all widgets except progress bar and message display
            combobox.config(state="disabled")
            combobox2.config(state="disabled")
            createMapButton.config(state="disabled")
            calculateButton.config(state="disabled")
            quitButton.config(state="disabled")
            resolutionChoice.config(state="disabled")
            resetButton.config(state="disabled")
          
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
            Delete_management("worldLayer")
            Delete_management("buffer_layer")
            Delete_management("meridian_layer")
            Delete_management("firstCountryLayer")
            Delete_management("secondCountryLayer")
            if self.__systemName and self.__systemRange:
                rangeRing = self.__systemName + "_" + str(self.__systemRange)
                Delete_management(rangeRing)
            else:
                pass
            if self.__systemName and self.__systemRange and self.__distanceUnit:
                layerName = "Minimum Range from " + self.__countryName + " (" + str('{:,}'.format(self.__systemRange)) + " " + self.__distanceUnit + ") to"
                Delete_management(layerName)
            else:
                pass
            if self.__featureName:
                Delete_management(self.__featureName.replace(".shp",""))
            else:
                pass

            # Step progressbar up 24 units
            valueSet.set(24)
            statusBar.update()

            # Restore buttons, comboboxes and status line to their default status and value
            displayText.set("Reseting GUI...")
            statusMessage.update()

            # Clear variables
            # Reset boolean variable to fast track subsequent format choices
            self.__justMapBoolean = False
            
            # Set variable to mxd map instance
            self.__mapTemplate = self.__mxdDirectory + "\\range_ring_template_wo_inset.mxd" 
            self.__mxd = mapping.MapDocument(self.__mapTemplate)

            # Restore buttons, comboboxes and status line to default
            combobox.config(state="normal", values=firstCountryValues)
            combobox.set(value="")
            combobox.update()

            combobox2.config(state="disabled", values=secondCountryValues)
            combobox2.set(value="")
            combobox.update()

            resolutionVariable.set("")
            resolutionChoice.update()
            resolutionChoice.config(state="disabled")

            calculateButton.config(state="normal")
            calculateButton.update()

            createMapButton.config(state="disabled")
            createMapButton.update()

            quitButton.config(state="normal")
            quitButton.update()
            
            resetButton.config(state="normal")
            quitButton.update()
            
            # Step progressbar up 30 units
            valueSet.set(30)
            statusBar.update()
            
            # Clear message display
            displayText.set("")
            statusMessage.update()

            # Reset progressbar
            valueSet.set(0)
            statusBar.update()

        # Forward arguments to dynamic match routine in range ring modules and returns a the closest country name match in country list
        def countryDynamicMatch(event):
            dynamicMatch(event, combobox, firstCountryValues, cntryName)
            valueHandler(self)

        # Forward arguments to dynamic match routine in range ring modules and returns a the closest country name match in country list
        def secondCountryDynamicMatch(event):
            dynamicMatch(event, combobox2, secondCountryValues, secondCntryName)

        # Function to handle removing values from target country combobox per each selection of threat country by user avoiding duplicate entry of threat and target country
        def valueHandler(*args):
            secondCountryValues.append(self.__swapCountryValue)
            secondCountryValues.sort()

            current = combobox.get()
            
            if current in firstCountryValues:
                combobox2.config(state="normal")
                combobox2.set("")
                secondCountryValues.remove(current)
                if "" in secondCountryValues:
                    secondCountryValues.remove("")
                else:
                    pass
                combobox2.config(values=secondCountryValues)
                combobox2.update()
                self.__swapCountryValue = current
            else:
                if combobox.get() == "":
                    combobox2.set("")             
                else:
                    combobox2.set("Threat country invalid")
                    combobox2.config(state="disabled")      

        # Function determining 04_minimum range between two countries entered by user
        def calculate(*args):
            while self.__continueProcessing == True:
                try:
                    self.__countryName = combobox.get()
                    self.__countryFileName = filter(str.isalnum, self.__countryName)
                   
                    # Raise error if no country is selected
                    if self.__countryName == "":
                        errorMessage = "Please choose a base country"
                        raise ValueError
                    elif self.__countryName not in firstCountryValues:
                        errorMessage = "Base country entry invalid"
                        raise ValueError
                    else:
                        pass

                    try:
                        self.__currentCountryTrigraph = countryDictionary[self.__countryName]
                    except:
                        windll.user32.MessageBoxA(0, "Country Entry does not have a valid matching trigraph", "Program Error", 0)
                        break 
                                
                    self.__secondCountryName = combobox2.get()
                    self.__secondCountryFileName = filter(str.isalnum, self.__secondCountryName)

                    if self.__secondCountryName == "":
                        errorMessage = "Please choose a target country"
                        raise ValueError
                    elif self.__secondCountryName not in secondCountryValues:
                        errorMessage = "Target country entry invalid"
                        raise ValueError
                    else:
                        pass
                except:
                    windll.user32.MessageBoxA(0, errorMessage, "Country Entry Error", 0)
                    break

                # Diagnostic time stamp print
                print strftime("%Y-%m-%d %H:%M:%S")

                # Start statusbar at 0
                valueSet.set(0)
                statusBar.update()

                # Disable threat combobox
                combobox.config(state="disabled")
                combobox.update()

                # Disable target combobox
                combobox2.config(state="disabled")
                combobox2.update() 
                
                # Disable calculate button
                calculateButton.config(state="disabled")
                calculateButton.update()

                # Disable exit button
                quitButton.config(state="disabled")
                quitButton.update()

                # Disable reset button
                resetButton.config(state="disabled")
                resetButton.update()

                # Update text display for processing input
                displayText.set("Processing Input")
                statusMessage.update()

                # Make a layer from the world feature class
                MakeFeatureLayer_management("world.shp", "worldLayer")
                worldLayer = "worldLayer" + ".lyr"
                self.__savedWorldLayer = self.__workingLayerDirectory + worldLayer
                SaveToLayerFile_management("worldLayer", self.__savedWorldLayer, "RELATIVE")

                # Create query string of 'NAME = countryName' for base and target country
                nameField = "NAME"
                queryString = '"' + nameField + '" = ' + "'" + self.__countryName + "'"
                queryString2 = '"' + nameField + '" = ' + "'" + self.__secondCountryName + "'"

                # Select within world feature class the target country   
                SelectLayerByAttribute_management("worldLayer", "NEW_SELECTION", queryString)

                # Write the selected features to a new featureclass
                firstCountryFCS = str(self.__countryFileName) + ".shp"
                CopyFeatures_management("worldLayer", firstCountryFCS)

                # Select within world feature class the target country   
                SelectLayerByAttribute_management("worldLayer", "NEW_SELECTION", queryString2)

                # Write the selected features to a new featureclass
                secondCountryFCS = str(self.__secondCountryFileName) + ".shp"
                CopyFeatures_management("worldLayer", secondCountryFCS)

                # Increment status bar by 15 units
                statusBar.step(15)
                statusBar.update()

                # Update text display for calculating 04_minimum distance
                displayText.set("Calculating Minimum Distance")
                statusMessage.update()

                # Perform calculation of 04_minimum distance between threat and target country
                Near_analysis(firstCountryFCS, secondCountryFCS, "", "","" , "GEODESIC")

                # Create list to hold country choices
                fcs = ListFeatureClasses(firstCountryFCS)
                curObj = SearchCursor(firstCountryFCS, ["NEAR_DIST"])

                for row in curObj:
                    self.__systemRange = row[0]

                self.__systemRange = int(self.__systemRange/1000)

                # Determine class of missile
                self.__systemClass, self.__kmRange = getSystemClass(self)

                displayText.set("Minimum Range = " + str('{:,}'.format(self.__systemRange)) + " km") 
                statusMessage.update()

                # Increment status bar by 15 units
                statusBar.step(15)
                statusBar.update()
                
                # Disable generate button
                calculateButton.config(state="disabled")
                calculateButton.update()

                # Disable Country Selections until reset button is pressed
                combobox.config(state="disabled")
                combobox.update()

                combobox2.config(state="disabled")
                combobox2.update()

                # If range exceeds capability of program display error (error 99999 a buffer currently cannot cover both poles)
                maximumRange = countryMaxRangeDictionary[self.__countryName]/1000
                try:
                    if self.__kmRange > maximumRange:
                        if self.__distanceUnit == "km": 
                                errorMessage = "System range cannot exceed " + str('{:,}'.format(maximumRange)) + " " + self.__distanceUnit +  "." + "\nFor the country of " + self.__countryName + "."
                                raise ValueError
                    else:
                        # Enable create map button
                        createMapButton.config(state="normal")
                        createMapButton.update()
                        
                        # Enable range ring resolution combobox
                        resolutionChoice.config(state="readonly")
                        resolutionChoice.update()

                        # Enable reset button
                        resetButton.config(state="normal")
                        resetButton.update()

                        # Enable exit button
                        quitButton.config(state="normal")
                        quitButton.update()
                        
                        # Diagnostic time stamp print
                        print strftime("%Y-%m-%d %H:%M:%S")
                except:
                    errorMessage += "\nPlease use Custom POI Range Ring Tool."
                    windll.user32.MessageBoxA(0, errorMessage, "Program Limitation Error", 0)
                    break         

                break
            
        def bufferPolygon():
            # Create variables for buffer tool
            self.__featureName = self.__variableName + "_" + str(self.__systemRange) + ".shp"
            draftBufferName = "draft_" + self.__featureName
            firstCountryFCS = str(self.__countryFileName) + ".shp"

            # Simplify country boundary if user selects "Low" else create range ring
            if self.__resolutionChoice == "Low":
                from arcpy import SimplifyPolygon_cartography
                simplifiedPolygon = str(self.__countryFileName) + "_simplified.shp"
                SimplifyPolygon_cartography(firstCountryFCS, simplifiedPolygon, "POINT_REMOVE", "9 Kilometers")
                Buffer_analysis(simplifiedPolygon, draftBufferName, "NEAR_DIST", "", "", "", "")
            else:
                Buffer_analysis(firstCountryFCS, draftBufferName, "NEAR_DIST", "", "", "", "")

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
                AggregatePolygons_cartography("prj_buffer.shp", self.__featureName, "1 Centimeter")
            else:
                # Project newly created buffer feature class
                Project_management(draftBufferName, self.__featureName, self.__prjFile)
 
        def checkFormat():
            while self.__continueProcessing == True:
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

                # Disable create map button 
                createMapButton.config(state="disabled")
                createMapButton.update()

                # Disable range ring resolution combobox
                resolutionChoice.config(state="disabled")
                resolutionChoice.update()     
                
                # Disable calculate button
                calculateButton.config(state="disabled")
                calculateButton.update()

                # Disable exit button
                quitButton.config(state="disabled")
                quitButton.update()

                # Disable reset button
                resetButton.config(state="disabled")
                resetButton.update()
                
                if self.__justMapBoolean == True:
                    valueSet.set(0)
                    statusBar.update()
                    displayText.set("Creating Map")
                    statusMessage.update()

                # Process Map and break from loop
                processMap()  

                # Enable create map button 
                createMapButton.config(state="normal")
                createMapButton.update()

                # Enable exit button
                quitButton.config(state="normal")
                quitButton.update()

                # Enable reset button
                resetButton.config(state="normal")
                resetButton.update()
                
                # Diagnostic time stamp print
                print strftime("%Y-%m-%d %H:%M:%S")             
                break
            
        def processMap():
            if self.__justMapBoolean == False:
                valueSet.set(0)
                statusBar.update()

                displayText.set("Creating Range Ring")
                statusMessage.update()
                
                # Execute buffer tool
                bufferPolygon()

                displayText.set("Range Ring Created")
                statusMessage.update()            

                # Increment progressbar by 15 units
                valueSet.set(15)
                statusBar.update()

                # Change text display to creating map
                displayText.set("Creating Map")
                statusMessage.update()

                # Set variable for range ring layer
                draftBufferName = "draft_" + self.__featureName

                # Update unprojected range ring to system name, system range and distance unit
                with UpdateCursor(draftBufferName, ['Name']) as cursor:
                # For each row, match system range up with system information (Missile 1, Missile 2, Missile 3...) 
                    for row in cursor:
                        row[0] = self.__secondCountryName

                        # Update the cursor with updated system information
                        cursor.updateRow(row)      

                # Make and save unprojected range ring layer
                layerName = "Minimum Range from " + self.__countryName + " (" + str('{:,}'.format(self.__systemRange)) + " " + self.__distanceUnit + ") to"
                MakeFeatureLayer_management(draftBufferName, layerName)
                if self.__systemClass == "":
                    rangeRingLayer_unprj = self.__countryFileName + "_" + self.__toolName + "_" + str(self.__systemRange) + "unprj" + ".lyr" 
                else:
                    rangeRingLayer_unprj = self.__countryFileName + "_" + self.__toolName + "_" + self.__systemClass + "_" + str(self.__systemRange) + "unprj" + ".lyr" 
                savedRangeRingLayer_unprj = self.__workingLayerDirectory + rangeRingLayer_unprj
                SaveToLayerFile_management(layerName, savedRangeRingLayer_unprj, "RELATIVE")
                
                # Make and save range ring layer
                MakeFeatureLayer_management(self.__featureName, self.__featureName.replace(".shp",""))
                rangeRingLayer = self.__featureName + ".lyr"
                rangeRingLayer = self.__countryFileName + "_" + self.__variableName + "_" + str(self.__systemRange) + ".lyr" 
                savedRangeRingLayer = self.__layerDirectory + "\\workinglayers\\" + rangeRingLayer
                SaveToLayerFile_management(self.__featureName.replace(".shp",""), savedRangeRingLayer, "RELATIVE")

                # Set layer variables
                elementWorldlyr = mapping.Layer(self.__savedWorldLayer)
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

                # Set data frame object for element and inset data frames
                dataFrameElement = mapping.ListDataFrames(self.__mxd, "element")[0]

                # Set data frame object for custom data frame
                self.__frame4KMZ = mapping.ListDataFrames(self.__mxd)[1]

                # Add range ring and world feature classes as layers to element dataframe
                legend.autoAdd = True
                ApplySymbologyFromLayer_management(ringlyr, symbologyRingLayer) # apply symbology
                mapping.AddLayer(dataFrameElement, ringlyr, "TOP")
                legend.autoAdd = False
                ApplySymbologyFromLayer_management(elementWorldlyr, symbologyElementWorldLayer) # apply symbology
                mapping.AddLayer(dataFrameElement, elementWorldlyr)
                mapping.AddLayer(dataFrameElement, elementWorldTopoLayer, "BOTTOM")

                # Add points of interest and range ring to custom frame dataframe
                ApplySymbologyFromLayer_management(ringlyr_unprj, symbologyRinglyr)
                mapping.AddLayer(self.__frame4KMZ, ringlyr_unprj, "TOP") 

                # Set extent of element data frame
                dataFrameElement.extent = ringlyr.getSelectedExtent()

                # Update legend in element data frame
                styleItem = mapping.ListStyleItems("ESRI.style", "Legend Items", "Horizontal Single Symbol Label Only")[0]
                lyr = mapping.ListLayers(self.__mxd, ringlyr, dataFrameElement)[0]
                legend = mapping.ListLayoutElements(self.__mxd, "LEGEND_ELEMENT")[0]
                lyr.name = str('{:,}'.format(self.__systemRange)) + " " + self.__distanceUnit
                legend.updateItem(lyr, styleItem)

                # Set classification banner marking 
                classificationBanner = "UNCLASSIFIED"

                # Set portion marking
                classificationPortionMarkingList = "(U)"

                # Obtain current username for Classified By:
                userName = environ.get("USERNAME")

                # Set source
                sourceWebSite = "DoS, Simplified World Polygons, March 2013"

                # Set variables for element configuration of map
                twoBibliography = "Created By: " + userName + " " + "Source: " + sourceWebSite

                # Obtain projection and datum information of newly created buffer
                spatialRef = Describe(self.__featureName)
                coordinateSystem = str(spatialRef.SpatialReference.Name)
                coordinateSystem = coordinateSystem.replace("_", " ")
                datum = str(spatialRef.SpatialReference.DatumName)
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
                        elm.text = classificationBanner
                        elm.elementPositionX = 10.7739
                        elm.elementPositionY = 8.3779
                    elif elm.text == "classification2":
                        elm.text = classificationBanner
                        elm.elementPositionX = .2317
                        elm.elementPositionY = .1254
                    elif elm.text == "subtitle":
                        elm.text = self.__countryName + " to " + self.__secondCountryName
                    elif elm.text == "title":
                        elm.text = classificationPortionMarkingList + " " + "Minimum Range Map" 

                # Modify legend element
                legend = mapping.ListLayoutElements(self.__mxd, "LEGEND_ELEMENT", "Legend")[0]

                # Save copy of map
                self.__saveMapVariable = self.__mxdDirectory + "\\range_ring_template_working.mxd"
                self.__mxd.saveACopy(self.__saveMapVariable)

                # Cleanup previous mxd in instance
                del self.__mxd

                # Cleanup dataframe instances
                del dataFrameElement, self.__frame4KMZ

                # Delete layer variables
                elementWorldlyr, elementWorldTopoLayer, ringlyr, ringlyr_unprj, symbologyRinglyr, symbologyElementWorldLayer

                # Set variable to fastrack subsequent format choices
                self.__justMapBoolean = True
            else:
                pass

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
            else:
                Popen('start ' + self.__outputFilePath, shell=True)
                displayText.set("Range Ring Map Created")
                statusMessage.update()                
                valueSet.set(30)
                statusBar.update()

        # Create GUI, name title of GUI and elevate window to topmost level
        root = Toplevel()
        root.title("Minimum Range Ring Generator")
        root.attributes('-topmost', 1)
        root.attributes('-topmost', 0)

        # Configure GUI frame, grid, column and root weights
        mainframe = ttk.Frame(root)
        mainframe.grid(column=0, row=0, sticky=(N, W, E, S))
        mainframe.columnconfigure(0, weight=1)
        mainframe.rowconfigure(0, weight=1)

        # Tie exiting out of program "red x" to quit command
        root.protocol("WM_DELETE_WINDOW", quitProgram)

        # Create variables to pass user input to program
        cntryName = StringVar()
        secondCntryName = StringVar()
        displayText = StringVar()
        resolutionVariable = StringVar()
        valueSet = StringVar()
        checkedValue = BooleanVar()

        # Dictionary list
        countryDictionary = buildCountryDictionary() # Create country dictionary (country and respective trigraph)
        countryCentroidDictionary = getCountryCentroidDictionary() # Retrieve country centroid dictionary
        countryMaxRangeDictionary = getCountryMaxRangeDictionary() # Retrieve country's maximum range for buffer (Fix for Error: Buffer cannot cover both poles)

        # Build first and second country lists
        firstCountryValues = []
        secondCountryValues = []
        resolutionList = ["Low", "Normal"] # Create list for user choices for range ring resolution 

        for key, value in countryDictionary.iteritems():
            firstCountryValues.append(key)
            secondCountryValues.append(key)

        firstCountryValues.sort()
        secondCountryValues.sort()

        # Create labels for comboboxes
        ttk.Label(mainframe, text="Threat Country:").grid(column=1, row=1, sticky=W)
        ttk.Label(mainframe, text="Target Country:").grid(column=1, row=3, sticky=W)

        # Create combobox for threat country
        combobox = ttk.Combobox(mainframe, width=39, state = "normal", textvariable=cntryName, values=firstCountryValues)
        combobox.grid(column=1, row=2, sticky=W)
        combobox.bind('<KeyRelease>', countryDynamicMatch, add="+")
        combobox.bind('<<ComboboxSelected>>', valueHandler, add="+")

        # Create combobox for target country
        combobox2 = ttk.Combobox(mainframe, width=39, state = "disabled", textvariable=secondCntryName, values=secondCountryValues)
        combobox2.grid(column=1, row=4, sticky=W)
        combobox2.bind('<KeyRelease>', secondCountryDynamicMatch, add="+")

        # Create combbox for range ring resolution
        resolutionChoice = ttk.Combobox(mainframe,state="disabled",width=5,textvariable=resolutionVariable,values=resolutionList)
        resolutionChoice.grid(column=1,row=5,sticky=E)
        resolutionChoiceLabel = Label(mainframe, text="Range Ring Resolution:")
        resolutionChoiceLabel.grid(column=1,row=5,sticky=W) 

        # Create progress bar
        statusBar = ttk.Progressbar(mainframe, orient=HORIZONTAL, length=175, mode='determinate', variable=valueSet, maximum=30)
        statusBar.grid(column=1, row=8, sticky=W)

        # Create read only entry for displaying program progress updates
        statusMessage = ttk.Entry(mainframe, width=28, state="readonly", textvariable=displayText)
        statusMessage.grid(column=1, row=7, sticky=W)

        # Create button for executing create map
        createMapButton = Button(mainframe, text="Create Map", command=checkFormat, state="disabled", width=10)
        createMapButton.grid(column=1, row=8, sticky=E)

        # Create button that executes the 04_minimum distance calculation
        calculateButton = Button(mainframe, text="Calculate", command=calculate, width=10)
        calculateButton.grid(column=1, row=7, sticky=E)

        # Create button for exiting program
        quitButton = Button(mainframe, text="Exit", command=quitProgram, width=10)
        quitButton.grid(column=2, row=8, sticky=W)

        # Create button resetting program
        resetButton = Button(mainframe, text="Reset", state="normal", command=reset, width=10)
        resetButton.grid(column=2, row=7, sticky=W)

        # Add 5 units of space in between established widgets
        for child in mainframe.winfo_children():
            child.grid_configure(padx=5, pady=5)

        # Set focus to threat country combobox
        combobox.focus()

        # Bind escape and return keys to quit button
        root.bind('<Escape>', quitProgram)

        # Make sure all mouse or keyboard events go to the root window
        root.grab_set()

        # Wait until GUI is exited 
        root.wait_window()

        # Return value of 1 that will activate main menu button selected
        return variable
