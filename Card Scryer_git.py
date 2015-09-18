# -*- coding: utf-8 -*-
import sys
#sys.stderr = open('Error_CardScryer.txt','a')
from PySide import QtCore
from PySide import QtGui
import cv2
import numpy as np
import os
from PIL import Image
import imagehash
from operator import itemgetter
import pandas as pd
import pickle
import csv
#%% Init Functions
def hex_to_hash(hexstr):
	l = []
	if len(hexstr) != 16:
		raise ValueError('The hex string has the wrong length')
	for i in range(8):
		h = hexstr[i*2:i*2+2]
		v = int("0x" + h, 16)
		l.append([v & 2**i > 0 for i in range(8)])
	return imagehash.ImageHash(np.array(l))
def init_db():
    global autocomplete
    workingHashes = csv.reader(open('ExampleHashes.csv','r'))
    workingPrices = csv.reader(open('ExamplePrices.csv','r'))
    cardHashes=[]
    priceList=[]
    for rows in workingHashes:
        cardHashes.append(rows)
        cardHashes[-1][2]=hex_to_hash(cardHashes[-1][2])
    for rows in workingPrices:
        priceList.append(rows)
    autocomplete=[]
    for rows in priceList:
        autocomplete.append(rows[0]+' {'+rows[1]+'}')
    return cardHashes,priceList
def add_card(cardName,setName,foilStatus):
    global inventory
    found=False
    for row in inventory:
        if cardName in row and setName in row and foilStatus==row[2]:
            row[3]+=1
            found=True
            break
    if found==False:
        inventory.append([cardName, setName,foilStatus,1,get_prices(cardName,setName)])
    return inventory
def get_prices(cardName, setName):
    price='No Info Available'
    for rows in range(len(priceList)):
        if priceList[rows][0]==cardName and priceList[rows][1]==setName:
            price = priceList[rows][2]
    return price            
def calc_dist(x1,y1,x2,y2):
    dist = np.sqrt(abs(x2-x1)**2 + abs(y2-y1)**2)
    return dist 
def get_perspective(p1,p2,p3,p4):
    if p1[0]>p2[0]:
        topRight = p1
        topLeft = p2
    else:
        topRight = p2
        topLeft = p1
    if p3[0]>p4[0]:
        botRight = p3
        botLeft = p4
    else:
        botRight = p4
        botLeft = p3
    return topLeft, topRight, botLeft, botRight    
def inventory_tally():
    global inventory
    tally=0
    for rows in inventory:
        tally+=rows[3]
    return tally
#%% Init Data
try:
    with open('Database\Config.cnf', 'rb') as csvfile:
        config = csv.reader(csvfile, delimiter=',')
        config = list(config)
    print 'Loading Configuration'
    videoDeviceNumber = int(config[0][1])
    vidWidth = int(config[1][1])
    vidHeight = int(config[2][1])
    inventoryPath = config[3][1]
except IOError: #Load Defaults
    print 'No configuration file found, loading defaults'
    videoDeviceNumber = 0
    vidWidth = 1280
    vidHeight = 720
    inventoryPath = 'Database\Inventory.csv'

tarHeight = 680
tarWidth = 480
dst = np.zeros((tarHeight,tarWidth))
artX1 = int(round(tarWidth*(67/480.0)))
artY1 = int(round(tarHeight*(85/680.0)))
artX2 = int(round(tarWidth*(427/480.0)))
artY2 = int(round(tarHeight*(367/680.0)))
artSleeveX1 = int(round(tarWidth*(77/480.0)))
artSleeveY1 = int(round(tarHeight*(109/680.0)))
artSleeveX2 = int(round(tarWidth*(413/480.0)))
artSleeveY2 = int(round(tarHeight*(372/680.0)))
#Initialize dummy variables

updatedManually=False
dialogOpen=False
decklist=[]
workingInventory = []
inventory=[]
foundCard=False
findCard=False

#Initialize old Inventory
try:
    inventory = pd.read_csv(inventoryPath,index_col=False)
    inventory = inventory.values.tolist()
