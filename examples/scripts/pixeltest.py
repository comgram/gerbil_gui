# Lasers a bitmap!

p2l = pixel2laser
t = gcodetools

grbl = self.grbl

self.new_job()

#gcode = p2l.do("tmp/patterntest.png", 5, 50)
#gcode = t.read("tmp/lasertest.ngc")
gcode = "F10000\n"
gcode += "G1X0Y0\n"
dist = 1000
ppmm = 1
for i in range(0,dist * ppmm):
    gcode += "X{:.1f}S255\n".format(i/ppmm)
    

#t.write("tmp/patterntest5dpmm.ngc", gcode)

grbl.write(gcode)

grbl.target = "simulator"
grbl.job_run()

