# (c) 2015 Michael Franzl

# This script reads a PNG image, translates it into G-Code
# and writes the resulting file to the tmp directory

p2l = pixel2laser
t = gcodetools

grbl = self.grbl

self.new_job()

gcode = p2l.do("tmp/patterntest2.png", 5, 20, 0.1)
#gcode = t.read("tmp/lasertest.ngc")

t.write("tmp/patterntest5dpmm.ngc", gcode)

grbl.preprocessor.do_fractionize = False
grbl.write(gcode)

self.set_target("simulator")
grbl.job_run()

