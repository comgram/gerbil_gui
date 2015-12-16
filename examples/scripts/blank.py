# my cnctoolbox script!
#
c = compiler
t = gcodetools
grbl = self.grbl

self.new_job()

# draw a simple square
input = []
input.append("F200")
input.append("G0X0")
#input.append("G1X100")
#input.append("G1Y100")
#input.append("G1X0")
#input.append("G1Y0")
input.append("G2 X300 Y300 R300")

grbl.preprocessor.do_fractionize_lines = True
grbl.preprocessor.do_fractionize_arcs = True
grbl.write(input)
grbl.preprocessor.do_fractionize_lines = True
grbl.preprocessor.do_fractionize_arcs = True

# do cool stuff!