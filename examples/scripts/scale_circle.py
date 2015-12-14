# (c) 2015 Michael Franzl

# This script demonstrates that relative-distance CW and CCW circles, in R as well as O mode, can be scaled via the gcodetools module.

grbl = self.grbl
t = gcodetools

# ===== THE SOURCE GCODE PROGRAM ======

# --- this first part will use Absolute distance mode
preamble = []
preamble.append("F1000")
preamble.append("G0 X0 Y0") # select arcs in XY plane
preamble.append("G17") # select arcs in XY plane

circles = []
circles.append("G91") # select relative distance mode
circles.append("G3 X15 Y40 R90") # Radius mode, less than 180 deg.
circles.append("G2 X-10 Y-10 R10") # Radius mode, more than 180 deg.
circles.append("G2 X-20 Y10 R-12") # Radius mode, more than 180 deg.
circles.append("G90") # reset to absolute distance mode


result = preamble
for i in range(1, 10):
    factor = 1/i
    lines = t.scale_factor(circles, [factor, factor, factor])
    result.extend(lines)

# fractionize above G-Codes and render the line segments in the simulator
self.set_target("simulator")
grbl.job_new()
grbl.preprocessor.do_fractionize = True # this is the default
grbl.write(result)
grbl.job_run() # draw in simulator
    

# next, send the above G-Codes unmodified to the Grbl controller
# and see if the traced path matches whatever has been rendered before
self.set_target("firmware")
grbl.job_new()
grbl.preprocessor.do_fractionize = False # to compare with reality
grbl.write(result)
#grbl.job_run()

grbl.preprocessor.do_fractionize = True # reset to default
