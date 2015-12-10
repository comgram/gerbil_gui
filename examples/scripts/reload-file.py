# Read a G-Code file and create a scaled copy of it at the origin

grbl = self.grbl
t = gcodetools

self.new_job()

gcode = t.read("tmp/patterntest3.ngc")
print(gcode)

grbl.write("\n".join(gcode))

self.set_target("simulator")
grbl.job_run()

