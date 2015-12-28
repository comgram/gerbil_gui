import os
import re
import numpy as np

from pyglpainter.classes.painterwidget import PainterWidget

from PyQt5.QtGui import QVector3D

import OpenGL
from OpenGL.GL import *


class SimulatorWidget(PainterWidget):
    def __init__(self, parent=None):
        super(SimulatorWidget, self).__init__(parent)

        self.cs_offsets = {
            "G54": (0, 0, 0),
            "G55": (0, 0, 0),
            "G56": (0, 0, 0),
            "G57": (0, 0, 0),
            "G58": (0, 0, 0),
            "G59": (0, 0, 0)
            }
        
    def initializeGL(self):
        super(SimulatorWidget, self).initializeGL()
        
        # ============= CREATE PROGRAMS BEGIN =============
        path = os.path.dirname(os.path.realpath(__file__)) + "/shaders/"
        self.program_create("simple3d", path + "simple3d-vertex.c", path + "simple3d-fragment.c")
        self.program_create("simple2d", path + "simple2d-vertex.c", path + "simple2d-fragment.c")
        # ============= CREATE PROGRAMS END =============
    
    def draw_stage(self, workarea_x, workarea_y):
        self.item_create("CoordSystem", "csm", "simple3d", (0,0,0), 120, 5)
        self.item_create("OrthoLineGrid", "working_area_grid", "simple3d", (0,0), (workarea_x,workarea_y), 10, (-workarea_x,-workarea_y,0))
        self.item_create("Star", "buffermarker", "simple3d", (0,0,0), 2)
        self.dirty = True


    def cleanup_stage(self):
        item_keys = self.items.keys()
        
        keys_to_delete = []
        for key in item_keys:
            if not (re.match(".*csG5[4-9].*", key) or key == "csm" or key == "working_area_grid" or key == "tool" or key == "buffermarker"):
                keys_to_delete.append(key)
        
        print("cleanup_stage: removing items {}".format(keys_to_delete))
        for key in keys_to_delete:
            self.item_remove(key)
            
        self.dirty = True

        
    def draw_coordinate_system(self, key, tpl_origin):
        self.cs_offsets[key] = tpl_origin
        cskey = "cs" + key
        if cskey in self.items:
            #update
            self.items[cskey].set_origin(tpl_origin)
        else:
            # create
            self.item_create("CoordSystem", cskey, "simple3d", tpl_origin, 30, 2)
            
        txtkey = "txtcs" + key
        if txtkey in self.items:
            #update
            self.items[txtkey].set_origin(tpl_origin)
        else:
            # create
            text = self.item_create("Text", txtkey, "simple3d", key, tpl_origin, 2, 1, (1,1,1,0.5))
            text.billboard = True
        
        self.dirty = True
        
        
    def draw_gcode(self, gcode, cwpos, ccs):
        if "gcode" in self.items:
            # remove old gcode item
            self.item_remove("gcode")
        
        # create a new one
        self.item_create("GcodePath", "gcode", "simple3d", gcode, cwpos, ccs, self.cs_offsets)
        #self.items["gcode"] = GcodePath("gcode", self.program, gcode, cwpos, ccs, self.cs_offsets)
        self.dirty = True
        
        
    def highlight_gcode_line(self, line_number):
        if "gcode" in self.items:
            self.items["gcode"].highlight_line(line_number)
        self.dirty = True
            

    def put_buffer_marker_at_line(self, line_number):
        #print("putting buffermarker at line {}".format(line_number))
        if "gcode" in self.items:
            if 2 * line_number <= self.items["gcode"].elementcount:
                bufferpos = self.items["gcode"].data["position"][2 * line_number]
                
                if "buffermarker" in self.items:
                    self.items["buffermarker"].set_origin(tuple(bufferpos))
            
            self.dirty = True
            
    
    def get_buffer_marker_pos(self):
        return self.items["buffermarker"].origin
        
        
    def draw_tool(self, cmpos):
        if "tool" in self.items:
            # if tool was already created, simply move it to cmpos
            self.items["tool"].set_origin(cmpos)
        else:
            # tool not yet created. create it and move it cmpos
            i = self.item_create("Item", "tool", "simple3d", GL_LINES, 7, (0,0,0), 1, False, 2)
            i.append_vertices([[(0, 0, 0), (1, 1, 1, .5)]])
            i.append_vertices([[(0, 0, 200), (1, 1, 1, .2)]])
            i.upload()
            i.set_origin(cmpos)

        if "tracer" in self.items:
            # update existing
            tr = self.items["tracer"]
            tr.append_vertices([[cmpos, (1, 1, 1, 0.2)]])
            #vertex_nr = tr.elementcount
            #tr.substitute(vertex_nr, cmpos, )
        else:
            # create new
            tr = self.item_create("Item", "tracer", "simple3d", GL_LINE_STRIP, 1, (0,0,0), 1, False, 1000000)
            tr.append_vertices([[cmpos, (1, 1, 1, 0.2)]])
            tr.upload()

        self.dirty = True
        
        
    def draw_workpiece(self, dim=(100, 100, 10), offset=(0, 0, 0)):
        off = np.add((-800, -1400, dim[2]), offset)
        col = (0.7, 0.2, 0.1, 0.6)
        #wp1 = self.item_create("OrthoLineGrid", "workpiece_top", "simple3d", (0,0,0), (dim[0],dim[1],0), off, 2, col, 2)
        #wp2 = self.item_create("OrthoLineGrid", "workpiece_front", "simple3d", (0,0,0), (dim[0],dim[2],0), off, 2, col, 2)
        #wp2.rotation_angle = -90
        #wp2.rotation_vector = QVector3D(1, 0, 0)
        
        self.dirty = True