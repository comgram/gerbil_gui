"""
cnctoolbox - Copyright (c) 2016 Michael Franzl

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

import logging
import re
import numpy as np


def read(fname):
    with open(fname, 'r') as f:
        return [l.strip() for l in f.readlines()]
    
def write(fname, contents):
    with open(fname, 'w') as f:
        f.write(contents)

def to_origin(gcode):
    bbox = bbox(gcode)
    xmin = bbox[0][0]
    ymin = bbox[1][0]
    translated_gcode = translate(gcode, [-xmin, -ymin, 0])
    return translated_gcode

def scale_into(gcode, width, height, depth, scale_zclear=False):
    bbox = bbox(gcode)
    xmin = bbox[0][0]
    xmax = bbox[0][1]
    ymin = bbox[1][0]
    ymax = bbox[1][1]
    zmin = bbox[2][0]
    zmax = bbox[2][1]
    translated_gcode = translate(gcode, [-xmin, -ymin, 0])
    
    if width > 0:
        w = xmax - xmin
        fac_x = width / w
        fac_y = fac_x
        fac_z = fac_x
        
    if height > 0:
        h = ymax - ymin
        fac_y = height / h
        
    if depth > 0:
        d = zmax - zmin
        fac_z = depth / d
    
    scaled_gcode = scale_factor(translated_gcode, [fac_x, fac_y, fac_z], scale_zclear)
    return scaled_gcode
    
# returns string
def bbox_draw(gcode, move_z=False):
    result = ""
    
    bbox = bbox(gcode)
    xmin = bbox[0][0]
    xmax = bbox[0][1]
    ymin = bbox[1][0]
    ymax = bbox[1][1]
    zmin = bbox[2][0]
    zmax = bbox[2][1]
    
    if move_z:
        pass
        
    result += "G0X{:0.1f}Y{:0.1f}\n".format(xmin, ymin)
    result += "M0\n"
    
    result += "G0X{:0.1f}\n".format(xmax)
    result += "M0\n"
    
    result += "G0Y{:0.1f}\n".format(ymax)
    result += "M0\n"
    
    result += "G0X{:0.1f}\n".format(xmin)
    result += "M0\n"
    
    result += "G0Y{:0.1f}\n".format(ymin)
    result += "M0\n"
    
    return result
    

# returns list
def translate(lines, offsets=[0, 0, 0]):
    logger = logging.getLogger('gerbil')
    
    result = []
    
    axes = ["X", "Y", "Z"]
    contains_regexps = []
    replace_regexps = []
    for i in range(0, 3):
        axis = axes[i]
        contains_regexps.append(re.compile(".*" + axis + "([-.\d]+)"))
        replace_regexps.append(re.compile(r"" + axis + "[-.\d]+"))
    
    for line in lines:
        
        if "G91" in line:
            logger.error("gcodetools.translate: It does not make sense to translate movements in G91 distance mode. Aborting at line {}".format(line))
            return
        
        for i in range(0, 3):
            axis = axes[i]
            cr = contains_regexps[i]
            rr = replace_regexps[i]
            ofst = offsets[i]
            
            m = re.match(cr, line)
            if m and offsets[i] != 0:
                a = float(m.group(1))
                a += ofst
                rep = "{}{:0.3f}".format(axis, a)
                rep = rep.rstrip("0").rstrip(".")
                line = re.sub(rr, rep, line)

        result.append(line)
    return result


# returns list
def scale_factor(lines, facts=[1, 1, 1], scale_zclear=False):
    result = []
    
    logger = logging.getLogger('gerbil')
    
    if facts[0] != facts[1] or facts[0] != facts[2] or facts[1] != facts[2]:
        logger.warning("gcodetools.scale_factor: Circles will stay circles even with inhomogeous scale factor ".format(facts))
    
    _re_motion_mode = re.compile("(G[0123])([^\d]|$)")
    _current_motion_mode = None
    
    words = ["X", "Y", "Z", "I", "J", "K", "R"]
    contains_regexps = []
    replace_regexps = []
    for i in range(0, 7):
        word = words[i]
        contains_regexps.append(re.compile(".*" + word + "([-.\d]+)"))
        replace_regexps.append(re.compile(r"" + word + "[-.\d]+"))
    
    for line in lines:
        for i in range(0, 7):
            m = re.match(_re_motion_mode, line)
            if m:
                _current_motion_mode = m.group(1)
            
            word = words[i]
            cr = contains_regexps[i]
            rr = replace_regexps[i]
            factor = facts[(i % 3)]
            
            m = re.match(cr, line)
            if m and facts[i % 3] != 0 and not ("_zclear" in line and scale_zclear == False):
                val = float(m.group(1))
                val *= factor
                rep = "{}{:0.3f}".format(word, val)
                rep = rep.rstrip("0").rstrip(".")
                line = re.sub(rr, rep, line)

        result.append(line)
    return result


# returns list
def bbox(gcode):
    bbox = []
    
    axes = ["X", "Y", "Z"]
    contains_regexps = []
    
    for i in range(0, 3):
        axis = axes[i]
        contains_regexps.append(re.compile(".*" + axis + "([-.\d]+)"))
        bbox.append([9999, -9999])
    
    for line in gcode:
        for i in range(0, 3):
            axis = axes[i]
            cr = contains_regexps[i]
            m = re.match(cr, line)
            if m:
                a = float(m.group(1))
                min = bbox[i][0]
                max = bbox[i][1]
                min = a if a < min else min
                max = a if a > max else max
                bbox[i][0] = min
                bbox[i][1] = max
    return bbox



def bumpify(gcode_list, cwpos, probe_points, probe_values):
    print("bumpify start")
    logger = logging.getLogger('gerbil')
    
    position = list(cwpos)

    axes = ["X", "Y", "Z"]
    re_allcomments_remove = re.compile(";.*")
    re_axis_values = []
    re_axis_replace = []
    
    # precompile regular expressions for speed increase
    for i in range(0, 3):
        axis = axes[i]
        re_axis_values.append(re.compile(".*" + axis + "([-.\d]+)"))
        re_axis_replace.append(re.compile(r"" + axis + "[-.\d]+"))
    
    # first, collect xy coords per line, because all of them will be interpolated at once
    coords_xy = [None]*len(gcode_list)
    for nr in range(0, len(gcode_list)):
        line = gcode_list[nr]
        line = re.sub(re_allcomments_remove, "", line) # replace comments
        
        if "G91" in line:
            logger.error("gcodetools.bumpify: G91 distance mode is not supported. Aborting at line {}".format(line))
            return
        
        if re.match("G(5[4-9]).*", line): 
            logger.error("gcodetools.bumpify: Switching coordinate systems is not supported. Aborting at line {}".format(line))
            return
        
        for i in range(0, 2): # only loop over x and y
            axis = axes[i]
            rv = re_axis_values[i]
            m = re.match(rv, line)
            if m:
                a = float(m.group(1))
                position[i] = a
                
        coords_xy[nr] = [position[0], position[1]]
                
    #print("parsed coords", coords_xy)
                
    
    print("bumpify interpol")
    
    # I put this here to not make it a hard requirement
    # it is difficult to install on Windows
    from scipy.interpolate import griddata
        
    # see http://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.griddata.html
    interpolated_z = griddata(
        probe_points,
        probe_values,
        coords_xy,
        method='cubic')
    
    z_at_xy_origin = griddata(
        probe_points,
        probe_values,
        [0,0],
        method='cubic')[0]
    
    #print("interpolated", interpolated_z)
    
    # next add/substitute Z values
    current_z = cwpos[2]
    for nr in range(0, len(gcode_list)):
        line = gcode_list[nr]
        line = re.sub(re_allcomments_remove, "", line) # remove comments
        
        axis = axes[2]
        rv = re_axis_values[2]
        rr = re_axis_replace[2]
        m = re.match(rv, line)
        if m:
            # contains Z, replace
            current_z = float(m.group(1))
            new_z = current_z + interpolated_z[nr] - z_at_xy_origin
            rep = "{}{:0.3f}".format(axis, new_z)
            rep = rep.rstrip("0").rstrip(".")
            line = re.sub(rr, rep, line)
        elif "X" in line or "Y" in line:
            # add Z
            new_z = current_z + interpolated_z[nr] - z_at_xy_origin
            line += "{}{:0.3f}".format(axis, new_z)
                    
        gcode_list[nr] = line
    
    #print("FINI", gcode_list)
    print("bumpify done")
    return gcode_list