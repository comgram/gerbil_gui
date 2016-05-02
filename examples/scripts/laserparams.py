# my cnctoolbox script!
#
c = compiler
t = gcodetools
grbl = self.grbl



def feedtest_line(direction):
    width = 200
    gcodes = []
    gcodes.append("G1 F500")
    for x in range(0,width):
        if direction == 1:
            feed = int(500 + x * 28)
        else:
            feed = int(500 + (width - x) * 28)
        gcodes.append("G1 X{:d} F{:d} S255".format(direction, feed))
    return gcodes


gcodes = []
gcodes.append("S0")
gcodes.append("M3")
gcodes.append("G90")
gcodes.append("G0 X0 Y0")
gcodes.append("G91")

# output 3 lines separated by large distance
for y in range(1,4):
    gcodes += feedtest_line(1)
    gcodes.append("G0 Y1 S0")
    gcodes += feedtest_line(-1)
    gcodes.append("G0 Y1 S0")

# output 3 lines separated by narrow distance
for y in range(1,10):
    gcodes += feedtest_line(1)
    gcodes.append("G0 Y0.1 S0")
    gcodes += feedtest_line(-1)
    gcodes.append("G0 Y0.1 S0")

self.new_job()

self.grbl.preprocessor.do_fractionize_arcs = False
self.grbl.preprocessor.do_fractionize_lines = False
self.grbl.write(gcodes)

self.set_target("simulator")
self.job_run()
