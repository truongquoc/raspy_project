# USAGE
# python recognize_video.py --detector face_detection_model --embedding-model openface_nn4.small2.v1.t7 --recognizer output/recognizer.pickle --le output/le.pickle

# import the necessary packages
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


#config local reference path
firebase = pyrebase.initialize_app(firebaseConfig)
db = firebase.database()


storage = firebase.storage()
path_on_cloud = "checkin/foo.jpg"
path_local = "images/frame.jpg"
# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-d", "--detector", required=True,
	help="path to OpenCV's deep learning face detector")
ap.add_argument("-m", "--embedding-model", required=True,
	help="path to OpenCV's deep learning face embedding model")
ap.add_argument("-r", "--recognizer", required=True,
	help="path to model trained to recognize faces")
ap.add_argument("-l", "--le", required=True,
	help="path to label encoder")
ap.add_argument("-c", "--confidence", type=float, default=0.5,
	help="minimum probability to filter weak detections")
args = vars(ap.parse_args())

#convert time function
def converttime(o):
  if isinstance(o, datetime.datetime):
        return o.__str__()
# load our serialized face detector from disk


# load our serialized face detector from disk
print("[INFO] loading face detector...")
protoPath = os.path.sep.join([args["detector"], "deploy.prototxt"])
modelPath = os.path.sep.join([args["detector"],
	"res10_300x300_ssd_iter_140000.caffemodel"])
detector = cv2.dnn.readNetFromCaffe(protoPath, modelPath)

# load our serialized face embedding model from disk
print("[INFO] loading face recognizer...")
embedder = cv2.dnn.readNetFromTorch(args["embedding_model"])

# load the actual face recognition model along with the label encoder
recognizer = pickle.loads(open(args["recognizer"], "rb").read())
le = pickle.loads(open(args["le"], "rb").read())

# initialize the video stream, then allow the camera sensor to warm up
print("[INFO] starting video stream...")
vs = VideoStream(src=0).start()
time.sleep(2.0)

# start the FPS throughput estimator
fps = FPS().start()

# loop over frames from the video file stream
count  =0
check =0
while True:
	# grab the frame from the threaded video stream
    state = True
    count = count +1
    print("count",count)
    frame = vs.read()
    frame = imutils.resize(frame, width=600)
    cv2.imwrite("images/frame.jpg", frame)  # save frame as JPEG file
    (h, w) = frame.shape[:2]
    # construct a blob from the image
    imageBlob = cv2.dnn.blobFromImage(
		cv2.resize(frame, (300, 300)), 1.0, (300, 300),
		(104.0, 177.0, 123.0), swapRB=False, crop=False)

	# apply OpenCV's deep learning-based face detector to localize
	# faces in the input image
    detector.setInput(imageBlob)
    detections = detector.forward()

    # loop over the detections
    for i in range(0, detections.shape[2]):
		# extract the confidence (i.e., probability) associated with
		# the prediction
        confidence = detections[0, 0, i, 2]
        # filter out weak detections
        if confidence > args["confidence"]:
			# compute the (x, y)-coordinates of the bounding box for
			# the face
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")
			# extract the face ROI
            face = frame[startY:endY, startX:endX]
            (fH, fW) = face.shape[:2]

			# ensure the face width and height are sufficiently large
            if fW < 20 or fH < 20:
                continue
			# construct a blob for the face ROI, then pass the blob
			# through our face embedding model to obtain the 128-d
			# quantification of the face
            faceBlob = cv2.dnn.blobFromImage(face, 1.0 / 255,
				(96, 96), (0, 0, 0), swapRB=True, crop=False)
            embedder.setInput(faceBlob)
            vec = embedder.forward()

			# perform classification to recognize the face
            preds = recognizer.predict_proba(vec)[0]
            j = np.argmax(preds)
            proba = preds[j]
            name = le.classes_[j]
            if count > 10:
                check = 0
                count = 0;
            if proba < 0.9 :
                name = 'unknown'
                print(name)
                continue
            else:
                check+=1
            if check==8:
                path_image = storage.child('checkin/foo.jpg').get_url(None)
                storage.child(path_on_cloud).put(path_local)
                data = {};
                users = db.child("Checkout").get()
                num_list = []
                for user in users.each():
                    num_list.append(user.val())
                # sort by name (Ascending order)
                num_list.sort(key=lambda x: x['time'], reverse=True)
                if num_list:
                    for user in num_list:
                       if user["name"] == name and user["checkout"] == False:
                          state = False
                          data = {"name": name, "time": json.dumps(datetime.datetime.now(), default=converttime), "url": path_image, "checkout": True, "checkin": user["time"]}
                          break
                       if user["name"] == name and user["checkout"] == True:
                          state = True
                          break
                if state:
                    data = {"name": name, "time": json.dumps(datetime.datetime.now(), default=converttime),
                                  "url": path_image, "checkout": False}
                db.child("Checkout").push(data)
                print("uploaded successfully")
                check = 0
                count = 0

			# draw the bounding box of the face along with the
			# associated probability
            print(name)
            text = "{}: {:.2f}%".format(name, proba * 100)
            y = startY - 10 if startY - 10 > 10 else startY + 10
            cv2.rectangle(frame, (startX, startY), (endX, endY),
				(0, 0, 255), 2)
            cv2.putText(frame, text, (startX, y),
				cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2)

	# update the FPS counter
    fps.update()
    d = {}
    d['date'] = datetime.datetime.now()
    print(json.dumps(d, default=converttime))
	# show the output frame
    cv2.imshow("Frame", frame)
    key = cv2.waitKey(1) & 0xFF
    time.sleep(1)
	# if the `q` key was pressed, break from the loop
    if key == ord("q"):
        break

# stop the timer and display FPS information
fps.stop()
print("[INFO] elasped time: {:.2f}".format(fps.elapsed()))
print("[INFO] approx. FPS: {:.2f}".format(fps.fps()))

# do a bit of cleanup
cv2.destroyAllWindows()
vs.stop()