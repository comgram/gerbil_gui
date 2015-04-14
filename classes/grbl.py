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
        self._rx_buffer_backlog_line_number = []
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

        self.connected = False
        self._streamed_bytes = 0 # to calculate progress percentage when streaming a file
        self._streamed_lines = 0 # keep track of the line number in a file
        self._added_lines = 0 # lines submitted as string to the `send()` method
        
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
        
        if self._iface == None:
            self.callback("on_log", "{}: Setting up interface on {}".format(self.name, self._ifacepath))
            self._iface = RS232("serial_" + self.name, self._ifacepath, 115200)
            self._iface.start(self._queue)
        else:
            self.callback("on_log", "{}: Cannot start another interface. There is already an interface {}. This should not have happened.".format(self.name, self._iface))
            
        self._iface_read_do = True
        self._thread_read_iface = threading.Thread(target=self._onread)
        self._thread_read_iface.start()
        
        self._callback_onboot = self.poll_start
        #self.softreset()
        
        
    def disconnect(self):
        """
        This method stops all threads, joins them, then closes the serial connection.
        """
        if self.is_connected() == False: return
        
        self.poll_stop()
        
        self._iface.stop()
        self._iface = None
        
        self.callback("on_log", "{}: Please wait until reading thread has joined...".format(self.name))
        self._iface_read_do = False
        self._queue.put("dummy_msg_for_joining_thread")
        self._thread_read_iface.join()
        self.callback("on_log", "{}: Reading thread successfully joined.".format(self.name))
        
        self.connected = False
        
        self._cleanup()
        
        self.callback("on_disconnected")
        
        
    def abort(self):
        """
        An alias for `softreset()`, but also performs cleaning up.
        """
        if self.is_connected() == False: return
        self.softreset()
        self._cleanup()
        
        
    def hold(self):
        """
        An alias for sending an exclamation mark.
        """
        if self.is_connected() == False: return
        self._iface_write("!")
        
        
    def resume(self):
        """
        An alias for sending a tilde.
        """
        if self.is_connected() == False: return
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
        if self.is_connected() == False: return
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
        if self.is_connected() == False: return
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
        logging.log(260, "Setting feed_override to %s", val)
        self._feed_override = val
        
        
    def set_feed(self, requested_feed):
        """
        Override the feed speed (in mm/min). Effecive only when you set `set_feed_override(True)`.
        An 'overriding' F gcode command will be inserted into the stream only when the currently
        requested feed differs from the last requested feed.
        """
        logging.log(260, "Setting _requested_feed to %s", requested_feed)
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
        
        - An argument other than a string is rejected.
        - A single command does not have to be newline-terminated.
        - To send multiple commands in one go, separate them by newlines.
        - Gcode comments (semicolon and parentesis) will be filtered out before submission to Grbl
        """
        if self.is_connected() == False: return
    
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
            self.callback("on_log", "{}: You can't append something to a running file stream. You only can append to a string stream. Please wait until the current job has completed or call .abort() for Grbl to become idle".format(self.name))
            return False
        
        self._streaming_mode = requested_mode
        
        if self._streaming_mode == "string":
            arr = source.split("\n")
            self._added_lines += len(arr) # for percentage calculation
            self._buffer.extend(arr)
        
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
            self._stream() # only needed at beginning, because once the streaming is kicked off, it is self-sustaining via the `handle_ok()` callback
            self._set_job_finished(False)



    # ====== 'private' methods ======
        
    def _stream(self):
        """
        Take commands from _buffer and send them to Grbl, either one-by-one, or until
        its buffer is full.
        """
        if self._streaming_src_end_reached:
            logging.log(200, "%s: _stream(): Nothing more in _buffer. Doing nothing")
            return
        
        if self._incremental_streaming:
            self._set_next_line()
            if self._streaming_src_end_reached == False:
                self._send_current_line()
                
        else:
            self._fill_rx_buffer_until_full()

        
        
    def _fill_rx_buffer_until_full(self):
        """
        Does what the function name says.
        """
        while True:
            if self._current_line_sent == True:
                self._set_next_line()
            
            if self._streaming_src_end_reached == False and self._rx_buf_can_receive_current_line():
                self._send_current_line()
            else:
                break
                
                
                
    def _set_next_line(self):
        """
        Gets next line from file or _buffer, and sets _current_gcodeblock
        """

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
                
        else:
            # string streaming mode progress percentage is based on line numbers
            progress_percent = int(100 * self._streamed_lines / self._added_lines)
            self.callback("on_progress_percent", progress_percent)

        if len(self._buffer) > 0:
            # still something in _buffer, pop it
            line = self._buffer.pop(0).strip()
            preprocessed_line = self._preprocess(line)
            self._current_line = preprocessed_line
            self._current_line_sent = False
                
        else:
            # the buffer is empty, nothing more to read
            self._set_streaming_src_end_reached(True)

        
    def _send_current_line(self):
        """
        Unconditionally sends the current line to Grbl.
        """
        self._set_streaming_complete(False)
        line_length = len(self._current_line) + 1 # +1 for \n which we will append below
        self._rx_buffer_fill.append(line_length) 
        self._rx_buffer_backlog.append(self._current_line)
        self._rx_buffer_backlog_line_number.append(self._streamed_lines)
        self._iface_write(self._current_line + "\n")
        self._current_line_sent = True
        self._streamed_lines += 1
    
    
    def _rx_buf_can_receive_current_line(self):
        """
        Returns True or False depeding on Grbl's rx buffer can hold _current_line
        """
        rx_free_bytes = self._rx_buffer_size - sum(self._rx_buffer_fill)
        required_bytes = len(self._current_line) + 1 # +1 because \n
        return rx_free_bytes >= required_bytes
    
    
    
    def _preprocess(self, line):
        """
        This removes comments and spaces, parses gcode to keep track of some G codes,
        and does feed override.
        """
        
        # strip comments (after semicolon and opening parenthesis)
        line = re.match("([^;(]*)", line).group(1)
        
        # strip
        line = line.strip()
        
        # remove whitespaces
        line = line.replace(" ", "")
        
        # check for $ settings
        contains_setting = re.match("\$[^CXHG$#]", line)
        if contains_setting and self._incremental_streaming == False:
            self.callback("on_log", "{}: I encountered a settings command '{}' in the gcode stream but the current streaming mode is not set to incremental. Grbl cannot handle that. I will not send the $ command.".format(self.name, line))
            line = ""
            
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
        
        # Update the UI for detected feed
        if contains_feed:
            if self._feed_override == False:
                parsed_feed = re.match(".*F([.\d]+)", line).group(1)
                self._current_feed = float(parsed_feed)
                self.callback("on_feed_change", self._current_feed)
                #self.callback("on_log", "FEED" + str(self._current_feed))
            
        if self._feed_override == True:
            if self._requested_feed:
                if contains_feed:
                    # strip the original F setting
                    line = re.sub(r"F[.\d]+", "", line)
                    
                if self._current_feed != self._requested_feed:
                    line += "F{:0.1f}".format(self._requested_feed)
                    self._current_feed = self._requested_feed
                    self.callback("on_log", "OVERRIDING FEED: " + str(self._current_feed))

        return line
    
        
    def _rx_buffer_fill_pop(self):
        """
        We keep a backlog (_rx_buffer_fill) of command sizes in bytes to know at any time
        how full Grbl's rx buffer is. Once we receive an 'ok' from Grbl, we can remove the first
        element in this backlog.
        """
            
        if len(self._rx_buffer_fill) > 0:
            self._rx_buffer_fill.pop(0)
            processed_command = self._rx_buffer_backlog.pop(0)
            processed_line = self._rx_buffer_backlog_line_number.pop(0)
            self.callback("on_processed_command", processed_line, processed_command)
            
        if self._streaming_src_end_reached == True and len(self._rx_buffer_fill) == 0:
            self._set_job_finished(True)
            self._set_streaming_complete(True)
            self.callback("on_log", "{}: Job completed".format(self.name))
    
    
    def _iface_write(self, data):
        """
        A convenient wrapper around _iface.write with a callback for UI's
        """
        num_written = self._iface.write(data)
        self.callback("on_send_command", data.strip())
        
        
    def _onread(self):
        """
        This method is run in a separate Thread. It blocks at the line queue.get() until
        the RS232 object put()'s something into this queue asynchronously. It's an endless
        loop, interruptable by setting _iface_read_do to False.
        """
        while self._iface_read_do == True:
            line = self._queue.get()
            
            if len(line) > 0:
                if line[0] == "<":
                    self._update_state(line)
                    
                elif "Grbl " in line:
                    if self.connected == False:
                        logging.log(200, "%s <----- %s", self.name, line)
                        self._on_bootup()
                    else:
                        logging.log(200, "%s Got second bootup message but already connected. Ignoring.", self.name)
                    
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
                        problem_line = self._rx_buffer_backlog_line_number[0]
                        self.callback("on_error", line, problem_command, problem_line)
                    else:
                        self.callback("on_log", "{}: Receiving additional errors: {}".format(self.name, line))
                        
                else:
                    logging.log(200, "%s <----- %s", self.name, line)
                    self.callback("on_read", line)
                
                
    def _handle_ok(self):
        """
        When we receive an 'ok' from Grbl, submit more.
        """

        if self._error == False:
            if self._streaming_complete == False:
                self._rx_buffer_fill_pop()
                if not (self._wait_empty_buffer and len(self._rx_buffer_fill) > 0):
                    self._wait_empty_buffer = False
                    self._stream()
                    
            else:
                logging.log(200, "%s handle_ok(): Streaming is already completed, Grbl is just sending OK's for the commands in its buffer.", self.name)
                
        else: 
            self.callback("on_log", "{}: GRBL class is in state of error, will not send any more. Please reset/abort before you can continue.".format(self.name))
        
        self._rx_buffer_fill_percent = int(100 - 100 * (self._rx_buffer_size - sum(self._rx_buffer_fill)) / self._rx_buffer_size)
        self.callback("on_rx_buffer_percentage", self._rx_buffer_fill_percent)
                
                            
    def _on_bootup(self):
        """
        Inform UI and bring distance modes to absolute.
        """
        self.connected = True
        self.callback("on_log", "{}: Booted!".format(self.name))
        self._callback_onboot()
        self.callback("on_boot")
        #self.send("G90")
        #self.send("G90.1")
            
            
    def _update_state(self, line):
        """
        Parse Grbl's status line and inform via callback
        """
        m = re.match("<(.*?),MPos:(.*?),WPos:(.*?)>", line)
        self.cmode = m.group(1)
        mpos_parts = m.group(2).split(",")
        wpos_parts = m.group(3).split(",")
        self.cmpos = (float(mpos_parts[0]), float(mpos_parts[1]), float(mpos_parts[2]))
        self.cwpos = (float(wpos_parts[0]), float(wpos_parts[1]), float(wpos_parts[2]))
        #self.callback("on_log", "=== STATE === %s %s %s", self.name, self.cmode, self.cmpos, self.cwpos)
        self.callback("on_stateupdate", self.cmode, self.cmpos, self.cwpos)
        
        
    def is_connected(self):
        if self.connected != True:
            self.callback("on_log", "{}: Not yet connected".format(self.name))
        return self.connected
    
    
    def _cleanup(self):
        del self._buffer[:]
        del self._rx_buffer_fill[:]
        del self._rx_buffer_backlog[:]
        del self._rx_buffer_backlog_line_number[:]
        
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
        self._streamed_lines = 0
        self._added_lines = 0
        self._clear_queue()
        
        
    def _clear_queue(self):
        try:
            junk = self._queue.get_nowait()
            logging.log(260, "Discarding junk %s", junk)
        except:
            logging.log(260, "Queue was empty")
            
            
    def _poll_state(self):
        while self._poll_do == True:
            self._get_state()
            time.sleep(self.poll_interval)
        self.callback("on_log", "{}: Polling has been stopped".format(self.name))
        
        
    def _get_state(self):
        if self.is_connected() == False: return
        self._iface.write("?")
        
            
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