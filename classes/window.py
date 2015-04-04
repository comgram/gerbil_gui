from gi.repository import Gtk

class MainWindow(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title="Hello World")


        self.label = Gtk.Label()
        self.label.set_text("This is a left-justified label.\nWith multiple lines.")
        self.add(self.label)

    #def on_button1_clicked(self, widget):
        #print("Hello")

    #def on_button2_clicked(self, widget):
        #print("Goodbye")