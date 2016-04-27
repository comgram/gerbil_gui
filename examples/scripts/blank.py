# my cnctoolbox script!
#
c = compiler
t = gcodetools
grbl = self.grbl

gcodes = []

gcodes.append(";blah")
gcodes.append("G0 X20 Y20 Z20 ; nice command")
gcodes.append("G1 X30")

self.new_job()

self.grbl.preprocessor.do_fractionize_arcs = False
self.grbl.preprocessor.do_fractionize_lines = False
self.grbl.write(gcodes)

self.set_target("simulator")
self.job_run()
