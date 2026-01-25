# Import modules from arcpy
from arcpy.da import SearchCursor
from arcpy import Delete_management
from arcpy import env
from arcpy import ListFeatureClasses
from arcpy import mapping
from arcpy import MapToKML_conversion
from collections import OrderedDict 

# Import modules from ctypes
from ctypes import wintypes
from ctypes import windll
from ctypes import create_unicode_buffer

# Import modules from os
from os import listdir
from os import remove
from os import path

# Import modules from Tkinter
from Tkinter import END
from Tkinter import INSERT

# Function to write tool instance running into a text file for the avoidance of duplicate programs running
def writeProgramInstanceOn(mainDirectory):
    
    # Open text file with carry over variables
    textDirectory = mainDirectory + "txt_files\\"
    fileVariable = textDirectory + "programRunning.txt" 
    textFile = open(fileVariable, "r")
    toolRunning = textFile.read()
    textFile.close()

    if toolRunning == "NO":
        textFile = open(fileVariable, "w")
        textFile.write("YES")
        textFile.close()
        result = 0
        pass
    else:
        result = 1
        pass

    return result

# Function to write tool instance running into a text file for the avoidance of duplicate programs running
def writeProgramInstanceOff(mainDirectory):
    
    # Open text file with carry over variables
    textDirectory = mainDirectory + "txt_files\\"
    fileVariable = textDirectory + "programRunning.txt" 
    textFile = open(fileVariable, "w")
    textFile.write("NO")
    textFile.close()

# Call routine to clean out files in world gdb created during program execution
def clearWorkspace(workSpace):
    # Restates the environment due to error in propogating env.workspace
    env.workspace = workSpace
    
    # Clean up geodatabase by deleting feature classes (fcs) other than the main world fcs        
    for fcs in ListFeatureClasses():
        if fcs == "world.shp":
            pass
        elif fcs == "meridian.shp":
            pass
        elif fcs == "cities.shp":
            pass
        elif fcs == "military_bases_US.shp":
            pass
        elif fcs == "Border.shp":
            pass        
        else:
            Delete_management(fcs)
            
# Call routine to clean out all files from scratch gdb
def clearScratchWorkspace(workSpace):
    env.workspace = workSpace
    for fcs in ListFeatureClasses():
        print fcs
        Delete_management(fcs)    

# Clean up working layer folder
def clearWorkingLayerDirectory(workingDirectory):
    dirs = listdir(workingDirectory)

    for layer in dirs:
        fileSource = workingDirectory + layer
        remove(fileSource)

# Obtain Weapon System Source
def getWeaponSystemSource():
    weaponSystemClassificationDictionary = {}
    weaponSystemClassificationDBF = SearchCursor("Weapon_List.dbf", ["sys_name", "Country", "Source"])
    
    for sourceElement in weaponSystemClassificationDBF:
        sourceID = sourceElement[1] + "_" + sourceElement[0]
        weaponSystemClassificationDictionary[sourceID] = sourceElement[2]

    return weaponSystemClassificationDictionary

# Obtain Weapon System Dictionary
def getWeaponSystemDictionary():
    weaponSystemDictionary = {}
    weaponSystemDBF = SearchCursor("Weapon_List.dbf", ["sys_name", "Country"])
    
    for weaponName in weaponSystemDBF:
        weaponSystemID = weaponName[1] + "_" + weaponName[0]
        weaponSystemDictionary[weaponSystemID] = weaponName[0]

    return weaponSystemDictionary

# Obtain Weapon Range Dictionary
def getWeaponRangeDictionary():
    weaponRangeDictionary = {}
    weaponRangeDBF = SearchCursor("Weapon_List.dbf", ["sys_name", "Max_Range", "Country"])

    for rangeValue in weaponRangeDBF:
        weaponRangeID = rangeValue[2] + "_" + rangeValue[0]
        weaponRangeDictionary[weaponRangeID] = rangeValue[1]
    
    return weaponRangeDictionary
    
# Obtain Weapon Banner Classification Dictionary
def bannerClassificationDictionary():
    classificationBannerDictionary = {}
    bannerDBF = SearchCursor("Weapon_List.dbf", ["sys_name", "B_MARKING", "Country"])

    for bannerMarking in bannerDBF:
        weaponClassificationID = bannerMarking[2] + "_" + bannerMarking[0]
        classificationBannerDictionary[weaponClassificationID] = bannerMarking[1]

    return classificationBannerDictionary

