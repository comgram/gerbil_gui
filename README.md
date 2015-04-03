# cnctoolbox

## How to script GRBL

Example for python3 console:

    import logging
    from classes.grbl import GRBL

    log_format = '%(asctime)s %(levelname)s %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_format)

    grbl = GRBL("grbl1", "/dev/ttyACM0")
    grbl.cnect()
    grbl.poll_start()
    grbl.set_streamingfile("out.ngc")
    grbl.run()

    grbl.poll_stop()
    grbl.softreset()


grbl.disconect()
~~~