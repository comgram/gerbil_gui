# my cnctoolbox script!
#
c = compiler
t = gcodetools
grbl = self.grbl

gcodes = []

gcodes.append(";blah")
gcodes.append("G0 X0 Y0 Z0 ; nice command")
gcodes.append("G1 X10 Y30")
gcodes.append("G4 P2")
gcodes.append("G2 X20 Y40 I5 J5")

self.new_job()

self.grbl.preprocessor.do_fractionize_arcs = True
self.grbl.preprocessor.do_fractionize_lines = True
self.grbl.write(gcodes)

self.set_target("simulator")
self.job_run()
