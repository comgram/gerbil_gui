# Lasers a bitmap!

p2l = pixel2laser
t = gcodetools

grbl = self.grbl

self.new_job()

gcode = p2l.do("tmp/patterntest.png", 5, 50, -0.05)
#gcode = t.read("tmp/lasertest.ngc")

t.write("tmp/patterntest5dpmm.ngc", gcode)

grbl.write(gcode)

grbl.target = "simulator"
grbl.job_run()

