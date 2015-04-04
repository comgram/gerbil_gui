from gi.repository import Gtk
import time
import logging

from classes.grbl import GRBL


class MainWindow(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title="Hello World")
        
        self.box = Gtk.Box(spacing=6)
        self.add(self.box)

        self.label = Gtk.Label()
        self.label.set_text("This is a left-justified label.\nWith multiple lines.")
        self.box.pack_start(self.label, True, True, 0)
        
        self.grbl = GRBL("grbl1", "/dev/ttyACM0", self.on_state_update)
        self.grbl.cnect()
        time.sleep(1)
        self.grbl.poll_start()
        
        self.button = Gtk.Button(label="Click Here")
        self.button.connect("clicked", self.on_button_clicked)
        self.box.pack_start(self.button, True, True, 0)
        
        self.connect("delete-event", self.on_quit)
        
    def on_state_update(self, mode, mpos, wpos):
        self.label.set_text(str(mpos))
        
    def on_quit(self, *args):
        logging.info("Quitting")
        self.grbl.disconect()
        Gtk.main_quit(*args)

    def on_button_clicked(self, widget):
        self.grbl.send("f:out.ngc")

    #def on_button2_clicked(self, widget):
        #print("Goodbye")