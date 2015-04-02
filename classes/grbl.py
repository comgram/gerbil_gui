import logging
import time
import re

from classes.rs232 import RS232


class GRBL:
    def __init__(self, name="", path=""):
        self.name = name
        self.path = path
        self.cmode = None
        self.cmpos = (0, 0, 0)
        self.cwpos = (0, 0, 0)
      
    def cnect(self):
        logging.info("%s connecting to %s", self.name, self.path)
        self.iface = RS232("serial_" + self.name, self.path, 115200, self.onread)
        self.iface.start()
        
    def reset(self):
        self.iface.write("\x18") # Ctrl-X
        
    def test(self):
        for i in range(0,3):
            time.sleep(1)
            self.iface.write("$$\r\n")
            time.sleep(1)
            self.iface.write("?\r\n")
            
        
        time.sleep(1)
        self.iface.stop()
        
    def onread(self, line):
        logging.info("%s onread line %s", self.name, line)
        if len(line) > 0 and line[0] == "<":
            self.update_state(line)
            
    def update_state(self, line):
        m = re.match("<(.*?),MPos:(.*?),WPos:(.*?)>", line)
        self.cmode = m.group(1)
        mpos_parts = m.group(2).split(",")
        wpos_parts = m.group(3).split(",")
        self.cmpos = (float(mpos_parts[0]), float(mpos_parts[1]), float(mpos_parts[2]))
        self.cwpos = (float(wpos_parts[0]), float(wpos_parts[1]), float(wpos_parts[2]))
        logging.info("%s === STATE === %s %s %s", self.name, self.cmode, self.cmpos, self.cwpos)
        