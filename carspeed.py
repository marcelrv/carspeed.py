# Speed Version 2.0

# hacked version to use ipcamera stream instead of the picamera

# changes by KirkLoeten (GITHUB)
# paramter for function [cv2.findContours ] form 3 to 2 - cnts, _
# Functions:
# Selector image 0 - off, 0 > speedlimit
# Selector csv 0 - off, 0 > speedlimit
# Selector of units m / ft -> kmh / mph
# read setup monitored area by setup.txt file, write a new file by use 'c' in setup
# Generate new CSV at new Day
# generate folders per Day
# Nice to have: set central text color for all images

# import the necessary packages
import time
import math
import datetime
import os
import cv2  # sudo apt-get install libopencv-dev python-opencv


# place a prompt on the displayed image
def prompt_on_image(txt):
    global image
    cv2.putText(image, txt, (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 127, 1))


# calculate speed from pixels and time
def get_speed(pixels, ftperpixel, secs):
    if secs > 0.0:
        if SPEED_UNIT == "mph":
            return ((pixels * unit_perpixel) / secs) * 0.681818
        else:
            # m/s to km/h
            return ((pixels * unit_perpixel) / secs) * 3.6
    else:
        return 0.0


# calculate elapsed seconds
def secs_diff(endTime, begTime):
    diff = (endTime - begTime).total_seconds()
    return diff


# record speed in .csv format
def record_speed(res):
    global csvfileout
    f = open(csvfileout, 'a')
    f.write(res + "\n")
    f.close


# mouse callback function for drawing capture area
def draw_rectangle(event, x, y, flags, param):
    global ix, iy, fx, fy, drawing, setup_complete, image, org_image, prompt

    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        ix, iy = x, y

    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing == True:
            image = org_image.copy()
            prompt_on_image(prompt)
            cv2.rectangle(image, (ix, iy), (x, y), (0, 255, 0), 2)

    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        fx, fy = x, y
        image = org_image.copy()
        prompt_on_image(prompt)
        cv2.rectangle(image, (ix, iy), (fx, fy), (0, 255, 0), 2)


# define some constants, selectors
DISTANCE = 10  # <---- enter your distance-to-road value here
SAVE_CSV = 5  # 0 is off, >0 is the speedlimit, record the results in .csv format in speed_(date).csv
SAVE_IMAGE = 5  # 0 is off, >0 is the speedlimit, no image as privaty setup
LEN_UNIT = "m"  # "ft" or "m" (mph or km/h is selected automaticly by this constant)

VIDEOSTREAM_URL = 'rtsp://192.168.3.144:8554/unicast'
rawCapture = cv2.VideoCapture(VIDEOSTREAM_URL, cv2.CAP_FFMPEG)

