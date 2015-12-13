# This script tests if the fractionization of circles by gerbil's preprocessor
# matches the actually traced path by the Grbl firmware.

grbl = self.grbl


input = []

input.append("F2000")
input.append("G0 X0 Y0")
input.append("G1 X20 Y20")

input.append("G17") # circle in XY plane
input.append("G2 X30 Y30 I5 J5") # CW circle

input.append("G18") # circle in XZ plane
input.append("G2 X30 Z30 I15 K15") # CW circle

input.append("G0 Y40") # line

input.append("G19") # circle in YZ plane
input.append("G2 Y40 Z30 J15 K15") # CW circle

input.append("G1 X0") # line

input.append("G17") # circle XY plane
input.append("G3 X0 Y40 Z0 I5 J5") # CCW helical movement down

input.append("G1 X-30") # line

input.append("G3 X-40Y50 R-8") # circle in radius mode, larger than 180°
input.append("G3 X-50Y60 R20") # circle in radius mode, smaller than 180°



# fractionize above G-Codes and render the line segments in the simulator
self.set_target("simulator")
grbl.job_new()
grbl.preprocessor.do_fractionize = True # this is the default
grbl.write(input)
grbl.job_run() # draw in simulator
    

# next, send the above G-Codes unmodified to the Grbl controller
# and see if the traced path matches whatever has been rendered before
self.set_target("firmware")
grbl.job_new()
grbl.preprocessor.do_fractionize = True # to compare with reality
grbl.write(input)
#grbl.job_run()