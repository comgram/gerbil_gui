import logging
import numpy as np
import ctypes
import sys

from PyQt5.QtCore import pyqtSignal, QPoint, Qt, QSize
from PyQt5.QtGui import QColor
from PyQt5.QtOpenGL import QGLWidget

import OpenGL
OpenGL.ERROR_CHECKING = True
OpenGL.FULL_LOGGING = True
from OpenGL.GL import *
#from OpenGL.GLUT import *




class GLWidget(QGLWidget):
    xRotationChanged = pyqtSignal(int)
    yRotationChanged = pyqtSignal(int)
    zRotationChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super(GLWidget, self).__init__(parent)
        print(glGetString(GL_EXTENSIONS))
        
        self.xRot = 0
        self.yRot = 0
        self.zRot = 0
        
        self.xPan = 0
        self.yPan = 0
        self.zPan = -10
        
        self.lastPos = QPoint()
       

    def minimumSizeHint(self):
        return QSize(50, 50)

    def sizeHint(self):
        return QSize(400, 400)

    def initializeGL(self):
        
        print("OPENGL VERSION", glGetString(GL_VERSION))
        print("OPENGL VENDOR", glGetString(GL_VENDOR))
        print("OPENGL RENDERER", glGetString(GL_RENDERER))
        print("OPENGL GLSL VERSION", glGetString(GL_SHADING_LANGUAGE_VERSION))
        
        
        program  = glCreateProgram()
        vertex   = glCreateShader(GL_VERTEX_SHADER)
        fragment = glCreateShader(GL_FRAGMENT_SHADER)
        
        data = np.zeros(4, [("position", np.float32, 2),
                            ("color",    np.float32, 4)])
        data['color']    = [ (1,0,0,1), (0,1,0,1), (0,0,1,1), (1,1,0,1) ]
        data['position'] = [ (-1,-1),   (-1,+1),   (+1,-1),   (+1,+1)   ]
        
        # Set shaders source
        with open("vertex.c", "r") as f: vertex_code = f.read()
        with open("fragment.c", "r") as f: fragment_code = f.read()
        glShaderSource(vertex, vertex_code)
        glShaderSource(fragment, fragment_code)
        
        # Compile shaders
        glCompileShader(vertex)
        glCompileShader(fragment)
        
        glAttachShader(program, vertex)
        glAttachShader(program, fragment)
        
        glLinkProgram(program)
        
        glDetachShader(program, vertex)
        glDetachShader(program, fragment)
        
        glUseProgram(program)
        
        # Request a buffer slot from GPU
        buffer = glGenBuffers(1)

        # Make this buffer the default one
        glBindBuffer(GL_ARRAY_BUFFER, buffer)

        # Upload data
        glBufferData(GL_ARRAY_BUFFER, data.nbytes, data, GL_DYNAMIC_DRAW)
        
        stride = data.strides[0]
        offset = ctypes.c_void_p(0)
        loc = glGetAttribLocation(program, "position")
        glEnableVertexAttribArray(loc)
        glBindBuffer(GL_ARRAY_BUFFER, buffer)
        glVertexAttribPointer(loc, 3, GL_FLOAT, False, stride, offset)

        offset = ctypes.c_void_p(data.dtype["position"].itemsize)
        loc = glGetAttribLocation(program, "color")
        glEnableVertexAttribArray(loc)
        glBindBuffer(GL_ARRAY_BUFFER, buffer)
        glVertexAttribPointer(loc, 4, GL_FLOAT, False, stride, offset)
        
        loc = glGetUniformLocation(program, "scale")
        glUniform1f(loc, 0.5)
        
        glEnable (GL_LINE_SMOOTH);
        glEnable (GL_BLEND);
        glBlendFunc (GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
        glHint (GL_LINE_SMOOTH_HINT, GL_DONT_CARE);
        glLineWidth (1);
        
        
        
        
        
        #glEnable(GL_LINE_SMOOTH);
        #glEnable(GL_POINT_SMOOTH);
        #glShadeModel(GL_SMOOTH);
        #glEnable(GL_LINE_STIPPLE);
        #glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
        #glEnable(GL_BLEND);
        
        #glClearColor(0.0, 0.0, 0.0, 1.0);
        #glClear(GL_COLOR_BUFFER_BIT);
        #glDisable(GL_DEPTH_TEST);
        
        
        ## the following settings affect the rendering quality of the mesh
        #glPolygonMode( GL_FRONT_AND_BACK, GL_FILL );

        #glEnable (GL_LINE_SMOOTH);
        #glEnable (GL_BLEND);
        #glBlendFunc (GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
        #glHint (GL_LINE_SMOOTH_HINT, GL_DONT_CARE);
        #glLineWidth (1);
        
        ##glShadeModel(GL_FLAT)
        #glEnable(GL_DEPTH_TEST)
        #glEnable(GL_CULL_FACE)
        
      
        
                
        #loc = glGetUniformLocation(program, "scale")
        #print("XXXXXXXXXXXX", loc)
        #glUniform1f(loc, 1.0)
        print("XXXXXXXXXX DOUBLE", self.doubleBuffer())
        
        

    def paintGL(self):
        print("paintGL")
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_MODELVIEW);
        glLoadIdentity();

        glMatrixMode(GL_PROJECTION);
        glLoadIdentity();
        
        # Perspective
        #gluPerspective(90.0, 2, 0.1, 1000.0);

        # Translate
        glTranslatef(self.xPan, self.yPan, self.zPan)
        
        # Scale
        #gluLookAt(0, 0, 1, 0, 0, 0, 0, 1, 0);
        
        glMatrixMode(GL_MODELVIEW);
        
        # Rotate
        glRotated(self.xRot / 16.0, 1.0, 0.0, 0.0)
        glRotated(self.yRot / 16.0, 0.0, 1.0, 0.0)
        glRotated(self.zRot / 16.0, 0.0, 0.0, 1.0)
        
        glDrawArrays(GL_LINE_STRIP, 0, 4)

    def resizeGL(self, width, height):
        print("resizeGL")
        glViewport(0, 0, width, height)
        
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(-0.1, 1.8, 1, -0.1, 4.0, 15.0)
        glMatrixMode(GL_MODELVIEW)
        
        
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
            self.zPan = val / 1000.0

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
        
    def normalizeAngle(self, angle):
        while angle < 0:
            angle += 360 * 16
        while angle > 360 * 16:
            angle -= 360 * 16
        return angle