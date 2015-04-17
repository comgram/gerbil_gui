# There are no offset calculations, you will need
# to do them yourself, so if your bit is 6mm, then you
# may have to go x or y + 6 to get the proper offset.

# All Compiler Functions are highlighted in cyan to tell them apart.
# Globals are:
Settings
FileLines
ZStack
State


# These are some example functions
speed(800)
diameter(6)
depth(-3)
line_to(10,10,-3)
# Line moves to the sx,sy and then down, whereas,
# line_to does not, it just goes to ex,ey 
line(0,0,10,10,-3)
# xc,yc,radius,segment length, and depth
circle(100,100,3,1.5,-3)
square(10,10,100,100,-3)

# Speed Control
speed(800) # sets the max feed speed
fast() # returns the max feed speed
slow() # returns 25% of max
slowly() # returns 35% of max

# Including gcode files
# You can include a gcode file and send it out like so:
include_gcode_from("./path/file.ngc",True)
# True means interpolate variables.
# Variables are things like #0-9, or #abc
# False means do not yet interpolate.
# When you include a gcode file, it is put into
# a buffer, to send it, you call:
send_gcode_lines()
# At this point, variables will be interpolated before
# sending.
setv("#0",-1) #set the variable named #0 to -1
getv("#myvar") # get the value of the variable
# Lines are in FileLines, so you can iterate
for l in FileLines:
   emit( _process_line(l) )

