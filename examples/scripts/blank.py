# my cnctoolbox script!
#
c = compiler
t = gcodetools
grbl = self.grbl

self.new_job()

# draw a simple square
input = []
input.append("F100")
input.append("G1X1000")


grbl.preprocessor.do_fractionize_lines = True
grbl.preprocessor.do_fractionize_arcs = True
grbl.write(input)
grbl.preprocessor.do_fractionize_lines = True
grbl.preprocessor.do_fractionize_arcs = True

# do cool stuff!