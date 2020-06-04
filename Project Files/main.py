# Import Libaries
from threading import Timer,Thread,Event
import time
import logging
from PIL import Image
import csv

import numpy as np
import pandas as pd
import statistics

import matplotlib.pyplot as plt

import paho.mqtt.client as mqtt
import mqtt_control
import ifttt_control

from tplink_smartplug import SmartPlug # tp-link api (Refer to "plug/plug_control.py" for usage and MIT licence)

import os.path
from os import system, name

# Stream camera data "data_streaming/server.py"
import sys
sys.path.append('data_streaming')
import server

# Fan power / Wifi - Plug
sys.path.append('plug')
import plug_control # tp-link class "plug/plug_control.py"

# Image Processing
sys.path.append('image_proccessing')
import fire_detection as fd #"image_proccessing/fire_detection.py"

# Handle camera images and run image processing on them
def handle_image(img,save_output = False,console_print=False):
    try:
        if not img == None:
            if save_output:
                #print('- Saving -')
                img.save("output.jpeg")

            # Processing
            if console_print:
                print('- Processing -')
            camera_detection_values = fd.run_fire_detection(img,save_output)
            return camera_detection_values
    except:
        print('Failed to process image')
        return None
    # Nothing
    return None
# --

# Counts down timer, returns if it activates
def alert_handler(message_dict_):
    timer_ = message_dict_['alert_timer']
    if timer_ <= 0: # Timer has gone off, can send
        return timer_, True
    else: # Count down
        timer_ -= 1
    return timer_, False
# --

# Clear screen
def clear_console():
    # Windows
    if name == 'nt':
        _ = system('cls')

    # Mac and linux(here, os.name is 'posix')
    else:
        _ = system('clear')


# Prediction Formula, gives current average of recent as well as a poly estimator to predict outcome
def prediction_calculator(data_dict_,console_print=False):
    '''
    This method is used to calculate data statistics.
    Inputs used:
        - detection times list
        - ratios list (see fire_detection.py)
        - temperatures list
    Calculated outputs:
        - 'current_average_calc' - Average of last 1800 detections (approx 15 mins usually)
        - 'prediction_function' - A first degree polynomial function (linear) built from last 1800 detections where x = time_list and y = calc_list_y
            - calc_list_y is a list corresponding to each temp - ratio value, calculated using (x+0.1) * y where x = ratio and y = temp
            - The resulting function will give the estimated ratio/temp (y) value against x input time.

    Time is seconds, can take a while to warm up as sample set increases.
    '''
    current_average_calc = 0
    try:
        time_list = data_dict_['time'][-1800:]

        ratio_list = data_dict_['cam_ratio'][-1800:]
        ratios_mean = statistics.mean(ratio_list)

        temp_list = data_dict_['temp_value'][-1800:]
        temp_floats = [float(x) for x in temp_list if not x == None]
        temps_mean = statistics.mean(temp_floats)

        # Calculate
        if ratios_mean and temps_mean:
            # Average
            current_average_calc = temps_mean * ratios_mean
            # Poly Fit temp and ratios_mean against time, linear fit line
            calc_list_y = [(x+0.1) * y for x, y in zip(ratio_list,temp_floats)]
            prediction_function = np.poly1d(np.polyfit(time_list,calc_list_y,1))
            if console_print:
                #print('--- Plot x - time, against y - ((ratio + 0.1) * temp) ---')
                lin_fit = []
                for x_ in time_list:
                    lin_fit.append(prediction_function(x_))
                fig, ax = plt.subplots(figsize=(20,10))
                ax.scatter(time_list,calc_list_y)
                ax.plot(time_list, lin_fit, c = 'r')
                ax.set_title("--- Plot x - time, against y - ((ratio + 0.1) * temp) ---")
                plt.savefig('Graph_stats.png')
        # --
        return current_average_calc, prediction_function
    except:
        if console_print:
            print('FAILED TO CALCULATE PREDICTIONS')
        return False, False
