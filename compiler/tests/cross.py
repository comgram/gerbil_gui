include_gcode_from("/media/ayon/KINGSTON/Cross1.ngc")
send_gcode_lines()
i = -3
include_gcode_from("/media/ayon/KINGSTON/CrossOutline.ngc",False)
comment("BEGINNING CrossOutline")

while i > -15:
    move(0,0)
    i -= 3
    print("i is: {}".format(i))
    if i < -15:
        i = -15
    setv("#1",i)
    send_gcode_lines()
comment("End CrossOutline")
include_gcode_from("/media/ayon/KINGSTON/CrossOutlinePunch.ngc",False)
comment("BEGINNING CrossOutlinePunch")

while i > -19:
    move(0,0)
    i -= 3
    print("now i is: {}".format(i))
    if i < -19:
        i = -19
    setv("#1",i)
    send_gcode_lines()
comment("End CrossOutlinePunch")