except IOError:
    print 'No existing inventory file found'
except TypeError:
    print 'No existing inventory file found'
#Initialize AutoComplete

        
#%% Main Program
class infoDialog(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self)
        self.setup_infoGUI()
    def setup_infoGUI(self):
        self.setWindowIcon(QtGui.QIcon('Database\Misc\Icon.png'))
        self.infoLayout = QtGui.QVBoxLayout()
        self.textEdit = QtGui.QLabel('Thanks for trying out Card Scryer! <br><br>\
        To detect cards place them (approximately) right side up in the webcam\'s <br>\
        field of view, flipping or mirroring the webcam feed as necessary. When the <br>\
        card is underneath the webcam, press the space bar to initialize detection. <br>\
        Once a card has been detected, use the left and right arrow keys to select the <br>\
        appropriate set (if applicable), and press space again to add the card to your <br>\
        working inventory. If the wrong card is detected, press ESC and try again. <br><br>\
        If no card is detected, toggle the view contours box. The red lines represent <br>\
        regions of high contrast, for detection to occur, the entire circumference must <br>\
        consist of a continuous contour. If contours are visible on the interior of the <br>\
        card, then a continuous contrast region was not detected. Place the card on a <br>\
        white or light gray surface if necessary, and eliminate any glare and/or shadows. <br>\
        If the card is too close to the edge of the field of view to complete drawing the <br>\
        overlay, it will not allow the user to proceed, try moving the card close to the <br>\
        center of the field of view. <br><br>\
        Detecting cards in sleeves is less accurate, however enabling the \'Sleeved\' <br>\
        checkbox will use an alternative ROI and slightly improve accuracy. <br><br>\
        The default video input device, as well as input resolution can be change by <br>\
        modifying \'Database\Config.cnf\' in a text editor. The active inventory file can <br>\
        also be changed through this dialogue. <br><br>\
        (This program has not been tested below 960*720 (4:3) resolution) <br><br>\
        Visit <a href=\"https://cardscryer.com\">http://cardscryer.com</a> for change logs and updates. Please address any <br>\
        [Questions] or [Suggestions] to Support@CardScryer.com. <br><br>\
        Set icons modified from <a href=\"https://github.com/jninnes/mtgicons\">jninnes @ github</a> <br>\
        App icon by <a href=\"http://www.jordanhaller.com/\">Jordan Haller</a><br>')
        self.textEdit.setTextFormat(QtCore.Qt.RichText)        
        self.textEdit.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse)
        self.textEdit.setOpenExternalLinks(True)

        self.infoLayout.addWidget(self.textEdit)
        self.closeInfoButton=QtGui.QPushButton('Close')
        self.closeInfoButton.clicked.connect(self.closeInfo)
        self.infoLayout.addWidget(self.closeInfoButton)
        self.setWindowTitle('About Card Scryer')  
        self.setLayout(self.infoLayout)
    def closeInfo(self):
        self.close()
        self.infoLayout.addWidget(self.closeInfoButton)