# --

# Set this value to the amount of time to predict ahead, when determining notifications (Seconds)
TIME_AHEAD_VALUE = 1600 # For 900 around 15 mins at 1 second interval
DETECTION_INTERVAL = 0.5 # Interval between detections (functions may slow this down)
RUN_TIME = 40000 # Time to run the progrma for, each iteration is DETECTION_INTERVAL
PREDICTION_THRESHOLD = 25 # Threshold for predicted value to start attention
PLOT_SAVE = True # Save a small plot of data values with a linear fit

plug_address = '192.168.0.64' # Address of plug
broker_address="192.168.0.203" # This computer (central control)
cameraStopFlag = None # Calling this event will stop the main server thread
thread = None # Main thread

start_time = time.perf_counter() # Used for timing

# Stores all current detection data recived in a persistant fashion (messages are overwritten)
message_dict = {
    'time':0,
    'total_area':0,
    'cam_ratio':None,
    'temp_value':'0.0',
    'cam_exists':True,
    'fan_power':False,
    'attention_need':'0',
    'predicted_value':20,
    'prediction_time':0,
    'current_value': 85,
    'fire_on':"1",
    'alert_cooldown':900, # Will aleart every this many
    'alert_timer':0,
    'attention_count_max':360, # The amount of times the is detected to need attention before deciding to send an alert
    'attention_count':0,
    'fire_attended':'0'
    }

# Stores all of current sessions detections, will be converted to dataframe and saved as csv file at end
data_dict = {
        'time':[],
        'total_area':[],
        'cam_ratio':[],
        'temp_value':[],
        'cam_exists':[],
        'fan_power':[],
        'attention_need':[],
        'predicted_value':[],
        'prediction_time':[],
        'current_value':[],
        'fire_on':[]
    }

# Init some message values
message_dict['prediction_time'] = TIME_AHEAD_VALUE * DETECTION_INTERVAL

# Power Plug
fan_power = plug_control.Plug(plug_address)
fan_power.info()
'''
fan_power.plug_on()
fan_power.plug_off()
Control power plug on/off functions ^
'''


# Setup phone connection
print('- MQTT Connection -')

'''
All MQTT publish and subscribe events are handled via this program.
All MQTT logic is run on python with the exeption of the phone.

Connections are run on a locally hosted mosquitto server that brokers for all clients.

Refer to phone images included to setup mqtt app
'''

client = mqtt_control.create_client_instance('P1',broker_address)
# Tempreture value recived from RSPi
client.subscribe("temp_value")
# Toggelable controller on MQTT phone setup
client.subscribe("fire_on")
# The fire has been attended, so don't worry for a while (reset alert cooldown)
client.subscribe("fire_attended")


# Setup Camera Server
print('- Starting Camera Server -')
cameraStopFlag = Event()
thread = server.Server_Connection(cameraStopFlag)
thread.start()
time.sleep(10)

try:
    print('Server Thread:',thread.is_alive(),thread)
except:
    print('Server - thread was unable to start')

