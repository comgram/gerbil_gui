import sys
import os
import math
import numpy
import logging

from classes.grbl import GRBL
from classes.glwidget import GLWidget

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import pyqtSignal, QPoint, QSize, Qt, QCoreApplication, QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QMessageBox, QSlider, QLabel, QPushButton, QWidget, QDialog, QMainWindow, QFileDialog, QLineEdit)

from lib.qt.cnctoolbox.ui_mainwindow import Ui_MainWindow

log_format = '%(asctime)s %(levelname)s %(message)s'
logging.basicConfig(level=300, format=log_format)


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        
        self.setupUi(self)
        
        self.grbl = GRBL()
        self.grbl.poll_interval = 0.1
        
        self.grbl.callback = self.on_grbl_event
        
        self.glWidget = GLWidget()
        
        self.grid_opengl.addWidget(self.glWidget)
        
        self.pushButton_connect.clicked.connect(self.grbl.cnect)
        self.pushButton_disconnect.clicked.connect(self.disconnect)
        self.pushButton_homing.clicked.connect(self.grbl.homing)
        self.pushButton_killalarm.clicked.connect(self.grbl.killalarm)
        self.pushButton_reset.clicked.connect(self.grbl.softreset)
        
        self.pushButton_filestream.clicked.connect(self.stream_file)
        self.pushButton_fileload.clicked.connect(self.pick_file)
        
        self.pushButton_hold.clicked.connect(self.grbl.hold)
        self.pushButton_resume.clicked.connect(self.grbl.resume)
        self.pushButton_abort.clicked.connect(self.grbl.abort)
        
        self.pushButton_zeroxyz.clicked.connect(self.zero_xyz)
        self.pushButton_zeroxy.clicked.connect(self.zero_xy)
        self.pushButton_zeroz.clicked.connect(self.zero_z)
        
        self.pushButton_w2mcoord.clicked.connect(self.w2mcoord)
        self.pushButton_g0wzerosafe.clicked.connect(self.g0wzerosafe)
        self.pushButton_g0wzero.clicked.connect(self.g0wzero)
               
        self.lineEdit_cmdline.returnPressed.connect(self.sendsingle)
        
        self.setWindowTitle("cnctoolbox")
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(20)
        
        return
    
        self.xSlider = self.createSlider()
        self.ySlider = self.createSlider()
        self.zSlider = self.createSlider()
        self.xPanSlider = self.createSlider()
        self.yPanSlider = self.createSlider()
        self.zPanSlider = self.createSlider()

        self.xSlider.valueChanged.connect(self.glWidget.setXRotation)
        self.glWidget.xRotationChanged.connect(self.xSlider.setValue)
        self.ySlider.valueChanged.connect(self.glWidget.setYRotation)
        self.glWidget.yRotationChanged.connect(self.ySlider.setValue)
        self.zSlider.valueChanged.connect(self.glWidget.setZRotation)
        self.glWidget.zRotationChanged.connect(self.zSlider.setValue)
        self.xPanSlider.valueChanged.connect(self.glWidget.setXPan)
        self.yPanSlider.valueChanged.connect(self.glWidget.setYPan)
        self.zPanSlider.valueChanged.connect(self.glWidget.setZPan)

        mainLayout = QHBoxLayout()
        mainLayout.addWidget(self.label_mpos)
        mainLayout.addWidget(self.btn_poll)
        mainLayout.addWidget(self.btn_run)
        mainLayout.addWidget(self.btn_quit)
        mainLayout.addWidget(self.glWidget)
        mainLayout.addWidget(self.xSlider)
        mainLayout.addWidget(self.ySlider)
        mainLayout.addWidget(self.zSlider)
        mainLayout.addWidget(self.xPanSlider)
        mainLayout.addWidget(self.yPanSlider)
        mainLayout.addWidget(self.zPanSlider)
        self.setLayout(mainLayout)

        self.xSlider.setValue(1 * 16)
        self.ySlider.setValue(355 * 16)
        self.zSlider.setValue(1 * 16)
        
        self.setUpdatesEnabled(True)
        
        
    def on_grbl_event(self, event, *data):
        logging.log(300, "GRBL event: %s, %s", event, data)
        if event == "on_stateupdate":
            state = data[0]
            mpos = data[1]
            wpos = data[2]
            self.lcdNumber_mx.display("{:0.2f}".format(mpos[0]))
            self.lcdNumber_my.display("{:0.2f}".format(mpos[1]))
            self.lcdNumber_mz.display("{:0.2f}".format(mpos[2]))
            self.lcdNumber_wx.display("{:0.2f}".format(wpos[0]))
            self.lcdNumber_wy.display("{:0.2f}".format(wpos[1]))
            self.lcdNumber_wz.display("{:0.2f}".format(wpos[2]))
            self.label_state.setText(state)
            self.glWidget.mpos = mpos
            self.glWidget.paintGL()
            
        elif event == "on_send_command":
            gcodeblock = data[0]
            self.label_currentgcodeblock.setText(gcodeblock)
        
        
    def pick_file(self):
        filename_tuple = QFileDialog.getOpenFileName(self, "Open File", os.getcwd(), "GCode Files (*.ngc, *.gcode, *.nc)")
        self.filename = filename_tuple[0]
        self.label_file.setText(self.filename)
    
    def stream_file(self):
        self.grbl.send("f:" + self.filename)
        
    def zero_xyz(self):
        self.grbl.send("G92 X0 Y0 Z0")
        
    def zero_xy(self):
        self.grbl.send("G92 X0 Y0")
        
    def zero_z(self):
        self.grbl.send("G92 Z0")
        
    def w2mcoord(self):
        self.grbl.send("G92.1")
        
    def g0wzerosafe(self):
        self.grbl.send("G0 Z20")
        self.grbl.send("G0 X0 Y0")
        
    def g0wzero(self):
        self.grbl.send("G0 X0 Y0 Z0")
        
    def sendsingle(self):
        cmd = self.lineEdit_cmdline.text()
        self.lineEdit_cmdline.setText("")
        self.grbl.send(cmd)
        
        
    def disconnect(self):
        self.grbl.disconnect()
        self.lcdNumber_mx.display("{:0.2f}".format(8888.88))
        self.lcdNumber_my.display("{:0.2f}".format(8888.88))
        self.lcdNumber_mz.display("{:0.2f}".format(8888.88))
        self.lcdNumber_wx.display("{:0.2f}".format(8888.88))
        self.lcdNumber_wy.display("{:0.2f}".format(8888.88))
        self.lcdNumber_wz.display("{:0.2f}".format(8888.88))
        self.label_state.setText("disconnected")
        self.label_currentgcodeblock.setText("")
        
    def refresh(self):
        self.glWidget.updateGL()
        
    def on_run_btn_clicked(self):
        self.grbl.send("f:out.ngc")
        
    def quit(self):
        QCoreApplication.instance().quit
        
    def createSlider(self):
        slider = QSlider(Qt.Vertical)

        slider.setRange(0, 360 * 16)
        slider.setSingleStep(16)
        slider.setPageStep(15 * 16)
        slider.setTickInterval(15 * 16)
        slider.setTickPosition(QSlider.TicksRight)

        return slider