class manualEntryDialog(QtGui.QDialog):
    global autocomplete
    global priceList
    global dialogOpen
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self)
        self.setup_manualGUI()
    def setup_manualGUI(self):  
        self.setWindowIcon(QtGui.QIcon('Database\Misc\Icon.png'))
        self.setWindowFlags(QtCore.Qt.CustomizeWindowHint)
        self.deckManualLayout = QtGui.QGridLayout()
        
        self.deckManualLayout.addWidget(QtGui.QLabel('Card Name:'),1,0)
        self.lineEdit=QtGui.QLineEdit(self)
        
        completer=QtGui.QCompleter(autocomplete, self)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.lineEdit.setCompleter(completer)
        self.lineEdit.textChanged[str].connect(self.onChanged)
        self.addManual_button = QtGui.QPushButton('Add Card')
        self.addManual_button.clicked.connect(self.addCard)
        self.addManual_close = QtGui.QPushButton('Close')
        self.addManual_close.clicked.connect(self.closeManual)
        self.deckManualLayout.addWidget(self.addManual_button,1,4)
        self.deckManualLayout.addWidget(self.addManual_close,0,4)
        self.pricePreview=QtGui.QLabel('')        
        self.deckManualLayout.addWidget(self.lineEdit,1,1,1,3)

        self.deckManualLayout.addWidget(self.pricePreview,0,0,1,3)
        self.setGeometry(400, 400, 350, 75)
        self.setWindowTitle('Manually Enter Card')
        self.setLayout(self.deckManualLayout)
    def onChanged(self,text):
        workingCard = str(text)
        workingCard = workingCard.replace('}','')
        workingCard = workingCard.split(' {')
        if len(workingCard)>1:
            self.workingCardName=workingCard[0]
            self.workingSetName=workingCard[1]
            for rows in priceList:
                if self.workingCardName==rows[0] and self.workingSetName==rows[1]:
                    self.pricePreview.setText(self.workingCardName+' {'+self.workingSetName+'} : '+get_prices(self.workingCardName,self.workingSetName))
    
    def closeManual(self):
        global dialogOpen
        dialogOpen=False
        self.close()
    
    def addCard(self):
        global workingInventory
        global dialogOpen
        global updatedManually
        try:
            workingInventory.append([self.workingCardName, self.workingSetName, False, get_prices(self.workingCardName,self.workingSetName)])
            updatedManually=True
        except AttributeError:
            pass
        
class deckListDialog(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self)
        self.setup_decklistGUI()
        
    def setup_decklistGUI(self):
        global workingInventory
        global decklist
        self.setWindowIcon(QtGui.QIcon('Database\Misc\Icon.png'))
        self.setWindowFlags(QtCore.Qt.CustomizeWindowHint)
        self.headerFont = QtGui.QFont()
        self.headerFont.setUnderline(True)
        self.deckListGrid = QtGui.QGridLayout()
        self.deckListCardNameHeader = QtGui.QLabel('Card Name')
        self.deckListCardNameHeader.setAlignment(QtCore.Qt.AlignCenter)
        self.deckListCardNameHeader.setFont(self.headerFont)
        self.deckListCardNameHeader.setMinimumWidth(100)
        self.deckListQuantityHeader = QtGui.QLabel('Quantity')
        self.deckListQuantityHeader.setAlignment(QtCore.Qt.AlignCenter)
        self.deckListQuantityHeader.setFont(self.headerFont)
        self.deckListQuantityHeader.setMinimumWidth(100)
        self.deckListGrid.addWidget(self.deckListCardNameHeader,0,0)        
        self.deckListGrid.addWidget(self.deckListQuantityHeader,0,1)
        #Consolidate Decklist
        for rows in workingInventory:
            found=False
            for rows2 in decklist:
                if rows[0]==rows2[0]:
                    rows2[1]+=1
                    found=True
                    break
            if found==False:
                decklist.append([rows[0],1])
        for rows in range(len(decklist)):
            self.deckListGrid.addWidget(QtGui.QLabel(decklist[rows][0]),rows+1,0)
            self.quantity = QtGui.QLabel(str(decklist[rows][1]))
            self.quantity.setAlignment(QtCore.Qt.AlignCenter)
            self.deckListGrid.addWidget(self.quantity,rows+1,1)
            plusButton = QtGui.QPushButton('+')
            plusButton.clicked.connect(self.deckListButtons)
            plusButton.setMaximumWidth(35)
            self.deckListGrid.addWidget(plusButton,rows+1,2)
            minusButton = QtGui.QPushButton('-')
            minusButton.clicked.connect(self.deckListButtons)
            minusButton.setMaximumWidth(35)
            self.deckListGrid.addWidget(minusButton,rows+1,3)
        exportButton = QtGui.QPushButton('OK')
        exportButton.clicked.connect(self.showDecklist)
        self.deckListGrid.addWidget(exportButton,rows+2,0,1,3)
        #self.deckListGrid.addStretch(1)
        #self.setGeometry(100, 100, 400, 500)
        self.setWindowTitle('Card Scryer')  
        self.setLayout(self.deckListGrid)
    def showDecklist(self):
        global decklist
        #Clear window
        for cnt in range(0,len(decklist)+2):
            for col in range(4):
                try:
                    widget = self.deckListGrid.itemAtPosition(cnt,col).widget()
                except AttributeError:
                    pass
                if widget is not None: 
                    widget.deleteLater()
        self.textEdit = QtGui.QPlainTextEdit()
        for rows in decklist:
            for cardCount in range(rows[1]):
                self.textEdit.insertPlainText('[['+rows[0]+']]\n')
        self.deckListGrid.addWidget(self.textEdit,1,0,8,3)
        quitDeckListButton = QtGui.QPushButton('Return to Scanner')
        quitDeckListButton.clicked.connect(self.quitDecklist)
        self.deckListGrid.addWidget(quitDeckListButton,9,0,1,3)
    def quitDecklist(self):
        global decklist
        global dialogOpen
        dialogOpen=False
        decklist=[]
        self.close()
    def deckListButtons(self):
        global decklist
        button = self.sender()
        idx = self.deckListGrid.indexOf(button)
        location = self.deckListGrid.getItemPosition(idx)
        decklist[location[0]-1][1]=decklist[location[0]-1][1]+1 if location[1]==2 else decklist[location[0]-1][1]-1
        widget = self.deckListGrid.itemAtPosition(location[0],1).widget()
        widget.setText(str(decklist[location[0]-1][1]))

