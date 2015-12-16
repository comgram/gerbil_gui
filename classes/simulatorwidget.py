import logging
import numpy as np
import ctypes
import sys
import math
import re

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
        self._translation_vec = QVector3D(300, 200, -350)
        #self._translation_vec = QVector3D(0, 0, 0)
        self._translation_vec_start = self._translation_vec
        
        # Zoom state
        self._zoom = 3
        
        self.buffer_labels = [None] * 2

        self._rotation_axis = QVector3D()
        
        self.width = 100
        self.height = 100
        self.model_rotation = 0
        
        self.draw_asap = True
        
        ## TIMER SETUP BEGIN ----------
        self.timer = QTimer()
        self.timer.timeout.connect(self._timer_timeout)
        ## TIMER SETUP END ----------

        self.program = None
        
        self.items = {}
        self.cs_offsets = {
            "G54": (0, 0, 0),
            "G55": (0, 0, 0),
            "G56": (0, 0, 0),
            "G57": (0, 0, 0),
            "G58": (0, 0, 0),
            "G59": (0, 0, 0)
            }
        
    def resetView(self):
        # Rotation state
        self._mouse_rotation_start_vec = QVector3D()
        self._rotation_quat = QQuaternion()
        self._rotation_quat_start = self._rotation_quat
        
        # Translation state
        self._translation_vec = QVector3D(300, 200, -350)
        self._translation_vec_start = self._translation_vec
        
        self._zoom = 3
        self._rotation_axis = QVector3D()


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

        self.timer.start(10)
        
        
    def draw_stage(self, workarea_x, workarea_y):
        #self.cleanup_stage()
        
        # this simply draws the machine coordinate system
        if not "csm" in self.items:
            self.items["csm"] = CoordSystem("csm", self.program, 12, (0, 0, 0))
            self.items["csm"].linewidth = 6

        if not "working_area_grid" in self.items:
            self.items["working_area_grid"] = Grid("working_area_grid", self.program, (0, 0), (workarea_x, workarea_y), (-workarea_x, -workarea_y, 0), 10)
        
        if not "buffermarker" in self.items:
            self.items["buffermarker"] = StarMarker("buffermarker", self.program, 2)
        
        self.draw_asap = True


    def cleanup_stage(self):
        item_keys = self.items.keys()
        
        keys_to_delete = []
        for key in item_keys:
            if not (re.match("G5[4-9].*", key) or key == "csm" or key == "working_area_grid" or key == "tool" or key == "buffermarker"):
                keys_to_delete.append(key)
        
        print("cleanup_stage: removing items {}".format(keys_to_delete))
        for key in keys_to_delete:
            self.remove_item(key)
            
        self.draw_asap = True
        
        
    def remove_item(self, label):
        if label in self.items:
            self.items[label].remove()
            del self.items[label]
            self.draw_asap = True
        

    def paintGL(self):
        """
        Auto-called by updateGL
        """
        #print("paintGL")
        
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        # VIEW MATRIX BEGIN ==========
        mat_v = QMatrix4x4()
        #mat_v.lookAt(QVector3D(1, -10, 10), QVector3D(0, 0, 0), QVector3D(0, 0, 1))
        mat_v.rotate(self._rotation_quat)
        mat_v.translate(self._translation_vec)
        
        mat_v = Item.qt_mat_to_array(mat_v)
        loc_mat_v = glGetUniformLocation(self.program, "mat_v")
        glUniformMatrix4fv(loc_mat_v, 1, GL_TRUE, mat_v)
        # VIEW MATRIX END ==========
        
        # PROJECTION MATRIX BEGIN ==========
        aspect = self.width / self.height
        mat_p = QMatrix4x4()
        mat_p.perspective(90, aspect, 0.1, 100000)
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
            self._zoom = self._zoom * 1.1
        else:
            self._zoom = self._zoom * 0.9
            
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
            self._translation_vec = self._translation_vec_start + (QVector3D(x, -y, 0) - self._mouse_translation_vec_current) / self._zoom * 10
            #self._translation_vec
        
        self.draw_asap = True
        
        
    def _timer_timeout(self):
        """
        called regularly from timer
        """
        if self.draw_asap:
            self.updateGL()
            self.draw_asap = False
        
    def draw_coordinate_system(self, key, tpl_origin):
        self.cs_offsets[key] = tpl_origin
        if key in self.items:
            #update
            self.items[key].set_origin(tpl_origin)
        else:
            # create
            self.items[key] = CoordSystem(key, self.program, 3, tpl_origin)
            
        self.draw_asap = True
        
        
    def draw_gcode(self, gcode, cwpos, ccs):
        if "gcode" in self.items:
            # remove old gcode item
            self.remove_item("gcode")
        
        # create a new one
        self.items["gcode"] = GcodePath("gcode", self.program, gcode, cwpos, ccs, self.cs_offsets)
        self.draw_asap = True
        
        
    def highlight_gcode_line(self, line_number):
        if "gcode" in self.items:
            self.items["gcode"].highlight_line(line_number)
        self.draw_asap = True
            

    def put_buffer_marker_at_line(self, line_number):
        if "gcode" in self.items:
            bufferpos = self.items["gcode"].data["position"][2 * line_number]
            #print("putting buffermarker at line {} pos {}".format(line_number, bufferpos))
            if "buffermarker" in self.items:
                self.items["buffermarker"].set_origin(tuple(bufferpos))
            
            self.draw_asap = True
            
    
    def get_buffer_marker_pos(self):
        return self.items["buffermarker"].origin
        
        
    def draw_tool(self, cmpos):
        if "tool" in self.items:
            # if tool was already created, simply move it to cmpos
            self.items["tool"].set_origin(cmpos)
        else:
            # tool not yet created. create it and move it cmpos
            i = Item("tool", self.program, 2, GL_LINES, 7)
            i.append((0, 0, 0), (1, 1, 1, .5))
            i.append((0, 0, 200), (1, 1, 1, .2))
            i.upload()
            i.set_origin(cmpos)
            self.items["tool"] = i

        if "tracer" in self.items:
            # update existing
            tr = self.items["tracer"]
            tr.append(cmpos)
            vertex_nr = tr.elementcount
            tr.substitute(vertex_nr, cmpos, (1, 1, 1, 0.2))

        else:
            # create new
            tr = Item("tracer", self.program, 1000000, GL_LINE_STRIP, 1)
            self.items["tracer"] = tr
            tr.append(cmpos, (1, 1, 1, 0.2))
            tr.upload()

        self.draw_asap = True
        
        
    def draw_workpiece(self, dim=(100, 100, 10), offset=(0, 0, 0)):
        off = np.add((-800, -1400, dim[2]), offset)
        self.items["workpiece_top"] = Grid("workpiece_top",
                                        self.program,
                                       (0, 0, 0),
                                       (dim[0], dim[1], 0),
                                       off,
                                       2,
                                       (0.7, 0.2, 0.1, 0.6)
                                       )
        
        self.items["workpiece_top"].linewidth = 2
        
        self.items["workpiece_front"] = Grid("workpiece_front",
                                        self.program,
                                       (0, 0, 0),
                                       (dim[0], dim[2], 0),
                                       off,
                                       2,
                                       (0.7, 0.2, 1, 0.6)
                                       )
        self.items["workpiece_front"].rotation_angle = -90
        self.items["workpiece_front"].rotation_vector = QVector3D(1, 0, 0)
        
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
        y = 1 - py / (self.height / 2)
        
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