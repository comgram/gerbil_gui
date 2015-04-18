from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget

class JogWidget(QWidget):
    def __init__(self, parent, callback):
        super(JogWidget, self).__init__(parent)
        
        self.parent = parent
        self.callback = callback
        
        self.wx_current = 0
        self.wy_current = 0
        self.wz_current = 0
        
        self._x_start_screen = 0
        self._y_start_screen = 0
        
        
    def mousePressEvent(self, event):
        #self.callback("G91") # incremental coordinates
        pos = event.pos()
        self._x_start_screen = pos.x()
        self._y_start_screen = pos.y()
        self._relative_origin_x = self.wx_current
        self._relative_origin_y = self.wy_current
        #self._relative_origin_z = self.wz_current
        
        
    def mouseReleaseEvent(self, event):
        """
        Safe Feed
        """
        self.callback("F100")
        
        
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        z_goto = self.wz_current + delta / 1000
        self.callback("G0 Z{:0.2f}".format(z_goto))
       
    def mouseMoveEvent(self, event):
        pos = event.pos()
        x_current_screen = pos.x()
        y_current_screen = pos.y()
        x_goto = self._relative_origin_x + (x_current_screen - self._x_start_screen) / 20
        y_goto = self._relative_origin_y + (self._y_start_screen - y_current_screen) / 20
        self.callback("G1 X{:0.2f} Y{:0.2f} F2000".format(x_goto, y_goto))