class MainApp(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.video_size = QtCore.QSize(vidWidth, vidHeight)
        self.setup_ui()
        self.setup_camera()     
    def setup_ui(self):
        global cardHashes
        global priceList
        global setPics

        cardHashes,priceList=init_db()
        
        self.setWindowIcon(QtGui.QIcon('Database\Misc\Icon.png'))
        self.video_feed = QtGui.QLabel()
        self.video_feed.setMinimumSize(175,200)
        self.video_tools = QtGui.QGridLayout()
        self.undo_button = QtGui.QPushButton("Undo")
        self.undo_button.clicked.connect(self.undoButton)
        self.about_button = QtGui.QPushButton("About")
        self.about_button.clicked.connect(self.aboutButton)
        self.switchDevice_button = QtGui.QPushButton("Switch Video Input")
        self.switchDevice_button.clicked.connect(self.change_camera)
        self.foil_button = QtGui.QPushButton("Foil Last")
        self.foil_button.clicked.connect(self.foilButton)
        self.sleeve_button = QtGui.QCheckBox("Sleeved?")
        self.save_button = QtGui.QPushButton("Save Inventory")
        self.save_button.clicked.connect(self.saveButton)
        self.decklist_button = QtGui.QPushButton("Export as Decklist")
        self.decklist_button.clicked.connect(self.decklistButton)
        self.HFlip_button = QtGui.QCheckBox("Flip Horizontally") 
        self.VFlip_button = QtGui.QCheckBox("Mirror Vertically")
        self.contours_button = QtGui.QCheckBox("View Contours")
        self.manual_button = QtGui.QPushButton("Enter Card Name")
        self.manual_button.clicked.connect(self.manualEntryButton)
        self.quit_button = QtGui.QPushButton("Quit")
        self.quit_button.clicked.connect(self.close)
        self.saved_cards = QtGui.QLabel(str(inventory_tally())+' Cards saved to inventory')
        self.unsaved_cards = QtGui.QLabel(str(len(workingInventory))+' Scanned cards waiting to be saved')

        self.video_tools.addWidget(self.undo_button,0,1)
        self.video_tools.addWidget(self.foil_button,0,0)
        self.video_tools.addWidget(self.save_button,1,0)
        self.video_tools.addWidget(self.decklist_button,1,1)
        self.video_tools.addWidget(self.contours_button,2,0) 
        self.video_tools.addWidget(self.sleeve_button,2,1)
        self.video_tools.addWidget(self.HFlip_button,3,0)
        self.video_tools.addWidget(self.VFlip_button,3,1)
        self.video_tools.addWidget(self.about_button,4,0)
        self.video_tools.addWidget(self.switchDevice_button,4,1)
        self.video_tools.addWidget(self.manual_button,5,0)
        self.video_tools.addWidget(self.quit_button,5,1)
        self.video_tools.addWidget(self.saved_cards,6,0,1,2)
        self.video_tools.addWidget(self.unsaved_cards,7,0,1,2)
        
        self.history_layout = QtGui.QVBoxLayout()
        priceHeader = QtGui.QLabel('MTG Price data provided by: <a href="http://www.mtgprice.com">MTGPrice.com</a>')
        priceHeader.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse);
        priceHeader.setOpenExternalLinks(True);
        self.history_layout.addWidget(priceHeader)
        
        self.right_parent = QtGui.QVBoxLayout()
        self.right_parent.addStretch(1)
        self.right_parent.addLayout(self.history_layout)
        self.updateHistory()
        self.right_parent.addStretch(2)        
        self.right_parent.addLayout(self.video_tools)
        self.right_parent.addStretch(1) 
        self.right_parent_widget = QtGui.QWidget()
        self.right_parent_widget.setLayout(self.right_parent)
        self.right_parent_widget.setMaximumWidth(300)

        self.left_parent = QtGui.QVBoxLayout()        
        self.left_parent.addWidget(self.video_feed)
        
        self.horizontal_parent = QtGui.QHBoxLayout()
        self.horizontal_parent.addLayout(self.left_parent)
        self.horizontal_parent.addWidget(self.right_parent_widget)

        self.setGeometry(100, 100, 1200, 700)
        self.setWindowTitle('Card Scryer')
        self.setLayout(self.horizontal_parent)
        
    def keyPressEvent(self, event):
        global currentPick
        global setMatches
        global cardName
        global setName
        global foundCard
        global findCard
        global dst
        global price
        if event.key()==QtCore.Qt.Key_Left:
            currentPick=currentPick-1 if currentPick>0 else len(setMatches)-1
            price=None
            for rows in priceList:
                if cardName==rows[0] and setMatches[currentPick][1]==rows[1]:
                    price = rows[2]
                    break                       
        elif event.key()==QtCore.Qt.Key_Right:
            currentPick=currentPick+1 if currentPick!=len(setMatches)-1 else 0
            price=None
            for rows in priceList:
                if cardName==rows[0] and setMatches[currentPick][1]==rows[1]:
                    price = rows[2]
                    break              
        elif event.key()==QtCore.Qt.Key_Space:
            if foundCard==True:
                setName=setMatches[currentPick][1] if len(setMatches)>0 else ''
                print cardName, setName
                dst=np.zeros((tarWidth, tarHeight, 3),dtype=np.uint8)
                findCard=False
                foundCard=False 
                workingInventory.append([cardName, setName, False, price])   
                self.updateHistory()
                self.unsaved_cards.setText(str(len(workingInventory))+' Scanned cards waiting to be saved')
            elif findCard==False:
                findCard=True
        elif event.key()==QtCore.Qt.Key_Escape:
            if foundCard==True:
                foundCard=False
                findCard=False
        else:
            QtGui.QWidget.keyPressEvent(self, event)
            print event.key()            
    def setup_camera(self):
        self.capture = cv2.VideoCapture(videoDeviceNumber)
        self.capture.set(3, self.video_size.width())
        self.capture.set(4, self.video_size.height())
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.display_video_stream)
        self.timer.start(30)
    def change_camera(self):
        self.capture.release()
        global videoDeviceNumber
        videoDeviceNumber+=1
        self.capture = cv2.VideoCapture(videoDeviceNumber)
        if self.capture.isOpened():
            pass
        else:
            videoDeviceNumber=0
            self.capture = cv2.VideoCapture(videoDeviceNumber)
        self.capture.set(3, self.video_size.width())
        self.capture.set(4, self.video_size.height())
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.display_video_stream)
        self.timer.start(30)

    def display_video_stream(self):
        global foundCard
        global findCard
        global dst
        global currentPick
        global foil
        global price
        global cardName
        global setMatches
        global priceList
        global hull
        global botLeft
        global decklist
        global dialogOpen
        global dialogOpen
        global updatedManually
        
        if dialogOpen==False: #Get keyboard input when not editing decklists
            self.video_feed.grabKeyboard()
          
        _, frame = self.capture.read()
        if self.HFlip_button.isChecked():
            frame = cv2.flip(frame,0)
        if self.VFlip_button.isChecked():
            frame = cv2.flip(frame,1)
             
        if findCard==True:         
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,15,7)
            gray = cv2.dilate(gray,np.ones((3,3),np.uint8),iterations = 1)
            edges = cv2.Canny(gray,100,200)
            image, contours, hierarchy = cv2.findContours(edges,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)  
            if len(contours)>=1:  
                for cnt in range(len(contours)):
                    if cv2.contourArea(contours[cnt],False)>10000 and cv2.arcLength(contours[cnt],False)>400 and (cv2.contourArea(contours[cnt],False)/cv2.arcLength(contours[cnt],False))>30:
                        hull = contours[cnt] 
                        poly = cv2.approxPolyDP(hull,0.05*cv2.arcLength(hull,True),True) 
                        if len(poly)==4:
                            poly = poly[:,0][poly[:,0][:,1].argsort()]
                            p1 = (poly[0][0],poly[0][1])
                            p2 = (poly[1][0],poly[1][1])
                            p3 = (poly[2][0],poly[2][1])
                            p4 = (poly[3][0],poly[3][1])
                            [topLeft, topRight, botLeft, botRight] = get_perspective(p1,p2,p3,p4)
                            pts1 = np.float32([topLeft,topRight,botLeft,botRight])
                            pts2 = np.float32([[0,0],[tarWidth,0],[0,tarHeight],[tarWidth,tarHeight]])
                            M = cv2.getPerspectiveTransform(pts1,pts2)
                            dst = cv2.warpPerspective(frame,M,(tarWidth,tarHeight))
                            artCrop=dst[artY1:artY2,artX1:artX2] if self.sleeve_button.isChecked()==False else dst[artSleeveY1:artSleeveY2,artSleeveX1:artSleeveX2]
                            artHash = imagehash.phash(Image.fromarray(artCrop))
                            

                            for rows in range(len(cardHashes)):
                                cardHashes[rows][3]=(artHash-cardHashes[rows][2]) 
                            topMatches = sorted(cardHashes, key=itemgetter(3))[0:15]
                            setMatches = []
                            if topMatches[0][0]=='Upgrade to Full':
                                fit = topMatches[0][3]
                                for rows in topMatches:
                                    if rows[0]!='Upgrade to Full' and rows[3]<(fit+4):
                                        cardName=rows[0]
                                    else:
                                        cardName='Upgrade to Full'
                            else:
                                cardName=topMatches[0][0]
                            if cardName!='Upgrade to Full':
                                for rows in topMatches:
                                    if rows[0]==cardName:
                                        setMatches.append(rows)
                                setMatches = sorted(setMatches, key=itemgetter(2))
                                      
                            #Re-Initialize Dummy Variables
                            currentPick=0    
                            findCard=False
                            foundCard=True
                        
        elif self.contours_button.isChecked():   
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,15,7)
            gray = cv2.dilate(gray,np.ones((3,3),np.uint8),iterations = 1)
            edges = cv2.Canny(gray,100,200)
            image, contours, hierarchy = cv2.findContours(edges,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)  
            cv2.drawContours(frame,contours,-1,(50,50,255),1,lineType = cv2.LINE_AA)

        if foundCard==True:
            if setMatches!=[]:
                setName=setMatches[currentPick][1]
                price=get_prices(cardName,setName)    
            else: 
                price=''  
                setName=''                     
            cv2.drawContours(frame,hull,-1,(50,255,50),2,lineType = cv2.LINE_AA)
            textSize = cv2.getTextSize(cardName+' '+price, cv2.FONT_HERSHEY_SIMPLEX, 1,1)
            cv2.rectangle(frame, (botLeft[0]-25,botLeft[1]-15), (botLeft[0]-25+textSize[0][0],botLeft[1]-47), (255,255,255), -1, lineType=cv2.LINE_AA)
            cv2.putText(frame, cardName+' '+price, (botLeft[0]-23,botLeft[1]-20), cv2.FONT_HERSHEY_SIMPLEX, 1, 0, 1, lineType = cv2.LINE_AA)
            for sets in range(len(setMatches)):
                icon = cv2.imread('Database\SetArt\\'+setMatches[sets][1]+'.png')
                if sets==currentPick:
                    icon[:,:,0:1]=icon[:,:,0:1]/10
                icY, icX = np.shape(icon)[:2]
                try:
                    frame[botLeft[1]-10:botLeft[1]-(10-icY),botLeft[0]-25+sets*40:botLeft[0]-25+sets*40+icX]=icon
                except ValueError:
                    foundCard=False
                    
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        qLabelWidth = self.video_feed.width()
        qLabelHeight = self.video_feed.height()
        if qLabelWidth>int(qLabelHeight*(float(vidWidth)/vidHeight)):
            frame = cv2.resize(frame, (int(qLabelHeight*(float(vidWidth)/vidHeight)), qLabelHeight), interpolation=cv2.INTER_AREA)
        else:
            frame = cv2.resize(frame, (qLabelWidth,int(qLabelWidth/(float(vidWidth)/vidHeight))), interpolation=cv2.INTER_AREA)

        image = QtGui.QImage(frame, frame.shape[1], frame.shape[0], frame.strides[0], QtGui.QImage.Format_RGB888)
        self.video_feed.setPixmap(QtGui.QPixmap.fromImage(image))
        
        if updatedManually==True:
            self.updateHistory()
            updatedManually=False
    
    def updateHistory(self):
        global workingInventory
        [self.history_layout.addWidget(QtGui.QLabel('-')) for x in range(9)]
        for rows in workingInventory:
            historyText = (rows[0]+' | '+rows[1]+' | '+get_prices(rows[0],rows[1])) if rows[2]==False else (rows[0]+' (Foil) | '+rows[1]+' | '+get_prices(rows[0],rows[1]))
            self.history_layout.addWidget(QtGui.QLabel(historyText))
        while(self.history_layout.count()>10):
            widget = self.history_layout.takeAt(1).widget()
            if widget is not None: 
                widget.deleteLater()                          
    def undoButton(self):
        global workingInventory
        workingInventory=workingInventory[:-1]
        self.updateHistory()
        self.unsaved_cards.setText(str(len(workingInventory))+' Scanned cards waiting to be saved')
    def foilButton(self):
        global workingInventory
        if len(workingInventory)>0:
            workingInventory[len(workingInventory)-1][2]=True
        self.updateHistory()
    def aboutButton(self):
        self.dialogInfo = infoDialog()
        self.dialogInfo.exec_()
    def saveButton(self):
        global workingInventory
        global inventory
        for rows in workingInventory:
            if rows[0]!='Upgrade to Full':
                inventory = add_card(rows[0],rows[1],str(rows[2]))
        df_writer = pd.DataFrame(inventory, columns=['Card Name','Set','Foil','Quantity','Price'])
        df_writer.to_csv(inventoryPath,index=False)
        workingInventory = []
        self.saved_cards.setText(str(inventory_tally())+' Cards saved to inventory')
        self.unsaved_cards.setText(str(len(workingInventory))+' Scanned cards waiting to be saved')
        self.updateHistory()
    def decklistButton(self):
        global workingInventory
        if len(workingInventory)>0:
            global dialogOpen
            dialogOpen = True
            self.video_feed.releaseKeyboard()
            self.dialog = deckListDialog()
            self.dialog.exec_()
    def manualEntryButton(self):
        global dialogOpen
        dialogOpen=True
        self.video_feed.releaseKeyboard()
        self.dialog = manualEntryDialog()
        self.dialog.exec_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    win = MainApp()
    win.show()
    sys.exit(app.exec_())
    
#sys.stderr.close()
#sys.stderr = sys.__stderr__