#ret, image = rawCapture.read()
w = int(rawCapture.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(rawCapture.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = int(rawCapture.get(cv2.CAP_PROP_FPS))

# picture and difference parameter
THRESHOLD = 50  # 15
MIN_AREA = 175
BLURSIZE = (15, 15)
IMAGEWIDTH = w
IMAGEHEIGHT = h
RESOLUTION = [IMAGEWIDTH, IMAGEHEIGHT]
FOV = 53.5  # <---- Field of view
FPS = fps
SHOW_BOUNDS = False
SHOW_IMAGE = False
WINDOW_ID = 'Speed Camera'

if LEN_UNIT.upper() == "ft".upper():  # ignore case, compare string upper letters
    SPEED_UNIT = "mph"
else:
    SPEED_UNIT = "km/h"

# the following enumerated values are used to make the program more readable
# state
WAITING = 0
TRACKING = 1
SAVING = 2
# dicection
UNKNOWN = 0
LEFT_TO_RIGHT = 1
RIGHT_TO_LEFT = 2

# calculate the the width of the image at the distance specified
frame_width_unit = 2 * (math.tan(math.radians(FOV * 0.5)) * DISTANCE)
unit_perpixel = frame_width_unit / float(IMAGEWIDTH)
print("Image width in {} {} at {} {} from camera".format("%.0f" % frame_width_unit, LEN_UNIT, "%.0f" % DISTANCE,
                                                         LEN_UNIT))

# state maintains the state of the speed computation process
# if starts as WAITING
# the first motion detected sets it to TRACKING

# if it is tracking and no motion is found or the x value moves
# out of bounds, state is set to SAVING and the speed of the object
# is calculated
# initial_x holds the x value when motion was first detected
# last_x holds the last x value before tracking was was halted
# depending upon the direction of travel, the front of the
# vehicle is either at x, or at x+w
# (tracking_end_time - tracking_start_time) is the elapsed time
# from these the speed is calculated and displayed

state = WAITING
direction = UNKNOWN
initial_x = 0
last_x = 0

# -- other values used in program
base_image = None
abs_chg = 0
speed = 0
secs = 0.0
ix, iy = -1, -1
fx, fy = -1, -1
drawing = False
setup_complete = False
tracking = False
text_on_image = 'No motions'
prompt = ''
# initialize the camera. Adjust vflip and hflip to reflect your camera's orientation
# camera = PiCamera()
# camera.resolution = RESOLUTION
# camera.framerate = FPS
# camera.vflip = True
# camera.hflip = True

# rawCapture = PiRGBArray(camera, size=camera.resolution)


# allow the camera to warm up
time.sleep(0.9)

# create an image window and place it in the upper left corner of the screen
cv2.namedWindow(WINDOW_ID)
cv2.moveWindow(WINDOW_ID, 10, 40)

# call the draw_rectangle routines when the mouse is used
cv2.setMouseCallback(WINDOW_ID, draw_rectangle)

# grab a reference image to use for drawing the monitored area's boundry
# camera.capture(rawCapture, format="bgr", use_video_port=True)
# image = rawCapture.array
# rawCapture.truncate(0)
ret, image = rawCapture.read()

org_image = image.copy()

setup_exist = os.path.isfile("setup.txt")
if setup_exist:
    prompt = "Define the monitored area - press 'c' to continue - press 'L' for lastsetup"
else:
    prompt = "Define the monitored area - press 'c' to continue"
# test for setup.txt file
prompt_on_image(prompt)

# wait while the user draws the monitored area's boundry
while not setup_complete:
    cv2.imshow(WINDOW_ID, image)

    # wait for for c to be pressed
    key = cv2.waitKey(1) & 0xFF

    # if the `c` key is pressed, break from the loop
    if key == ord("c"):
        break

    # if the `l` key is pressed, use last setup
    if (key == ord("L") or key == ord("l")) and setup_exist:
        with open("setup.txt", 'r') as f:
            setup_txt = f.readlines()
            f.close()
            for line in setup_txt:
                line = line.strip()
                line = line.split("=")
                if line[0] == "ix":
                    ix = int(line[1])
                if line[0] == "iy":
                    iy = int(line[1])
                if line[0] == "fx":
                    fx = int(line[1])
                if line[0] == "fy":
                    fy = int(line[1])
        break

# the monitored area is defined, time to move on
prompt = "Press 'q' to quit"
prompt_on_image(prompt)
# since the monitored area's bounding box could be drawn starting
# from any corner, normalize the coordinates

if fx > ix:
    upper_left_x = ix
    lower_right_x = fx
else:
    upper_left_x = fx
    lower_right_x = ix

if fy > iy:
    upper_left_y = iy
    lower_right_y = fy
else:
    upper_left_y = fy
    lower_right_y = iy

monitored_width = lower_right_x - upper_left_x
monitored_height = lower_right_y - upper_left_y

print("Monitored area:")
print(" upper_left_x {} px".format(upper_left_x))
print(" upper_left_y {} px".format(upper_left_y))
print(" lower_right_x {} px".format(lower_right_x))
print(" lower_right_y {} px".format(lower_right_y))
print(" monitored_width {0:d} px ({1:.2f} {2:s})".format(monitored_width, frame_width_unit, LEN_UNIT))
print(" monitored_height {} px".format(monitored_height))
print(" monitored_area {} px".format(monitored_width * monitored_height))

# save setup
if monitored_width > 10 and monitored_height > 10:
    with open("setup.txt", 'w') as f:
        f.write("ix=" + str(upper_left_x) + "\n")
        f.write("iy=" + str(upper_left_y) + "\n")
        f.write("fx=" + str(lower_right_x) + "\n")
        f.write("fy=" + str(lower_right_y) + "\n")
        f.close()

    # capture frames from the camera (using capture_continuous.
#   This keeps the picamera in capture mode - it doesn't need
#   to prep for each frame's capture.

# for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
dropCounter = 0
imgCounter = 0
newImage= image.copy()
while True:
    # initialize the timestamp
    timestamp = datetime.datetime.now()

    # grab the raw NumPy array representing the image
    #    image = frame.array
    # image = frame.array
    ret, image = rawCapture.read()
    if ret is False:
        print("Capture resulted in ", ret)
        dropCounter += 1
        if dropCounter > 120:
            break
        continue
    dropCounter = 0
    imgCounter += 1
    if (imgCounter % (FPS * 5)) == 0:
        print("Capture #", imgCounter, datetime.datetime.now(), state)
        # periodically refresh the screen, but only if we're waiting
        if state == WAITING:
            cv2.imshow(WINDOW_ID, image)

    # crop area defined by [y1:y2,x1:x2]
    gray = image[upper_left_y:lower_right_y, upper_left_x:lower_right_x]

    # convert the fram to grayscale, and blur it
    gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, BLURSIZE, 0)

    # if the base image has not been defined, initialize it
    if base_image is None:
        base_image = gray.copy().astype("float")
        lastTime = timestamp
        #        rawCapture.truncate(0)
        cv2.imshow(WINDOW_ID, image)

    # compute the absolute difference between the current image and
    # base image and then turn eveything lighter gray than THRESHOLD into
    # white
    frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(base_image))
    thresh = cv2.threshold(frameDelta, THRESHOLD, 255, cv2.THRESH_BINARY)[1]

    # dilate the thresholded image to fill in any holes, then find contours
    # on thresholded image
    thresh = cv2.dilate(thresh, None, iterations=2)
    cnts, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # look for motion
    motion_found = False
    biggest_area = 0

    # examine the contours, looking for the largest one
    for c in cnts:
        (x1, y1, w1, h1) = cv2.boundingRect(c)
        # get an approximate area of the contour
        found_area = w1 * h1
        # find the largest bounding rectangle
        if (found_area > MIN_AREA) and (found_area > biggest_area):
            biggest_area = found_area
            motion_found = True
            x = x1
            y = y1
            h = h1
            w = w1

    if motion_found:
        if state == WAITING:
            # intialize tracking
            state = TRACKING
            initial_x = x
            last_x = x
            initial_time = timestamp
            last_speed = 0
            text_on_image = 'Tracking'
            print(text_on_image)
            print("x-chg    Secs       {} dir  x-pos width".format(SPEED_UNIT))
            newImage= image.copy()
        else:
            # compute the lapsed time
            secs = secs_diff(timestamp, initial_time)

            if secs >= 15:
                state = WAITING
                direction = UNKNOWN
                text_on_image = 'No motion detected'
                motion_found = False
                biggest_area = 0
                #                rawCapture.truncate(0)
                base_image = None
                print('Resetting')
                cv2.imshow(WINDOW_ID, newImage)
                continue


            if state == TRACKING:
                if x >= last_x:
                    direction = LEFT_TO_RIGHT
                    abs_chg = x + w - initial_x
                else:
                    direction = RIGHT_TO_LEFT
                    abs_chg = initial_x - x
                speed = get_speed(abs_chg, unit_perpixel, secs)

                print("{0:4d}  {1:7.2f}  {2:7.0f}    {3:1d}  {4:4d}  {5:4d}".format(abs_chg, secs, speed, direction, x,
                                                                                    w))
                real_y = upper_left_y + y
                real_x = upper_left_x + x
                # is front of object outside the monitired boundary? Then write date, time and speed on image
                # and save it
                if ((x <= 2) and (direction == RIGHT_TO_LEFT)) \
                        or ((x + w >= monitored_width - 2) and (direction == LEFT_TO_RIGHT)):
                    if last_speed > SAVE_CSV or last_speed > SAVE_IMAGE:  # save the image
                        # timestamp the image
                        cv2.putText(image, timestamp.strftime("%A %d %B %Y %H:%M:%S"),
                                    (10, image.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 127), 1)
                        # write the speed: first get the size of the text
                        size, base = cv2.getTextSize("{0:.0f} {1:s}".format(last_speed, SPEED_UNIT),
                                                     cv2.FONT_HERSHEY_SIMPLEX, 2, 3)
                        # then center it horizontally on the image
                        cntr_x = int((IMAGEWIDTH - size[0]) / 2)
                        cv2.putText(image, "{0:.0f} {1:s}".format(last_speed, SPEED_UNIT),
                                    (cntr_x, int(IMAGEHEIGHT * 0.2)), cv2.FONT_HERSHEY_SIMPLEX, 2.00, (0, 255, 127), 3)
                        # and save to disk
                        # check folder
                        folder = "{}".format(datetime.datetime.now().strftime("%Y%m%d"))
                        if not os.path.exists(folder):
                            os.makedirs(folder)
                            csvfileout = folder + "/speed_{}.cvs".format(timestamp.strftime("%Y%m%d"))
                            record_speed("Date, Time, Speed ({}), Richtung (1>, 2<), Image".format(SPEED_UNIT))
                        else:
                            # Initial
                            csvfileout = folder + "/speed_{}.cvs".format(datetime.datetime.now().strftime("%Y%m%d"))

                        if last_speed > SAVE_IMAGE:
                            imageFilename = folder + "/motion_at_" + timestamp.strftime("%Y%m%d_%H%M%S") + ".jpg"
                            # use the following image file name if you want to be able to sort the images by speed
                            # imageFilename = "motion_at_%02.0f" % last_speed + "_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".jpg"

                            cv2.imwrite(imageFilename, image)
                        else:
                            imageFilename = "No image"
                        if last_speed > SAVE_CSV:
                            record_speed(timestamp.strftime("%Y.%m.%d") + ',' + timestamp.strftime('%H:%M') + ',' + (
                                    "%.0f" % last_speed) + ',' + ("%d" % direction) + ',' + imageFilename)
                    state = SAVING
                # if the object hasn't reached the end of the monitored area, just remember the speed
                # and its last position
                last_speed = speed
                last_x = x
    else:
        if state != WAITING:
            state = WAITING
            direction = UNKNOWN
            text_on_image = 'No motion detected'
            print(text_on_image)

    # only update image and wait for a keypress when waiting for a motion
    # This is required since waitkey slows processing.
    if state == WAITING:

        # draw the text and timestamp on the frame
        cv2.putText(image, datetime.datetime.now().strftime("%A %d %B %Y %H:%M:%S"),
                    (10, image.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 127), 1)
        cv2.putText(image, "Road Status: {}".format(text_on_image), (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 127), 1)

        if SHOW_BOUNDS:
            # define the monitored area right and left boundary
            cv2.line(image, (upper_left_x, upper_left_y), (upper_left_x, lower_right_y), (0, 255, 127))
            cv2.line(image, (lower_right_x, upper_left_y), (lower_right_x, lower_right_y), (0, 255, 127))

        # show the frame and check for a keypress
        if SHOW_IMAGE:
            prompt_on_image(prompt)
            cv2.imshow(WINDOW_ID, image)

        # Adjust the base_image as lighting changes through the day
        if state == WAITING:
            last_x = 0
            cv2.accumulateWeighted(gray, base_image, 0.25)

        state = WAITING
        key = cv2.waitKey(1) & 0xFF

        # if the `q` key is pressed, break from the loop and terminate processing
        if key == ord("q"):
            break

    # clear the stream in preparation for the next frame
    # rawCapture.truncate(0)

# cleanup the camera and close any open windows
cv2.destroyAllWindows()
