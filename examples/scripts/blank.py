# my cnctoolbox script!
#
c = compiler
t = gcodetools
grbl = self.grbl

input = []
input.append("G1X1000")

self.new_job()

self.grbl.write(input)

self.set_target("simulator")
self.job_run()
