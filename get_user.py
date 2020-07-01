import pyrebase
from imutils.video import VideoStream
from imutils.video import FPS
import numpy as np
import argparse
import imutils
import pickle
import time
import cv2
import os
import time
import json
import datetime

#config firebase
firebaseConfig = {
    "apiKey": "AIzaSyBAh2EGtDNhuOP9LF5jw0ViBPmWH71OaMo",
    "authDomain": "raspberry-face-recognition.firebaseapp.com",
    "databaseURL": "https://raspberry-face-recognition.firebaseio.com",
    "projectId": "raspberry-face-recognition",
    "storageBucket": "raspberry-face-recognition.appspot.com",
    "messagingSenderId": "469377065466",
    "appId": "1:469377065466:web:cfe2c3c3933e76c1958443",
    "measurementId": "G-WQVN4Q38MH"
}

firebase = pyrebase.initialize_app(firebaseConfig)
db = firebase.database()
def swap(a, b):
    temp = a
    a = b
    b =temp

num_list = []


users = db.child("Checkout").get()

# if users:
for user in users.each():
    num_list.append(user.val())
#sort by name (Ascending order)
num_list.sort(key=lambda x: x['time'], reverse=True)
for user in num_list:
 print(user["time"])