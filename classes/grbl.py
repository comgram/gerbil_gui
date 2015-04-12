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
        """
        Set up initial values of all properties.
        """
        
        # 'public' stuff
        self.name = name
        self._ifacepath = ifacepath
        
        self.cmode = None
        self.cmpos = (0, 0, 0)
        self.cwpos = (0, 0, 0)
        
        self.poll_interval = 0.2 # suggested by Grbl documentation
        
        # 'private' stuff, don't mess
        self._rx_buffer_size = 128
        self._rx_buffer_fill = []
        self._rx_buffer_backlog = []
        self._rx_buffer_fill_percent = 0
        
        self._gcodefile = None
        self._gcodefilename = None
        self._gcodefilesize = 999999999
        
        self._current_line = "; _INIT" # explicit init string for debugging
        self._current_line_sent = True

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
        self._job_finished = True
        self._streaming_src_end_reached = True
        
        self._error = False
        self._alarm = False
        
        self._buffer = []

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
      
    def cnect(self,path=False):
        """
        Connect to the RS232 port of the Grbl controller. This is done by instantiating
        a RS232 object which by itself block-listens (in a thread) to asynchronous data
        sent by the Grbl controller. To read these data, the method 'self._onread' will
        block-run in a separate thread and fetch data via a thread queue. Once this is
        set up, we soft-reset the Grbl controller, after which status polling starts.
        
        The only argument to this method is `path` (e.g. /dev/ttyACM0), which you can
        set if you haven't given the path during object instatiation.
        """
        
        if path:
            self._ifacepath = path
            
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
        """
        This method stops all threads, joins them, then closes the serial connection.
        """
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
        """
        An alias for `softreset()`, but also performs cleaning up.
        """
        if self._is_connected() == False: return
        self.softreset()
        self._cleanup()
        
        
    def hold(self):
        """
        An alias for sending an exclamation mark.
        """
        if self._is_connected() == False: return
        self._iface_write("!")
        
        
    def resume(self):
        """
        An alias for sending a tilde.
        """
        if self._is_connected() == False: return
        self._iface_write("~")
        
        
    def killalarm(self):
        """
        An alias for sending $X, but also performs a cleanup of data
        """
        self._iface_write("$X\n")
        self._cleanup()
        
        
    def softreset(self):
        """
        An alias for sending Ctrl-X
        """
        self._iface.write("\x18") # Ctrl-X
        
        
    def homing(self):
        """
        An alias for sending $H
        """
        self._iface_write("$H\n")
        
        
    def poll_start(self):
        """
        Start method `_poll_state()` in a thread, which sends question marks in regular
        intervals forever, or until _poll_do is set to False. Grbl responds to the 
        question marks with a status string enclosed in angle brackets < and >.
        """
        if self._is_connected() == False: return
        self._poll_do = True
        if self._thread_polling == None:
            self._thread_polling = threading.Thread(target=self._poll_state)
            self._thread_polling.start()
            self.callback("on_log", "{}: Polling thread started".format(self.name))
        else:
            self.callback("on_log", "{}: Cannot start polling task: Another polling thread seems to be already running".format(self.name))
            
        
    def poll_stop(self):
        """
        Set _poll_do to False, which completes the status polling thread. This method
        also joins the thread to make sure it comes to a well defined end.
        """
        if self._is_connected() == False: return
        if self._thread_polling != None:
            self._poll_do = False
            self.callback("on_log", "{}: Please wait until polling thread has joined...".format(self.name))
            self._thread_polling.join()
            self.callback("on_log", "{}: Polling thread has successfully  joined...".format(self.name))
        else:
            self.callback("on_log", "{}: Cannot start a polling thread. Another one is already running. This should not have happened.".format(self.name))
            
        self._thread_polling = None
        
        
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
        """
        Pass True or False as argument to enable or disable feed override. If you pass
        True, all F gcode-commands will be stripped out from the stream. In addition, no feed
        override takes place until you also have set the requested feed via the method
        `set_feed()`.
        """
        self._feed_override = val
        
        
    def set_feed(self, requested_feed):
        """
        Override the feed speed (in mm/min). Effecive only when you set `set_feed_override(True)`.
        An 'overriding' F gcode command will be inserted into the stream only when the currently
        requested feed differs from the last requested feed.
        """
        self._requested_feed = float(requested_feed)
        
        
    def set_incremental_streaming(self, a):
        """
        Pass True to enable incremental streaming. The default is False.
        
        Incremental streaming means that a new command is sent to Grbl only after
        Grbl has responded with 'ok' to the last sent command.
        
        Non-incremental streaming means that Grbl's 128-byte receive buffer will
        be kept as full as possible at all times, to give it's motion planner system
        enough data to work with. This results in smoother and faster axis motion.
        
        You can change the streaming method even during streaming.
        """
        self._incremental_streaming = a
        if self._incremental_streaming == True:
            self._wait_empty_buffer = True
        self.callback("on_log", "{}: Incremental streaming is {}".format(self.name, self._incremental_streaming))
    
    
    def write(self,source):
        """
        The Gcode compiler requires a method "write" to be present. This is just an alias for `send()`
        """
        self.send(source)
        
    
    def send(self, source):
        """
        Stream one or many commands to Grbl.
        
        An argument other than a string is rejected.
        A single command does not have to be newline-terminated.
        To send multiple commands in one go, separate them by newlines.
        Empty or blank strings are simply ignored.
        Gcode comments (semicolon and parentesis) will be filtered out
        
        
        """
        logging.log(200, "%s: send(): %s", self.name, source)
        if self._is_connected() == False: return
    
        if not isinstance(source, str):
            self.callback("on_log", "{}: send() can only receive strings.".format(self.name))
            return
    
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
            # append to buffer
            arr = source.split("\n")
            arr_stripped = []
            for l in arr:
                # when sending individual strings, strip comments early
                # when first individual string contains comment-only, it
                # mimics src_end_reached
                l = re.match("([^;(]*)", l).group(1)
                if l != "":
                    arr_stripped.append(l.strip())
            self._buffer.extend(arr_stripped)
        
        elif self._streaming_mode == "file":
            filename = source.replace("f:", "")
            self._gcodefile = open(filename)
            self._gcodefilesize = os.path.getsize(filename)
            self._streamed_bytes = 0
            self.callback("on_log", "{}: File size is {:d}".format(self.name, self._gcodefilesize))
            if self._feed_override == True and self._current_feed == None:
                self.set_feed(self._requested_feed)
            
        self._set_streaming_src_end_reached(False)
        self._set_streaming_complete(False)
        
        if self._job_finished == True:
            if len(self._buffer) > 0:
                # happens when first line is comment
                self._stream() # only needed at beginning, because once kicked off it is self-sustaining
                self._set_job_finished(False)



    # ====== 'private' methods ======
        

    # decides if Grbl's rx buffer can take commands, and if yes, takes them from _buffer and sends them, either fast or slow
    # must be called regularly, at least on 'ok' reception
    def _stream(self):
        if self._streaming_src_end_reached:
            logging.log(200, "%s: _stream(): Nothing more in _buffer. Doing nothing")
            return
        
        if self._incremental_streaming:
            # buffer is guaranteed to be underfull, so it is safe to send without checking Grbl's rx buffer size
            logging.log(200, "%s: _stream(): Is incremental. Setting next line.")
            self._set_next_line()
            logging.log(200, "%s: _stream(): Source end reached=%s", self.name, self._streaming_src_end_reached)
            if self._streaming_src_end_reached == False:
                self._send_current_line()
                
        else:
            logging.log(200, "%s: _stream(): Calling _fill_rx_buffer_until_full", self.name)
            self._fill_rx_buffer_until_full()

        
        
    def _fill_rx_buffer_until_full(self):
        logging.log(200, "%s: _fill_rx_buffer_until_full(): called. checking for while: end_reached=%s, current_line_sent=%s", self.name, self._streaming_src_end_reached, self._current_line_sent)
        
        while True:
            if self._current_line_sent == True:
                self._set_next_line()
                
            logging.log(200, "%s: _fill_rx_buffer_until_full(): in WHILE loop: end_reached=%s, buf_can_receive=%s", self.name, self._streaming_src_end_reached, self._rx_buf_can_receive_current_line())
            
            if self._streaming_src_end_reached == False and self._rx_buf_can_receive_current_line():
                logging.log(200, "%s: _fill_rx_buffer_until_full(): in WHILE loop: sending current line!")
                self._send_current_line() # will add _SENT comment to _current_line
            else:
                break
                
                
                
    # gets next line from file or _buffer, and sets _current_gcodeblock
    def _set_next_line(self):
        preprocessed_line = ""
        
        if self._streaming_src_end_reached == True:
            logging.log(200, "%s: _set_next_line(): Will not enter while loop because end_reached=%s", self.name, self._streaming_src_end_reached)
            
        while preprocessed_line == "" and self._streaming_src_end_reached == False:
            # read one line from file and append it to _buffer
            if self._streaming_mode == "file":
                l = self._gcodefile.readline()
                # even blank lines will at least contain \n, at EOF we will get ""
                if l != "":
                    # EOF not yet reached
                    self._buffer.append(l)
                    self._streamed_bytes += len(l)
                    progress_percent = int(100 * self._streamed_bytes / self._gcodefilesize)
                    self.callback("on_progress_percent", progress_percent)
                else:
                    # EOF reached
                    self._gcodefile.close()
                    self._gcodefile = None
                    self.callback("on_log", "{}: Closed file.".format(self.name))
                    
                
            # at this point, buffer contains comments etc.
            if len(self._buffer) > 0:
                # still something in _buffer, get it
                line = self._buffer.pop(0).strip()
                preprocessed_line = self._preprocess(line)
                    
            else:
                # the buffer is empty, nothing more to read
                self._set_streaming_src_end_reached(True)
            
        if preprocessed_line != "":
            self._current_line = preprocessed_line
            self._current_line_sent = False
            logging.log(200, "%s: _set_next_line(): SETTING CURRENT LINE TO '%s'", self.name, preprocessed_line)
        else:
            logging.log(200, "%s: _set_next_line(): Did NOT set CURRENT LINE because line was empty", self.name)
        
        
        
    # this unconditionally sends the current line to Grbl
    def _send_current_line(self):
        logging.log(200, "%s: _send_current_line(): Sending '%s'", id(self), self._current_line)
        self._set_streaming_complete(False)
        line_length = len(self._current_line) + 1 # +1 for \n which we will append below
        self._rx_buffer_fill.append(line_length) 
        self._rx_buffer_backlog.append(self._current_line)
        self._iface_write(self._current_line + "\n")
        self._current_line_sent = True
    
    



    def _rx_buf_can_receive_current_line(self):
        rx_free_bytes = self._rx_buffer_size - sum(self._rx_buffer_fill)
        required_bytes = len(self._current_line) + 1 # +1 because \n
        return rx_free_bytes >= required_bytes
    
    
    
    
    
    def _preprocess(self, line):
        if line == None:
            return line
                
        # strip comments (after semicolon and opening parenthesis)
        line = re.match("([^;(]*)", line).group(1)
        
        # strip
        line = line.strip()
        
        # remove whitespaces
        line = line.replace(" ", "")
        
        # check for $ settings
        contains_setting = re.match("\$\d+", line)
        if contains_setting and self._incremental_streaming == False:
            self.callback("on_log", "{}: I encountered a settings command '{}' in the gcode stream but the current streaming mode is not set to incremental. Grbl cannot handle that. I will not send the $ command.".format(self.name, line))
            line = "; $ setting stripped"
            
        # keep track of distance modes        
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
                self._current_feed = float(parsed_feed)
                self.callback("on_feed_change", self._current_feed)
                self.callback("on_log", "FEED" + str(self._current_feed))
            
        if self._feed_override == True:
            if contains_feed:
                # strip the original F setting
                line = re.sub(r"F[.\d]+", "", line)
                
            if self._requested_feed and self._current_feed != self._requested_feed:
                line += "F{:0.1f}".format(self._requested_feed)
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
        logging.log(200, "%s: handle ok: error:%s complete:%s mode:%s incremental:%s", self.name, self._error, self._streaming_complete, self._streaming_mode, self._incremental_streaming)

        if self._error == False:
            if self._streaming_complete == False:
                self._rx_buffer_fill_pop()
                if not (self._wait_empty_buffer and len(self._rx_buffer_fill) > 0):
                    self._wait_empty_buffer = False
                    logging.log(200, "%s handle_ok(): Calling stream()", self.name)
                    self._stream()
                    
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
        #self.send("G90")
        #self.send("G90.1")
            
            
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
        self._current_line = "; _CLEANUP" # explicit magic string for debugging
        self._current_line_sent = True
        self._gcodefilesize = 999999999
        self._streamed_bytes = 0
        self._rx_buffer_fill_percent = 0
            
            
    def _poll_state(self):
        while self._poll_do == True:
            self._get_state()
            time.sleep(self.poll_interval)
        self.callback("on_log", "{}: Polling has been stopped".format(self.name))
        
        
    def _get_state(self):
        if self._is_connected() == False: return
        self._iface.write("?")
        
            
    def _set_streaming_src_end_reached(self, a):
        self._streaming_src_end_reached = a
        self.callback("on_log", "{}: Streaming source end reached: {}".format(self.name, a))
        print("STREAMING SOURCE END REACHED", a)


    # The buffer has been fully written to Grbl, but Grbl is still processing the last commands.
    def _set_streaming_complete(self, a):
        self._streaming_complete = a
        self.callback("on_log", "{}: Streaming completed: {}".format(self.name, a))
        
        
    # Grbl has finished processing everything
    def _set_job_finished(self, a):
        self._job_finished = a
        self.callback("on_log", "{}: Job finished: {}".format(self.name, a))
        

    def _default_callback(self, status, *args):
        print("DEFAULT CALLBACK", status, args)
        
        
    def test1(self):
        self.send(";Pocket")
        self.send("G0 X0")
        for y in range(0, 100, 6):
            self.send("G0 Y{:0.3f}".format(y))
            self.send("G0 X50 ; a lot of comments here")
            self.send("; a lot of comments here")
            self.send("")
            self.send("G0 Y{:0.3f}".format(y+3))
            self.send("G0 X0")
            
    def test2(self):
        allcode = ";blah"
        allcode = "\n"
        allcode += "G0 X0\n"
        for y in range(0, 100, 6):
            allcode += "G0 Y{:0.3f}\n".format(y)
            allcode += "G0 X50 ; a lot of comments here\n"
            allcode += "; a lot of comments here\n"
            allcode += "\n\n"
            allcode += "G0 Y{:0.3f}\n\n\n\n".format(y+3)
            allcode += "G0 X0\n"
        self.send(allcode)