import logging
import time
import re
import multiprocessing

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
        self.current_gcodeblock = None
        
        self.streaming_active = False
        self.streaming_completed = False
        self.streaming_eof_reached = False
        

        
      
    def cnect(self):
        logging.info("%s connecting to %s", self.name, self.ifacepath)
        self.iface = RS232("serial_" + self.name, self.ifacepath, 115200, self.onread)
        self.iface.start()
        time.sleep(1)
        self.reset()
        self.status_polling_process = multiprocessing.Process(target=self.poll_state)
        self.status_polling_process.start()
        
    def set_streamingfile(self, filename):
        self.gcodefile = open(filename)
        
    def reset(self):
        self.iface.write("\x18") # Ctrl-X
        
    def poll_state(self):
        while True:
            self.get_state()
            time.sleep(0.2)
        
    def get_state(self):
        self.iface.write("?")
        
    def stream(self):
        logging.info("%s starting to stream %s", self.name, self.gcodefile)
        self.streaming_active = True
        self.streaming_completed = False
        self.streaming_eof_reached = False
        self.fill_buffer()
        
    def fill_buffer(self):
        sent = True
        while sent == True:
          sent = self.maybe_send_next_line()
        
        
        
    def maybe_send_next_line(self):
        will_send = False
        if (self.streaming_active == True and
            self.streaming_eof_reached == False and
            self.current_gcodeblock == None):
            
            self.current_gcodeblock = self.gcodefile.readline().strip()
            if self.current_gcodeblock == "":
                self.current_gcodeblock = None
                self.streaming_eof_reached = True
                return False
            
        if self.current_gcodeblock != None:
            want_bytes = len(self.current_gcodeblock) + 1 # +1 because \n
            free_bytes = self.rx_buffer_size - sum(self.rx_buffer_fill)
            
            will_send = free_bytes >= want_bytes
            
            #logging.info("MAYBE buf=%s fill=%s fill=%s free=%s want=%s, will_send=%s", self.rx_buffer_size, self.rx_buffer_fill, sum(self.rx_buffer_fill), free_bytes, want_bytes, will_send)
        
        if will_send == True:
            self.rx_buffer_fill.append(len(self.current_gcodeblock) + 1) # +1 means \n
            self.iface.write(self.current_gcodeblock + "\n")
            self.current_gcodeblock = None
        
        return will_send
    
    def rx_buffer_fill_pop(self):
        if len(self.rx_buffer_fill) > 0:
            self.rx_buffer_fill.pop(0)
        
        if self.streaming_eof_reached == True and len(self.rx_buffer_fill) == 0:
            self.streaming_completed = True
            self.streaming_active = False
            print("STREAM COMPLETE")

        
    def onread(self, line):
        #logging.info("GRBL %s: <----- %s", self.name, line)
        if len(line) > 0:
            if line[0] == "<":
                self.update_state(line)
            elif "Grbl " in line:
                self.on_bootup()
            elif line == "ok":
                self.rx_buffer_fill_pop()
                self.fill_buffer()
            elif "error" in line:
                self.streaming_active = False
                logging.info("GRBL %s: <----- %s", self.name, line)
            elif "to unlock" in line:
                self.streaming_active = False
                logging.info("GRBL %s: <----- %s", self.name, line)
                
                
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
        