# Obtain Weapon Portion Classification Dictionary
def portionClassificationDictionary():
    classificationPortionDictionary = {}
    portionDBF = SearchCursor("Weapon_List.dbf", ["sys_name", "P_MARKING", "Country"])

    for portionMarking in portionDBF:
        weaponClassificationID = portionMarking[2] + "_" + portionMarking[0]
        classificationPortionDictionary[weaponClassificationID] = portionMarking[1]

    return classificationPortionDictionary

# Obtain Country Centroid Dictionary
def getCountryCentroidDictionary():
    countryCentroidDictionary = {}
    countryCentroidDBF = SearchCursor("world.shp", ["ISO3", "Centroid"])

    for centroid in countryCentroidDBF:
        countryCentroidDictionary[centroid[0]] = float(centroid[1])

    return countryCentroidDictionary    

# Obtain Country Maximum Range (for buffer) Dictionary
def getCountryMaxRangeDictionary():
    dictionary = {}
    rangeDBF = SearchCursor("world.shp", ["NAME", "Max_Range"])

    for field in rangeDBF:
        dictionary[field[0]] = int(field[1])

    return dictionary

# Obtain country trigraph dictionary to be used for FGIDictionary in classification tool
def getFGIDictionary():
    FGIDictionary = {}
    FGIDBF = SearchCursor("world.shp", ["ISO3", "NAME"])

    for trigraph in FGIDBF:
        if "dispute" in trigraph[1]: # if the territory is disputed exclude from list
            pass
        else:
            FGIDictionary[trigraph[0]] = trigraph[1]

    return FGIDictionary 

# Function to get short file path for opening que
# Source: http://stackoverflow.com/questions/23598289/how-to-get-windows-short-file-name-in-python
def getShortFilePath(exportPath):
    _GetShortPathNameW = windll.kernel32.GetShortPathNameW
    _GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    _GetShortPathNameW.restype = wintypes.DWORD 
    output_buf_size = 0
    
    while True:
        output_buf = create_unicode_buffer(output_buf_size)
        needed = _GetShortPathNameW(exportPath, output_buf, output_buf_size)
        if output_buf_size >= needed:
            return output_buf.value
            break
        else:
            output_buf_size = needed
            
# Generic autocomplete routine
def autocomplete(x,y,z):
    matchedName = ""
    # Change variable may be 0/1/-1 to cycle through possible dings
    dings = []
    dingIndex = 0
    changeVariable=0
    if changeVariable: # Delete selection in text entry
        x.delete(0, END)
    else: # Set position to end so selection starts where text entry ends
        x.position = len(z.get())

    # Collect matches to the string typed in entry
    Match = []        
    for element in y:
        if element.lower().startswith(x.get().lower()): # Insensitive Case Match
                Match.append(element)
                
    # Save a new match list
    if Match != dings:
        dingIndex = 0
        dings = Match
        
    # Decision loop only allowing a cycle if in a known ding list
    if Match == dings and dings:
        dingIndex = (dingIndex + changeVariable) % len(dings)
        
    # Perform autocompletion
    if dings:
        x.delete(0,END)
        x.insert(0,dings[dingIndex])
        x.select_range(x.position,END)

    x.config(values = Match)

    return dings

# Generic dynamic match routine
def dynamicMatch(event,x,y,z): #event object, widget_entry, list, widget_text_variable
    dings = []
    if event.keysym == "BackSpace":
        x.delete(x.index(INSERT), END)
        x.position = x.index(END)
    if event.keysym == "Left":
        if x.position < x.index(END): # delete the selection
                x.delete(x.position, END)
        else:
                x.position = x.position-1 # delete one character
                x.delete(x.position, END)
    if event.keysym == "Right":
        x.position = x.index(END) # go to end (no selection)
    if len(event.keysym) == 1:
        dings = autocomplete(x,y,z)
    else:
        pass

    return dings
        
