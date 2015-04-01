import sys
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
    'header': "G17 G21 G90 G94 G54;header\n",
    'ignoreZ': False,
    'port': sys.stdout,
    'feed_speed': 300,
    'max_feed_speed': 400,
    'debug': True,
    'debug_gcode': True,
    'material': {
        'width': 0,
        'length': 0,
        'depth': 0
    },

    'bit': {
        'diameter': 2,
        'length': 0,
        'type': 'flat',
        'v_angle': 0,
        'center_edge': True,
        'centered': False,
  }
}
State = {
    'x': 0,
    'y': 0,
    'z': 0,
    'white_space': 0
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
def comment(txt):
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
    Settings['port'] = open(path,'w') if path else sys.stdout
def write_header():
    emit(Settings['header'])
    home()
'''
    Remember that Z0 is exactlty the top of the
    material!
'''
def depth(d,f=50):
    global State
    global Settings
    if State['z'] == d:
        return
    if Settings['ignoreZ'] == False:
        State['z'] = d
        emit("G53 G1 Z%.3f F%d;depth(%.3f,%d)" % (d,f,d,f))
    else:
        emit(";IgnoreZ depth(%f,%f)" % (d,f))
def up():
    push_z()
    depth(3,300)
def down():
    pop_z()
def home():
    global Settings
    depth(0, Settings['max_feed_speed'])
    move(0,  0, Settings['max_feed_speed'])
    
def move(x,y,f=False):
    global State
    State['x'] = x
    State['y'] = y
    if f == False:
        f = Settings['feed_speed']
    emit("G53 G1 X%.3f Y%.3f F%d" % (x,y,f))
def done():
    global Settings
    emit("M2")
    if Settings['port'] is not sys.stdout:
        Settings['port'].close()        
def emit(txt=";Nothing Emitted\n"):
    global Settings
    global State
    
    if Settings['debug_gcode'] == True or txt[0] != ';':
        for x in range(0,State['white_space']):
            Settings['port'].write(" ")  
        Settings['port'].write(txt)
        Settings['port'].write("\n")
            
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
def arc_to(sx,sy,ex,ey,c):
    comment("ARC is not yet implemented")

''' Basic Milling Functions '''

def pocket(sx,sy,ex,ey,d):
    global Settings
    block_start("Pocket")
    inc = Settings['bit']['diameter'] / 2
    cx = sx + ((ex - sx) / 2)
    cy = sy + ((ey - sy) / 2 )
    
    nsx = cx - inc
    nsy = cy - inc
    nex = cx + inc
    ney = cy + inc
    square(sx,sy,ex,ey,d)
    while nsx > sx and nsy > sy:
        square(nsx,nsy,nex,ney,d)
        nsx -= inc
        nsy -= inc
        nex += inc
        ney += inc
    block_end("Pocket")

''' Basic Gerometry Functions Test '''
receiver("test.ngc")
write_header()
line(10,10,50,50, -3)
square(10,10,50,50, -4)
line(50,10,10,50,-2)
pocket(55,55, 100,100,-2)
done()
