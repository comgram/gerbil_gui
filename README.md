# cnctoolbox

## How to script GRBL

Example for python3 console:

import logging
from classes.grbl import GRBL

log_format = '%(asctime)s %(levelname)s %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format)

grbl = GRBL("mygrbl", "/dev/ttyACM0")
grbl.cnect()
grbl.set_streamingfile("out.ngc")
grbl.run()
grbl.disconect()

Other stuff:

grbl.poll_start()
grbl.poll_stop()

grbl.pause()
grbl.play()