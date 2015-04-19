from __future__ import division                 
import sys,traceback
import pprint
import copy
import math
import inspect
import logging
import re
module_logger = logging.getLogger('cnctoolbox.compiler')
try:
    unicode = unicode
except NameError:
    # 'unicode' is undefined, must be Python 3
    str = str
    unicode = str
    bytes = bytes
    basestring = (str,bytes)
else:
    # 'unicode' exists, must be Python 2
    str = str
    unicode = unicode
    bytes = str
    basestring = basestring

'''
    When considering a bit, think of it like this.
    Does the point specified mean the center of the
    bit, or the edge of the bit?

    If you tool is 6mm diameter, and you move
    to x30 y30, and it is centered, then your
    line will really start at x27 and y27

    If you center_edge, x30 y30 for a
    6mm diameter bit, then really you are saying x33 y33

    center_edge is the default.
'''
Settings = {
    'header': "G17 G21 G91 G94 G54;header\n",
    'ignoreZ': False,
    'port': sys.stdout,
    'port_stack': [],
    'feed_speed': 400,
    'max_feed_speed': 800,
    'debug': True,
    'debug_gcode': True,
    'safe_z': 2.5,
    'log_callback': lambda str: print(str),
    'material': {
        'width': 0,
        'length': 0,
        'depth': 0
    },

    'bit': {
        'diameter': 6,
        'length': 0,
        'type': 'flat',
        'v_angle': 0,
        'center_edge': True,
        'centered': False,
  }
}
FileLines = []
State = {
    'x': 0,
    'y': 0,
    'z': 0,
    'white_space': 0,
    'vars': { },
    're_var': re.compile(".*(#[\da-z]+)"),
    're_var_assign': re.compile(".*(#[\da-z+])=([\d.-]+)"),
}
'''
    LOW LEVEL FUNCTIONS

    You probably won't want to touch these functions, they are
    the bare metal emission functions. 
'''

''' We often want save and restore the x,y '''
PositionStack = []
''' We have to save the z-depth separately '''
ZStack = []
def speed(s):
    global Settings
    Settings['max_feed_speed'] = s
def diameter(d):
    global Settings
    Settings['bit']['diameter'] = d
def push_receiver():
    global Settings
    Settings['port_stack'].append(Settings['port'])
def pop_receiver():
    global Settings
    Settings['port'] = Settings['port_stack'].pop()
def evaluate(txt):
    global Settings
    global ZStack
    global PositionStack
    global State
    global FileLines
    try:
        exec(txt)
    except:
        print("Compiler: Exception in user code:")
        log(traceback.format_exc())
def getv(name):
    if name in State['vars']:
        return State['vars'][name]
    else:
        raise NameError("Compiler: {} is not defined".format(name))
def setv(name,val):
    global State
    State['vars'][name] = val
def add_gcode_line(l):
    global FileLines
    FileLines.append(l)
def _process_line(line,rep=True):
    global State
    line = line.strip()
    match = re.match(State['re_var_assign'], line)
    contains_var_assignment = True if match else False
    if contains_var_assignment:
        key = match.group(1)
        val = float(match.group(2))
        setv(key,val)
        return ""
    if rep:
        match = re.match(State['re_var'], line)
        contains_var = True if match else False
        if contains_var:
            key = match.group(1)
            line = line.replace(key, str(getv(key)) )
            return _process_line(line)
    return line
def include_gcode_from(fname,rep=True):
    global FileLines
    FileLines = [_process_line(line,rep) for line in open(fname,'r')]
def send_gcode_lines():
    global FileLines
    for line in FileLines:
        line = _process_line(line,True)
        emit(line)
def flush():
    global FileLines
    send_gcode_lines()
    FileLines = []       
def log(str):
    global Settings
    Settings['log_callback'](str)
def slow():
    global Settings
    return int(math.floor(Settings['feed_speed'] * 0.25))
def slowly():
    global Settings
    return int(math.floor(Settings['feed_speed'] * 0.35))
def fast():
    global Settings
    return Settings['max_feed_speed']
def comment(txt):
    #log(txt)
    emit(";%s" % txt)
def push_z():
    global ZStack
    global State
    comment("Z Pushed %.3f" % State['z'])
    ZStack.append(State['z'])
