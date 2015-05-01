import logging
import numpy as np
import ctypes
import sys
import math

from PyQt5.QtCore import pyqtSignal, QPoint, Qt, QSize, QTimer
from PyQt5.QtGui import QColor, QMatrix4x4, QVector2D, QVector3D, QQuaternion
from PyQt5.QtOpenGL import QGLWidget

import OpenGL
OpenGL.ERROR_CHECKING = False
OpenGL.FULL_LOGGING = False
from OpenGL.GL import *

from .item import *


class SimulatorWidget(QGLWidget):
    def __init__(self, parent=None):
        super(SimulatorWidget, self).__init__(parent)
        print(glGetString(GL_EXTENSIONS))
        
        # Rotation state
        self._mouse_rotation_start_vec = QVector3D()
        self._rotation_quat = QQuaternion()
        self._rotation_quat_start = self._rotation_quat
        
        # Translation state
        self._translation_vec = QVector3D()
        self._translation_vec_start = self._translation_vec
        
        # Zoom state
        self._zoom = 100
        
        self.buffer_labels = [None] * 2

        self._rotation_axis = QVector3D()
        
        self.width = 100
        self.height = 100
        self.model_rotation = 0
        
        #self.draw_grid()
        
        self.draw_asap = True
        self.load_geometry_asap = True
        
        ## TIMER SETUP BEGIN ----------
        self.timer = QTimer()
        self.timer.timeout.connect(self._timer_timeout)
        ## TIMER SETUP END ----------

        self.program = None
        
        self.items = {}


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
        
        glEnable(GL_DEPTH_TEST)
        glEnable (GL_BLEND)
        glBlendFunc (GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        glEnable (GL_LINE_SMOOTH)
        glHint (GL_LINE_SMOOTH_HINT, GL_DONT_CARE)
        
        glClearColor(0, 0, 0, 1.0)

        self.create_items()
        self.timer.start(10)
        
        
    def create_items(self):
        #self.draw_coordinate_system("blah", (1, 1, 1))
        self.items["csm"] = CoordSystem(self.program, 12, (0, 0, 0))
        self.items["csm"].linewidth = 6
        #self.items["cs2"] = CoordSystem(self.program, 0.2, (1, 1, 1))
        self.items["grid1"] = Grid(self.program, (0, 0), (800, 1400), (-800, -1400, 0))


    def paintGL(self):
        """
        Auto-called by updateGL
        """
        print("paintGL")
        
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        # VIEW MATRIX BEGIN ==========
        mat_v = QMatrix4x4()
        mat_v.translate(self._translation_vec)
        mat_v.rotate(self._rotation_quat)
        mat_v = Item.qt_mat_to_array(mat_v)
        loc_mat_v = glGetUniformLocation(self.program, "mat_v")
        glUniformMatrix4fv(loc_mat_v, 1, GL_TRUE, mat_v)
        # VIEW MATRIX END ==========
        
        # PROJECTION MATRIX BEGIN ==========
        aspect = self.width / self.height
        mat_p = QMatrix4x4()
        mat_p.perspective(90, aspect, 0.1, 1000)
        mat_p = Item.qt_mat_to_array(mat_p)
        loc_mat_p = glGetUniformLocation(self.program, "mat_p")
        glUniformMatrix4fv(loc_mat_p, 1, GL_TRUE, mat_p)
        # PROJECTION MATRIX END ==========
        
        # DRAW ITEMS BEGIN ===============
        for key, obj in self.items.items():
            obj.draw()
        # DRAW ITEMS END ===============
      
        
        # swapping buffer automatically by Qt


    def resizeGL(self, width, height):
        print("resizeGL")
        self.width = width
        self.height = height
        self.aspect = width / height
        glViewport(0, 0, width, height)


    def mousePressEvent(self, event):
        btns = event.buttons()
        x = event.localPos().x()
        y = event.localPos().y()
        
        if btns & Qt.LeftButton:
            self._mouse_rotation_start_vec = self._find_ball_vector(x, y)
            self._rotation_quat_start = self._rotation_quat
            
        elif btns & (Qt.LeftButton | Qt.MidButton):
            self._mouse_translation_vec_current = QVector3D(x, -y, 0)
            self._translation_vec_start = self._translation_vec
        
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        
        if delta > 0:
            self._zoom = self._zoom * 1.1 #if self._zoom < 20 else self._zoom
        else:
            self._zoom = self._zoom * 0.9 #if self._zoom > 0.01 else self._zoom

        print(self._zoom)
        
        self._translation_vec = QVector3D(
            self._translation_vec[0],
            self._translation_vec[1],
            self._translation_vec[2] + delta / self._zoom
            )
        
        self.draw_asap = True
            
            
    def mouseReleaseEvent(self, event):
        pass


    def mouseMoveEvent(self, event):
        btns = event.buttons()
        x = event.localPos().x()
        y = event.localPos().y()
        
        if btns & Qt.LeftButton:
            mouse_rotation_current_vec = self._find_ball_vector(x, y)
            angle_between = self.angle_between(mouse_rotation_current_vec, self._mouse_rotation_start_vec)
            angle = 10 * math.fmod( 4 * angle_between, 2 * math.pi)
            crossproduct = QVector3D.crossProduct(
                self._mouse_rotation_start_vec,
                mouse_rotation_current_vec
                )
            delta = QQuaternion.fromAxisAndAngle(crossproduct, angle)
            delta.normalize()            
            self._rotation_quat = delta * self._rotation_quat_start
            self._rotation_quat.normalize()
            
        elif btns & (Qt.LeftButton | Qt.MidButton):
            self._translation_vec = self._translation_vec_start + (QVector3D(x, -y, 0) - self._mouse_translation_vec_current) / self._zoom * 2
            #self._translation_vec
        
        self.draw_asap = True
        
        
    def _timer_timeout(self):
        """
        called regularly from timer
        """
        #if self.load_geometry_asap:
            #self._load_geometry()
            #self.load_geometry_asap = False
            #self.draw_asap = True
            
        if self.draw_asap:
            self.updateGL()
            self.draw_asap = False
        
        
    def wipe(self):
        self.load_geometry_asap = True
        
        
    def draw_coordinate_system(self, key, tpl_origin):
        if key in self.items:
            #update
            self.items[key].moveto(tpl_origin)
        else:
            # create
            self.items[key] = CoordSystem(self.program, 6, tpl_origin)
        self.draw_asap = True
    
            
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
        y = 1-py / (self.height / 2)
        
        #if self.width < self.height:
            #x *= self.width / self.height
        #else:
            #y *= self.height / self.width
        
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