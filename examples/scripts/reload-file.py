# Read a G-Code file and create a scaled copy of it at the origin

grbl = self.grbl

self.new_job()

gcode = t.read("tmp/lasertest.ngc")

grbl.write(gcode)

grbl.target = "simulator"
grbl.job_run()

