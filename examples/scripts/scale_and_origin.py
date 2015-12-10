# Read a G-Code file and create a scaled copy of it at the origin

c = compiler
t = gcodetools
grbl = self.grbl

self.new_job()

cat = t.read("examples/gcode/cat.ngc")

grbl.write("\n".join(cat))
grbl.write("\n".join(t.bbox(cat)))

scaled_origin_cat = t.scale_factor(t.to_origin(cat), [0.2, 0.2, 0])

grbl.write("\n".join(scaled_origin_cat))
grbl.write("\n".join(t.bbox(scaled_origin_cat)))

self.sim_dialog.simulator_widget.draw_workpiece((110, 120, 10), (350, 650, 0))


grbl.preprocessor.set_vars({"1":0})
self.set_target("simulator")
grbl.job_run()

