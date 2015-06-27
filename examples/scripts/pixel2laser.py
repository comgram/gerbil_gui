# Lasers a bitmap!

p2l = pixel2laser
t = gcodetools

grbl = self.grbl

self.new_job()

gcode = p2l.do("tmp/patterntest3.png", 5, 20, 0.1)
#gcode = t.read("tmp/lasertest.ngc")

t.write("tmp/patterntest5dpmm.ngc", gcode)

grbl.write(gcode)

grbl.target = "simulator"
grbl.job_run()

