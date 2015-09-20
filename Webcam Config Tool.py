# -*- coding: utf-8 -*-
print 'Card Scryer | Copyright (C) 2015 | Blake Anderson'
print 'This program comes with ABSOLUTELY NO WARRANTY.'
print 'This is free software, and you are welcome to redistribute it under certain conditions.'
print 'For details on GNU General Public License 3.0 see: http://www.gnu.org/licenses/'
print ''
print ''

import sys
import cv2
import os 
import csv
import numpy as np
import time

os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))
sys.stderr = open('Error_WebcamConfig.txt','a')

def nothing(x):
    pass
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
    
tarHeight = 680
tarWidth = 480   

try:
    with open(os.path.join('Database','Config.cnf'), 'rb') as csvfile:
        config = csv.reader(csvfile, delimiter=',')
        config = list(config)
    print 'Loading Configuration'
    videoDeviceNumber = int(config[0][1])
    vidWidth = int(config[1][1])
    vidHeight = int(config[2][1])
except IOError: #Load Defaults
    print 'No configuration file found, loading defaults'
    videoDeviceNumber = 0
    vidWidth = 1280
    vidHeight = 720
    inventoryPath = os.path.join('Database','Inventory.csv')
    

Y = raw_input("Change old/default config options (Device/Resolution) [y/n]?  ")

frameArea = float(vidWidth*vidHeight)
framePerimiter = float(vidWidth*2+vidHeight*2)

if Y.upper() == 'Y' or Y.upper() == 'YES':
    videoDeviceNumber = int(raw_input('Enter default video device number (Current is '+str(videoDeviceNumber)+'):  '))
    vidWidth = int(raw_input('Enter horizontal resolution (Current is '+str(vidWidth)+'):  '))  
    vidHeight = int(raw_input('Enter vertical resolution (Current is '+str(vidHeight)+'):  ')) 
    
print 'Using video device '+str(videoDeviceNumber)+', at '+str(vidWidth)+'x'+str(vidHeight)+' resolution.'

print ''
print 'In the following Dialog:'
print "'Kernel' refers to the area used to normalize brightness, its effect changes between even and odd numbers, but changes continually as it increases"
print "'Subtract' refers to the global threshold for binarizing the image for detection, increasing this will reduce interference from glare/lighting but may inhibit detection of weak contrast gradients"
print "Configuration window will now display, Press 'S' to save and exit, and 'Q' to exit, discarding changes"
raw_input("Press ENTER to begin")

cv2.namedWindow('Preview')
cv2.createTrackbar('Kernel','Preview',13,20,nothing)
cv2.createTrackbar('Subtract','Preview',5,30,nothing)

cap = cv2.VideoCapture(videoDeviceNumber)

while cap.isOpened():
    threshKernel = cv2.getTrackbarPos('Kernel','Preview')
    threshKernel = 3+threshKernel*2
    threshSubtract = cv2.getTrackbarPos('Subtract','Preview')
    
    frame = cap.read()[1]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,threshKernel,threshSubtract)
    gray = cv2.dilate(gray,np.ones((3,3),np.uint8),iterations = 1)
    edges = cv2.Canny(gray,100,200)
    image, contours, hierarchy = cv2.findContours(edges,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)     
            
    if len(contours)>=1:  
        for cnt in range(len(contours)):
            area=cv2.contourArea(contours[cnt],False)
            if area/frameArea>0.005:
                perimiter=cv2.arcLength(contours[cnt],False)
                if perimiter/framePerimiter>0.075:
                    if area/perimiter>20:
                        hull = contours[cnt] 
                        poly = cv2.approxPolyDP(hull,0.1*cv2.arcLength(hull,True),True) 
                        if len(poly)==4:
                            poly = poly[:,0][poly[:,0][:,1].argsort()]
                            p1 = (poly[0][0],poly[0][1])
                            p2 = (poly[1][0],poly[1][1])
                            p3 = (poly[2][0],poly[2][1])
                            p4 = (poly[3][0],poly[3][1])
                            [topLeft, topRight, botLeft, botRight] = get_perspective(p1,p2,p3,p4)
                            pts = np.array([topLeft,topRight,botRight,botLeft],np.int32)
                            pts = pts.reshape((-1,1,2))
                            cv2.polylines(frame,[pts],True,(255,0,0),2,lineType=cv2.LINE_AA)
    
    cv2.drawContours(frame,contours,-1,(50,50,255),1,lineType = cv2.LINE_AA)
    cv2.imshow('Preview',frame)

    K=cv2.waitKey(25)
    if K==ord('q') or K==ord('Q'):
        break
    if K==ord('s') or K==ord('S'):
        output=[]
        output.append(['Video Device Number', videoDeviceNumber])
        output.append(['Horizontal Resolution', vidWidth])
        output.append(['Vertical Resolution', vidHeight])
        output.append(['Inventory Path', os.path.join('Database','Inventory.csv')])
        output.append(['GaussianKernel', threshKernel])
        output.append(['GaussianSubtract', threshSubtract])
        
        with open(os.path.join('Database','Config.cnf'), 'wb') as csvfile:
            writer=csv.writer(csvfile)            
            writer.writerows(output)
        break
    
cap.release()
cv2.destroyAllWindows()

print 'Exiting in 5'
time.sleep(5)

    