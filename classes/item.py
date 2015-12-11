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
    def __init__(self, label, prog, size, pt=GL_LINES, lw=1):
        self.vbo = glGenBuffers(1)
        self.vao = glGenVertexArrays(1)
        self.program = prog
        self.label = label

        self.elementcount = 0
        
        #self.matrix_model = QMatrix4x4()
        
        self.primitive_type = pt
        self.linewidth = lw
        
        self.scale = 1
        self.origin = QVector3D(0, 0, 0)
        self.rotation_angle = 0
        self.rotation_vector = QVector3D(0, 0, 0)
        
        self.dirty = True
        
        self.size = size
        self.data = np.zeros(self.size, [("position", np.float32, 3), ("color", np.float32, 4)])
        
    def __del__(self):
        print("DELETING MYSELF: {}".format(self.label))
        
        
    def append(self, pos, col=(1, 1, 1, 1)):
        self.data["position"][self.elementcount] = pos
        self.data["color"][self.elementcount] = col
        self.elementcount += 1
        
    def remove(self):
        glDeleteBuffers(1, [self.vbo])
        glDeleteVertexArrays(1, [self.vao])
        self.dirty = True
        print("REMOVING {}".format(self.label))
        
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
        # TODO: only draw if dirty
        mat_m = QMatrix4x4()
        mat_m.translate(self.origin)
        mat_m.scale(self.scale)
        mat_m.rotate(self.rotation_angle, self.rotation_vector)
        
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
        
        self.dirty = False
    
    @staticmethod
    def qt_mat_to_array(mat):
        arr = [0] * 16
        for i in range(4):
            for j in range(4):
                idx = 4 * i + j
                arr[idx] = mat[i, j]
        return arr
        
        
        
class StarMarker(Item):
    def __init__(self,
                 label,
                 prog,
                 scale=1,
                 origin=(0, 0, 0)
                 ):
        
        size = 6
        super(CoordSystem, self).__init__(label, prog, size)
        
        self.primitive_type = GL_LINES
        self.linewidth = 2
        self.set_scale(scale)
        self.set_origin(origin)
        
        col = (1, 1, 1, 1)
        
        self.append((-1, 0, 0), col)
        self.append((1, 0, 0), col)
        self.append((0, -1, 0), col)
        self.append((0, 1, 0), col)
        self.append((0, 0, -1), col)
        self.append((0, 0, 1), col)
        
        self.upload()
        
        
class CoordSystem(Item):
    def __init__(self,
                 label,
                 prog,
                 scale=1,
                 origin=(0, 0, 0),
                 hilight=False
                 ):
        
        size = 6
        super(CoordSystem, self).__init__(label, prog, size)
        
        self.primitive_type = GL_LINES
        self.linewidth = 3
        self.set_scale(scale)
        self.set_origin(origin)
        self.hilight = hilight
        
        self.append((0, 0, 0), (1, 0, 0, 1))
        self.append((10, 0, 0), (1, 0, 0, 1))
        self.append((0, 0, 0), (0, 1, 0, 1))
        self.append((0, 10, 0), (0, 1, 0, 1))
        self.append((0, 0, 0), (0, 0, 1, 1))
        self.append((0, 0, 10), (0, 0, 1, 1))
        self.upload()
        

    def highlight(self, val):
        self.hilight = val
        alpha = 1 if self.hilight == True else 0
        for x in range(0,3):
            col = self.data["color"][x * 2 + 1]
            if self.hilight == True:
                newcol = (1, 1, 1, 1)
                self.linewidth = 3
            else:
                #newcol = (col[0], col[1], col[2], 0)
                newcol = (0, 0, 0, 1)
                self.linewidth = 2
                
            self.data["color"][x * 2] = newcol

        self.dirty = True
        self.upload()
        
        

