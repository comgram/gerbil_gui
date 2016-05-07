# (c) 2015 Michael Franzl

# This script reads a PNG image, translates it into G-Code
# and writes the resulting file to the tmp directory

p2l = pixel2laser
t = gcodetools

grbl = self.grbl
grbl.buffer = []

self.new_job()

gcode = p2l.do("tmp/patterntest2.png", 10, 20, 0)
#gcode = t.read("tmp/lasertest.ngc")

gcode = t.translate(gcode, [30, 30, 0])

#t.write("tmp/patterntest5dpmm.ngc", gcode)

grbl.preprocessor.do_fractionize_lines = False
grbl.preprocessor.do_fractionize_arcs = False
grbl.write(gcode)

#self.probe_load()
#grbl.buffer = t.bumpify(grbl.buffer, self.wpos, self.probe_points, self.probe_values)

self.set_target("simulator")
grbl.job_run()

