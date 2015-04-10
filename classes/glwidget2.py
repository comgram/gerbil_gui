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
from OpenGL.GLUT import *




class GLWidget(QGLWidget):


    def __init__(self, parent=None):
        super(GLWidget, self).__init__(parent)
        print(glGetString(GL_EXTENSIONS))
       

    def minimumSizeHint(self):
        return QSize(50, 50)

    def sizeHint(self):
        return QSize(400, 400)

    def initializeGL(self):
        
        print("OPENGL VERSION", glGetString(GL_VERSION))
        print("OPENGL VENDOR", glGetString(GL_VENDOR))
        print("OPENGL RENDERER", glGetString(GL_RENDERER))
        
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
        glUniform1f(loc, 1.0)
        
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
        glClear(GL_COLOR_BUFFER_BIT)
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

    def resizeGL(self, width, height):
        print("resizeGL")
        glViewport(0, 0, width, height)

    