import logging
import numpy as np
import ctypes
import sys

from PyQt5.QtCore import pyqtSignal, QPoint, Qt, QSize
from PyQt5.QtGui import QColor
from PyQt5.QtOpenGL import QGLWidget

import OpenGL
OpenGL.ERROR_CHECKING = False
OpenGL.FULL_LOGGING = False
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
        
        self.colors = [ (1,0,0,1), (0,1,0,1), (0,0,1,1), (1,1,1,1), (1,1,1,1), (1,0,0,1) ]
        self.positions = [ (-1,-1),   (-0.5,+1),   (+1,-1),   (+0.7,+0.6), (-1,-1), (-0.7,+0.7)   ]
        self._linecount = len(self.positions)
        
        self.data = np.zeros(self._linecount, [("position", np.float32, 2), ("color",    np.float32, 4)])
        self.data['color']    = self.colors
        self.data['position'] = self.positions
        
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
        
        
        self.program  = glCreateProgram()
        vertex   = glCreateShader(GL_VERTEX_SHADER)
        fragment = glCreateShader(GL_FRAGMENT_SHADER)
        
        
        
        # Set shaders source
        with open("vertex.c", "r") as f: vertex_code = f.read()
        with open("fragment.c", "r") as f: fragment_code = f.read()
        glShaderSource(vertex, vertex_code)
        glShaderSource(fragment, fragment_code)
        
        # Compile shaders
        glCompileShader(vertex)
        glCompileShader(fragment)
        
        glAttachShader(self.program, vertex)
        glAttachShader(self.program, fragment)
        
        glLinkProgram(self.program)
        
        glDetachShader(self.program, vertex)
        glDetachShader(self.program, fragment)
        
        glUseProgram(self.program)
        
        # Request a buffer_label slot from GPU
        self.buffer_label = glGenBuffers(1)
        #print("XXXXXXXXXX BUF", self.buffer_label)
        
        glBindBuffer(GL_ARRAY_BUFFER, self.buffer_label)

      
        
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
        #print("XXXXXXXXXX DOUBLE", self.doubleBuffer())
        
    def add_vertex(self, tuple):
        #self.colors = [ (1,0,0,1), (0,1,0,1), (0,0,1,1), (1,1,0,1) ]
        #self.positions = [ (-1,-1),   (-1,+1),   (+1,-1),   (+1,+1)   ]
        
        glBufferData(GL_ARRAY_BUFFER, self.data.nbytes, None, GL_DYNAMIC_DRAW) #https://www.opengl.org/wiki/Buffer_Object_Streaming#Buffer_update
        
        self.positions.append(tuple)
        self.colors.append((1, 1, 1, 1))
        self._linecount = len(self.positions)
        
        self.data = np.zeros(self._linecount, [("position", np.float32, 2), ("color",    np.float32, 4)])
        self.data['color']    = self.colors
        self.data['position'] = self.positions
        #glInvalidateBufferData(self.buffer_label)
        
    def _setup_buffer(self):
        #print("XXXXXXXXXXXXXXX" + str(self.data.nbytes))
         
        glBufferData(GL_ARRAY_BUFFER, self.data.nbytes, self.data, GL_DYNAMIC_DRAW)
        
        stride = self.data.strides[0]
        
        offset = ctypes.c_void_p(0)
        loc = glGetAttribLocation(self.program, "position")
        glEnableVertexAttribArray(loc)
        glBindBuffer(GL_ARRAY_BUFFER, self.buffer_label)
        glVertexAttribPointer(loc, 3, GL_FLOAT, False, stride, offset)

        offset = ctypes.c_void_p(self.data.dtype["position"].itemsize)
        loc = glGetAttribLocation(self.program, "color")
        glEnableVertexAttribArray(loc)
        glBindBuffer(GL_ARRAY_BUFFER, self.buffer_label)
        glVertexAttribPointer(loc, 4, GL_FLOAT, False, stride, offset)
        
        loc = glGetUniformLocation(self.program, "scale")
        glUniform1f(loc, 0.01)


    def paintGL(self):
        #print("paintGL")
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
        
        self._setup_buffer()
        glDrawArrays(GL_LINE_STRIP, 0, self._linecount)

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