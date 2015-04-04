import logging
import time
import re
import threading
import atexit

from queue import Queue
from classes.rs232 import RS232

class GRBL:
    def __init__(self, name="", ifacepath="", state_cb=lambda:None):
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
        
        self.current_gcodeline = 0
        self.buffer = []
        
        self.streaming_mode = None
        self.streaming_active = False
        self.streaming_completed = False
        self.streaming_end_reached = False
        
        self.do_poll = False
        self.do_read = False
        
        self.polling_thread = None
        self.reading_thread = None
        
        self.iface = None
        
        self.queue = Queue()
        
        self.after_boot_callback =  lambda : None
            
        atexit.register(self.disconect)
        
        self.state_cb = state_cb
        
      
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
        
    def abort(self):
        if self.is_connected() == False: return
        self.softreset()
        self._cleanup()
        
    def pause(self):
        if self.is_connected() == False: return
        self.iface.write("!")
        
    def play(self):
        if self.is_connected() == False: return
        self.iface.write("~")
        
    def killalarm(self):
        self.iface.write("$X\n")
        self._cleanup()
        
    def softreset(self):
        self.iface.write("\x18") # Ctrl-X
        
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
        
    def poll_state(self):
        while self.do_poll == True:
            self.get_state()
            time.sleep(2)
        logging.info("polling has been stopped")
        
    def get_state(self):
        if self.is_connected() == False: return
        self.iface.write("?")
        
    def send(self, source):
        if self.is_connected() == False: return
    
        if "f:" in source:
            requested_mode = "file"
        elif "$" in source:
            requested_mode = "settings"
        else:
            requested_mode = "string"
    
        if self.streaming_active == True and (self.streaming_mode == "file" or self.streaming_mode == "settings"):
            logging.info("Already streaming %s. I can't append. Doing nothing now.", self.streaming_mode)
            return
    
        if requested_mode == "file":
            self.streaming_mode = "file"
            self.gcodefile = open(source.replace("f:", ""))
        elif requested_mode == "settings":
            self.streaming_mode = "settings"
        else:
            self.streaming_mode = "string"
            arr = source.split("\n")
            arr_stripped = [x.strip() for x in arr]
            self.buffer.extend(arr_stripped)
            self.streaming_end_reached = False
            
        if self.streaming_active == False:
            if requested_mode == "file":
                # only first time for files
                self.after_boot_callback = self.fill_buffer
                self.softreset()
            else:
                self.fill_buffer()
                
        self._set_streaming_active(True)
        self.streaming_completed = False
        self.streaming_end_reached = False

        
    def fill_buffer(self):
        logging.info("Filling buffer to the max")
        sent = True
        while sent == True:
          sent = self._maybe_send_next_line()
        
    def get_next_line(self):
        line = ""
        if self.streaming_mode == "file":
            line = self.gcodefile.readline().strip()
            
        elif self.streaming_mode == "string":
            if len(self.buffer) > 0:
                line = self.buffer.pop(0)
            else:
                line = "" # same behavior as .readline() from file
                
        if line == "":
            line = None
            self.streaming_end_reached = True
            if self.streaming_mode == "file":
                self.gcodefile.close()
                logging.info("closed file")
            
        logging.info("NEXT LINE %s", line)
        return line
    
        
    def _maybe_send_next_line(self):
        bf = self.rx_buffer_fill
        
        will_send = False
        if (self.streaming_end_reached == False and
            self.current_gcodeblock == None):
            
            self.current_gcodeblock = self.get_next_line()
            
        logging.info("MAYBE sa=%s se=%s gc=%s", self.streaming_active, self.streaming_end_reached, self.current_gcodeblock)

        if self.current_gcodeblock != None:
            want_bytes = len(self.current_gcodeblock) + 1 # +1 because \n
            free_bytes = self.rx_buffer_size - sum(bf)
            will_send = free_bytes >= want_bytes
            
            logging.info("MAYBE rx_buf=%s fillsum=%s free=%s want=%s, will_send=%s", bf, sum(bf), free_bytes, want_bytes, will_send)
        
        if will_send == True:
            bf.append(len(self.current_gcodeblock) + 1) # +1 means \n
            self.iface.write(self.current_gcodeblock + "\n")
            self.current_gcodeblock = None # Mark this gcode block as processed!
            
        
        
        return will_send
    
    def rx_buffer_fill_pop(self):
        bf = self.rx_buffer_fill
        logging.info("rx_buffer_fill_pop %s %s", bf, len(bf))
        if len(bf) > 0:
            bf.pop(0)
        
        if self.streaming_end_reached == True and len(bf) == 0:
            self.streaming_completed = True
            self._set_streaming_active(False)
            print("STREAM COMPLETE. streaming_completed=True, streaming_active=False")
    
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
                    if self.streaming_active:
                        self.rx_buffer_fill_pop()
                        self.fill_buffer()
                elif "ALARM" in line:
                    self.alarm = True
                    logging.info("GRBL %s: <----- %s", self.name, line)
                elif "error" in line:
                    self._set_streaming_active(False)
                    logging.info("GRBL %s: <----- %s", self.name, line)
                elif "to unlock" in line:
                    self._set_streaming_active(False)
                    logging.info("GRBL %s: <----- %s", self.name, line)
                else:
                    logging.info("grbl sent something unsupported %s", line)
                

                
    def on_bootup(self):
        logging.info("%s has booted!", self.name)
        self.connected = True
        self.after_boot_callback()
            
    def update_state(self, line):
        m = re.match("<(.*?),MPos:(.*?),WPos:(.*?)>", line)
        self.cmode = m.group(1)
        mpos_parts = m.group(2).split(",")
        wpos_parts = m.group(3).split(",")
        self.cmpos = (float(mpos_parts[0]), float(mpos_parts[1]), float(mpos_parts[2]))
        self.cwpos = (float(wpos_parts[0]), float(wpos_parts[1]), float(wpos_parts[2]))
        logging.info("GRBL %s: === STATE === %s %s %s", self.name, self.cmode, self.cmpos, self.cwpos)
        self.state_cb(self.cmode, self.cmpos, self.cwpos)
        
    def is_connected(self):
        if self.connected != True:
            logging.info("Not yet connected")
        return self.connected
    
    def _cleanup(self):
        logging.info("%s cleaning up", self.name)
        del self.buffer[:]
        del self.rx_buffer_fill[:]
        logging.info("%s cleaning up, buffer is now %s", self.name, self.buffer)
        if self.gcodefile and not self.gcodefile.closed:
            logging.info("%s closing file", self.name)
            self.gcodefile.close()

        self.gcodefile = None
        self.gcodefilename = None
        self.streaming_mode = None
        self._set_streaming_active(False)
        self.streaming_completed = False
        self.streaming_end_reached = False
        self.after_boot_callback =  lambda : None
            
    def _set_streaming_active(self, a):
        self.streaming_active = a
        logging.info("streaming_active: %s", a)
        
        
    def test_string(self):
        for i in range(0,10):
            self.send("G1 X3 Y0 Z0 F1000")
            self.send("G1 X-3 Y0 Z0 F1000")