def pop_z():
    global ZStack
    z = ZStack.pop()
    comment("Z Popped %.3f" % z)
    depth(z)
def push_position():
    global PositionStack
    global State
    PositionStack.append([State['x'],State['y']])
def pop_position():
    global PositionStack
    pos = PositionStack.pop()
    move(pos[0],pos[1])
def receiver(path=False):
    global Settings
    if isinstance(path,basestring):
        Settings['port'] = open(path,'w')
    elif not path == False:
        print("Adding class as receiver")
        Settings['port'] = path
    else:
        print("using stdout")
        Settings['port'] = sys.stdout
def write_header():
    emit(Settings['header'])
    home()
'''
    Remember that Z0 is exactlty the top of the
    material!
'''
def depth(d,f=False):
    global State
    global Settings
    if not f:
        f = Settings['max_feed_speed'] / 2
    if Settings['ignoreZ'] == False:
        State['z'] = d
        emit("G1 Z%.3f F%d;depth(%.3f,%d)" % (d,f,d,f))
    else:
        emit(";IgnoreZ depth(%f,%f)" % (d,f))
def up():
    global Settings
    push_z()
    depth(Settings['safe_z'],Settings['max_feed_speed'])
def down():
    pop_z()
def home():
    global Settings
    depth(Settings['safe_z'], Settings['max_feed_speed'])
    move(0,  0, Settings['max_feed_speed'])
    
def move(x,y,f=False):
    global State
    State['x'] = x
    State['y'] = y
    if f == False:
        f = Settings['feed_speed']
    emit("G1 X%.3f Y%.3f F%d" % (x,y,f))
def done():
    global Settings
    emit("M2")
    if Settings['port'] is not sys.stdout:
        Settings['port'].close()        
def emit(txt=";Nothing Emitted\n"):
    global Settings
    global State

    if txt == "\n":
        return
    if len(txt) < 1:
        return
    
    if Settings['debug_gcode'] == True or txt[0] != ';':
        for x in range(0,State['white_space']):
            Settings['port'].write(" ")  
        #log("Writing Text: %s" % txt)
        if txt and isinstance(txt,basestring) and len(txt) > 2:
            print("WRITING", txt)
            Settings['port'].write("%s\n" % txt)
            
'''
    USE THESE TO PRETTY UP GCODE!!

    Otherwise, it's a huge block of
    text.
'''
def block_start(cmnt="BEGIN"):
    global State
    comment(cmnt)
    State['white_space'] = State['white_space'] + 4
def block_end(cmnt="END"):
    State['white_space'] = State['white_space'] - 4
    comment(cmnt)
    if State['white_space'] < 0:
        raise SyntaxError("block_end must match a block_start")
'''
    BASIC GEOMETRY FUNCTIONS

    These functions here form the basic geometrical
    functions that you can use.

    Each call comes in two varieties, the raw way
    usually _to or something, like line_to, which
    doesn't manage the z-axis so it can break the
    blank.

    line however does manage the z-axis for you.
    
'''
def line_to(ex,ey,d):
    global Settings
    depth(d)
    move(ex,ey, Settings['feed_speed'])
def path(pts,d=0):
    up()
    st = pts.pop(0)
    move(st[0],st[1])
    if len(st) > 2:
        d = st[2]
    down()
    depth(d)
    for coord in pts:
        st = coord
        if len(st) > 2:
            d = st[2]
        line_to(st[0],st[1],d)
        
def line(sx,sy, ex,ey, d):
    global Settings
    block_start("BEGIN: line(%.3f,%.3f,%.3f,%.3f,%.3f" % (sx,sy, ex,ey, d))
    up()
    move(sx,sy)
    down()
    line_to(ex,ey,d)
    block_end()
def square(bx,by,tx,ty,d):
    block_start("BEGIN: square(%.3f,%.3f,%.3f,%.3f,%.3f" % (bx,by,tx,ty,d))
    up()
    move(bx,by)
    down()
    line_to(bx,ty,d)
    line_to(tx,ty,d)
    line_to(tx,by,d)
    line_to(bx,by,d)
    block_end();
