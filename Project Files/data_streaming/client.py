import io
import socket
import struct
import time
import picamera
from threading import Timer,Thread,Event
import logging

import paho.mqtt.client as mqtt # Client importing #sudo pip3 install paho-mqtt
import mqtt_control

from w1thermsensor import W1ThermSensor

broker_address="192.168.0.203"

'''
This file is run on the raspberry pi, preferably run with python3 (may run with python2)
'''

logging.basicConfig(level=logging.DEBUG, format='(%(threadName)-9s) %(message)s',)

class Camera_Connection(Thread):
    '''
    This class is responsable for transmitting image data
        - Waits for socket connection with host
        - Upon connecting with host, will transmit data from NOIR Camera, will terminate when finished or when error is encountered.
    '''
    
    def __init__(self,event):
        Thread.__init__(self)
        self.stopped = event
        self.save_image = None
    # --
    
    def run(self):
        logging.debug('Trying - Connect to server')
        # Connection
        client_socket = socket.socket()
        try:
            client_socket.connect(('192.168.0.203', 8000))
        except:
            logging.debug('Connection attempt - Failed')
            #return False
        logging.debug('Connected - Trying - Stream Camera')

        # Make a file-like object out of the connection
        connection = client_socket.makefile('wb')
        try:
            camera = picamera.PiCamera()
            camera.resolution = (640, 480)
            # Start a preview and let the camera warm up for 2 seconds
            camera.start_preview()
            time.sleep(2)
            logging.debug('Camera - Ready')
            # Note the start time and construct a stream to hold image data
            # temporarily (we could write it directly to connection but in this
            # case we want to find out the size of each capture first to keep
            # our protocol simple)
            #start = time.time()
            stream = io.BytesIO()
            for foo in camera.capture_continuous(stream, 'jpeg'):
                # Write the length of the capture to the stream and flush to
                # ensure it actually gets sent
                connection.write(struct.pack('<L', stream.tell()))
                connection.flush()
                # Rewind the stream and send the image data over the wire
                stream.seek(0)
                connection.write(stream.read())
                # If we've been capturing for more than 30 seconds OR it event is .set(), quit
                if self.stopped.is_set():
                    break
                # Reset the stream for the next capture
                stream.seek(0)
                stream.truncate()
            # Write a length of zero to the stream to signal we're done
            connection.write(struct.pack('<L', 0))
            logging.debug('Connection - Finished - Closing')
            #return True
        except:
            logging.debug('Connection - Failed - Closing')
            #return False
        finally:
            logging.debug('Connection - Closing')
            try:
                connection.close()
                client_socket.close()
            except:
                logging.debug('Connection - Got closed on')
        # --
# --

# Tempreture Sensor
temp_sensor = W1ThermSensor()


# Setup Tempreture
print('- Temp MQTT Connection -')
temp_client = mqtt_control.create_client_instance('P12',broker_address)


# Setup & run camera thread
print('- Starting First Thread -')
cameraStopFlag = Event()
thread = Camera_Connection(cameraStopFlag)
thread.start()
time.sleep(4)

# Always run
while True:
    
    # Tempreture detection
    time.sleep(2)
    temperature = temp_sensor.get_temperature()

    if temperature is not None:
        mqtt_control.publish_data(temp_client,"temp_value",temperature)
    else:
        print("Failed to retrieve data from temperature sensor")
    
    # If the thread is not working NOTE: This part serves no purpose currently, a later implementation may allow for continued operation after disconnecting.
    if not thread.is_alive():
        break
        # Make new thread
        print('- Trying New Thread Starting -')
        cameraStopFlag.set()
        time.sleep(2)
        
        # Start new thread
        cameraStopFlag.clear()
        try:
            thread = Camera_Connection(cameraStopFlag)
            thread.start()
            print('- New Thread Started -')
        except:
            print('Failed')
            time.sleep(5)
            continue
        
        time.sleep(4)
    # --
# -- |

temp_client.loop_stop()






