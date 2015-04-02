import logging
import time
import re

from classes.rs232 import RS232


class GRBL:
    def __init__(self, name="", ifacepath=""):
        self.name = name
        self.ifacepath = ifacepath
        self.booted = False
        
        self.cmode = None
        self.cmpos = (0, 0, 0)
        self.cwpos = (0, 0, 0)
        
        self.rx_buffer_size = 128
        self.rx_buffer_fill = []
        
        self.gcodefile = None
        self.gcodefile_currentline = 0
        self.gcodeblock = None
        
        self.streaming_active = False
        self.streaming_completed = False
        
      
    def cnect(self):
        logging.info("%s connecting to %s", self.name, self.ifacepath)
        self.iface = RS232("serial_" + self.name, self.ifacepath, 115200, self.onread)
        self.iface.start()
        time.sleep(1)
        self.reset()
        
    def set_streamingfile(self, filename):
        self.gcodefile = open(filename)
        
    def reset(self):
        self.iface.write("\x18") # Ctrl-X
        
    def stream(self):
        logging.info("%s starting to stream %s", self.name, self.gcodefile)
        self.streaming_active = True
        self.maybe_send_next_line(self.name)
        
    def maybe_send_next_line(self, calledfrom):
        sending = False
        if self.streaming_active == True and self.gcodeblock == None:
            self.gcodeblock = self.gcodefile.readline().strip()
            if self.gcodeblock == "":
                self.streaming_active = False
                self.streaming_completed = True
                return False
            
        free_bytes = self.rx_buffer_size - sum(self.rx_buffer_fill)
        
        sending = free_bytes > (len(self.gcodeblock) + 1)
        logging.info("MAYBE buf=%s fill=%s fill=%s free=%s want=%s", self.rx_buffer_size, self.rx_buffer_fill, sum(self.rx_buffer_fill), free_bytes, len(self.gcodeblock))
        
        if sending == True:
            # current gcodeblock can be sent
            self.rx_buffer_fill.append(len(self.gcodeblock) + 1) # +1 means \n
            #self.name = str(len(self.gcodeblock))
            #logging.info("APPENDING %s", self.rx_buffer_fill)
            self.iface.write(self.gcodeblock + "\n")
            self.gcodeblock = None
        
        
        return sending
    
    def do_pop(self):
        print("popping1", self.rx_buffer_fill)
        self.rx_buffer_fill.pop(0)
        print("popping2", self.rx_buffer_fill)

        
    def onread(self, line):
        logging.info("GRBL %s: <----- %s", self.name, line)
        if len(line) > 0:
            if line[0] == "<":
                self.update_state(line)
            elif "Grbl " in line:
                self.on_bootup()
            elif line == "ok":
                #logging.info("%s OK", self.name)
                if self.streaming_active == True:
                  #del self.rx_buffer_fill[0]
                  self.do_pop()
                  self.maybe_send_next_line("onread" + self.name)
                  self.maybe_send_next_line("onread" + self.name)
            elif "error" in line:
                self.streaming_active = False
            elif "to unlock" in line:
                self.streaming_active = False
                
                
    def on_bootup(self):
        logging.info("%s has booted!", self.name)
        self.booted = True
        self.stream()
            
    def update_state(self, line):
        m = re.match("<(.*?),MPos:(.*?),WPos:(.*?)>", line)
        self.cmode = m.group(1)
        mpos_parts = m.group(2).split(",")
        wpos_parts = m.group(3).split(",")
        self.cmpos = (float(mpos_parts[0]), float(mpos_parts[1]), float(mpos_parts[2]))
        self.cwpos = (float(wpos_parts[0]), float(wpos_parts[1]), float(wpos_parts[2]))
        logging.info("GRBL %s: === STATE === %s %s %s", self.name, self.cmode, self.cmpos, self.cwpos)
        
                
    def start_streaming(self):
        logging.info("%s starting to stream!", self.name)
        
    def test(self):
        for i in range(0,3):
            time.sleep(1)
            self.iface.write("$$\r\n")
            time.sleep(1)
            self.iface.write("?\r\n")

        time.sleep(1)
        self.iface.stop()
        