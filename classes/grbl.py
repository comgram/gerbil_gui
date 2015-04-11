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
        self._incremental_streaming = False
        
        self._wait_empty_buffer = False
        
        self.distance_mode_arc = None
        self.distance_mode_linear = None
        
        self._feed_override = False
        self._current_feed = None
        self._requested_feed = None
        
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
        self._cleanup()
        
        self._iface_read_do = True
        self._thread_read_iface = threading.Thread(target=self._onread)
        self._thread_read_iface.start()

        if self._iface == None:
            self.callback("on_log", "{}: Setting up interface on {}".format(self.name, self._ifacepath))
            self._iface = RS232("serial_" + self.name, self._ifacepath, 115200)
            self._iface.start(self._queue)
        else:
            self.callback("on_log", "{}: Cannot start another interface. There is already an interface {}. This should not have happened.".format(self.name, self._iface))
        
        self._callback_onboot = self.poll_start
        self.softreset()
        
        
    def disconnect(self):
        if self._is_connected() == False: return
        
        self.poll_stop()
        self.abort()
        
        self.callback("on_log", "{}: Please wait until reading thread has joined...".format(self.name))
        self._iface_read_do = False
        self._queue.put("ok")
        self._thread_read_iface.join()
        self.callback("on_log", "{}: Reading thread successfully joined.".format(self.name))
        
        self._iface.stop()
        self._iface = None
        self._connected = False
        self._rx_buffer_fill = []
        
        self._cleanup()
        
        self.callback("on_log", "{}: Successfully disconnected".format(self.name))
        
        
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
            self.callback("on_log", "{}: Polling thread started".format(self.name))
        else:
            self.callback("on_log", "{}: Cannot start polling task: Another polling thread seems to be already running".format(self.name))
            
        
    def poll_stop(self):
        if self._is_connected() == False: return
        if self._thread_polling != None:
            self._poll_do = False
            self.callback("on_log", "{}: Please wait until polling thread has joined...".format(self.name))
            self._thread_polling.join()
            self.callback("on_log", "{}: Polling thread has successfully  joined...".format(self.name))
        else:
            self.callback("on_log", "{}: Cannot start a polling thread. Another one is already running. This should not have happened.".format(self.name))
            
        self._thread_polling = None
        
        
    def send(self, source):
        if self._is_connected() == False: return
    
        if self._error:
            self.callback("on_log", "{}: GRBL class is in a state of error. Please reset before you continue.".format(self.name))
    
        if "f:" in source:
            requested_mode = "file"
        else:
            requested_mode = "string"
    
        if self._streaming_mode == "file" and self.cmode == "Run":
            self.callback("on_log", "{}: You can't append something to a running stream except when you're streaming strings. Please wait until the current job has completed or call .abort() for Grbl to become idle".format(self.name))
            return False
        
        self._streaming_mode = requested_mode
        
        if self._streaming_mode == "string":
            # add everything into buffer
            arr = source.split("\n")
            arr_stripped = [x.strip() for x in arr]
            self._buffer.extend(arr_stripped)
        
        self._set_job_finished(False)
        self._set_streaming_src_end_reached(False)
        self._set_streaming_complete(False)
        
        if self._job_finished == False:
            # kick-off!
            if self._streaming_mode == "file":
                filename = source.replace("f:", "")
                self._gcodefile = open(filename)
                self._gcodefilesize = os.path.getsize(filename)
                self._streamed_bytes = 0
                self.callback("on_log", "{}: File size is {:d}".format(self.name, self._gcodefilesize))
                if self._feed_override == True and self._current_feed == None:
                    self.set_feed(self._requested_feed)
                
            if self._incremental_streaming == True:
                # only send one line
                self._maybe_send_next_line()
            else:
                # fill grbl's rx buffer as much as possible
                self._fill_buffer()
                
        else:
            self.callback("on_log", "{}: Job not yet finished, cannot send.".format(self.name))
                
        return True
    
    def settings_from_file(self, filename):
        if self.cmode == "Idle":
            self.callback("on_log", "{}: Stopping polling.".format(self.name))
            self.poll_stop()
            time.sleep(1)
            self.callback("on_log", "{}: Writing settings.".format(self.name))
            self.send("".join([x for x in open(filename).readlines()]))
            time.sleep(1)
            self.callback("on_log", "{}: Restarting polling.".format(self.name))
            self.poll_start()
        else:
            self.callback("on_log", "{}: Grbl has to be idle to stream settings.".format(self.name))
            
            
    def set_feed_override(self, val):
        self._feed_override = val
        
        
    def set_feed(self, requested_feed):
        if self._current_feed != requested_feed:
            self._requested_feed = int(requested_feed)
        
    def set_incremental_streaming(self, a):
        self._incremental_streaming = a
        if self._incremental_streaming == True:
            self._wait_empty_buffer = True
        self.callback("on_log", "{}: Incremental streaming is {}".format(self.name, self._incremental_streaming))
        
    # ====== 'private' methods ======
        
    def _poll_state(self):
        while self._poll_do == True:
            self._get_state()
            time.sleep(self.poll_interval)
        self.callback("on_log", "{}: Polling has been stopped".format(self.name))
        
        
    def _get_state(self):
        if self._is_connected() == False: return
        self._iface.write("?")
        
        
    def _fill_buffer(self):
        sent = True
        if self._incremental_streaming:
            sent = self._maybe_send_next_line()
        else:
            while sent: sent = self._maybe_send_next_line()

        
    def _maybe_send_next_line(self):
        will_send = False
        
        if (self._streaming_src_end_reached == False and self._current_gcodeblock == None):
            self._current_gcodeblock = self._get_next_line()
            
        #if self._current_gcodeblock == "":
            #logging.log(200, "MAYBE: Empty line, not sending")
            #self._current_gcodeblock = None
            #return True
            
        logging.log(200, "MAYBE s_active=%s s_end=%s curr_gcode=%s", self._streaming_complete, self._streaming_src_end_reached, self._current_gcodeblock)
        
        if self._current_gcodeblock != None:
            want_bytes = len(self._current_gcodeblock) + 1 # +1 because \n
            free_bytes = self._rx_buffer_size - sum(self._rx_buffer_fill)
            will_send = self._incremental_streaming or (free_bytes >= want_bytes)

            logging.log(200, "MAYBE rx_buf=%s fillsum=%s free=%s want=%s, will_send=%s", self._rx_buffer_fill, sum(self._rx_buffer_fill), free_bytes, want_bytes, will_send)

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
            l = self._gcodefile.readline()
            if l != "":
                self._buffer.append(l)
                self._streamed_bytes += len(l)
                progress_percent = int(100 * self._streamed_bytes / self._gcodefilesize)
                self.callback("on_progress_percent", progress_percent)
            
        if len(self._buffer) > 0:
            line = self._buffer.pop(0).strip()
        else:
            line = None # nothing more to read
                
        if line and self._incremental_streaming == False and "$" in line:
            self.callback("on_log", "{}: I encountered a settings command '{}' in the gcode stream but the current streaming mode is not set to incremental. Grbl cannot handle that. I will not send.".format(self.name, line))
            line = "\n"
            
        logging.log(200, "%s: NEXT LINE %s", self.name, line)
                
        if line == None:
            self._set_streaming_src_end_reached(True)
            if self._streaming_mode == "file":
                self._gcodefile.close()
                self._gcodefile = None
                self.callback("on_log", "{}: Closed file.".format(self.name))

        line = self._preprocess(line)
            
        return line
    
    
    def _preprocess(self, line):
        if line == None:
            return line
                
        # strip comments (after semicolon and opening parenthesis)
        line = re.match("([^;(]*)", line).group(1)
        
        # strip
        line = line.strip()
        
        # remove whitespaces
        line = line.replace(" ", "")
        
        if re.match("G90($|[^.])", line):
            self.distance_mode_linear = "absolute"
            self.callback("on_linear_distance_mode_change", self.distance_mode_linear)
        
        if re.match("G91($|[^.])", line):
            self.distance_mode_linear = "incremental"
            self.callback("on_linear_distance_mode_change", self.distance_mode_linear)
            
        if "G90.1" in line:
            self.distance_mode_arc = "absolute"
            self.callback("on_arc_distance_mode_change", self.distance_mode_arc)
            
        if "G91.1" in line:
            self.distance_mode_arc = "incremental"
            self.callback("on_arc_distance_mode_change", self.distance_mode_arc)

        contains_feed = True if re.match(".*F[.\d]+", line) else False
        if contains_feed:
            if self._feed_override == False:
                parsed_feed = re.match(".*F([.\d]+)", line).group(1)
                self._current_feed = int(parsed_feed)
                self.callback("on_feed_change", self._current_feed)
                self.callback("on_log", "FEED" + str(self._current_feed))
            
        if self._feed_override == True:
            if contains_feed:
                # strip the original F setting
                line = re.sub(r"F[.\d]+", "", line)
                
            if self._requested_feed and self._current_feed != self._requested_feed:
                line += "F{:d}".format(self._requested_feed)
                self._current_feed = self._requested_feed
                self.callback("on_log", "OVERRIDING FEED" + str(self._current_feed))
            
        
        return line
        
        
    
    
    def _rx_buffer_fill_pop(self):
        logging.log(200, "%s: _rx_buffer_fill_pop %s %s", self.name, self._rx_buffer_fill, len(self._rx_buffer_fill))
            
        if len(self._rx_buffer_fill) > 0:
            self._rx_buffer_fill.pop(0)
            processed_command = self._rx_buffer_backlog.pop(0)
            self.callback("on_processed_command", processed_command)
            
        if self._streaming_src_end_reached == True and len(self._rx_buffer_fill) == 0:
            self._set_job_finished(True)
            self._set_streaming_complete(True)
            self.callback("on_log", "{}: Job completed".format(self.name))
    
    
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
                    logging.log(200, "%s <----- %s", self.name, line)
                    self._handle_ok()
                    
                elif "ALARM" in line:
                    self.callback("on_alarm", line)
                    
                elif "error" in line:
                    logging.log(200, "%s <----- %s", self.name, line)
                    if self._error == False:
                        # First time
                        self._error = True
                        logging.log(200, "%s: _rx_buffer_backlog at time of error: %s", self.name,  self._rx_buffer_backlog)
                        problem_command = self._rx_buffer_backlog[0]
                        self.callback("on_error", line, problem_command)
                    else:
                        self.callback("on_log", "{}: Receiving additional errors: {}".format(self.name, line))
                        
                else:
                    self.callback("on_read", line)
                

                
    def _handle_ok(self):
        logging.log(200, "%s: handle ok: %s %s %s %s", self.name, self._error, self._streaming_complete, self._streaming_mode, self._incremental_streaming)

        if self._error == False:
            if self._streaming_complete == False:
                self._rx_buffer_fill_pop()
                if not (self._wait_empty_buffer and len(self._rx_buffer_fill) > 0):
                    self._wait_empty_buffer = False
                    self._fill_buffer()
                    
            else:
                logging.log(200, "%s handle_ok(): Streaming is already completed, Grbl is just sending OK's for the commands in its buffer.", self.name)
                
        else: 
            self.callback("on_log", "{}: GRBL class is in state of error, will not send any more. Please reset/abort before you can continue.".format(self.name))
        
        self._rx_buffer_fill_percent = int(100 - 100 * (self._rx_buffer_size - sum(self._rx_buffer_fill)) / self._rx_buffer_size)
        self.callback("on_rx_buffer_percentage", self._rx_buffer_fill_percent)
                
                            
    def _on_bootup(self):
        self.callback("on_log", "{}: Booted!".format(self.name))
        self._connected = True
        self._callback_onboot()
        self.callback("on_boot")
        self.send("G90")
        self.send("G90.1")
            
            
    def _update_state(self, line):
        m = re.match("<(.*?),MPos:(.*?),WPos:(.*?)>", line)
        self.cmode = m.group(1)
        mpos_parts = m.group(2).split(",")
        wpos_parts = m.group(3).split(",")
        self.cmpos = (float(mpos_parts[0]), float(mpos_parts[1]), float(mpos_parts[2]))
        self.cwpos = (float(wpos_parts[0]), float(wpos_parts[1]), float(wpos_parts[2]))
        #self.callback("on_log", "=== STATE === %s %s %s", self.name, self.cmode, self.cmpos, self.cwpos)
        self.callback("on_stateupdate", self.cmode, self.cmpos, self.cwpos)
        
        
    def _is_connected(self):
        if self._connected != True:
            self.callback("on_log", "{}: Not yet connected".format(self.name))
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
        #self.callback("on_log", "{}: Streaming source end reached: {}".format(self.name, a))


    # The buffer has been fully written to Grbl, but Grbl is still processing the last commands.
    def _set_streaming_complete(self, a):
        self._streaming_complete = a
        #self.callback("on_log", "{}: Streaming completed: {}".format(self.name, a))
        
        
    # Grbl has finished processing everything
    def _set_job_finished(self, a):
        self._job_finished = a
        #self.callback("on_log", "{}: Job finished: {}".format(self.name, a))
        

    def _default_callback(self, status, *args):
        print("DEFAULT CALLBACK", status, args)
        
        
    def test_string(self):
        for i in range(0,10):
            self.send("G1 X3 Y0 Z0 F1000")
            self.send("G1 X-3 Y0 Z0 F1000")