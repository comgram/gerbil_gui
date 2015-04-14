import re
import logging

class Preprocessor:
    def __init__(self):
        self.line = ""
        self._feed_override = False
        self._requested_feed = None
        self._current_feed = None
        
        self.callback = self._default_callback
    
    def set_feed_override(self, val):
        self._feed_override = val
        #logging.log(260, "Preprocessor: Feed override set to %s", val)
        
    def set_feed(self, val):
        self._requested_feed = val
        #logging.log(260, "Preprocessor: Feed request set to %s", val)
    
    def do(self, line):
        self.line = line
        self._strip_comments()
        self._strip()
        self._handle_feed()
        return self.line
        
    def _strip_comments(self):
        """
        strip comments (after semicolon and opening parenthesis)
        """
        self.line = re.match("([^;(]*)", self.line).group(1)

    def _strip(self):
        """
        Remove blank spaces and newlines from beginning and end,
        and remove blank spaces from the middle of the line.
        """
        self.line = self.line.strip()
        self.line = self.line.replace(" ", "")
        
        
    def _handle_feed(self):
        contains_feed = True if re.match(".*F[.\d]+", self.line) else False
        
        # Update the UI for detected feed
        if contains_feed:
            if self._feed_override == False:
                parsed_feed = re.match(".*F([.\d]+)", self.line).group(1)
                self._current_feed = float(parsed_feed)
                self.callback("on_feed_change", self._current_feed)
                #self.callback("on_log", "FEED" + str(self._current_feed))
            
        if self._feed_override == True:
            if self._requested_feed:
                if contains_feed:
                    # strip the original F setting
                    self.line = re.sub(r"F[.\d]+", "", self.line)
                    
                if self._current_feed != self._requested_feed:
                    self.line += "F{:0.1f}".format(self._requested_feed)
                    self._current_feed = self._requested_feed
                    self.callback("on_log", "OVERRIDING FEED: " + str(self._current_feed))
                    
            
            
    def _default_callback(self, status, *args):
        print("PREPROCESSOR DEFAULT CALLBACK", status, args)