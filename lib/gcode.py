import logging
import re

def move_to_origin(gcode):
    bbox = get_bbox(gcode)
    xmin = bbox[0][0]
    ymin = bbox[1][0]
    translated_gcode = translate(gcode, [-xmin, -ymin, 0])
    return translated_gcode

def get_bbox(gcode):
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


def translate(lines, offsets=[0, 0, 0]):
    result = []
    
    axes = ["X", "Y", "Z"]
    contains_regexps = []
    replace_regexps = []
    for i in range(0, 3):
        axis = axes[i]
        contains_regexps.append(re.compile(".*" + axis + "([-.\d]+)"))
        replace_regexps.append(re.compile(r"" + axis + "[-.\d]+"))
    
    for line in lines:
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

def scale(filename, axes, fac_x=1, fac_y=1, fac_z=1):
    pass