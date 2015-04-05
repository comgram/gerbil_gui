import sys
import os
import math

import logging
from classes.grbl import GRBL
import numpy

from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, QPoint, QSize, Qt, QCoreApplication, QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QMessageBox, QSlider, QLabel, QPushButton, QWidget, QDialog, QMainWindow, QFileDialog)
from PyQt5.QtOpenGL import QGLWidget

from lib.qt.cnctoolbox.ui_mainwindow import Ui_MainWindow

log_format = '%(asctime)s %(levelname)s %(message)s'
logging.basicConfig(level=300, format=log_format)

try:
    from OpenGL import GL
except ImportError:
    app = QApplication(sys.argv)
    QMessageBox.critical(None, "OpenGL hellogl",
            "PyOpenGL must be installed to run this example.")
    sys.exit(1)


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        
        self.setupUi(self)
        
        self.grbl = GRBL()
        self.grbl.poll_interval = 0.1
        
        self.grbl.callback = self.on_grbl_event
        
        self.glWidget = GLWidget()
        
        self.grid_opengl.addWidget(self.glWidget)
        
        self.pushButton_resume.clicked.connect(self.on_run_btn_clicked)
        self.pushButton_fileload.clicked.connect(self.pick_file)
        self.pushButton_connect.clicked.connect(self.grbl.cnect)
        self.pushButton_disconnect.clicked.connect(self.grbl.disconnect)
        
        return
        
        self.label_mpos = QLabel("blah", self)
        
        self.btn_poll = QPushButton("poll", self)
        self.btn_poll.clicked.connect(self.grbl.poll_start)
        
        self.btn_run = QPushButton("run", self)
        self.btn_run.clicked.connect(self.on_run_btn_clicked)
        
        self.btn_quit = QPushButton("quit", self)
        #self.btn_quit.clicked.connect(self.quit)
        
        
        

        
        self.setWindowTitle("cnctoolbox")
        

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
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(20)
        
        self.setUpdatesEnabled(True)
        
        
    def on_grbl_event(self, event, *data):
        logging.log(300, "GRBL event: %s, %s", event, data)
        if event == "on_stateupdate":
            state = data[0]
            mpos = data[1]
            wpos = data[2]
            self.lcdNumber_x.display(mpos[0])
            self.lcdNumber_y.display(mpos[1])
            self.lcdNumber_z.display(mpos[2])
            self.glWidget.paintGL()
        
        
    def pick_file(self):
        self.filename = QFileDialog.getOpenFileName(self, "Open File", os.getcwd(), "GCode Files (*.ngc)")
        self.label_file.setText(self.filename[0])
        
        
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


