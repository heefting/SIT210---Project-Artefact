import io
import socket
import struct
from PIL import Image
import matplotlib.pyplot as pl
import time
from threading import Thread,Event
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='(%(threadName)-9s) %(message)s',)


class Server_Connection(Thread):
    '''
    This class is responsable for connecting to its corrisponding client partner thread (run on the Raspberry Pi)
        - Listens to socket
        - Upon connecting with client, recive unpacked array of image bytes, will terminate 
          if an error is encountered or if client signals end of stream with zero length signal
        - Image data can be retrived via accessing thread's "save_image"
    '''
    
    def __init__(self,event):
        Thread.__init__(self)
        self.stopped = event
        self.save_image = None
    # --
    
    def run(self):
        logging.debug('Trying - Server Create')
        server_socket = socket.socket()
        server_socket.bind(('192.168.0.203', 8000))
        server_socket.listen(0)
        # Accept a single connection and make a file-like object out of it
        connection = server_socket.accept()[0].makefile('rb')
        try:
            # While NOT true (when .set() is used it becomes true), block for 0.5 seconds if false/(not .set()) then return false
            while not self.stopped.wait(0.5):
                # Read the length of the image as a 32-bit unsigned int. If the
                # length is zero, quit the loop
                image_len = struct.unpack('<L', connection.read(struct.calcsize('<L')))[0]
                if not image_len:
                    break
                # Construct a stream to hold the image data and read the image
                # data from the connection
                image_stream = io.BytesIO()
                image_stream.write(connection.read(image_len))
                # Rewind the stream, open it as an image with PIL and do some
                # processing on it
                image_stream.seek(0)
                #image = Image.open(image_stream)
                #logging.debug('Image is %dx%d' % image.size)
                #image.verify()
                #logging.debug('Image is verified')
                #image_save = Image.open(image_stream)
                #image_save.save("haha.jpeg")
                self.save_image = Image.open(image_stream)
            logging.debug('Server - Success - Closing')
            #return True
        except:
            logging.debug('Server - Failed - Closing')
            #return False
        finally:
            connection.close()
            server_socket.close()
            logging.debug('Server - Closing')
    # --
# --





