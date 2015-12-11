import logging
import re

def read(fname):
    with open(fname, 'r') as f:
        return f.readlines()
    
def write(fname, contents):
    with open(fname, 'w') as f:
        f.write(contents)

def to_origin(gcode):
    bbox = _get_bbox(gcode)
    xmin = bbox[0][0]
    ymin = bbox[1][0]
    translated_gcode = translate(gcode, [-xmin, -ymin, 0])
    return translated_gcode

def scale_into(gcode, width, height, depth, scale_zclear=False):
    bbox = _get_bbox(gcode)
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
def bbox(gcode, move_z=False):
    result = "F1000\n"
    #result = "G0X0Y0\n"
    #result += "G4P1\n"
    #result += "M0\n"
    
    bbox = _get_bbox(gcode)
    xmin = bbox[0][0]
    xmax = bbox[0][1]
    ymin = bbox[1][0]
    ymax = bbox[1][1]
    zmin = bbox[2][0]
    zmax = bbox[2][1]
    
    if move_z:
        pass
        
    result += "G0X{:0.1f}Y{:0.1f}\n".format(xmin, ymin)
    #result += "G4P1\n"
    result += "M0\n"
    
    result += "G0Y{:0.1f}\n".format(ymax)
    #result += "G4P1\n"
    result += "M0\n"
    
    result += "G0X{:0.1f}\n".format(xmax)
    #result += "G4P1\n"
    result += "M0\n"
    
    result += "G0Y{:0.1f}\n".format(ymin)
    #result += "G4P1\n"
    result += "M0\n"
    
    result += "G0X{:0.1f}\n".format(xmin)
    return result
    

# returns list
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

# returns list
def scale_factor(lines, facts=[0, 0, 0], scale_zclear=False):
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
            factor = facts[i]
            
            m = re.match(cr, line)
            if m and facts[i] != 0 and not ("_zclear" in line and scale_zclear == False):
                a = float(m.group(1))
                a *= factor
                rep = "{}{:0.3f}".format(axis, a)
                rep = rep.rstrip("0").rstrip(".")
                line = re.sub(rr, rep, line)

        result.append(line)
    return result

# returns list
def _get_bbox(gcode):
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