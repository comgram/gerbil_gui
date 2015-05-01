from lib.qt.cnctoolbox.ui_simulatordialog import Ui_SimulatorDialog

from .simulatorwidget import SimulatorWidget

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import pyqtSignal, QPoint, QSize, Qt, QCoreApplication, QTimer
from PyQt5.QtGui import QColor,QPalette
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QMessageBox, QSlider, QLabel, QPushButton, QWidget, QDialog, QMainWindow, QFileDialog, QLineEdit, QSpacerItem, QListWidgetItem, QMenuBar, QMenu, QAction, QTableWidgetItem, QDialog

class SimulatorDialog(QWidget, Ui_SimulatorDialog):
    def __init__(self, parent=None):
        super(SimulatorDialog, self).__init__()
        self.setupUi(self)
        
        self.checkBox_sim_enable.stateChanged.connect(self._sim_enabled_changed)
        self.pushButton_sim_wipe.clicked.connect(self._sim_wipe)
        
        ## SIMULATOR SETUP BEGIN -------------
        self._sim_enabled = True
        self.simulator_widget = SimulatorWidget()
        self.gridLayout_simulator.addWidget(self.simulator_widget)
        ## SIMULATOR SETUP END -------------
        
    def _sim_enabled_changed(self, val):
        val = False if val == 0 else True
        self._sim_enabled = val
        
    def _sim_wipe(self):
        self.simulator_widget.wipe()