# Decision loop to determine class of missile
def getSystemClass(self):
    matchBoolean = False
    typeList = ["SRBM","MRBM","IRBM","ICBM","SLBM","ALBM","LACM","GLCM","ALCM","SAM","ATBM"]
    v = "self._rangeRing__"
    systemName = eval(v+"systemName")
    distance = int(eval(v+"systemRange"))
    unit = eval(v+"distanceUnit")
    systemClass = "" 
    
    systemName = systemName.upper()[-4:]

    if unit == "mi":
        kmdistance = distance * 1.60934 # mi to km
    elif unit == "m":
        kmdistance = distance * 0.001 # m to km
    elif unit == "ft":
        kmdistance = distance * 0.0003048 # ft to km
    elif unit == "nm":
        kmdistance = distance * 1.852 # nm to km
    elif unit == "yd":
        kmdistance = distance * 0.0009144 # yd to km
    else:
        kmdistance = distance

    # Iterate through type list if any matches occur keep system class at "" since the type of system is already in the system name
    for itemType in typeList:
        if itemType in systemName:
            matchBoolean = True
        else:
            pass

    # If a match does not occur base the system type off of its range
    if matchBoolean == False:
        if kmdistance < 1000:
            systemClass = "SRBM"
        elif kmdistance >= 1000 and kmdistance < 3000:
            systemClass = "MRBM"
        elif kmdistance >= 3000 and kmdistance < 5500:
            systemClass = "IRBM"
        else:
            systemClass = "ICBM"
    else:
        pass

    return systemClass, kmdistance

# Create dictionary of country (with respective trigraph)
def buildCountryDictionary(): 
    countryDictionary = {}
    
    worldFeatureClass = SearchCursor("world.shp", ["NAME", "ISO3"])

    for row in worldFeatureClass:
        if "dispute" in row[0]: # if the territory is disputed exclude from list
            pass
        else:
            countryDictionary[row[0]] = row[1]

    return countryDictionary

# Build Military Base List
def buildMilitaryBaseList():
    militaryBaseList = []
    
    militaryBaseFeatureClass = SearchCursor("military_bases_US.shp", ["SITE_NAME", "COMPONENT"])

    for row in militaryBaseFeatureClass:
        recordName = row[0] + " (" + row[1] + ")"
        militaryBaseList.append(recordName)

    return militaryBaseList

# Build country list (country name)
def buildCountryList(countryDictionary):
    countryList = []

    for key, value in countryDictionary.iteritems():
            countryList.append(key)
            
    countryList.sort()
    
    return countryList

# Build city list # http://stackoverflow.com/questions/9835762/find-and-list-duplicates-in-python-list
def buildCityDictionary():
    citySearch = SearchCursor("cities.shp", ["CITY_NAME", "ADMIN_NAME", "ISO3"])
    cityList = []
    cityDictionary = {}
    for city in citySearch:
        if city[1] == "FIX_LATER":
            pass
        else:
            cityList.append(city[0])
            key = city[2] + "_" + city[0]
            cityDictionary[key] = city[1]

    setList = set(cityList)
    duplicateList = []

    for city in cityList:
        if city in setList:
            setList.remove(city)
        else:
            duplicateList.append(city)

    citySearch2 = SearchCursor("cities.shp", ["CITY_NAME", "ADMIN_NAME", "ISO3"])
    
    for city in citySearch2:
        if city[0] in duplicateList:
            cityList.remove(city[0])
            value = city[0] + " " + "(" + city[1] + ")"
            key = city[2] + "_" + city[0]
            cityDictionary[key] = value
            cityList.append(value)
        else:
            pass
        
    cityList.sort()
    
    return cityList, cityDictionary

# Build consolidated weapon system list
def consolidatedWpnsList(weaponSystemDictionary):
    consolidatedWeaponsList = []

    for key, value in weaponSystemDictionary.iteritems():
        if value not in consolidatedWeaponsList:
            consolidatedWeaponsList.append(value)
    consolidatedWeaponsList.sort()

    return consolidatedWeaponsList

