from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QLineEdit)

class CommandLineEdit(QLineEdit):
    def __init__(self, parent, callback):
        super(CommandLineEdit, self).__init__(parent)
        
        self.callback = callback
        self.parent = parent
       
    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Up:
            self.callback("UP")
        elif key == Qt.Key_Down:
            self.callback("DOWN")
        elif key == Qt.Key_Enter:
            self.callback("Enter")
        elif key == Qt.Key_Return:
            self.callback("Enter")
        QLineEdit.keyPressEvent(self, event)