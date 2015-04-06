import logging
import time
import re
import threading
import atexit
import os

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
        
        
        
        self.poll_interval = 0.2
        
        # 'private' stuff, don't mess
        self._rx_buffer_size = 128
        self._rx_buffer_fill = []
        self._rx_buffer_backlog = []
        self._rx_buffer_fill_percent = 0
        
        self._gcodefile = None
        self._gcodefilename = None
        self._gcodefilesize = 999999999

        # state variables
        self._streaming_mode = None
        
        self._streaming_complete = True
        self._job_finished = False
        self._streaming_src_end_reached = True
        
        self._error = False
        self._alarm = False
        
        self._buffer = []
        self._current_gcodeblock = None
        self._connected = False
        self._streamed_bytes = 0
        
        # for interrupting long-running tasks in threads
        self._poll_do = False
        self._iface_read_do = False
        
        # this class maintains two threads
        self._thread_polling = None
        self._thread_read_iface = None
        
        self._iface = None
        self._queue = Queue()
        
        self._callback_onboot =  lambda : None
        self.callback = self._default_callback
        
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
        self._rx_buffer_backlog = []
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
        self._rx_buffer_backlog = []
        
        
    def abort(self):
        if self._is_connected() == False: return
        self.softreset()
        self._cleanup()
        
        
    def hold(self):
        if self._is_connected() == False: return
        self._iface_write("!")
        
        
    def resume(self):
        if self._is_connected() == False: return
        self._iface_write("~")
        
        
    def killalarm(self):
        self._iface_write("$X\n")
        self._cleanup()
        
        
    def softreset(self):
        self._iface.write("\x18") # Ctrl-X
        
        
    def homing(self):
        self._iface_write("$H\n")
        
        
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
    
        if (self._streaming_mode == "file" or self._streaming_mode == "settings") and self.cmode == "Run":
            self.callback("on_log", "You can't append something to a running stream except when you're streaming strings. Please wait until job has completed or call .abort() for GRBL to become idle")
            return False
        
        self._streaming_mode = requested_mode
        
        if self._streaming_mode != "file":
            # string and settings are added to the buffer
            arr = source.split("\n")
            arr_stripped = [x.strip() for x in arr]
            self._buffer.extend(arr_stripped)
        
        self._set_job_finished(False)
        self._set_streaming_src_end_reached(False)
        
        if self._job_finished == False:
            # kick-off!
            if self._streaming_mode == "file":
                filename = source.replace("f:", "")
                self._gcodefile = open(filename)
                self._gcodefilesize = os.path.getsize(filename)
                self._streamed_bytes = 0
                self.callback("on_log", "File size is " + str(self._gcodefilesize))
                self._fill_buffer()
                #self._callback_onboot = self._fill_buffer
                #self.softreset()
                    
            elif self._streaming_mode == "string":
                self._fill_buffer()
                
            elif self._streaming_mode == "settings":
                self._maybe_send_next_line()
        else:
            self.callback("on_log", "Job not yet finished, cannot send. Please reset.")
                
        return True
    
    def settings_from_file(self, filename):
        if self.cmode == "Idle":
            logging.log(200, "%s: Stopping polling.", self.name)
            self.poll_stop()
            time.sleep(1)
            logging.log(200, "%s: Writing settings.", self.name)
            self.send("".join([x for x in open(filename).readlines()]))
            time.sleep(1)
            logging.log(200, "%s: Re-starting polling.", self.name)
            self.poll_start()
        else:
            logging.log(200, "%s: Have to be in Idle state to stream settings.", self.name)
        
        
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
        will_send = False
        
        if (self._streaming_src_end_reached == False and self._current_gcodeblock == None):
            self._current_gcodeblock = self._get_next_line()
            
        logging.log(200, "%s: MAYBE s_active=%s s_end=%s curr_gcode=%s", self.name, self._streaming_complete, self._streaming_src_end_reached, self._current_gcodeblock)
        
        if self._streaming_mode == "settings":
            if self._current_gcodeblock != None:
                self._iface_write(self._current_gcodeblock + "\n")
                self._rx_buffer_backlog.append(self._current_gcodeblock)
                self._current_gcodeblock = None # Mark this gcode block as processed!
            
        else:
            if self._current_gcodeblock != None:
                want_bytes = len(self._current_gcodeblock) + 1 # +1 because \n
                free_bytes = self._rx_buffer_size - sum(self._rx_buffer_fill)
                will_send = free_bytes >= want_bytes
                
                logging.log(200, "%s: MAYBE rx_buf=%s fillsum=%s free=%s want=%s, will_send=%s", self.name, self._rx_buffer_fill, sum(self._rx_buffer_fill), free_bytes, want_bytes, will_send)
            
            if will_send == True:
                line_length = len(self._current_gcodeblock) + 1 # +1 means \n
                self._set_streaming_complete(False)
                self._rx_buffer_fill.append(line_length) 
                self._rx_buffer_backlog.append(self._current_gcodeblock)
                self._iface_write(self._current_gcodeblock + "\n")
                self._current_gcodeblock = None # Mark this gcode block as processed!
                
                
        return will_send
    
    
    def _get_next_line(self):
        line = ""
        if self._streaming_mode == "file":
            line = self._gcodefile.readline()
            
            self._streamed_bytes += len(line)
            progress_percent = int(100 * self._streamed_bytes / self._gcodefilesize)
            self.callback("on_progress_percent", progress_percent)
            
            if line == "":
                line = None  # nothing more to read
            
        else:
            if len(self._buffer) > 0:
                line = self._buffer.pop(0).strip()
            else:
                line = None # nothing more to read
                
        if line and self._streaming_mode != "settings" and "$" in line:
            self.callback("on_log", "I encountered a settings command in the gcode stream but the current streaming mode is %s. Grbl cannot handle that. I will not send this settings cmd.", self._streaming_mode)
            line = "\n"
            
        logging.log(200, "%s: NEXT LINE %s", self.name, line)
                
        if line == None:
            self._set_streaming_src_end_reached(True)
            if self._streaming_mode == "file":
                self._gcodefile.close()
                self._gcodefile = None
                logging.log(200, "%s: closed file", self.name)

        if line:
            line = re.match("([^;(]*)", line).group(1) # strip comments and parentheses
            line = line.strip()
            
        return line
    
    
    def _rx_buffer_fill_pop(self):
        logging.log(200, "%s: _rx_buffer_fill_pop %s %s", self.name, self._rx_buffer_fill, len(self._rx_buffer_fill))
            
        if len(self._rx_buffer_fill) > 0:
            self._rx_buffer_fill.pop(0)
            processed_command = self._rx_buffer_backlog.pop(0)
            self.callback("on_processed_command", processed_command)
            
        if self._streaming_src_end_reached == True and len(self._rx_buffer_fill) == 0:
            self._set_job_finished(True)
            logging.log(200, "%s: JOB COMPLETE", self.name)
            self._set_streaming_complete(True)
            self.callback("on_log", "Job completed")
    
    
    def _iface_write(self, data):
        num_written = self._iface.write(data)
        self.callback("on_send_command", data.strip())
        
        
    def _onread(self):
        while self._iface_read_do == True:
            line = self._queue.get()
            if len(line) > 0:
                if line[0] == "<":
                    self._update_state(line)
                elif "Grbl " in line:
                    self._on_bootup()
                elif line == "ok":
                    logging.log(200, "%s: <----- %s", self.name, line)
                    self._handle_ok()
                    
                            
                elif "ALARM" in line:
                    logging.log(200, "%s: <----- %s", self.name, line)
                    self.callback("on_alarm", line)
                    logging.log(200, "%s: ALARM!: %s %s", self.name, line, self._rx_buffer_backlog)
                    self.abort()
                    
                elif "error" in line:
                    logging.log(200, "%s: <----- %s", self.name, line)
                    if self._error == False:
                        # First time
                        self._error = True
                        problem_command = self._rx_buffer_backlog[1]
                        self.callback("on_error", line, problem_command)
                        logging.log(200, "%s: ERROR!: %s %s", self.name, line, self._rx_buffer_backlog)
                        #self.abort()
                    else:
                        logging.log(200, "%s: Receiving additional errors: %s", self.name, line)
                    
                elif "to unlock" in line:
                    logging.log(200, "%s: <----- %s", self.name, line)
                    self.callback("on_log", line)
                    
                else:
                    logging.log(200, "%s: sent something unsupported: %s", self.name, line)
                    self.callback("on_log", "Unknown response: " + line)
                

                
    def _handle_ok(self):
        logging.log(200, "%s: handle ok: %s %s %s", self.name, self._error, self._streaming_complete, self._streaming_mode)

        if self._error == False:
            if self._streaming_complete == False:
                if self._streaming_mode != "settings":
                    # File and string
                    self._rx_buffer_fill_pop()
                    self._fill_buffer()
            else:
                logging.log(200, "%s handle_ok(): Streaming is already completed, Grbl is just sending OK's for the commands in its buffer.")
                    
            if self._streaming_mode == "settings":
                del self._rx_buffer_backlog[:]
                self._maybe_send_next_line()
                
        else: 
            self.callback("on_log", "Will not send because GRBL class has received an error. Please reset")
        
        self._rx_buffer_fill_percent = int(100 - 100 * (self._rx_buffer_size - sum(self._rx_buffer_fill)) / self._rx_buffer_size)
        self.callback("on_rx_buffer_percentage", self._rx_buffer_fill_percent)
                
                            
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
        #logging.log(200, "%s: === STATE === %s %s %s", self.name, self.cmode, self.cmpos, self.cwpos)
        self.callback("on_stateupdate", self.cmode, self.cmpos, self.cwpos)
        
        
    def _is_connected(self):
        if self._connected != True:
            logging.log(200, "%s: Not yet connected", self.name)
        return self._connected
    
    
    def _cleanup(self):
        del self._buffer[:]
        del self._rx_buffer_fill[:]
        del self._rx_buffer_backlog[:]
        logging.log(200, "%s: cleaning up, buffer is now %s", self.name, self._buffer)
        if self._gcodefile and not self._gcodefile.closed:
            logging.log(400, "%s: closing file", self.name)
            self._gcodefile.close()

        self._gcodefile = None
        self._gcodefilename = None
        self._streaming_mode = None
        self._set_streaming_complete(True)
        self._set_job_finished(True)
        self._set_streaming_src_end_reached(True)
        self._error = False
        self._callback_onboot =  lambda : None
        self._current_gcodeblock = None
        self._gcodefilesize = 999999999
        self._streamed_bytes = 0
        self._rx_buffer_fill_percent = 0
            
            
    def _set_streaming_src_end_reached(self, a):
        self._streaming_src_end_reached = a
        logging.log(200, "%s: _set_streaming_src_end_reached: %s", self.name, a)


    # The buffer has been fully written to Grbl, but Grbl is still processing the last commands.
    def _set_streaming_complete(self, a):
        self._streaming_complete = a
        logging.log(200, "%s: _set_streaming_complete: %s", self.name, a)
        
        
    # Grbl has finished processing everything
    def _set_job_finished(self, a):
        self._job_finished = a
        logging.log(200, "%s: _set_job_finished: %s", self.name, a)
        
        
    def _default_callback(self, status, *args):
        print("CALLBACK", status, args)
        
        
    def test_string(self):
        for i in range(0,10):
            self.send("G1 X3 Y0 Z0 F1000")
            self.send("G1 X-3 Y0 Z0 F1000")