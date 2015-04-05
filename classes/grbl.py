import logging
import time
import re
import threading
import atexit

from queue import Queue
from classes.rs232 import RS232

class GRBL:
    def __init__(self, name="mygrbl", ifacepath="/dev/ttyACM0"):
        
        # 'public' stuff
        self.name = name
        self._ifacepath = ifacepath
        
        self.cmode = None
        self.cmpos = (0, 0, 0)
        self.cwpos = (0, 0, 0)
        
        self.callback = lambda event, *data : None
        
        self.poll_interval = 0.2
        
        # 'private' stuff, don't mess
        self._rx_buffer_size = 128
        self._rx_buffer_fill = []
        
        self._gcodefile = None
        self._gcodefilename = None

        # state variables
        self._streaming_mode = None
        self._streaming_active = False
        self._streaming_completed = False
        self._streaming_src_end_reached = False
        self._buffer = []
        self._current_gcodeblock = None
        self._connected = False
        
        # for interrupting long-running tasks in threads
        self._poll_do = False
        self._iface_read_do = False
        
        # this class maintains two threads
        self._thread_polling = None
        self._thread_read_iface = None
        
        self._iface = None
        self._queue = Queue()
        
        self._callback_onboot =  lambda : None
        
        atexit.register(self.disconnect)
        
        
    # ====== 'public' methods ======
      
    def cnect(self):
        self._iface_read_do = True
        self._thread_read_iface = threading.Thread(target=self._onread)
        self._thread_read_iface.start()

        if self._iface == None:
            logging.log(200, "%s: setting up interface on %s", self.name, self._ifacepath)
            self._iface = RS232("serial_" + self.name, self._ifacepath, 115200)
            self._iface.start(self._queue)
        else:
            logging.log(200, "%s: there is already an interface %s", self.name, self._iface)
        
        self._rx_buffer_fill = []
        self._callback_onboot = self.poll_start
        self.softreset()
        
        
    def disconnect(self):
        if self._is_connected() == False: return
        
        self.poll_stop()
        self.abort()
        
        logging.log(200, "%s: Please wait until threads are joined...", self.name)
        self._iface_read_do = False
        self._queue.put("ok")
        self._thread_read_iface.join()
        logging.log(200, "%s: JOINED GRBL READING THREAD", self.name)
        
        self.poll_stop()
        self._iface.stop()
        self._iface = None
        self._connected = False
        self._rx_buffer_fill = []
        
        
    def abort(self):
        if self._is_connected() == False: return
        self.softreset()
        self._cleanup()
        
        
    def pause(self):
        if self._is_connected() == False: return
        self._iface.write("!")
        
        
    def resume(self):
        if self._is_connected() == False: return
        self._iface.write("~")
        
        
    def killalarm(self):
        self._iface.write("$X\n")
        self._cleanup()
        
        
    def softreset(self):
        self._iface.write("\x18") # Ctrl-X
        
        
    def poll_start(self):
        if self._is_connected() == False: return
        self._poll_do = True
        if self._thread_polling == None:
            self._thread_polling = threading.Thread(target=self._poll_state)
            self._thread_polling.start()
            logging.log(200, "%s: polling thread started", self.name)
        else:
            logging.log(200, "%s: the polling thread seems to be already running", self.name)
            
        
    def poll_stop(self):
        if self._is_connected() == False: return
        if self._thread_polling != None:
            self._poll_do = False
            self._thread_polling.join()
            logging.log(200, "%s: JOINED polling thread", self.name)
        else:
            logging.log(200, "%s: There was no polling thread running", self.name)
            
        self._thread_polling = None
        
        
    def send(self, source):
        if self._is_connected() == False: return
    
        if "f:" in source:
            requested_mode = "file"
        elif "$" in source:
            requested_mode = "settings"
        else:
            requested_mode = "string"
    
        if self._streaming_mode != "string" and self.cmode != "Idle":
            logging.log(200, "%s: You can't append something to a running stream except when you're streaming strings. Please wait until job has completed or call .abort() for GRBL to become idle", self.name)
            return False
        
        self._streaming_mode = requested_mode
        if self._streaming_mode != "file":
            # string and settings are added to the buffer
            arr = source.split("\n")
            arr_stripped = [x.strip() for x in arr]
            self._buffer.extend(arr_stripped)
        
        self._set_streaming_completed(False)
        self._set_streaming_src_end_reached(False)
        
        if self._streaming_active == False:
            # kick-off!
            if self._streaming_mode == "file":
                self._gcodefile = open(source.replace("f:", ""))
                self._callback_onboot = self._fill_buffer
                self.softreset()
                    
            elif self._streaming_mode == "string":
                self._fill_buffer()
                
            elif self._streaming_mode == "settings":
                self._maybe_send_next_line()
                
        return True
        
        
    # ====== 'private' methods ======
        
    def _poll_state(self):
        while self._poll_do == True:
            self._get_state()
            time.sleep(self.poll_interval)
        logging.log(200, "%s: polling has been stopped", self.name)
        
        
    def _get_state(self):
        if self._is_connected() == False: return
        self._iface.write("?")
        
        
    def _fill_buffer(self):
        sent = True
        while sent:
            #logging.log(200, "_fill_buffer")
            sent = self._maybe_send_next_line()

        
    def _maybe_send_next_line(self):
        bf = self._rx_buffer_fill
        
        will_send = False
        if (self._streaming_src_end_reached == False and
            self._current_gcodeblock == None):
            
            self._current_gcodeblock = self._get_next_line()
            
        logging.log(200, "%s: MAYBE s_active=%s s_end=%s curr_gcode=%s", self.name, self._streaming_active, self._streaming_src_end_reached, self._current_gcodeblock)
        
        if self._streaming_mode == "settings":
            if self._current_gcodeblock != None:
                self._iface.write(self._current_gcodeblock + "\n")
                self._current_gcodeblock = None # Mark this gcode block as processed!
            
        else:
            if self._current_gcodeblock != None:
                want_bytes = len(self._current_gcodeblock) + 1 # +1 because \n
                free_bytes = self._rx_buffer_size - sum(bf)
                will_send = free_bytes >= want_bytes
                
                logging.log(200, "%s: MAYBE rx_buf=%s fillsum=%s free=%s want=%s, will_send=%s", self.name, bf, sum(bf), free_bytes, want_bytes, will_send)
            
            if will_send == True:
                self._set_streaming_active(True)
                bf.append(len(self._current_gcodeblock) + 1) # +1 means \n
                self._iface.write(self._current_gcodeblock + "\n")
                self._current_gcodeblock = None # Mark this gcode block as processed!
                
        return will_send
    
    
    def _get_next_line(self):
        line = ""
        if self._streaming_mode == "file":
            line = self._gcodefile.readline()
            if line == "":
                line = None  # nothing more to read
            
        else:
            if len(self._buffer) > 0:
                line = self._buffer.pop(0).strip()
            else:
                line = None # nothing more to read
                
        if line and self._streaming_mode != "settings" and "$" in line:
            logging.log(200, "%s: I encountered a settings command in the gcode stream but the current streaming mode is %s. Grbl cannot handle that. I will not send this settings cmd.", self.name, self._streaming_mode)
            line = "\n"
            
        logging.log(200, "%s: NEXT LINE %s", self.name, line)
                
        if line == None:
            self._set_streaming_src_end_reached(True)
            if self._streaming_mode == "file":
                self._gcodefile.close()
                logging.log(200, "%s: closed file", self.name)

        if line: line = line.strip()
        return line
    
    
    def _rx_buffer_fill_pop(self):
        bf = self._rx_buffer_fill
        logging.log(200, "%s: _rx_buffer_fill_pop %s %s", self.name, bf, len(bf))
        if len(bf) > 0:
            bf.pop(0)
        
        if self._streaming_src_end_reached == True and len(bf) == 0:
            self._set_streaming_completed(True)
            logging.log(200, "%s: STREAM COMPLETE. streaming_completed=True, streaming_active=False", self.name)
            self._set_streaming_active(False)
    
    
    def _onread(self):
        while self._iface_read_do == True:
            line = self._queue.get()
            logging.log(200, "%s: <----- %s", self.name, line)
            if len(line) > 0:
                if line[0] == "<":
                    self._update_state(line)
                elif "Grbl " in line:
                    self._on_bootup()
                elif line == "ok":
                    if self._streaming_mode != "settings":
                        self._rx_buffer_fill_pop()
                        self._fill_buffer()
                    else:
                        self._maybe_send_next_line()
                            
                elif "ALARM" in line:
                    self.alarm = True
                elif "error" in line:
                    self._set_streaming_active(False)
                elif "to unlock" in line:
                    self._set_streaming_active(False)
                else:
                    logging.log(200, "%s: sent something unsupported: %s", self.name, line)
                

                
    def _on_bootup(self):
        logging.log(200, "%s: has booted!", self.name)
        self._connected = True
        self._callback_onboot()
        self.callback("on_boot")
            
            
    def _update_state(self, line):
        m = re.match("<(.*?),MPos:(.*?),WPos:(.*?)>", line)
        self.cmode = m.group(1)
        mpos_parts = m.group(2).split(",")
        wpos_parts = m.group(3).split(",")
        self.cmpos = (float(mpos_parts[0]), float(mpos_parts[1]), float(mpos_parts[2]))
        self.cwpos = (float(wpos_parts[0]), float(wpos_parts[1]), float(wpos_parts[2]))
        logging.log(200, "%s: === STATE === %s %s %s", self.name, self.cmode, self.cmpos, self.cwpos)
        self.callback("on_stateupdate", self.cmode, self.cmpos, self.cwpos)
        
        
    def _is_connected(self):
        if self._connected != True:
            logging.log(200, "%s: Not yet connected", self.name)
        return self._connected
    
    
    def _cleanup(self):
        del self._buffer[:]
        del self._rx_buffer_fill[:]
        logging.log(200, "%s: cleaning up, buffer is now %s", self.name, self._buffer)
        if self._gcodefile and not self._gcodefile.closed:
            logging.log(200, "%s: closing file", self.name)
            self._gcodefile.close()

        self._gcodefile = None
        self._gcodefilename = None
        self._streaming_mode = None
        self._set_streaming_active(False)
        self._set_streaming_completed(False)
        self._set_streaming_src_end_reached(False)
        self._callback_onboot =  lambda : None
            
            
    def _set_streaming_active(self, a):
        self._streaming_active = a
        logging.log(200, "%s: _set_streaming_active: %s", self.name, a)
        
        
    def _set_streaming_completed(self, a):
        self._streaming_completed = a
        logging.log(200, "%s: _set_streaming_completed: %s", self.name, a)
        
        
    def _set_streaming_src_end_reached(self, a):
        self._streaming_src_end_reached = a
        logging.log(200, "%s: _set_streaming_src_end_reached: %s", self.name, a)
        
        
    def test_string(self):
        for i in range(0,10):
            self.send("G1 X3 Y0 Z0 F1000")
            self.send("G1 X-3 Y0 Z0 F1000")