# Create projection file to adapt map to where range ring will originate from
def adaptPRJ(trigraph, centroid, prjDirectory):
    country = trigraph
    centroid = centroid
    fileName = country + "_" + str(centroid)

    prjName = '"' + 'Eckert III (world) (Central Meridan ' + str(centroid) + ')' + '"' 
    coordinatesystem = '"GCS_WGS_1984"'
    datum = '"D_WGS_1984"'
    spheroid = '"WGS_1984",6378137.0,298.257223563'
    primeMeridian = '"Greenwich",0.0'
    unitOne = '"Degree",0.0174532925199433'
    projection = '"Eckert_III"'
    parameterOne = '"False_Easting",0.0'
    parameterTwo = '"False_Northing",0.0'
    parameterThree = '"Central_Meridian"'+ ',' + str(centroid) + "'"
    unitTwo = '"Meter",1.0'
    authority = '"ESRI", 54013'
    
    fileContents = 'PROJCS['+ prjName + ',GEOGCS[' + coordinatesystem + ',DATUM[' + datum + ',SPHEROID[' + spheroid + ']],PRIMEM[' + primeMeridian + '],UNIT[' + unitOne + ']],PROJECTION[' + projection + '],PARAMETER[' + parameterOne + '],PARAMETER[' + parameterTwo + '],PARAMETER[' + parameterThree + '],UNIT[' + unitTwo + ']' + ',AUTHORITY[' + authority + ']]' 

    prjVariable = prjDirectory + "\\World_Eckert_III.prj" 
    prjFile = open(prjVariable, "w")
    prjFile.write(fileContents)
    prjFile.close()

    return prjVariable  

# Decision loop depending on user format output choice
def exportMap(outputDirectory, mxd, saveMapVariable):

# Export JPEG (settings) to associated directory
# ExportToJPEG (map_document, out_jpeg, {data_frame}, {df_export_width}, {df_export_height}, {resolution}, {world_file}, {color_mode}, {jpeg_quality}, {progressive})

# Export to pdf (settings) to associated directory
# ExportToPDF (map_document, out_pdf, {data_frame}, {df_export_width}, {df_export_height}, {resolution}, {image_quality}, {colorspace}, {compress_vectors}, {image_compression}, {picture_symbol}, {convert_markers}, {embed_fonts}, {layers_attributes}, {georef_info}, {jpeg_compression_quality})

    # Create variable to carry forward the message number determined by user choice
    messageNumber = 0

    # Export format determined by user\
    # JPEG
    if outputDirectory[-3:] == "jpg":
        mapping.ExportToJPEG(mxd, outputDirectory,resolution=100)
    # PDF
    elif outputDirectory[-3:] == "pdf":
        while outputDirectory[-3:] == "pdf":
            try:
                mapping.ExportToPDF(mxd, outputDirectory,'PAGE_LAYOUT',640,180,100)
                break
            except:
                MessageBox = windll.user32.MessageBoxA
                errorMessage = str(outputDirectory.split("\\")[-1]) + " is presently open." + "\n" + "To continue please close file"
                messageNumber = MessageBox(0, errorMessage, 'PDF Creation Error', 1)
                if messageNumber == 2:
                    break
                else:
                    pass
    # KMZ
    elif outputDirectory[-3:] == "kmz":
        MapToKML_conversion(saveMapVariable, "customFrame", outputDirectory)
        
    return messageNumber

