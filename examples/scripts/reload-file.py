# Read a G-Code file and create a scaled copy of it at the origin

grbl = self.grbl
t = gcodetools

self.new_job()

#gcode = t.read("tmp/patterntest3.ngc")
gcode = t.read("/mnt/files/output.ngc")

grbl.preprocessor.do_fractionize_lines = False
grbl.preprocessor.do_fractionize_arcs = False
grbl.write(gcode)

self.set_target("simulator")
grbl.job_run()