# Get image stuff
for x in range(RUN_TIME):
    time.sleep(0.5)

    '''//NOTE: Print stuff going on.'''
    #clear_console()
    #print('-',x,'-')

    # Take messages and set values for message_dict
    msg_exists, msg_value = mqtt_control.get_q_message()
    while msg_exists:
        message_dict[msg_value[0]] = msg_value[1]
        msg_exists, msg_value = mqtt_control.get_q_message()
    # --

    # If the user has attended the fire, reset the attendion timer cooldown
    if message_dict['fire_attended'] == '1':
        print('-- Fire has been attended --')
        message_dict['fire_attended'] == '0'
        message_dict['alert_timer'] = message_dict['alert_cooldown']

    # Set current time from start (seconds 2 decimal)
    message_dict['time'] = round(time.perf_counter() - start_time, 2)

    # Handle Alert - set: timer time, set: if timer is up (not reset here)
    message_dict['alert_timer'], timer_can_send = alert_handler(message_dict)

    # Image proccessing thread
    if thread.is_alive() and x % 2 == 0:
        img = thread.save_image
        cam_values = handle_image(img,True)

        # Message Dict
        message_dict['cam_exists'] = cam_values['exists']
        message_dict['total_area'] = cam_values['combined_area']
        message_dict['cam_ratio'] = cam_values['ratio']

        # Send user image
        mqtt_control.publish_image(client,"phone/fire_image",img)

    # --

    # Update Users Phone MQTT
    mqtt_control.publish_data(client,"phone/fire_ratio",str(message_dict['cam_ratio']))
    mqtt_control.publish_data(client,"phone/fire_temp",str(message_dict['temp_value']))
    if message_dict['fan_power'] == True:
        mqtt_control.publish_data(client,"phone/fan","ON")
    else:
        mqtt_control.publish_data(client,"phone/fan","OFF")


    # If alert allowed, needs attention,
    if timer_can_send == True and message_dict['attention_need'] == '1' and message_dict['fire_on'] == '1':
        print('Fire Needs Attention')
        # Reset timer
        message_dict['alert_timer'] = message_dict['alert_cooldown']
        # Send ifttt alert -- Event name, Confidence, Prediction, Prediction Time - Message to notifications mobile app
        ifttt_control.ifttt_alert('fire_alert',str(message_dict['predicted_value']),str(message_dict['prediction_time'] / 60),str(message_dict['current_value']))

        # If fire is ending and heat is very low , then turn off
    elif message_dict['fire_on'] == '0' and float(message_dict['temp_value']) < 30.0:
        print('Fire Ending - Temp Low - Off')
        fan_power.plug_off()
        message_dict['fan_power'] = False
    else:
        fan_power.plug_on()
        message_dict['fan_power'] = True
    # --

    '''//NOTE: Unappend the print below for detection readouts each detection.'''
    #print('Adding Values:',message_dict,'\n')

    # Append current iteration's corrisponding message_dict values to datadict
    for msg_ in message_dict:
        msg_value_ = message_dict[msg_]

        if msg_ in data_dict:
            data_dict[msg_].append(msg_value_)
        # --

    # --

    # Print and apply calculation of predicted temperature
    cur_avg, prediction_func = prediction_calculator(data_dict,PLOT_SAVE)
    if cur_avg:
        predicted_value = prediction_func(message_dict['time'] + TIME_AHEAD_VALUE)
        message_dict['predicted_value'] = predicted_value
        message_dict['current_value'] = prediction_func(message_dict['time'] + 0)
        '''Current average and predicted printouts refer to prediction_calculator()'''
        #print('\n Current Avg:',cur_avg,'Prediction {} seconds:'.format(TIME_AHEAD_VALUE),predicted_value)

        if predicted_value < PREDICTION_THRESHOLD:
            if message_dict['attention_count'] >= message_dict['attention_count_max']:
                message_dict['attention_count'] = 0
                message_dict['attention_need'] = '1'
            else:
                message_dict['attention_count'] += 1
        # --
    # --
# --

# Stop server
cameraStopFlag.set()
time.sleep(5)

client.loop_stop()


''' Save gathered data'''

# Save dataframe to "data.csv"

file_name = 'data.csv'

# If file exists
file_exists = os.path.exists(file_name)

# Save to new file
count = 0
while file_exists:
    file_name = 'data_{}.csv'.format(count)
    file_exists = os.path.exists(file_name)
    #data_df_existing = pd.read_csv()
    count += 1
# --

# Init dataframe
data_df = None
data_df = pd.DataFrame(data=data_dict)

# Save to file
print('\n Saving data to:',file_name,'\n')
data_df.to_csv(file_name)
