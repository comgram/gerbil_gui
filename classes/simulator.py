import logging
import numpy as np
import ctypes
import sys
import math

from PyQt5.QtCore import pyqtSignal, QPoint, Qt, QSize
from PyQt5.QtGui import QColor, QMatrix4x4, QVector2D, QVector3D, QQuaternion
from PyQt5.QtOpenGL import QGLWidget

import OpenGL
OpenGL.ERROR_CHECKING = True
OpenGL.FULL_LOGGING = True
from OpenGL.GL import *


class Simulator(QGLWidget):
    xRotationChanged = pyqtSignal(int)
    yRotationChanged = pyqtSignal(int)
    zRotationChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super(Simulator, self).__init__(parent)
        print(glGetString(GL_EXTENSIONS))
        
        self.colors = [ (1,0,0,1) ]
        self.positions = [ (0,0) ]
        self._linecount = len(self.positions)
        
        self.data = np.zeros(self._linecount, [("position", np.float32, 2), ("color",    np.float32, 4)])
        self.data['color']    = self.colors
        self.data['position'] = self.positions
        
        self._mouse_rotation_start_vec = QVector3D()
        
        self._rotation_quat = QQuaternion()
        self._rotation_quat_start = self._rotation_quat
        
        self._rotation_axis = QVector3D()
        
        self.width = 100
        self.height = 100
        self.model_rotation = 0
        
        self.draw_grid()


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
        
        glBindBuffer(GL_ARRAY_BUFFER, self.buffer_label)

        glEnable (GL_LINE_SMOOTH)
        glEnable (GL_BLEND)
        glBlendFunc (GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glHint (GL_LINE_SMOOTH_HINT, GL_DONT_CARE)
        glLineWidth (1)
        
        
    def wipe(self):
        self.colors = []
        self.positions = []
        
        
    def add_vertex(self, tuple):
        glBufferData(GL_ARRAY_BUFFER, self.data.nbytes, None, GL_DYNAMIC_DRAW) #https://www.opengl.org/wiki/Buffer_Object_Streaming#Buffer_update
        
        tuple = (tuple[0], tuple[1])
        self.positions.append(tuple)
        self.colors.append((1, 1, 1, 1))
        self._linecount = len(self.positions)
        
        self.data = np.zeros(self._linecount, [("position", np.float32, 2), ("color",    np.float32, 4)])
        self.data['color']    = self.colors
        self.data['position'] = self.positions
        
    def _setup_buffer(self):
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
        
        #loc = glGetUniformLocation(self.program, "scale")
        #glUniform1f(loc, 0.01)
        
        # MODEL MATRIX BEGIN ==========
        #qu_rot = QQuaternion.fromAxisAndAngle(self._rotation_axis, self.model_rotation)
        mat_m = QMatrix4x4()
        #mat_m.rotate(self.model_rotation, QVector3D(0, 1, 0))
        mat_m.rotate(self._rotation_quat)
        mat_m = self.qt_mat_to_array(mat_m)
        loc_mat_m = glGetUniformLocation(self.program, "mat_m")
        glUniformMatrix4fv(loc_mat_m, 1, GL_TRUE, mat_m)
        # MODEL MATRIX END ==========
        
        # VIEW MATRIX BEGIN ==========
        mat_v = QMatrix4x4()
        mat_v.lookAt(QVector3D(10, 10, 10), QVector3D(0, 0, 0), QVector3D(0, 0, 1))
        mat_v = self.qt_mat_to_array(mat_v)
        loc_mat_v = glGetUniformLocation(self.program, "mat_v")
        glUniformMatrix4fv(loc_mat_v, 1, GL_TRUE, mat_v)
        # VIEW MATRIX END ==========
        
        # PROJECTION MATRIX BEGIN ==========
        aspect = self.width / self.height
        mat_p = QMatrix4x4()
        mat_p.perspective(90, aspect, 1, 100)
        mat_p = self.qt_mat_to_array(mat_p)
        loc_mat_p = glGetUniformLocation(self.program, "mat_p")
        glUniformMatrix4fv(loc_mat_p, 1, GL_TRUE, mat_p)
        # PROJECTION MATRIX END ==========
        


    def paintGL(self):
        #print("paintGL")
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)        
        self._setup_buffer()
        glDrawArrays(GL_LINE_STRIP, 0, self._linecount)
        # swapping buffer automatically by Qt


    def resizeGL(self, width, height):
        print("resizeGL")
        self.width = width
        self.height = height
        
        glViewport(0, 0, width, height)


    def mousePressEvent(self, event):
        x = event.localPos().x()
        y = event.localPos().y()
        self._mouse_rotation_start_vec = self._find_ball_vector(x, y)
        #print("START VEC", self._mouse_rotation_start_vec)
        self._rotation_quat_start = self._rotation_quat
        #print("START QUAT", self._rotation_quat_start)
        
        
    def mouseReleaseEvent(self, event):
        pass


    def mouseMoveEvent(self, event):
        x = event.localPos().x()
        y = event.localPos().y()
        mouse_rotation_current_vec = self._find_ball_vector(x, y)
        #print("MOVE VEC", mouse_rotation_current_vec)
        angle = 10 * math.fmod( 4 * self.angle_between(self._mouse_rotation_start_vec, mouse_rotation_current_vec), 2 * math.pi)
        print("ANGLE", angle)
        
        delta = QQuaternion.fromAxisAndAngle(QVector3D.crossProduct(self._mouse_rotation_start_vec, mouse_rotation_current_vec), angle)
        
        delta.normalize()
        print("DELTA", delta, self._rotation_quat_start)
        
        self._rotation_quat = delta * self._rotation_quat_start
        #self._rotation_quat.normalize()

    
    def draw_grid(self):
        #self.add_vertex((0, 0))
        #self.add_vertex((1000, 1000))
        #self.add_vertex((9.9, 9.9))
        #self.add_vertex((-9.9, -9.9))
        #return
        for i in range(10):
            dir = 1 if (i % 2) == 0 else -1
            self.add_vertex((i, 10 * dir))
            self.add_vertex((i + 1, 10 * dir))
        
    def qt_mat_to_array(self, mat):
        #arr = [[0 for x in range(4)] for x in range(4)]
        arr = [0] * 16
        for i in range(4):
            for j in range(4):
                idx = 4 * i + j
                arr[idx] = mat[i, j]
        return arr
    
    def _project_to_sphere(self, x, y):
        r = 0.8
        d = math.sqrt(x*x + y*y)
        if d < r * 0.70710678118654752440:
            # inside sphere
            z = math.sqrt(r*r - d*d)
        else:
            # hyperbola
            t = r / 1.41421356237309504880
            z = t*t / d
            
        vec = QVector3D(x, y, z)
        #vec.normalize()
        return vec
    
    
    def _find_ball_vector(self, px, py):
        x = px / (self.width / 2) - 1
        y = 1 - py / (self.height / 2)
        
        if self.width < self.height:
            x *= self.width / self.height
        else:
            y *= self.height / self.width
        
        z2 = 1 - x * x - y * y
        if z2 > 0:
            z = math.sqrt(z2)
        else:
            # clamp to zero
            z = 0
            
        vec = QVector3D(x, y, z)
        vec.normalize()
        #print("HERE", x, y, z, vec)
        return vec
                

    def angle_between(self, v1, v2):
        return math.acos(QVector3D.dotProduct(v1, v2) / (v1.length() * v2.length()))