class Grid(Item):
    def __init__(self,
                 label,
                 prog,
                 ll=(0, 0),
                 ur=(1000, 1000),
                 trans=(0, 0, 0),
                 unit=10,
                 color=(1, 1, 1, 0.2)
                 ):
        
        width = ur[0] - ll[0]
        height = ur[1] - ll[1]
        width_units = int(width / unit) + 1
        height_units = int(height / unit) + 1
        
        size = 2 * width_units + 2 * height_units
        
        super(Grid, self).__init__(label, prog, size)
        
        self.primitive_type = GL_LINES
        self.linewidth = 1
        self.color = color
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
    def __init__(self, label, prog, gcode, cwpos, ccs, cs_offsets):
        
        self.line_count = 2 * (len(gcode) + 1)
        #self.line_count = 1 * (len(gcode) + 1)
        
        super(GcodePath, self).__init__(label, prog, self.line_count)
        
        self.primitive_type = GL_LINE_STRIP
        self.linewidth = 1
        
        self.gcode = gcode
        self.cwpos = list(cwpos)
        self.spindle_speed = None
        self.ccs = ccs
        self.cs_offsets = cs_offsets
        
      
        
        self.highlight_lines_queue = []
        
        self.axes = ["X", "Y", "Z"]
        
        self.contains_regexps = []
        for i in range(0, 3):
            axis = self.axes[i]
            self.contains_regexps.append(re.compile(".*" + axis + "([-.\d]+)"))
            
        self.contains_spindle_regexp = re.compile(".*S(\d+)")
            
        self.render()
        self.upload()
        
        
    def highlight_line(self, line_number):
        self.highlight_lines_queue.append(line_number)
        
    def draw(self):
        for line_number in self.highlight_lines_queue:
            #print("highlighting line", line_number)
            stride = self.data.strides[0]
            position_size = self.data.dtype["position"].itemsize
            color_size = self.data.dtype["color"].itemsize
            
            offset = 2 * line_number * stride + position_size
            #offset = 1 * line_number * stride + position_size
            
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
            
            col = np.array([0.8, 0.8, 1, 1], dtype=np.float32)
            #print("highlighting line", line_number, offset, color_size)
            glBufferSubData(GL_ARRAY_BUFFER, offset, color_size, col)
            #glBindBuffer(GL_ARRAY_BUFFER, 0)
            #self.draw()
            
        del self.highlight_lines_queue[:]
        
        super(GcodePath, self).draw()
        
        
    def render(self):
        # TODO: Arcs, move in machine coordinates
        
        pos = self.cwpos # current position
        cs = self.ccs # current coordinate system
        offset = self.cs_offsets[cs] # current cs offset tuple
        motion = "" # current motion mode
        
        colg0 = (1, 1, 0.5, 1)
        colg1 = (0.3, 0.3, 1, 1)

        diff = [0, 0, 0]
        
        # start of path
        end = np.add(offset, pos)
        self.append(tuple(end), colg0)
        
        for line in self.gcode:
            # get current motion mode G0, G1, G2, G3
            mm = re.match("G(\d).*", line)
            if mm: motion = "G" + mm.group(1)
            col = colg0 if motion == "G0" else colg1
            
            # get current coordinate system G54-G59
            mcs = re.match("G(5[4-9]).*", line)
            if mcs: 
                cs = "G" + mcs.group(1)
                offset = cs_offsets[cs]
                
            if re.match("G[23]", motion):
                self.render_arc(line)
                
            # parse X, Y, Z axis and S values
            for i in range(0, 3):
                axis = self.axes[i]
                cr = self.contains_regexps[i]
                m = re.match(cr, line)
                if m:
                    a = float(m.group(1))
                    pos[i] = a
               
            m = re.match(self.contains_spindle_regexp, line)
            if m:
                self.spindle_speed = int(m.group(1))
                
            if self.spindle_speed:
                rgb = self.spindle_speed / 255.0
                col = (rgb, rgb, rgb, 1)
                
            #target = np.add(offset, pos)
            #self.append(tuple(target), col)

            start = end
            end = np.add(offset, pos)
            diff = np.subtract(end, start)
            
            # generate 2 line segments per gcode for sharper color transitions when using spindle speed
            self.append(start + diff * 0.01, col)
            self.append(start + diff, col)
            
    def render_arc(self, line):
        if "R" in line:
            pass
            # radius mode
            #dx = pos[0]