def getClassificationBanner(classificationList):
    classList = []

    classLine = ""

    FGIList = []

    otherRELList = []

    relCaveat = ""

    relCaveatList = []

    finalBannerClassification = ""

    # Obtain most restrictive classification marking
    for element in classificationList:
        if "TOP SECRET" in element:
            finalBannerClassification = "TOP SECRET"
            break
        elif "SECRET" in element:
           finalBannerClassification = "SECRET"
        elif "CONFIDENTIAL" in element:
            if "SECRET" in finalBannerClassification:
                pass
            else:
                finalBannerClassification = "CONFIDENTIAL"
        elif "UNCLASSIFIED" in element:
            if "SECRET" in finalBannerClassification or "CONFIDENTIAL" in finalBannerClassification:
                pass
            else:
                finalBannerClassification = "UNCLASSIFIED"
        else:
            pass

    # Get Most restrictive SCI marking
    for element in classificationList:
        tempList = element.split("//")
        if len(tempList) == 1:
            pass
        else:
            if "FGI" in tempList[1] or "REL" in tempList[1]:
                pass
            else:
                if "HCS-P" in tempList[1] or "SI" in tempList[1] or "TK" in tempList[1]:
                    classList.append(tempList[1])
                    
    if len(tempList) == 1:
            pass
    else:
        classLine = ''.join(classList).replace("/", "")
                    
        if "HCS-P" in classLine:
            if "HCS-P" in finalBannerClassification:
                pass
            else:
                finalBannerClassification += "//" + "HCS-P"        
        if "SI-G" in classLine:
            if "SI-G" in finalBannerClassification:
                pass
            else:
                if "HCS-P" in finalBannerClassification:
                    finalBannerClassification += "/SI-G"
                else:
                    finalBannerClassification += "//SI-G"                
        elif "SI" in classLine:
            if "HCS-P" in finalBannerClassification:
                if "SI-G" in finalBannerClassification:
                    pass
                if "SI" in finalBannerClassification:
                    pass
                else:
                    finalBannerClassification += "/SI"
            else:
                finalBannerClassification += "//SI"
        if "TK" in classLine:
            if "HCS-P" in finalBannerClassification or "SI-G" in finalBannerClassification or "SI" in finalBannerClassification:
                finalBannerClassification += "/TK"
            else:
                finalBannerClassification += "//TK"
        else:
            pass

    # Get FGI trigraph list out of classification list
    if len(tempList) == 1:
            pass
    else:
        for element in classificationList:
            tempList = element.split("//")
            for item in tempList:
                if "FGI" in item:
                    FGIElement = item.replace("FGI ", "")
                    if len(FGIElement) > 1:
                        FGISplit = FGIElement.split()
                        for trigraph in FGISplit:
                            FGIList.append(trigraph)
                    elif len(FGIElement) == 0:
                        print "Program Error: No FGI in FGI Loop"
                    else:
                        FGIList.append(FGIElement)

        FGIList = list(OrderedDict.fromkeys(FGIList))
        FGIList.sort()
        
        if len(FGIList) == 0:
            finalBannerClassification += "//"
        else:
            finalBannerClassification += "//FGI " + ' '.join(FGIList) + "//"
                
    # Obtain most restrictive releasibility caveats
    for element in classificationList:
        tempList = element.split("//")
        if len(tempList) == 1:
            pass
        else:
            for item in tempList:
                if "REL TO USA," in item:
                    relCaveat = item.replace("REL TO USA, ", "")
                    relCaveat = relCaveat.split(",")
                    if "FVEY" in relCaveat:
                        relCaveatList.append(["AUS","CAN","GBR", "NZL"])
                    elif "ACGU" in relCaveat:
                        relCaveatList.append(["AUS","CAN","GBR"])
                    else:
                        relCaveatList.append(relCaveat)
                if "FOUO" in item or "RSEN" in item or "ORCON" in item or "IMCON" in item or "NOFORN" in item:
                    otherRELList.append(item)
                else:
                    pass

    otherRELLine = ''.join(otherRELList).replace("/", "")
    if "UNCLASSIFIED" in finalBannerClassification:
        if "FOUO" in otherRELLine:
            finalBannerClassification += "FOUO"
            
    if "RSEN" in otherRELLine:
        finalBannerClassification += "RSEN"
        
    if "ORCON" in otherRELLine:
        if "RSEN" in finalBannerClassification:        
            finalBannerClassification += "/ORCON"
        else:
            finalBannerClassification += "ORCON"
            
    if "IMCON" in otherRELLine:
        if "RSEN" in finalBannerClassification or "ORCON" in finalBannerClassification: 
            finalBannerClassification += "/IMCON"
        else:
            finalBannerClassification += "IMCON"
            
    if "NOFORN" in otherRELLine:
        if "RSEN" in finalBannerClassification or "ORCON" in finalBannerClassification or "IMCON" in finalBannerClassification: 
            finalBannerClassification += "/NOFORN"
        else:
            finalBannerClassification += "NOFORN"
    else:        
        for caveat in relCaveatList:
            for element in caveat:
                element = element.replace(" ", "")
                filteredCaveat = set.intersection(set(relCaveatList[0]),set(caveat))
                    
            filteredCaveat = str(filteredCaveat)
            newString = str(filteredCaveat[5:-2])
            newString = newString.replace("'", "")
            newString = newString.replace(" ","")
            relCaveat = newString.split(",")
            relCaveat.sort()
            relCaveat = "REL TO USA, " + ', '.join(relCaveat)

            if len(newString) == 0:
                relCaveat = "NOFORN"
                
        finalBannerClassification += relCaveat

    return finalBannerClassification
