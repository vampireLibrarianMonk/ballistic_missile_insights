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

# Import modules from ttk
import ttk

# Set variables for environment workspace and main directory (move to rangeRingModules)
fileName =  path.basename(argv[0])
mainDirectory = argv[0]
mainDirectory = mainDirectory.replace(fileName, "")
mainDirectory += "range_ring\\"
worldPath = mainDirectory + "Data"
scratchPath = mainDirectory + "scratch"

CCC_Tool_Var = mainDirectory + "code\\rangeRingModules.pyc"
load_compiled('rangeRingModules', CCC_Tool_Var)
from rangeRingModules import *

# Set environment workspace and main directory (fixes problem with spaces in directories)
worldPath = getShortFilePath(worldPath)
env.workspace = worldPath
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
            elif len(self.__classificationList) == 3 and UVar.get() == True:
                top.grab_release()
                top.destroy()
            elif len(self.__classificationList) == 3 and exerciseVar.get() == True:
                top.grab_release()
                top.destroy()
            else:
                self.__classificationList = []
                top.grab_release()
                top.destroy()

        def cancelWindow():
            self.__classificationList = []
            top.grab_release()
            top.destroy()  

        def enableDerivedDeclassEntry():
            if TSVar.get() == True or SVar.get() == True or CVar.get() == True:
                derivedFromEntry.config(state="normal")
                declassOnEntry.config(state="normal")
            elif UVar.get() == True:
                derivedFromEntry.config(state="normal")
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
                
                resetButton.config(state="normal")
                
            elif TSVar.get() == False:
                resetMenu()
                TSButton.config(state="normal")
                SButton.config(state="normal")
                CButton.config(state="normal")
                UButton.config(state="normal")
                
                okButton.config(state="disabled")
            else:
                pass

            enableDerivedDeclassEntry()
                
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
                
                resetButton.config(state="normal")
            elif SVar.get() == False:
                resetMenu()
                TSButton.config(state="normal")
                SButton.config(state="normal")
                CButton.config(state="normal")
                UButton.config(state="normal")
                
                okButton.config(state="disabled")
                resetButton.config(state="disabled")
            else:
                pass

            enableDerivedDeclassEntry()
                
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
                
                okButton.config(state="disabled")
                resetButton.config(state="normal")
            elif CVar.get() == False:
                resetMenu()
                TSButton.config(state="normal")
                SButton.config(state="normal")
                CButton.config(state="normal")
                UButton.config(state="normal")
                
                resetButton.config(state="disabled")
            else:
                pass

            enableDerivedDeclassEntry()

        def USwitch():
            if UVar.get() == True:
                TSButton.deselect()
                TSButton.config(state="disabled")

                SButton.deselect()
                SButton.config(state="disabled")

                CButton.deselect()
                CButton.config(state="disabled")
                
                FGIName_entry.config(state="normal")

                host.configure(text="Source:")
                
                SCICaveatSwitch()
                
                resetButton.config(state="normal")
            elif UVar.get() == False:
                resetMenu()
                TSButton.config(state="normal")
                SButton.config(state="normal")
                CButton.config(state="normal")
                UButton.config(state="normal")

                host.configure(text="Derived From:")
                
                okButton.config(state="disabled")
                resetButton.config(state="disabled")
            else:
                pass

            enableDerivedDeclassEntry()
            
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
            TSButton.config(state="normal")

             # Reset S Button
            SButton.deselect()
            SButton.config(state="normal")

            # Reset C Button
            CButton.deselect()
            CButton.config(state="normal")

            # Reset U Button
            UButton.deselect()
            UButton.config(state="normal")
            
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

            # Reset Derived From:
            derivedFromText.set("")
            derivedFromEntry.config(state="disabled")

            # Reset Declassify On:
            declassOnText.set("")
            declassOnEntry.config(state="disabled")

            # Disable OK button
            okButton.config(state="disabled")

        # Reset entire menu
        def resetAll():
            # Reset classificationList
            self.__classificationList = []
            
            # Reset menu
            resetMenu()

        # Provide a classification of " EXERCISE EXERCISE EXERCISE" for training scenarios
        def exerciseSwitch():
            if exerciseVar.get() == True:            
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
                TSButton.config(state="normal")
                TSButton.update()

                SButton.config(state="normal")
                SButton.update()

                CButton.config(state="normal")
                CButton.update()

                UButton.config(state="normal")
                UButton.update()                

        # Assemble classification banner from user selection 
        def classificationAssembler():
            if exerciseVar.get() == True:
                self.__classificationList = ["","EXERCISE EXERCISE EXERCISE",""]
                closeClassificationWindow()
            else:            
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
                    else:
                        pass
                        
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
                    else:
                        pass
                    
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
                    else:
                        pass

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
                    else:
                        pass
                            
                    # ORCON-USGOV
                    if ORCONUSGOVVar.get() == True:
                        if RSENVar.get() == True:
                            portionMarking += "/" + "OC-USGOV" 
                            classificationBanner += "/" + "ORCON-USGOV"                    
                        else:
                            portionMarking += "//" + "OC-USGOV" 
                            classificationBanner += "//" + "ORCON-USGOV"
                    else:
                        pass
                    
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
                    else:
                        pass
                            
                    # REL TO
                    if RELTOVar.get() == True:
                        string = RELTO_entry.get()
                        if RELTO_entry.get() == "":
                            windll.user32.MessageBoxA(0, 'Please make a "REL TO" choice', "Classification Entry Error", 0)
                            break
                        elif string[0:4] != "USA,":
                            windll.user32.MessageBoxA(0, 'Releasability caveat must start with "USA,".', "Classification Entry Error", 0)
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
                    else:
                        pass
                    
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
                    else:
                        pass
                    
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
                    else:
                        pass
                    
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

                    # Add parathesis to portion marking text
                    portionMarking = "(" + portionMarking + ")"
                    
                    try:
                        if RSENVar.get() == False and FOUOVar.get() == False and ORCONVar.get() == False and ORCONUSGOVVar.get() == False and IMCONVar.get() == False and RELIDOVar.get() == False and RELTOVar.get() == False and NOFORNVar.get() == False and FISAVar.get() == False:
                            if UVar.get() == True:
                                pass
                            else:
                                raise ValueError
                        else:
                            pass
                    except:
                        windll.user32.MessageBoxA(0, "Please choose a releasibility caveat", "Classification Entry Error", 0)
                        break

                    if UVar.get() == True:
                        self.__classificationList = [portionMarking, classificationBanner, derivedFromText.get()]
                    else:
                        self.__classificationList = [portionMarking, classificationBanner, derivedFromText.get(), declassOnText.get()]
                    closeClassificationWindow()
                    print "classification done"
                    break

        def DDSwitch(event):
            if UVar.get() == True:
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
        RELTOStorageList = ["USA, FVEY", "USA, ACGU", "USA, GBR", "USA, KOR", "USA, DEU", "USA, JPN", "USA, NATO", "USA, ISR"]

        for key, value in self.__FGIDictionary.iteritems():
            FGIList.append(value)

        FGIList.sort()

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

        portionMarkingText = StringVar()
        bannerMarkingText = StringVar()
        derivedFromText = StringVar()
        declassOnText = StringVar()
      
        classMarking = ttk.Label(top, text="Classification Marking")
        classMarking.grid(column=1,row=1,sticky=W)

        TSButton = Checkbutton(top, text="TOP SECRET", variable=TSVar, state="normal", command=TSwitch)
        TSButton.grid(column=1,row=2,sticky=W)

        SButton = Checkbutton(top, text="SECRET", variable=SVar, state="normal", command=SSwitch)
        SButton.grid(column=1,row=3,sticky=W)

        CButton = Checkbutton(top, text="CONFIDENTIAL", variable=CVar, state="normal", command=CSwitch)
        CButton.grid(column=1,row=4,sticky=W)

        UButton = Checkbutton(top, text="UNCLASSIFIED", variable=UVar, state="normal", command=USwitch)
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

        okButton = Button(top, text="OK", state="disabled",command=classificationAssembler)    
        okButton.grid(column=2, row=9, sticky=(W,E)) 

        cancelButton = Button(top,text="Cancel",command=cancelWindow)
        cancelButton.grid(column=1, row=10, sticky=(W,E))

        resetButton = Button(top, text="Reset", state="disabled", command=resetAll) 
        resetButton.grid(column=2, row=10, sticky=(W,E))

        derivedFromEntry = Entry(top, width=50, state="disabled", textvariable=derivedFromText) 
        derivedFromEntry.grid(column=2,row=16,columnspan=3,sticky=W)
        derivedFromEntry.bind('<KeyRelease>',DDSwitch)
        host = Label(top, text="Derived From:")
        host.grid(column=1,row=16,sticky=W)

        exerciseButton = Checkbutton(top, text="Exercise Only",variable=exerciseVar,state="normal",command=exerciseSwitch)
        exerciseButton.grid(column=5,row=16,sticky=W)

        declassOnEntry = ttk.Entry(top, width=50, state="disabled", textvariable=declassOnText)
        declassOnEntry.grid(column=2,row=17, columnspan=3, sticky=W)
        declassOnEntry.bind('<KeyRelease>', DDSwitch)
        ttk.Label(top, text="Declassify On:").grid(column=1, row=17, sticky=W)

        for child in top.winfo_children():
            child.grid_configure(padx=2, pady=2)

        top.grab_set()

        # Wait until classification tool closes then return classification portion marking and banner
        top.wait_window()
        return self.__classificationList
