import logging
import time
import re
import threading
from queue import Queue

from classes.rs232 import RS232

class GRBL:
    def __init__(self, name="", ifacepath=""):
        self.name = name
        self.ifacepath = ifacepath
        self.connected = False
        
        self.cmode = None
        self.cmpos = (0, 0, 0)
        self.cwpos = (0, 0, 0)
        
        self.rx_buffer_size = 128
        self.rx_buffer_fill = []
        
        self.gcodefile = None
        self.gcodefilename = None
        self.current_gcodeblock = None
        
        self.streaming_active = False
        self.streaming_completed = False
        self.streaming_eof_reached = False
        
        self.do_poll = False
        self.do_read = False
        
        self.polling_thread = None
        self.reading_thread = None
        
        self.iface = None
        
        self.queue = Queue()
        
      
    def cnect(self):
        self.do_read = True
        self.reading_thread = threading.Thread(target=self.onread)
        self.reading_thread.start()

        if self.iface == None:
            logging.info("%s setting up interface on %s", self.name, self.ifacepath)
            self.iface = RS232("serial_" + self.name, self.ifacepath, 115200)
            self.iface.start(self.queue)
        else:
            logging.info("%s there is already an interface %s", self.name, self.iface)
            
        self.softreset()
        self.rx_buffer_fill = []
        
    def disconect(self):
        if self.is_connected() == False: return
            
        self.abort()
        
        logging.info("Please wait until threads are joined...")
        
        self.do_read = False
        self.queue.put("ok")
        self.reading_thread.join()
        logging.info("JOINED GRBL READING THREAD")
        
        self.poll_stop()
        self.iface.stop()
        self.iface = None
        self.connected = False
        self.rx_buffer_fill = []
        
    def poll_start(self):
        if self.is_connected() == False: return
        self.do_poll = True
        if self.polling_thread == None:
            self.polling_thread = threading.Thread(target=self.poll_state)
            self.polling_thread.start()
            logging.info("polling thread started")
        else:
            logging.info("the polling thread seems to be already running")
            
        
    def poll_stop(self):
        if self.is_connected() == False: return
        if self.polling_thread != None:
            self.do_poll = False
            self.polling_thread.join()
            logging.info("JOINED polling thread")
        else:
            logging.info("There was no polling thread running")
            
        self.polling_thread = None
        
        
    def set_streamingfile(self, filename):
        self.gcodefilename = filename
        
    def poll_state(self):
        while self.do_poll == True:
            self.get_state()
            time.sleep(4)
        logging.info("polling has been stopped")
        
    def get_state(self):
        if self.is_connected() == False: return
        self.iface.write("?")
        
    def run(self):
        if self.is_connected() == False: return
        logging.info("%s running %s", self.name, self.gcodefilename)
        self.gcodefile = open(self.gcodefilename)
        self.softreset()
        self.rx_buffer_fill = []
        self.streaming_active = True
        self.streaming_completed = False
        self.streaming_eof_reached = False
        self.fill_buffer()
        
    def abort(self):
        if self.is_connected() == False: return
        self.softreset()
        
    def pause(self):
        if self.is_connected() == False: return
        self.iface.write("!")
        
    def play(self):
        if self.is_connected() == False: return
        self.iface.write("~")
        
    def killalarm(self):
        self.iface.write("$X\n")
        
    def softreset(self):
        self.iface.write("\x18") # Ctrl-X
        
    def fill_buffer(self):
        sent = True
        while sent == True:
          sent = self.maybe_send_next_line()
        
        
        
    def maybe_send_next_line(self):
        bf = self.rx_buffer_fill
        
        will_send = False
        if (self.streaming_active == True and
            self.streaming_eof_reached == False and
            self.current_gcodeblock == None):
            
            self.current_gcodeblock = self.gcodefile.readline().strip()
            if self.current_gcodeblock == "":
                self.current_gcodeblock = None
                self.streaming_eof_reached = True
                self.gcodefile.close()
                logging.info("closed file")
                return False
            
        if self.current_gcodeblock != None:
            want_bytes = len(self.current_gcodeblock) + 1 # +1 because \n
            free_bytes = self.rx_buffer_size - sum(bf)
            
            will_send = free_bytes >= want_bytes
            
            logging.info("MAYBE buf=%s fill=%s fill=%s free=%s want=%s, will_send=%s", self.rx_buffer_size, bf, sum(bf), free_bytes, want_bytes, will_send)
        
        if will_send == True:
            bf.append(len(self.current_gcodeblock) + 1) # +1 means \n
            self.iface.write(self.current_gcodeblock + "\n")
            self.current_gcodeblock = None
        
        return will_send
    
    def rx_buffer_fill_pop(self):
        bf = self.rx_buffer_fill
        logging.info("rx_buffer_fill_pop %s %s", bf, len(bf))
        if len(bf) > 0:
            bf.pop(0)
        
        if self.streaming_eof_reached == True and len(bf) == 0:
            self.streaming_completed = True
            self.streaming_active = False
            print("STREAM COMPLETE")
    
    def onread(self):
        while self.do_read == True:
            line = self.queue.get()
            logging.info("GRBL %s: <----- %s", self.name, line)
            if len(line) > 0:
                if line[0] == "<":
                    self.update_state(line)
                elif "Grbl " in line:
                    self.on_bootup()
                elif line == "ok":
                    self.rx_buffer_fill_pop()
                    self.fill_buffer()
                elif "ALARM" in line:
                    self.alarm = True
                    logging.info("GRBL %s: <----- %s", self.name, line)
                elif "error" in line:
                    self.streaming_active = False
                    logging.info("GRBL %s: <----- %s", self.name, line)
                elif "to unlock" in line:
                    self.streaming_active = False
                    logging.info("GRBL %s: <----- %s", self.name, line)
                else:
                    logging.info("grbl sent something unsupported %s", line)
                
                
    def on_bootup(self):
        logging.info("%s has booted!", self.name)
        self.connected = True
            
    def update_state(self, line):
        m = re.match("<(.*?),MPos:(.*?),WPos:(.*?)>", line)
        self.cmode = m.group(1)
        mpos_parts = m.group(2).split(",")
        wpos_parts = m.group(3).split(",")
        self.cmpos = (float(mpos_parts[0]), float(mpos_parts[1]), float(mpos_parts[2]))
        self.cwpos = (float(wpos_parts[0]), float(wpos_parts[1]), float(wpos_parts[2]))
        logging.info("GRBL %s: === STATE === %s %s %s", self.name, self.cmode, self.cmpos, self.cwpos)
        
    def is_connected(self):
        if self.connected != True:
            logging.info("Not yet connected")
        return self.connected
        