class GLWidget(QGLWidget):
    xRotationChanged = pyqtSignal(int)
    yRotationChanged = pyqtSignal(int)
    zRotationChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super(GLWidget, self).__init__(parent)

        self.object = 0
        self.xRot = 0
        self.yRot = 0
        self.zRot = 0
        self.xPan = 0
        self.yPan = 0
        self.zPan = 0
        
        self.mpos = (0,0,0)

        self.lastPos = QPoint()

        self.trolltechGreen = QColor.fromCmykF(0.40, 0.0, 1.0, 0.0)
        self.trolltechPurple = QColor.fromCmykF(0.39, 0.39, 0.0, 0.0)

    def minimumSizeHint(self):
        return QSize(50, 50)

    def sizeHint(self):
        return QSize(400, 400)

    def setXRotation(self, angle):
        angle = self.normalizeAngle(angle)
        if angle != self.xRot:
            self.xRot = angle
            self.xRotationChanged.emit(angle)
            #self.updateGL()

    def setYRotation(self, angle):
        angle = self.normalizeAngle(angle)
        if angle != self.yRot:
            self.yRot = angle
            self.yRotationChanged.emit(angle)
            #self.updateGL()

    def setZRotation(self, angle):
        angle = self.normalizeAngle(angle)
        if angle != self.zRot:
            self.zRot = angle
            self.zRotationChanged.emit(angle)
            #self.updateGL()
            
    def setXPan(self, val):
        if val != self.xPan:
            self.xPan = val / 1000.0
            
    def setYPan(self, val):
        if val != self.yPan:
            self.yPan = val / 1000.0
            
    def setZPan(self, val):
        if val != self.zPan:
            self.zPan = val / 1000.0 - 10

    def initializeGL(self):
        self.qglClearColor(self.trolltechPurple.darker())
        #self.object = self.makeObject()
        GL.glShadeModel(GL.GL_FLAT)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_CULL_FACE)
        #GL.glEnable(GL_POINT_SMOOTH);
        GL.glEnable(GL_LINE_SMOOTH);
        GL.glEnable(GL_POLYGON_SMOOTH);

    def paintGL(self):
        #print("paintGL")
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glLoadIdentity()
        GL.glTranslated(self.xPan, self.yPan, self.zPan)
        #GL.glTranslated(0, 0, -10)
        GL.glRotated(self.xRot / 16.0, 1.0, 0.0, 0.0)
        GL.glRotated(self.yRot / 16.0, 0.0, 1.0, 0.0)
        GL.glRotated(self.zRot / 16.0, 0.0, 0.0, 1.0)
        GL.glCallList(self.makeObject())

    def resizeGL(self, width, height):
        side = min(width, height)
        if side < 0:
            return

        GL.glViewport((width - side) // 2, (height - side) // 2, side, side)

        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GL.glOrtho(-0.5, +0.5, +0.5, -0.5, 4.0, 15.0)
        GL.glMatrixMode(GL.GL_MODELVIEW)

    def mousePressEvent(self, event):
        self.lastPos = event.pos()

    def mouseMoveEvent(self, event):
        dx = event.x() - self.lastPos.x()
        dy = event.y() - self.lastPos.y()

        if event.buttons() & Qt.LeftButton:
            self.setXRotation(self.xRot + 8 * dy)
            self.setYRotation(self.yRot + 8 * dx)
        elif event.buttons() & Qt.RightButton:
            self.setXRotation(self.xRot + 8 * dy)
            self.setZRotation(self.zRot + 8 * dx)

        self.lastPos = event.pos()

    def makeObject(self):
        #print("make object", str(self.mpos))
        
        coord = numpy.divide(self.mpos, 30)
        line_from = coord
        line_to = (coord[0], coord[1], coord[2] + 1)
        
        genList = GL.glGenLists(1)
        GL.glNewList(genList, GL.GL_COMPILE)

        GL.glBegin(GL.GL_LINES)
        #GL.glColor3d(1.0,0.0,0.0);
        GL.glVertex3d(*line_from);
        GL.glVertex3d(*line_to);
        #GL.glVertex3d(2,0,0);
        
        for i in range(0,10):
            j = i/10
            GL.glVertex3d(j, 0, 0)
            GL.glVertex3d(j, 1, 0)
            GL.glVertex3d(0, j, 0)
            GL.glVertex3d(1, j, 0)

        GL.glEnd()
        GL.glEndList()

        return genList

    def quad(self, x1, y1, x2, y2, x3, y3, x4, y4):
        self.qglColor(self.trolltechGreen)

        GL.glVertex3d(x1, y1, -0.05)
        GL.glVertex3d(x2, y2, -0.05)
        GL.glVertex3d(x3, y3, -0.05)
        GL.glVertex3d(x4, y4, -0.05)

        GL.glVertex3d(x4, y4, +0.05)
        GL.glVertex3d(x3, y3, +0.05)
        GL.glVertex3d(x2, y2, +0.05)
        GL.glVertex3d(x1, y1, +0.05)

    def extrude(self, x1, y1, x2, y2):
        self.qglColor(self.trolltechGreen.darker(250 + int(100 * x1)))

        GL.glVertex3d(x1, y1, +0.05)
        GL.glVertex3d(x2, y2, +0.05)
        GL.glVertex3d(x2, y2, -0.05)
        GL.glVertex3d(x1, y1, -0.05)

    def normalizeAngle(self, angle):
        while angle < 0:
            angle += 360 * 16
        while angle > 360 * 16:
            angle -= 360 * 16
        return angle