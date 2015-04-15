include_gcode_from("/home/michael/Documents/Cross1.ngc")
send_gcode_lines()
i = -2
include_gcode_from("/home/michael/Documents/CrossOutline.ngc",False)
comment("BEGINNING CrossOutline")

while i > -11:
    move(0,0)
    i -= 2
    print("i is: {}".format(i))
    if i < -11:
        i = -11
    setv("#1",i)
    send_gcode_lines()
comment("End CrossOutline")
include_gcode_from("/home/michael/Documents/CrossOutlinePunch.ngc",False)
comment("BEGINNING CrossOutlinePunch")

while i > -14:
    move(0,0)
    i -= 2
    print("now i is: {}".format(i))
    if i < -14:
        i = -14
    setv("#1",i)
    send_gcode_lines()
comment("End CrossOutlinePunch")