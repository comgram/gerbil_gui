# Read a G-Code file and create a scaled copy of it at the origin

grbl = self.grbl
t = gcodetools

self.new_job()

gcode = ["M3"]
gcode += t.read("/mnt/files/output.ngc")
#gcode = t.read("examples/gcode/speedtest.ngc")

grbl.preprocessor.do_fractionize_lines = True
grbl.preprocessor.do_fractionize_arcs = True
grbl.write(gcode)

self.set_target("simulator")
grbl.job_run()

