import serial
import time
import multiprocessing
import signal
import logging

class RS232:
    def __init__(self, name="", path="/dev/null", baud=115200, callback=None):
        self.name = name
        self.path = path
        self.baud = baud
        self.cb = callback
        self.buf_receive = ""
        
    def start(self):
        logging.info("%s connecting to %s", self.name, self.path)
        self.serialport = serial.Serial(self.path, self.baud, timeout=None)
        self.serial_process = multiprocessing.Process(target=self.receiving)
        self.serial_process.start()
        print self.serial_process, self.serial_process.is_alive()
        
    def stop(self):
        self.cleanup()
        
        logging.info("%s disconnecting from %s", self.name, self.path)
        self.serialport.close()
        self.serial_process.terminate()
        time.sleep(1)
        isalive = self.serial_process.is_alive()
        if isalive == False:
            logging.info("%s has successfully terminated", self.serial_process)
        else:
            logging.info("WARNING! %s has not terminated within 1 second", self.serial_process)
        
    def cleanup(self):
        logging.info("%s: cleaning up before disconnecting", self.name)
        self.write("!\r\n") # feed hold
        logging.info("%s: ready to be disconnected", self.name)
        
    def write(self, data):
        logging.info("%s writing %s", self.name, data)
        self.serialport.write(data)

    def receiving(self):
        while True:
            data = self.serialport.read(1)
            waiting = self.serialport.inWaiting()
            data += self.serialport.read(waiting)
            self.handle_data(data)
            
    def handle_data(self, data):
        for i in range(0, len(data)):
            self.buf_receive += data[i]
            if data[i] == "\n":
                self.cb(self.buf_receive.strip())
                self.buf_receive = ""
        