def cw_arc_to(sx,sy,ex,ey,r,t,d):
    Q = math.sqrt( (ex - sx)**2 + (ey - sy)**2 ) / 2
    xm = (sx+ex)/2
    ym = (sy+ey)/2
    if  r < Q:
        r = Q+1
    print("Q: %3.f" % Q)
   
    Xc = xm + 0.5*math.sqrt(r**2-Q**2)*(ey-sy)/Q
    Yc = ym - 0.5*math.sqrt(r**2-Q**2)*(ex-sx)/Q

    print("Xc: %.3f Yc: %.3f" % (Xc,Yc))

    I = Xc - sx
    J = Yc - sy
    if t == 0:
        code = "G2"
    else:
        code = "G3"
    emit("%s X%.3f Y%.3f I%.3f J%.3f F%d" %(code,ex,ey,I,J,300))
def cw_circle_to(sx,sy,ex,ey,r,t,d):
    Q = math.sqrt( (ex - sx)**2 + (ey - sy)**2 ) / 2
    xm = (sx+ex)/2
    ym = (sy+ey)/2
    if  r < Q:
        r = Q+1
    print("Q: %3.f" % Q)
   
    Xc = xm - 0.5*math.sqrt(r**2-Q**2)*(ey-sy)/Q
    Yc = ym + 0.5*math.sqrt(r**2-Q**2)*(ex-sx)/Q

    print("Xc: %.3f Yc: %.3f" % (Xc,Yc))

    I = Xc - sx
    J = Yc - sy
    if t == 0:
        code = "G2"
    else:
        code = "G3"
    emit("%s X%.3f Y%.3f I%.3f J%.3f F%d" %(code,sx,sy,I,J,300))
def cw_arc(sx,sy,ex,ey,r,t,d):
    block_start("Arc")
    move(sx,sy)
    depth(d)
    cw_arc_to(sx,sy,ex,ey,r,t,d)
    up()
    block_end()
'''
    h: x coord
    k: y coord
    r: radius
    d: segment length
    dth: depth
'''
def circle(h,k,r,d,dth):
    global Settings
    n = int(math.floor(2 * math.pi * r / d))
    depth(0)
    move(h,k)
    depth(-2)
    depth(1)
    xs = h + r
    ys = k
    move(xs,ys)
    depth(dth)
    
    fi = 2 * math.pi / n
    for i in range(1,n):
        xe = h + r * math.cos(i * fi)
        ye = k + r * math.sin(i * fi)
        line_to(xe,ye,dth)
        xs = xe
        ys = ye
    up()
    move(h,k)
    
def hole(h,k,r,d=0.5,dth=0.5):
    global Settings
    inc = Settings['bit']['diameter'] / 2
    i = inc
    while i < r:
        circle(h,k,i,d,dth)
        i += inc
        if i > r:
            i = r

def triangle(blx,bly,brx,bry,ax,ay,d):
    block_start("Triangle")
    depth(1)
    move(blx,bly)
    depth(d)
    move(brx,bry)
    move(ax,ay)
    move(blx,bly)
    block_end()
def equal_triangle(blx,bly, brx,bry, d):
    block_start("Equalateral Triangle")
    ax = blx + ((brx - blx) / 2)
    ay = bly + (brx - blx)
    up()
    triangle(blx,bly,brx,bry,ax,ay,d)
    down()
    block_end()
''' Basic Milling Functions '''

def pocket(sx,sy,ex,ey,d):
    global Settings
    osx = sx
    osy = sy
    block_start("Pocket")
    inc = Settings['bit']['diameter'] * 0.75
    up()
    move(sx,sy)
    while sx < ex - inc:
        print("sx: %.3f ey: %.3f" % (sx,ey))
        line_to(sx,ey,d)
        sx += inc
        line_to(sx,ey,d)
        line_to(sx,sy,d)
        sx += inc
        line_to(sx,sy,d)
        
    block_end("Pocket")

#''' Basic Gerometry Functions Test '''
#receiver("test.ngc")
#write_header()
##line(10,10,50,50, -3)
##square(10,10,110,110, -4)
##line(50,10,10,50,-2)
#pocket(0,0, 450,200,-2)
##equal_triangle(55,10, 85, 10, -3.2)
##line(100,100, 150,100, -3)
##cw_arc(10,15,11,16,5,0,-3)
##circle(60,60,15,3,-3)

#done()
