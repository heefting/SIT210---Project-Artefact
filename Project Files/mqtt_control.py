import paho.mqtt.client as mqtt # Client importing
import time
import io
from queue import Queue

# Message q
q=Queue()


# To start server GO HERE (your directory\mosquitto) AND RUN mosquitto -v

# IF you are replicationg this project you will need to run the mosquitto server in 
# its corrisponding directory, additionally certain dlls may be needed (these are mentioned in the mosquitto readme)

'''
Following methods handle MQTT interations, all values recived from the 'on_message' event will be placed in a Queue for later retrieval
if necessery.

'''

def on_message(client, userdata, message):
    #print("--- Message Callback ---")
    #print("message received " ,str(message.payload.decode("utf-8")))
    #print("message topic=",message.topic)
    #print("message qos=",message.qos)
    #print("message retain flag=",message.retain)
    
    # Put in q
    m = (message.topic,message.payload.decode("utf-8"))
    q.put(m)

# Will Retive value from end of Q
def get_q_message():
    if not q.empty():
        message = q.get()
        return True, message
    else:
        return False, None


def publish_data(client_,topic_string, input_value,print_output=False):
    # Publish
    if print_output:
        print("P - Topic:",topic_string,'Value:',input_value)
    client_.publish(topic_string,input_value)
    # Wait
    time.sleep(0.2)

def publish_image(client_,topic_string, input_image,print_output=False):
    # Convert to bytes
    imgByteArr = io.BytesIO()
    input_image.save(imgByteArr, format='jpeg')
    byteArr = imgByteArr.getvalue()
    # Publish
    if print_output:
        print("P - Topic:",topic_string)
    client_.publish(topic_string,byteArr)
    # Wait
    time.sleep(0.5)

def create_client_instance(name,connect_address):
    # Create new instance
    print("creating new instance")
    client = mqtt.Client(name)
    client.on_message=on_message
    
    # Connect to broker
    print("-- Broker Connect ---")
    client.connect(connect_address)
    client.loop_start()
    
    return client


















