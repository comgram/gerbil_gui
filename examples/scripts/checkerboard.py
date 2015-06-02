# Read arbitrary G-Code from a file and create a checkerboard array of 8 x 8

t = gcodetools
grbl = self.grbl

self.new_job()

cat = t.read("examples/gcode/cat.ngc")

scaled_origin_cat = t.to_origin(t.scale_factor(cat, [0.2, 0.2, 0]))

for i in range(0,200,25):
    for j in range(0, 200, 25):
        x = 1 if j % 2 == 0 else 0
        if i % 2 == x:
            gcode = t.translate(scaled_origin_cat, [i, j, 0])
            grbl.write(gcode)




# The job will not be sent to Grbl, it will only be simulated. Be careful with the code below when you're sitting at the machine!

grbl.preprocessor.set_vars({"1":0})
grbl.target = "simulator"
grbl.job_run()