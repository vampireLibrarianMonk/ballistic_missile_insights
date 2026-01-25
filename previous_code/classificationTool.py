# Import modules from arcpy
from arcpy import env

# Import modules from ctypes
from ctypes import windll

# Import modules from imp
from imp import load_compiled

# Import modules from os
from os import path

# Import modules from sys
from sys import argv

# Import modules from Tkinter
from Tkinter import *

# Import ttk modules
import ttk

# Set variables for environment workspace and main directory (move to rangeRingModules)
fileName =  path.basename(argv[0])
mainDirectory = argv[0]
mainDirectory = mainDirectory.replace(fileName, "")
dataPath = mainDirectory + "range_ring\\Data"
scratchPath = mainDirectory + "range_ring\\scratch"

CC_Tool_Var = mainDirectory + "range_ring\\code\\rangeRingModules.pyc"
load_compiled('rangeRingModules', CC_Tool_Var)
from rangeRingModules import *

# Set environment workspace and main directory (fixes problem with spaces in directories)
dataPath = getShortFilePath(dataPath)
env.workspace = dataPath
env.scratchWorkspace = getShortFilePath(scratchPath)
mainDirectory = getShortFilePath(mainDirectory)

class classTool:

    def __init__(self, *args):
        self.__classificationList = []
        self.__FGIDictionary = getFGIDictionary() # Create FGI dictionary
        self.__continueProcessing = True
        
    def classificationTool(self):

        def closeClassificationWindow():     
            if len(self.__classificationList) == 4:
                top.grab_release()
                top.destroy()
            elif len(self.__classificationList) == 3:
                if exerciseVar.get() == True:
                    top.grab_release()
                    top.destroy()
                elif self.__classificationList[0][1] == "U" and self.__classificationList[1][0] == "U":
                    top.grab_release()
                    top.destroy()
                else:
                    pass
                
        def cancelWindow():
            self.__classificationList = []
            top.grab_release()
            top.destroy()   
                
        def enableDerivedDeclassEntry():
            if TSVar.get() == True or SVar.get() == True or CVar.get() == True or UVar.get() == True:
                derivedFromEntry.config(state="normal")
                declassOnEntry.config(state="normal")
            else:
                derivedFromEntry.config(state="disabled")
                declassOnEntry.config(state="disabled")         

        def TSwitch():
            if TSVar.get() == True:
                SButton.deselect()
                SButton.config(state="disabled")

                CButton.deselect()
                CButton.config(state="disabled")

                UButton.deselect()
                UButton.config(state="disabled")

                FGIName_entry.config(state = "normal")
                
                FOUOButton.deselect()
                FOUOButton.config(state = "disabled")
                
                SCICaveatSwitch()                
            elif TSVar.get() == False:
                if portionVar.get() == True or bannerVar.get() == True:
                    resetMenu()
                    TSButton.config(state="normal")
                    SButton.config(state="normal")
                    CButton.config(state="normal")
                    UButton.config(state="normal")
                else:
                    resetMenu()
            else:
                pass
                
        def SSwitch():            
            if SVar.get() == True:
                TSButton.deselect()
                TSButton.config(state="disabled")

                CButton.deselect()
                CButton.config(state="disabled")

                UButton.deselect()
                UButton.config(state="disabled")

                FGIName_entry.config(state = "normal")
                
                FOUOButton.deselect()
                FOUOButton.config(state = "disabled")
                
                SCICaveatSwitch()
            elif SVar.get() == False:
                if portionVar.get() == True or bannerVar.get() == True:
                    resetMenu()
                    TSButton.config(state="normal")
                    SButton.config(state="normal")
                    CButton.config(state="normal")
                    UButton.config(state="normal")
                else:
                    resetMenu()                
            else:
                pass
                
        def CSwitch():
            if CVar.get() == True:
                TSButton.deselect()
                TSButton.config(state="disabled")

                SButton.deselect()
                SButton.config(state="disabled")

                UButton.deselect()
                UButton.config(state="disabled")
                
                FOUOButton.deselect()
                FOUOButton.config(state = "disabled")
                
                FGIName_entry.config(state="normal")
                SCICaveatSwitch()
            elif CVar.get() == False:
                if portionVar.get() == True or bannerVar.get() == True:
                    resetMenu()
                    TSButton.config(state="normal")
                    SButton.config(state="normal")
                    CButton.config(state="normal")
                    UButton.config(state="normal")
                else:
                    resetMenu()
            else:
                pass

        def USwitch():
            if UVar.get() == True:
                TSButton.deselect()
                TSButton.config(state="disabled")

                SButton.deselect()
                SButton.config(state="disabled")

                CButton.deselect()
                CButton.config(state="disabled")
                FGIName_entry.config(state="normal")
                                
                SCICaveatSwitch()
            elif UVar.get() == False:
                if portionVar.get() == True or bannerVar.get() == True:
                    resetMenu()
                    TSButton.config(state="normal")
                    SButton.config(state="normal")
                    CButton.config(state="normal")
                    UButton.config(state="normal")
                else:
                    resetMenu()
            else:
                pass

        def SCICaveatSwitch():
            if UVar.get() == True:
                
                # Disable HCS check button
                HCSButton.deselect()
                HCSButton.config(state="disabled")
                
                # Disable SI check button                    
                SIButton.deselect()
                SIButton.config(state="disabled")
                
                # Disable SI-G check button
                SIGButton.config(state="disabled")
                
                # Disable TK check button
                TKButton.deselect()
                TKButton.config(state="disabled")
                
                # Enable FOUO check button
                FOUOButton.config(state="normal")                        
                
                # Disable RSEN button
                RSENButton.deselect()
                RSENButton.config(state="disabled")
              
                # Disable ORCON check button
                ORCONButton.deselect()
                ORCONButton.config(state = "disabled")

                # Disable ORCON-USGOV check button
                ORCONButton.deselect()
                ORCONUSGOVButton.config(state="disabled")

                # Disable IMCON check button
                IMCONButton.deselect()
                IMCONButton.config(state = "disabled")

                # Enable RELTO check button
                RELTOButton.config(state = "normal")

                # Enable RELIDO check button
                RELIDOButton.config(state = "normal")

                # Enable NOFORN check button
                NOFORNButton.config(state = "normal")
                    
                # Enable FISA check button
                FISAButton.config(state="normal")
                
            if UVar.get() == False:
                # Enable HCS check button only if TOP SECRET or SECRET is selected
                if TSVar.get() == True or SVar.get() == True:
                    HCSButton.config(state="normal")
                else:
                    HCSButton.config(state="disabled")
                
                # Enable SI check button
                if SIGVar.get() == True:
                    pass
                else:
                    SIButton.config(state="normal")

                # Enable SI-G check button
                if SIVar.get() == True:
                    pass
                else:
                    if TSVar.get() == True:
                        SIGButton.config(state="normal")
                    else:
                        pass
                
                # Enable TK check button
                TKButton.config(state="normal")
                
                # Enable RSEN check button
                RSENButton.config(state="normal")                 

                # Enable FOUO check button
                FOUOButton.config(state="normal")

                # Enable ORCON check button
                ORCONButton.config(state="normal")

                # Enable ORCON-USGOV check button
                ORCONUSGOVButton.config(state="normal")                

                # Enable IMCON check button only if TOP SECRET or SECRET button is checked
                if CVar.get() == True:
                    pass
                else:
                    IMCONButton.config(state="normal")                    
            
                # Enable RELTO check button
                RELTOButton.config(state = "normal")
                
                # Enable RELDIO check button
                RELIDOButton.config(state="normal")

                # Enable NOFORN check button
                NOFORNButton.config(state="normal")
                    
                # Enable FISA check button
                FISAButton.config(state="normal")

            if TSVar.get() == True or SVar.get() == True or CVar.get() == True:
                FOUOButton.deselect()
                FOUOButton.config(state="disabled")
            elif UVar.get() == True:
                FOUOButton.config(state="normal")

        def HCSSwitch():
            if HCSVar.get() == True:
                RELTOButton.deselect()
                RELTOButton.config(state="disabled")
                RELIDOButton.deselect()
                RELIDOButton.config(state="disabled")
                NOFORNButton.select()
                NOFORNButton.config(state="disabled")
            elif HCSVar.get() == False:
                RELTOButton.config(state="normal")
                RELIDOButton.config(state="normal")
                NOFORNButton.deselect()
                NOFORNButton.config(state="normal")
            else:
                pass
             
        def SISwitch():
            if SIVar.get() == True:
                SIGButton.deselect()
                SIGButton.config(state="disabled")
            elif SIVar.get() == False:
                SIGButton.config(state="normal")
            else:
                pass
            
            if SIGVar.get() == True:
                SIButton.deselect()
                SIButton.config(state="disabled")
                ORCONButton.select()
                ORCONButton.config(state="disabled")
                ORCONUSGOVButton.deselect()
                ORCONUSGOVButton.config(state="disabled")                    
            elif SIGVar.get() == False:
                SIButton.config(state="normal")
                ORCONButton.deselect()
                ORCONButton.config(state="normal")
                ORCONUSGOVButton.config(state="normal")
            else:
                pass

        def getFGISelection(event):
            currentFGISelection = FGIName_entry.current()
            if currentFGISelection != -1:
                FGIAddButton.config(state="normal")
                FGIResetButton.config(state="normal")
            else:
                FGIAddButton.config(state="disabled")
                FGISubtractButton.config(state="disabled")
                FGIResetButton.config(state="disabled")
                
        def dynamicFGIMatch(event):          
            dings = dynamicMatch(event,FGIName_entry,FGIList,FGIName)

            if dings:                    
                FGIAddButton.config(state="normal")
            else:
                pass

        # Return sorted FGI country name selection
        def storeFGISelection():
            try: 
                currentFGICountry = FGIName_entry.get()
                if currentFGICountry == "":
                    errorMessage = "Please select or enter FGI country."
                    raise ValueError
                elif currentFGICountry not in FGIList:
                    errorMessage = "Unidentified country entered, please check spelling."
                    raise ValueError    
                else:
                    FGINameStorage_entry.config(state="readonly")
                    FGIStorageList.append(currentFGICountry)
                    FGIList.remove(currentFGICountry)
                    
                    FGIName.set("")                
                    FGIName_entry.config(values=FGIList)

                    FGIStorageName.set(currentFGICountry)
                    FGIStorageList.sort()
                    FGINameStorage_entry.config(values=FGIStorageList)
                    FGISubtractButton.config(state="normal")
            except: 
                windll.user32.MessageBoxA(0, errorMessage, "FGI Entry Error", 0)

        def subtractFGISelection():
            try:
                if FGINameStorage_entry.instate(['focus']):
                    currentFGIStorageCountry = FGINameStorage_entry.current()
                    FGIList.append(FGIStorageList[currentFGIStorageCountry])
                    FGIList.sort()
                    FGIName_entry.config(values=FGIList)
                    FGIStorageList.remove(FGIStorageList[currentFGIStorageCountry])
                    FGINameStorage_entry.config(values=FGIStorageList)
                    if FGIStorageList:
                        FGIStorageName.set(FGIStorageList[0])
                    else:
                        FGIStorageName.set("")
                else:
                    raise ValueError
            except:                    
                errorMessage = "Please select stored FGI country to remove" 
                windll.user32.MessageBoxA(0, errorMessage, "FGI Entry Error", 0)

        def resetFGISelection():
            FGIName.set("")
            FGIStorageName.set("")
            
            clearedFGIList = []
            
            clearedFGIStorageList = []

            for key, value in self.__FGIDictionary.iteritems():
                clearedFGIList.append(value)

            FGIList.sort()
            FGIName_entry.config(values=clearedFGIList)
            FGINameStorage_entry.config(values=clearedFGIStorageList) 
            FGINameStorage_entry.config(state="disabled")
            FGIAddButton.config(state="disabled")
            FGISubtractButton.config(state="disabled")

            FGIName_entry.focus()

        def FOUOSwitch():
            if FOUOVar.get() == True:
                RELTOButton.deselect()
                RELTOButton.config(state = "disabled")
                RELIDOButton.deselect()
                RELIDOButton.config(state="disabled")
                NOFORNButton.deselect()
                NOFORNButton.config(state="disabled")
                FISAButton.deselect()
                FISAButton.config(state="disabled")
            elif FOUOVar.get() == False:
                RELTOButton.config(state = "normal")
                RELIDOButton.config(state="normal")
                NOFORNButton.config(state="normal")
                FISAButton.config(state="normal")
            else:
                pass

        def ORCONSwitch():
            if ORCONVar.get() == True:
                ORCONUSGOVButton.deselect()
                ORCONUSGOVButton.config(state="disabled")
                RELIDOButton.deselect()
                RELIDOButton.config(state="disabled")
            elif ORCONVar.get() == False:
                ORCONUSGOVButton.config(state="normal")
                if HCSVar.get() == True:
                    pass
                else:
                    RELIDOButton.config(state="normal")
            else:
                pass

        def ORCONUSGOVSwitch():
            if ORCONUSGOVVar.get() == True:
                ORCONButton.deselect()
                ORCONButton.config(state="disabled")
                RELIDOButton.deselect()
                RELIDOButton.config(state="disabled")
            elif ORCONUSGOVVar.get() == False:
                ORCONButton.config(state="normal")
                if HCSVar.get() == True:
                    pass
                else:
                    RELIDOButton.config(state="normal")
            else:
                pass    

        def RELTOSwitch():                    
            if RELTOVar.get() == True:
                FOUOButton.deselect()
                FOUOButton.config(state = "disabled")
                RELTO_entry.config(state="normal")                    
                NOFORNButton.deselect()
                NOFORNButton.config(state = "disabled")
            elif RELTOVar.get() == False:
                if TSVar.get() == True:
                    pass
                elif SVar.get() == True:
                    pass
                elif CVar.get() == True:
                    pass
                else:
                    FOUOButton.config(state = "normal")
                RELTOStorageName.set("")
                RELTO_entry.config(state="disabled")
                NOFORNButton.config(state = "normal")

        def dynamicRELTOMatch(event):           
            dynamicMatch(event,RELTO_entry,RELTOStorageList,RELTOStorageName)                              

        def RELIDOSwitch():
            if RELIDOVar.get() == True:
                FOUOButton.deselect()
                FOUOButton.config(state = "disabled")
                ORCONButton.deselect()
                ORCONButton.config(state="disabled")
                ORCONUSGOVButton.deselect()
                ORCONUSGOVButton.config(state="disabled")
                NOFORNButton.deselect()
                NOFORNButton.config(state = "disabled")
            elif RELIDOVar.get() == False:
                if TSVar.get() == True:
                    pass
                elif SVar.get() == True:
                    pass
                elif CVar.get() == True:
                    pass
                else:
                    FOUOButton.config(state = "normal")
                ORCONButton.config(state="normal")
                ORCONUSGOVButton.config(state="normal")
                NOFORNButton.config(state = "normal")

        def NOFORNSwitch():                    
            if NOFORNVar.get() == True:
                FOUOButton.deselect()
                FOUOButton.config(state = "disabled")
                RELTOButton.deselect()                    
                RELTOButton.config(state = "disabled")
                RELIDOButton.deselect()
                RELIDOButton.config(state = "disabled")
            elif NOFORNVar.get() == False:
                if TSVar.get() == True:
                    pass
                elif SVar.get() == True:
                    pass
                elif CVar.get() == True:
                    pass
                else:
                    FOUOButton.config(state = "normal")
                if HCSVar.get() == True:
                    pass
                else:
                    RELTOButton.config(state = "normal")
                    RELIDOButton.config(state = "normal")

        def FISASwitch():
            if FISAVar.get() == True:
                FOUOButton.deselect()
                FOUOButton.config(state = "disabled")
            elif FISAVar.get() == False:
                if TSVar.get() == True:
                    pass
                elif SVar.get() == True:
                    pass
                elif CVar.get() == True:
                    pass
                else:
                    FOUOButton.config(state = "normal")
                
        def resetMenu():        
            # Reset TS Button
            TSButton.deselect()
            TSButton.config(state="disabled")

             # Reset S Button
            SButton.deselect()
            SButton.config(state="disabled")

            # Reset C Button
            CButton.deselect()
            CButton.config(state="disabled")

            # Reset U Button
            UButton.deselect()
            UButton.config(state="disabled")
            
            # Reset HCS check button
            HCSButton.deselect()
            HCSButton.config(state="disabled")
            
            # Reset SI check button                
            SIButton.deselect()
            SIButton.config(state="disabled")
            
            # Reset SI-G check button
            SIGButton.deselect()
            SIGButton.config(state="disabled")
            
            # Reset TK check button
            TKButton.deselect()
            TKButton.config(state="disabled")
            
            # Reset FGI combo box
            resetFGISelection()
            FGIName_entry.config(state="disabled")
            FGIResetButton.config(state="disabled")
            
            # Enable FOUO check button
            FOUOButton.deselect()                
            FOUOButton.config(state="disabled")                        
            
            # Reset RSEN button
            RSENButton.deselect()
            RSENButton.config(state="disabled")
          
            # Reset ORCON check button
            ORCONButton.deselect()
            ORCONButton.config(state = "disabled")

            # Reset ORCON-USGOV check button
            ORCONUSGOVButton.deselect()
            ORCONUSGOVButton.config(state = "disabled")

            # Reset IMCON check button
            IMCONButton.deselect()
            IMCONButton.config(state = "disabled")

            # Reset RELTO check button
            RELTOButton.deselect()
            RELTOButton.config(state = "disabled")

            # Reset RELTO Entry
            RELTOStorageName.set("")
            RELTO_entry.config(state="disabled")

            # Reset RELDIO check button
            RELIDOButton.deselect()
            RELIDOButton.config(state = "disabled")

            # Reset NOFORN check button
            NOFORNButton.deselect()
            NOFORNButton.config(state = "disabled")
                
            # Reset FISA check button
            FISAButton.deselect()
            FISAButton.config(state="disabled")

        # Reset entire menu
        def resetAll():
            # Reset classificationList
            self.__classificationList = []
            
            # Reset menu
            resetMenu()

            # Disable all classification markings
            TSButton.deselect()
            TSButton.config(state="disabled")
            SButton.deselect()
            SButton.config(state="disabled")
            CButton.deselect()
            CButton.config(state="disabled")
            UButton.deselect()
            UButton.config(state="disabled")

            # Reset FGI Selection
            resetFGISelection()

            # Disable OK button
            okButton.config(state="disabled")
            
            # Disable reset button
            resetButton.config(state="disabled")
                    
            # Reset portion marking and classification banner check buttons
            portionMarkingButton.deselect()
            portionMarkingButton.config(state="normal")
            bannerMarkingButton.deselect()
            bannerMarkingButton.config(state="disabled")

            # Reset portion marking and classification banner register buttons
            registerPortionButton.config(state="disabled")
            registerBannerButton.config(state="disabled")

            # Reset portion marking and classification banner read outs
            bannerMarkingText.set("")
            portionMarkingText.set("")

            # Reset derived from entry
            derivedFromText.set("")
            derivedFromEntry.config(state="disabled")

            # Reset declassify from entry
            declassOnText.set("")
            declassOnEntry.config(state="disabled")

            # Set focus to portion marking button
            portionMarkingButton.focus()

        # Enable portion marking entry
        def enablePortionMarking():
            if portionVar.get() == True or bannerVar.get() == True:
                TSButton.config(state="normal")
                SButton.config(state="normal")
                CButton.config(state="normal")
                UButton.config(state="normal")
                registerPortionButton.config(state="normal")
                resetButton.config(state="normal")
            else:
                TSButton.deselect()
                TSButton.config(state="disabled")
                SButton.config(state="disabled")
                SButton.deselect()
                CButton.config(state="disabled")
                CButton.deselect()
                UButton.config(state="disabled")
                UButton.deselect()
                registerPortionButton.config(state="disabled")
                resetButton.config(state="disabled")

        # Enable banner classification entry
        def enableBannerMarking():
            if bannerVar.get() == True:
                TSButton.config(state="normal")
                SButton.config(state="normal")
                CButton.config(state="normal")
                UButton.config(state="normal")
                registerBannerButton.config(state="normal")
                resetButton.config(state="normal")
            else:
                TSButton.deselect()
                TSButton.config(state="disabled")
                SButton.config(state="disabled")
                SButton.deselect()
                CButton.config(state="disabled")
                CButton.deselect()
                UButton.config(state="disabled")
                UButton.deselect()
                registerBannerButton.config(state="disabled")
                resetButton.config(state="disabled")

        # Provide a classification of "EXERCISE EXERCISE EXERCISE" for training scenarios
        def exerciseSwitch():
            if exerciseVar.get() == True:
                resetMenu()

                portionMarkingButton.deselect()
                portionMarkingButton.config(state="disabled")
                portionMarkingButton.update()

                bannerMarkingButton.deselect()
                bannerMarkingButton.config(state="disabled")
                bannerMarkingButton.update()

                portionMarkingText.set("No Portion Marking")
                portionMarkingReadOut.update()
                
                bannerMarkingText.set("EXERCISE EXERCISE EXERCISE")
                bannerMarkingButton.update()
                
                TSButton.deselect()
                TSButton.config(state="disabled")
                TSButton.update()

                SButton.deselect()
                SButton.config(state="disabled")
                SButton.update()

                CButton.deselect()
                CButton.config(state="disabled")
                CButton.update()

                UButton.deselect()
                UButton.config(state="disabled")
                UButton.update()

                okButton.config(state="normal")
                okButton.update()
                            
                derivedFromText.set("")
                derivedFromEntry.config(state="disabled")
                derivedFromEntry.update()

                declassOnText.set("")
                declassOnEntry.config(state="disabled")
                declassOnEntry.update()
            else:
                portionMarkingButton.config(state="normal")
                portionMarkingButton.update()

                portionMarkingText.set("")
                portionMarkingReadOut.update()
                
                bannerMarkingText.set("")
                bannerMarkingButton.update()

                okButton.config(state="disabled")
                okButton.update()             

        # Assemble classification banner from user selection 
        def classificationAssembler():
            while self.__continueProcessing == True:
                portionMarking = ""
                classificationBanner = ""

                try:
                    if TSVar.get() == False and SVar.get() == False and CVar.get() == False and UVar.get() == False:
                        raise ValueError
                    else:
                        pass
                except:
                    windll.user32.MessageBoxA(0, "Please choose a classification marking", "Classification Entry Error", 0)
                    break

                # US classification markings
                # TOP SECRET
                if TSVar.get() == True:
                    portionMarking += "TS"
                    classificationBanner += "TOP SECRET"
                else:
                    pass

                # SECRET
                if SVar.get() == True:
                    portionMarking += "S"
                    classificationBanner += "SECRET"
                else:
                    pass
                
                # CONFIDENTIAL
                if CVar.get() == True:
                    portionMarking += "C"
                    classificationBanner += "CONFIDENTIAL"
                else:
                    pass
                
                # UNCLASSIFIED
                if UVar.get() == True:
                    portionMarking += "U"
                    classificationBanner += "UNCLASSIFIED"
                else:
                    pass
                
                # SCI control markings

                # HCS
                if HCSVar.get() == True:
                    portionMarking += "//" + "HCS-P"
                    classificationBanner += "//" + "HCS-P"
                else:
                    pass
                
                # SI
                if SIVar.get() == True:
                    if HCSVar.get() == True:
                        portionMarking += "/" + "SI"
                        classificationBanner += "/" + "SI"
                    else:
                        portionMarking += "//" + "SI"
                        classificationBanner += "//" + "SI"
                    
                # SI-G
                if SIGVar.get() == True:
                    if HCSVar.get() == True:
                        portionMarking += "/" + "SI-G"
                        classificationBanner += "/" + "SI-G"
                    elif SIVar.get() == True:
                        portionMarking += "/" + "SI-G"
                        classificationBanner += "/" + "SI-G"
                    else:
                        portionMarking += "//" + "SI-G"
                        classificationBanner += "//" + "SI-G"
                
                # TK
                if TKVar.get() == True:
                    if HCSVar.get() == True:
                        portionMarking += "/" + "TK"
                        classificationBanner += "/" + "TK"
                    elif SIVar.get() == True:
                        portionMarking += "/" + "TK"
                        classificationBanner += "/" + "TK"
                    else:
                        portionMarking += "//" + "TK"
                        classificationBanner += "//" + "TK"

                # FGI Country Name (insert FGI selection into classification banner)
                if FGIStorageList:
                    portionMarking += "//" + "FGI"
                    classificationBanner += "//" + "FGI"
                    countryTrigraphList = []
                    for item in FGIStorageList:
                        for key, value in self.__FGIDictionary.iteritems():
                            if value == item:
                                countryTrigraphList.append(key)
                            else:
                                pass
                    countryTrigraphList.sort()
                    for element in countryTrigraphList:
                        portionMarking += " " + element
                        classificationBanner += " " + element
                else:
                    pass

                # Dissemination control markings
                
                # RSEN
                if RSENVar.get() == True:
                    portionMarking += "//" + "RS"
                    classificationBanner += "//" + "RSEN"
                else:
                    pass
                # FOUO
                if FOUOVar.get() == True:
                    portionMarking += "//" + "FOUO"
                    classificationBanner += "//" + "FOUO"
                else:
                    pass
                # ORCON
                if ORCONVar.get() == True:
                    if RSENVar.get() == True:
                        portionMarking += "/" + "OC"
                        classificationBanner += "/" + "ORCON"
                    else:
                        portionMarking += "//" + "OC"
                        classificationBanner += "//" + "ORCON"
                # ORCON-USGOV
                if ORCONUSGOVVar.get() == True:
                    if RSENVar.get() == True:
                        portionMarking += "/" + "OC-USGOV" 
                        classificationBanner += "/" + "ORCON-USGOV"                    
                    else:
                        portionMarking += "//" + "OC-USGOV" 
                        classificationBanner += "//" + "ORCON-USGOV"
                # IMCON
                if IMCONVar.get() == True:
                    if RSENVar.get() == True:
                        portionMarking += "/" + "IMC"
                        classificationBanner += "/" + "IMCON"
                    elif ORCONVar.get() == True:
                        portionMarking += "/" + "IMC"
                        classificationBanner += "/" + "IMCON"
                    elif ORCONUSGOVVar.get() == True:
                        portionMarking += "/" + "IMC"
                        classificationBanner += "/" + "IMCON"                   
                    else:
                        portionMarking += "//" + "IMC"
                        classificationBanner += "//" + "IMCON"
                # REL TO
                if RELTOVar.get() == True:
                    if RELTO_entry.get() == "":
                        windll.user32.MessageBoxA(0, 'Please make a "REL TO" choice', "Classification Entry Error", 0)
                        break
                    else:
                        pass
                    if RSENVar.get() == True:
                        portionMarking += "/" + "REL TO " + RELTO_entry.get()
                        classificationBanner += "/" + "REL TO " + RELTO_entry.get()
                    elif ORCONVar.get() == True:
                        portionMarking += "/" + "REL TO " + RELTO_entry.get()
                        classificationBanner += "/" + "REL TO " + RELTO_entry.get()
                    elif ORCONUSGOVVar.get() == True:
                        portionMarking += "/" + "REL TO " + RELTO_entry.get()
                        classificationBanner += "/" + "REL TO " + RELTO_entry.get()       
                    elif IMCONVar.get() == True:
                        portionMarking += "/" + "REL TO " + RELTO_entry.get()
                        classificationBanner += "/" + "REL TO " + RELTO_entry.get()
                    else:
                        portionMarking += "//" + "REL TO " + RELTO_entry.get()
                        classificationBanner += "//" + "REL TO " + RELTO_entry.get()
                # RELIDO
                if RELIDOVar.get() == True:
                    if RSENVar.get() == True:
                        portionMarking += "/" + "RELIDO"
                        classificationBanner += "/" + "RELIDO"
                    elif IMCONVar.get() == True:
                        portionMarking += "/" + "RELIDO"
                        classificationBanner += "/" + "RELIDO"
                    elif RELTOVar.get() == True:
                        portionMarking += "/" + "RELIDO"
                        classificationBanner += "/" + "RELIDO"                 
                    else:
                        portionMarking += "//" + "RELIDO"
                        classificationBanner += "//" + "RELIDO"
                
                # NOFORN
                if NOFORNVar.get() == True:
                    if RSENVar.get() == True:
                        portionMarking += "/" + "NF"
                        classificationBanner += "/" + "NOFORN"
                    elif ORCONVar.get() == True:
                        portionMarking += "/" + "NF"
                        classificationBanner += "/" + "NOFORN"
                    elif IMCONVar.get() == True:
                        portionMarking += "/" + "NF"
                        classificationBanner += "/" + "NOFORN"
                    else:
                        portionMarking += "//" + "NF"
                        classificationBanner += "//" + "NOFORN"
                # FISA
                if FISAVar.get() == True:
                    if RSENVar.get() == True:
                        portionMarking += "/" + "FISA"
                        classificationBanner += "/" + "FISA"
                    elif ORCONVar.get() == True:
                        portionMarking += "/" + "FISA"
                        classificationBanner += "/" + "FISA"
                    elif ORCONUSGOVVar.get() == True:
                        portionMarking += "/" + "FISA"
                        classificationBanner += "/" + "FISA"
                    elif IMCONVar.get() == True:
                        portionMarking += "/" + "FISA"
                        classificationBanner += "/" + "FISA"
                    elif RELTOVar.get() == True:
                        portionMarking += "/" + "FISA"
                        classificationBanner += "/" + "FISA"             
                    elif RELIDOVar.get() == True:
                        portionMarking += "/" + "FISA"
                        classificationBanner += "/" + "FISA"                                 
                    elif NOFORNVar.get() == True:
                        portionMarking += "/" + "FISA"
                        classificationBanner += "/" + "FISA"
                    else:
                        portionMarking += "//" + "FISA"
                        classificationBanner += "//" + "FISA"
                else:
                    pass
                try:
                    if RSENVar.get() == False and FOUOVar.get() == False and ORCONVar.get() == False and ORCONUSGOVVar.get() == False and IMCONVar.get() == False and RELIDOVar.get() == False and RELTOVar.get() == False and NOFORNVar.get() == False and FISAVar.get() == False:
                        if UVar.get() == True:
                            pass
                        else:
                            raise ValueError
                    else:
                        pass
                except:
                    windll.user32.MessageBoxA(0, "Please choose releasibility caveat", "Classification Entry Error", 0)
                    break

                if portionVar.get() == True and bannerVar.get() == False:
                    return portionMarking
                else:
                    pass

                if bannerVar.get() == True:
                    return classificationBanner
                else:
                    pass

                break

        def portionAssembler():
            portionMarking = classificationAssembler()
            if portionMarking != None:
                portionMarking = "(" + portionMarking + ")"
                portionMarkingText.set(portionMarking)
                
                try:
                    if portionVar.get() == True:
                        if portionMarking != "":
                            self.__classificationList.append(portionMarking)
                            portionMarkingButton.config(state="disabled")
                            registerPortionButton.config(state="disabled")
                            resetMenu()
                            resetButton.config(state="normal")
                            bannerMarkingButton.config(state="normal")
                        else:
                            errorMessage = "Error in portion marking entry"
                            raise ValueError              
                    else:
                        errorMessage = "Please register portion marking"
                        raise ValueError
                except:
                    windll.user32.MessageBoxA(0, errorMessage, "Classification Entry Required", 0)
            else:
                pass

        def bannerAssembler():
            classificationBanner = classificationAssembler()
            if classificationBanner != None:
                bannerMarkingText.set(classificationBanner)
                try:
                    if bannerVar.get() == True:
                        if classificationBanner != "":
                            self.__classificationList.append(classificationBanner)
                            bannerMarkingButton.config(state="disabled")
                            registerBannerButton.config(state="disabled")
                            resetMenu()
                            if self.__classificationList[0][1] == "U" and self.__classificationList[1][0] == "U":
                                host.configure(text="Source:")
                                derivedFromEntry.config(state="normal")
                            else:
                                host.configure(text="Derived From:")
                                derivedFromEntry.config(state="normal")
                                declassOnEntry.config(state="normal")
                        else:
                            errorMessage = "Error in classification banner entry"
                            raise ValueError
                    else:
                        errorMessage = "Please register banner marking"
                        raise ValueError
                except:
                    windll.user32.MessageBoxA(0, errorMessage, "Classification Entry Required", 0)
            else:
                pass

        def DDSwitch(event):
            if self.__classificationList[0][1] == "U" and self.__classificationList[1][0] == "U":
                if derivedFromEntry.get() == "":
                    okButton.config(state="disabled")  
                else:
                    okButton.config(state="normal")
            elif exerciseVar.get() == True:
                okButton.config(state="normal")
            else:                
                if derivedFromEntry.get() == "" or declassOnEntry.get() == "":
                    okButton.config(state="disabled")  
                else:
                    okButton.config(state="normal")

        def retrieveDD():
            if exerciseVar.get() == True:
                self.__classificationList = ["","EXERCISE EXERCISE EXERCISE",""]
                closeClassificationWindow()
            else:
                try:
                    if self.__classificationList[0][1] == "U" and self.__classificationList[1][0] == "U":
                        source = derivedFromEntry.get()
                        if source:
                            self.__classificationList.append(source)
                        else:
                            errorMessage = "What source was the classification derived from?"
                            raise ValueError
                    else:
                        derivedFrom = derivedFromEntry.get()
                        declassifyOn = declassOnEntry.get()
                        
                        if derivedFrom:
                            self.__classificationList.append(derivedFrom)
                        else:
                            errorMessage = "What source was the classification derived from?"
                            raise ValueError
                        if declassifyOn:
                            self.__classificationList.append(declassifyOn)                   
                        else:
                            errorMessage = "Please enter a declassifcation entry"
                            raise ValueError
                except:
                    windll.user32.MessageBoxA(0, errorMessage, "User Entry Required", 0)
                
            closeClassificationWindow()
            
        top = Toplevel()
        top.title("Classification Tool")
        top.attributes('-topmost', 1)
        top.attributes('-topmost', 0) # put window on top of all others

        top.protocol("WM_DELETE_WINDOW", closeClassificationWindow)

        classificationframe = ttk.Frame(top)
        classificationframe.grid(column=0, row=0, sticky=(N, W, E, S))
        classificationframe.columnconfigure(0, weight=1)
        classificationframe.rowconfigure(0, weight=1)

        FGIList = []
        FGIStorageList = []
        RELTOStorageList = ["USA, FVEY", "USA, ACGU", "USA, GBR", "USA, KOR", "USA, DEU", "USA, JPN", "USA, NATO"]

        for key, value in self.__FGIDictionary.iteritems():
            FGIList.append(value)

        FGIList.sort()
        
        portionMarkingText = StringVar()
        classificationBannerText = StringVar()

        TSVar = BooleanVar()
        SVar = BooleanVar()
        CVar = BooleanVar()
        UVar = BooleanVar()

        HCSVar = BooleanVar()
        SIVar = BooleanVar()
        SIGVar = BooleanVar()
        TKVar = BooleanVar()

        FGIName = StringVar()
        FGIStorageName = StringVar()

        RSENVar = BooleanVar()
        FOUOVar = BooleanVar()
        ORCONVar = BooleanVar()
        ORCONUSGOVVar = BooleanVar()
        IMCONVar = BooleanVar()
        RELIDOVar = BooleanVar()
        RELTOVar = BooleanVar()
        RELTOStorageName = StringVar()
        NOFORNVar = BooleanVar()
        FISAVar = BooleanVar()

        exerciseVar = BooleanVar()

        portionVar = BooleanVar()
        bannerVar = BooleanVar()

        portionMarkingText = StringVar()
        bannerMarkingText = StringVar()
        derivedFromText = StringVar()
        declassOnText = StringVar()
      
        classMarking = ttk.Label(top, text="Classification Marking")
        classMarking.grid(column=1,row=1,sticky=W)

        TSButton = Checkbutton(top, text="TOP SECRET", variable=TSVar, state="disabled", command=TSwitch)
        TSButton.grid(column=1,row=2,sticky=W)

        SButton = Checkbutton(top, text="SECRET", variable=SVar, state="disabled", command=SSwitch)
        SButton.grid(column=1,row=3,sticky=W)

        CButton = Checkbutton(top, text="CONFIDENTIAL", variable=CVar, state="disabled", command=CSwitch)
        CButton.grid(column=1,row=4,sticky=W)

        UButton = Checkbutton(top, text="UNCLASSIFIED", variable=UVar, state="disabled", command=USwitch)
        UButton.grid(column=1,row=5,sticky=W)

        classMarking = ttk.Label(top, text="SCI Caveat")
        classMarking.grid(column=2,row=1,sticky=W)

        HCSButton = Checkbutton(top, text="HCS-P", variable=HCSVar, state = "disabled", command=HCSSwitch)
        HCSButton.grid(column=2,row=2,sticky=W)

        SIButton = Checkbutton(top, text="SI", variable=SIVar, state="disabled", command=SISwitch)
        SIButton.grid(column=2,row=3,sticky=W)
                                      
        SIGButton = Checkbutton(top, text="SI-G", variable=SIGVar, state="disabled", command=SISwitch)
        SIGButton.grid(column=2,row=4,sticky=W)

        TKButton = Checkbutton(top, text="TK", variable=TKVar, state="disabled")
        TKButton.grid(column=2,row=5,sticky=W)

        FGIName_entry = ttk.Combobox(top, width=30, state="disabled", textvariable=FGIName, values=FGIList)
        FGIName_entry.grid(column=4, row=1, sticky=W)
        FGIName_entry.bind('<<ComboboxSelected>>', getFGISelection, add ="+")
        FGIName_entry.bind('<KeyRelease>', dynamicFGIMatch, add="+")
        ttk.Label(top, text="FGI Country:").grid(column=3, row=1, sticky=W)

        FGINameStorage_entry = ttk.Combobox(top, width=30, state="disabled", textvariable=FGIStorageName, values=FGIStorageList)
        FGINameStorage_entry.grid(column=4, row=2,sticky=W)
        ttk.Label(top, text="Stored FGI:").grid(column=3, row=2, sticky=W)

        FGIAddButton = Button(top, text="Add", state="disabled", command=storeFGISelection)
        FGIAddButton.grid(column=5, row=1, sticky=(W,E))

        FGISubtractButton = Button(top, text="Subtract", state="disabled", command=subtractFGISelection)
        FGISubtractButton.grid(column=5, row=2, sticky=(W,E)) 

        FGIResetButton = Button(top, text="Reset FGI", state="disabled", command=resetFGISelection)
        FGIResetButton.grid(column=5, row=3, sticky=(W,E)) 

        classMarking = ttk.Label(top, text="Releasibility Caveat")
        classMarking.grid(column=6,row=1,sticky=W)

        RSENButton = Checkbutton(top, text="RSEN", variable=RSENVar, state = "disabled")
        RSENButton.grid(column=6,row=2,sticky=W)

        FOUOButton = Checkbutton(top, text="FOUO", variable=FOUOVar, state="disabled", command=FOUOSwitch)
        FOUOButton.grid(column=6,row=3,sticky=W)

        ORCONButton = Checkbutton(top, text="ORCON", variable=ORCONVar, state="disabled", command=ORCONSwitch)
        ORCONButton.grid(column=6,row=4,sticky=W)

        ORCONUSGOVButton = Checkbutton(top, text="ORCON-USGOV", variable=ORCONUSGOVVar, state="disabled", command=ORCONUSGOVSwitch)
        ORCONUSGOVButton.grid(column=6,row=5,sticky=W)

        IMCONButton = Checkbutton(top, text="IMCON", variable=IMCONVar, state="disabled")
        IMCONButton.grid(column=6,row=6,sticky=W)

        RELIDOButton = Checkbutton(top, text="RELIDO", variable=RELIDOVar, state="disabled", command=RELIDOSwitch)
        RELIDOButton.grid(column=6,row=7,sticky=W)

        RELTOButton = Checkbutton(top, text="REL TO", variable=RELTOVar, state="disabled", command=RELTOSwitch)
        RELTOButton.grid(column=6,row=8,sticky=W)

        RELTO_entry = ttk.Combobox(top, width=15, state="disabled", textvariable=RELTOStorageName, values=RELTOStorageList)
        RELTO_entry.grid(column=7, row=8,sticky=W)
        RELTO_entry.bind('<KeyRelease>', dynamicRELTOMatch)

        NOFORNButton = Checkbutton(top, text="NOFORN",variable=NOFORNVar,state="disabled",command=NOFORNSwitch)
        NOFORNButton.grid(column=6,row=9,sticky=W)

        FISAButton = Checkbutton(top, text="FISA",variable=FISAVar,state="disabled",command=FISASwitch)
        FISAButton.grid(column=6,row=10,sticky=W)     

        okButton = Button(top, text="OK", state="disabled",command=retrieveDD)    
        okButton.grid(column=2, row=9, sticky=(W,E)) 

        cancelButton = Button(top,text="Cancel",command=cancelWindow)
        cancelButton.grid(column=1, row=10, sticky=(W,E))

        resetButton = Button(top, text="Reset", state="disabled", command=resetAll) 
        resetButton.grid(column=2, row=10, sticky=(W,E))

        portionMarkingButton = Checkbutton(top,text="Portion Marking:",variable=portionVar,state="normal",command=enablePortionMarking)
        portionMarkingButton.grid(column=1,row=7,sticky=W)

        portionMarkingReadOut = ttk.Entry(top,width=100, state = "readonly", textvariable=portionMarkingText)
        portionMarkingReadOut.grid(column=2,row=14, columnspan=4,sticky=W)
        ttk.Label(top, text="Portion Marking:").grid(column=1,row=14,sticky=W)

        registerPortionButton = Button(top,text="Register Portion Marking", state="disabled",command=portionAssembler)
        registerPortionButton.grid(column=2,row=7,sticky=(W,E)) 

        bannerMarkingButton = Checkbutton(top, text="Banner Marking",variable=bannerVar,state="disabled",command=enableBannerMarking)
        bannerMarkingButton.grid(column=1,row=8,sticky=W)

        bannerMarkingReadOut = ttk.Entry(top, width = 100, state = "readonly", textvariable=bannerMarkingText)
        bannerMarkingReadOut.grid(column=2,row=15,columnspan=4,sticky=W)
        ttk.Label(top, text="Banner Marking:").grid(column=1,row=15,sticky=W)

        registerBannerButton = Button(top, text="Register Banner Marking", state="disabled",command=bannerAssembler)
        registerBannerButton.grid(column=2,row=8,sticky=(W,E))

        derivedFromEntry = ttk.Entry(top, width=35, state="disabled", textvariable=derivedFromText)
        derivedFromEntry.grid(column=2,row=16,columnspan=3,sticky=W)
        derivedFromEntry.bind('<KeyRelease>',DDSwitch)
        host = ttk.Label(top, text="Derived From:")
        host.grid(column=1,row=16,sticky=W)

        exerciseButton = Checkbutton(top, text="Exercise Only",variable=exerciseVar,state="normal",command=exerciseSwitch)
        exerciseButton.grid(column=4,row=16,sticky=W)
        
        declassOnEntry = ttk.Entry(top, width=35, state="disabled", textvariable=declassOnText)
        declassOnEntry.grid(column=2,row=17, columnspan=3, sticky=W)
        declassOnEntry.bind('<KeyRelease>',DDSwitch)
        ttk.Label(top, text="Declassify On:").grid(column=1,row=17,sticky=W)        

        for child in top.winfo_children():            
            child.grid_configure(padx=2, pady=2)

        portionMarkingButton.focus()

        top.grab_set()

        # Wait until classification tool closes then return classification portion marking and banner
        top.wait_window()
        return self.__classificationList
