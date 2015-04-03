import serial
import time
import threading
import logging

class RS232:
    def __init__(self, name="", path="/dev/null", baud=115200):
        self.name = name
        self.path = path
        self.baud = baud
        self.buf_receive = ""
        self.do_receive = False
        
        self.queue = None
        
    def start(self, q):
        self.queue = q
        logging.info("RS232 %s: connecting to %s", self.name, self.path)
        self.serialport = serial.Serial(self.path, self.baud, timeout=5)
        
        #time.sleep(0.2)
        self.serialport.flushInput()
        self.serialport.flushOutput()
        #time.sleep(0.2)
        
        self.do_receive = True
        self.serial_thread = threading.Thread(target=self.receiving)
        self.serial_thread.start()
        
    def stop(self):
        self.cleanup()
        self.do_receive = False
        logging.info("RS232 %s: stop()", self.name)
        self.serial_thread.join()
        logging.info("RS232 %s: JOINED thread", self.name)
        
    def cleanup(self):
        logging.info("RS232 %s: cleaning up", self.name)
        self.write("!") # feed hold
        logging.info("RS232 %s: ready to be disconnected", self.name)
        
    def write(self, data):
        if len(data) > 0:
            logging.info("RS232 %s:     -----------> %ibytes %s", self.name, len(data), data.strip())
            self.serialport.write(bytes(data,"ascii"))
        else:
            logging.info("RS232 %s: nothing to write", self.name)

    def receiving(self):
        while self.do_receive == True:
            logging.info("receiving...")
            data = self.serialport.read(1)
            waiting = self.serialport.inWaiting()
            data += self.serialport.read(waiting)
            self.handle_data(data)
        self.serialport.close()
            
    def handle_data(self, data):
        asci = data.decode("ascii")
        for i in range(0, len(asci)):
            char = asci[i]
            self.buf_receive += char
            if char == "\n":
                self.queue.put(self.buf_receive.strip())
                self.buf_receive = ""
