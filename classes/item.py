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

class Item():
    def __init__(self, prog, size, pt=GL_LINES, lw=1):
        self.vbo = glGenBuffers(1)
        self.vao = glGenVertexArrays(1)
        self.program = prog

        self.elementcount = 0
        
        #self.matrix_model = QMatrix4x4()
        
        self.primitive_type = pt
        self.linewidth = lw
        
        self.scale = 1
        self.origin = QVector3D(0, 0, 0)
        
        self.size = size
        self.data = np.zeros(self.size, [("position", np.float32, 3), ("color", np.float32, 4)])
        
        
    def append(self, pos, col=(1, 1, 1, 1)):
        self.data["position"][self.elementcount] = pos
        self.data["color"][self.elementcount] = col
        self.elementcount += 1
        
        
    def upload(self):
        # chop unneeded bytes
        self.data = self.data[0:self.elementcount]
        
        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, self.data.nbytes, self.data, GL_DYNAMIC_DRAW)
        
        print("UPLOADING {} BYTES".format(self.data.nbytes))
        stride = self.data.strides[0]
        
        offset = ctypes.c_void_p(0)
        loc = glGetAttribLocation(self.program, "position")
        glEnableVertexAttribArray(loc)
        glVertexAttribPointer(loc, 3, GL_FLOAT, False, stride, offset)

        offset = ctypes.c_void_p(self.data.dtype["position"].itemsize)
        loc = glGetAttribLocation(self.program, "color")
        glEnableVertexAttribArray(loc)
        glVertexAttribPointer(loc, 4, GL_FLOAT, False, stride, offset)
        
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)
        
        
    def set_scale(self, fac):
        self.scale = fac
        
        
    def set_origin(self, tpl):
        self.origin = QVector3D(tpl[0], tpl[1], tpl[2])

        
    def draw(self):
        # upload Model Matrix
        mat_m = QMatrix4x4()
        mat_m.translate(self.origin)
        mat_m.scale(self.scale)
        
        mat_m = self.qt_mat_to_array(mat_m)
        loc_mat_m = glGetUniformLocation(self.program, "mat_m")
        glUniformMatrix4fv(loc_mat_m, 1, GL_TRUE, mat_m)
        
        # bind VBO and VAO
        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        
        # actual draw command
        glLineWidth(self.linewidth)
        glDrawArrays(self.primitive_type, 0, self.elementcount)
        
        # unbind VBO and VAO
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)
    
    @staticmethod
    def qt_mat_to_array(mat):
        arr = [0] * 16
        for i in range(4):
            for j in range(4):
                idx = 4 * i + j
                arr[idx] = mat[i, j]
        return arr
        
        
        
class CoordSystem(Item):
    def __init__(self,
                 prog,
                 scale=1,
                 origin=(0, 0, 0)
                 ):
        
        size = 6
        super(CoordSystem, self).__init__(prog, size)
        
        self.primitive_type = GL_LINES
        self.linewidth = 3
        self.set_scale(scale)
        self.set_origin(origin)
        
        self.append((0, 0, 0), (1, 0, 0, 1))
        self.append((10, 0, 0), (1, 0, 0, 1))
        self.append((0, 0, 0), (0, 1, 0, 1))
        self.append((0, 10, 0), (0, 1, 0, 1))
        self.append((0, 0, 0), (0, 0, 1, 1))
        self.append((0, 0, 10), (0, 0, 1, 1))
        self.upload()
        

class Grid(Item):
    def __init__(self,
                 prog,
                 ll=(0, 0),
                 ur=(1000, 1000),
                 trans=(0, 0, 0),
                 unit=10
                 ):
        
        width = ur[0] - ll[0]
        height = ur[1] - ll[1]
        width_units = int(width / unit) + 1
        height_units = int(height / unit) + 1
        
        size = 2 * width_units + 2 * height_units
        
        super(Grid, self).__init__(prog, size)
        
        self.primitive_type = GL_LINES
        self.linewidth = 1
        self.color = (1, 1, 1, 0.2)
        self.set_origin(trans)
        
        for wu in range(0, width_units):
            x = unit * wu
            self.append((x, 0, 0), self.color)
            self.append((x, height, 0), self.color)
            
        for hu in range(0, height_units):
            y = unit * hu
            self.append((0, y, 0), self.color)
            self.append((width, y, 0), self.color)

        self.upload()
        
        
class GcodePath(Item):
    def __init__(self, prog, gcode, cwpos, ccs, cs_offsets):
        
        size = len(gcode)
        super(GcodePath, self).__init__(prog, size)
        
        self.primitive_type = GL_LINE_STRIP
        self.linewidth = 1
        
        # TODO: Arcs, move in machine coordinates
        
        pos = list(cwpos) # current position
        cs = ccs # current coordinate system
        offset = cs_offsets[cs] # current cs offset tuple
        motion = "" # current motion mode
        
        colg0 = (1, 1, 1, 1)
        colg1 = (0.5, 0.5, 1, 1)

        axes = ["X", "Y", "Z"]
        contains_regexps = []
        for i in range(0, 3):
            axis = axes[i]
            contains_regexps.append(re.compile(".*" + axis + "([-.\d]+)"))
        
        # start of line
        target = np.add(offset, pos)
        self.append(tuple(target), colg0)
        
        for line in gcode:
            # get current motion mode G0, G1, G2, G3
            mm = re.match("G(\d).*", line)
            if mm: motion = "G" + mm.group(1)
            col = colg0 if motion == "G0" else colg1
            
            # get current coordinate system G54-G59
            mcs = re.match("G(5[4-9]).*", line)
            if mcs: 
                cs = "G" + mcs.group(1)
                offset = cs_offsets[cs]
                
            # parse X, Y and Z axis values
            for i in range(0, 3):
                axis = axes[i]
                cr = contains_regexps[i]
                m = re.match(cr, line)
                if m:
                    a = float(m.group(1))
                    pos[i] = a

            target = np.add(offset, pos)
            self.append(tuple(target), col)
        
        self.upload()