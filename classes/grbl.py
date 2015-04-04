import logging
import time
import re
import threading
import atexit

from queue import Queue
from classes.rs232 import RS232

class GRBL:
    def __init__(self, name="", ifacepath="", state_cb=None):
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
        self.streaming_src_end_reached = False
        
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
            logging.error("%s there is already an interface %s", self.name, self.iface)
            
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
            logging.error("the polling thread seems to be already running")
            
        
    def poll_stop(self):
        if self.is_connected() == False: return
        if self.polling_thread != None:
            self.do_poll = False
            self.polling_thread.join()
            logging.info("JOINED polling thread")
        else:
            logging.warning("There was no polling thread running")
            
        self.polling_thread = None
        
    def poll_state(self):
        while self.do_poll == True:
            self.get_state()
            time.sleep(0.1) # 10 polls per second
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
    
        if self.cmode != "Idle" and (requested_mode == "file" or requested_mode == "settings"):
            logging.info("To stream a file or settings, GRBL must be idle. Please wait until job has completed or call .abort()")
            return
        
        self.streaming_mode = requested_mode
        if self.streaming_mode != "file":
            # string and settings are added to the buffer
            arr = source.split("\n")
            arr_stripped = [x.strip() for x in arr]
            self.buffer.extend(arr_stripped)
            #self._set_streaming_src_end_reached(False)
        
        
        self._set_streaming_completed(False)
        self._set_streaming_src_end_reached(False)
        
        if self.streaming_active == False:
            # begin of job
            

            # kick-off!
            if self.streaming_mode == "file":
                self.gcodefile = open(source.replace("f:", ""))
                self.after_boot_callback = self.fill_buffer
                self.softreset()
                    
            elif self.streaming_mode == "string":
                self.fill_buffer()
                
            elif self.streaming_mode == "settings":
                self._maybe_send_next_line()
        
                

    def fill_buffer(self):
        sent = True
        while sent:
            logging.log(5, "fill_buffer")
            sent = self._maybe_send_next_line()
          
        
  
        
    def _maybe_send_next_line(self):
        bf = self.rx_buffer_fill
        
        will_send = False
        if (self.streaming_src_end_reached == False and
            self.current_gcodeblock == None):
            
            self.current_gcodeblock = self.get_next_line()
            
        logging.info("MAYBE s_active=%s s_end=%s curr_gcode=%s", self.streaming_active, self.streaming_src_end_reached, self.current_gcodeblock)
        
        if self.streaming_mode == "settings":
            if self.current_gcodeblock != None:
                self.iface.write(self.current_gcodeblock + "\n")
                self.current_gcodeblock = None # Mark this gcode block as processed!
            
        else:
            if self.current_gcodeblock != None:
                want_bytes = len(self.current_gcodeblock) + 1 # +1 because \n
                free_bytes = self.rx_buffer_size - sum(bf)
                will_send = free_bytes >= want_bytes
                
                logging.info("MAYBE rx_buf=%s fillsum=%s free=%s want=%s, will_send=%s", bf, sum(bf), free_bytes, want_bytes, will_send)
            
            if will_send == True:
                self._set_streaming_active(True)
                bf.append(len(self.current_gcodeblock) + 1) # +1 means \n
                self.iface.write(self.current_gcodeblock + "\n")
                self.current_gcodeblock = None # Mark this gcode block as processed!
                
        return will_send
    
    def get_next_line(self):
        line = ""
        if self.streaming_mode == "file":
            line = self.gcodefile.readline()
            if line == "":
                line = None  # nothing more to read
            
        else:
            if len(self.buffer) > 0:
                line = self.buffer.pop(0).strip()
            else:
                line = None # nothing more to read
                
        if line and self.streaming_mode != "settings" and "$" in line:
            logging.warning("I read a %s settings command in the gcode stream but the current streaming mode is %s. Grbl cannot handle that. I will not send this settings cmd.", line, self.streaming_mode)
            line = "\n"
            
        logging.info("NEXT LINE %s", line)
                
        if line == None:
            self._set_streaming_src_end_reached(True)
            if self.streaming_mode == "file":
                self.gcodefile.close()
                logging.log(0, "closed file")
            
        
        
        if line: line = line.strip()
        return line
    
    
    def rx_buffer_fill_pop(self):
        bf = self.rx_buffer_fill
        logging.info("rx_buffer_fill_pop %s %s", bf, len(bf))
        if len(bf) > 0:
            bf.pop(0)
        
        if self.streaming_src_end_reached == True and len(bf) == 0:
            self._set_streaming_completed(True)
            logging.info("STREAM COMPLETE. streaming_completed=True, streaming_active=False")
            self._set_streaming_active(False)
    
    def onread(self):
        while self.do_read == True:
            line = self.queue.get()
            logging.log(10, "GRBL %s: <----- %s", self.name, line)
            if len(line) > 0:
                if line[0] == "<":
                    self.update_state(line)
                elif "Grbl " in line:
                    self.on_bootup()
                elif line == "ok":
                    if self.streaming_mode != "settings":
                        self.rx_buffer_fill_pop()
                        self.fill_buffer()
                    else:
                        self._maybe_send_next_line()
                            
                elif "ALARM" in line:
                    self.alarm = True
                elif "error" in line:
                    self._set_streaming_active(False)
                elif "to unlock" in line:
                    self._set_streaming_active(False)
                else:
                    logging.log(10, "grbl sent something unsupported %s", line)
                

                
    def on_bootup(self):
        logging.log(10, "%s has booted!", self.name)
        self.connected = True
        self.after_boot_callback()
            
    def update_state(self, line):
        m = re.match("<(.*?),MPos:(.*?),WPos:(.*?)>", line)
        self.cmode = m.group(1)
        mpos_parts = m.group(2).split(",")
        wpos_parts = m.group(3).split(",")
        self.cmpos = (float(mpos_parts[0]), float(mpos_parts[1]), float(mpos_parts[2]))
        self.cwpos = (float(wpos_parts[0]), float(wpos_parts[1]), float(wpos_parts[2]))
        logging.log(10, "GRBL %s: === STATE === %s %s %s", self.name, self.cmode, self.cmpos, self.cwpos)
        if self.state_cb != None:
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
        self._set_streaming_completed(False)
        self._set_streaming_src_end_reached(False)
        self.after_boot_callback =  lambda : None
            
    def _set_streaming_active(self, a):
        self.streaming_active = a
        logging.info("_set_streaming_active: %s", a)
        
    def _set_streaming_completed(self, a):
        self.streaming_completed = a
        logging.info("_set_streaming_completed: %s", a)
        
    def _set_streaming_src_end_reached(self, a):
        self.streaming_src_end_reached = a
        logging.info("_set_streaming_src_end_reached: %s", a)
        
        
    def test_string(self):
        for i in range(0,10):
            self.send("G1 X3 Y0 Z0 F1000")
            self.send("G1 X-3 Y0 Z0 F1000")