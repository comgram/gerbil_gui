# cnctoolbox

## How to script GRBL

Example for python3 console:

import logging
from colorlog import ColoredFormatter
from classes.grbl import GRBL

log_format = '%(asctime)s %(levelname)s %(message)s'

logging.basicConfig(level=0, format=log_format)

grbl = GRBL("mygrbl", "/dev/ttyACM0")
grbl.cnect()
grbl.send("f:out.ngc")

grbl.test_string()
grbl.send("G0 X100")

grbl.disconect()

Other stuff:

grbl.poll_start()
grbl.poll_stop()

grbl.pause()
grbl.play()
grbl.abort()
grbl.killalarm()

grbl._cleanup()

grbl.send("".join([x for x in open("data/eshapeoko-settings.txt").readlines()]))
