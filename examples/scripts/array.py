# Read a simple square G-Code from a file and create an array of 10 x 10 of the same square

t = gcodetools
grbl = self.grbl

self.new_job()

sq = t.read("examples/gcode/square_offset.ngc")

for i in range(0,200,20):
    for j in range(0, 200, 20):
        grbl.write(t.translate(sq, [i, j, 0]))


# Send the result straight to the simulator window
grbl.target = "simulator"
grbl.job_run()