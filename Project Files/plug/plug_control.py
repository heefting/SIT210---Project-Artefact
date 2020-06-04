from tplink_smartplug import SmartPlug
import time

# MIT HS1xx Git: https://github.com/vrachieru/tplink-smartplug-api

class Plug():
    
    def __init__(self,plug_ip):
        # Init plug
        self.plug = SmartPlug(plug_ip)
    # --
    
    def info(self):
        print(' -- Plug Info -- ')
        print('Name:      %s' % self.plug.name)
        print('Model:     %s' % self.plug.model)
        print('Mac:       %s' % self.plug.mac)
        print('Time:      %s' % self.plug.time)

        print('Is on:     %s' % self.plug.is_on)
        print('Nightmode: %s' % (not self.plug.led))
        print('RSSI:      %s' % self.plug.rssi)
    # --
    
    def plug_on(self):
        time.sleep(1)
        if not self.plug.is_on:
            self.plug.turn_on()
            print('Plug turned on')
    # --
    
    def plug_off(self):
        time.sleep(1)
        if self.plug.is_on:
            self.plug.turn_off()
            print('Plug turned off')
    # --
# --



