# cnctoolbox

## Installation

### Dependencies

For a Debian Jessie system:

Install Python 3
    apt-get install python3
    
Install Python 3 modules which are shipped with the Debian Jessie distribution:

    apt-get install python3-pip python3-serial python3-pil python3-numpy python3-pyqt5 python3-pyqt5.qtopengl python3-opengl

Install Python 3 modules not shipped with the Debian Jessie distribution: 
    
    python3 -m pip install svgwrite --user

### run!

    git clone ...
    cd cnctoolbox
    ./cnctoolbox.py -h
    
To start the GUI:

    ./cnctoolbox gui
    
    
    

## How to script GRBL

Example for python3 console:

First set up environment:

    import logging
    from classes.grbl import GRBL

    log_format = '%(asctime)s %(levelname)s %(message)s'
    logging.basicConfig(level=0, format=log_format)

Next, initialize and connect to Grbl:
    
    grbl = GRBL("mygrbl", "/dev/ttyACM0")
    grbl.cnect()

Now, work with Grbl. To send a file, Grbl must be in 'Idle' state:

    grbl.send("f:out.ngc")
    
The file will be read from disk line-by-line, so this is memory-efficient.
    
Settings (starting with a '$') placed amongst gcode in the file will be ignored. You have to send settings separately in the following way, and only when GRBL is in 'Idle' mode:

    grbl.send("$40=1\n$$12=0.002")
    
For settings, the GRBL class will use a simple challenge-response communication protocol (the next settings command will only be sent after an 'ok' has been received for the last settings command). This is neccessary due to Grbl's internals. To send an entire file full of settings, use this method (Grbl must be in Idle state otherwise this method will do nothing):

    grbl.settings_from_file("data/eshapeoko-settings.txt")

To send a single gcode command:

    grbl.send("G0 X100")
    
To send many commands, separate them with a newline character:

    grbl.send("G0 X100\nG0 X0")

This way, you can 'script' as many commands as you like, as fast as you like, without risking the overflow of Grbl's 128 byte serial receive buffer. The GRBL class will add them to an internal buffer and stream them as smoothly and fast as possible, using the method suggested by Grbl's main developer. With this method, Grbl's receive buffer will be kept as full as possible at any time, giving its look-ahead motion planner enough data to work with.

During a running job you can call `pause()` to pause the job. The axes will slow down smoothly. To resume after this, call `resume()`. The method `abort()` will stop the axes abruptly, but Grbl will retain it's current coordinates. But the internal buffer of the GRBL class will be emptied, so you can't resume a job.

    grbl.pause()
    grbl.resume()
    grbl.abort()

If Grbl is in alarm state, you can clear the alarm:

    grbl.killalarm()
    
To run the homing cycle:

    grbl.homing()

When you're done:

    grbl.disconnect()
    
This will call `abort()` to bring Grbl to a stop, and do some clean-up work. After that, it is safe to kill the Python program, or exit the Python console with Ctrl+D.

For integration into a larger project, the GRBL class features a multiple-purpose callback function `callback(event, *data)`:

    grbl.callback = my_function
    
Where `my_function`:

    def my_function(event, *data):
        pass
    
`callback` will be called for the following events:

* `on_boot`: When Grbl has booted
* `on_cnect`: When GRBL is connected to Grbl
* `on_stateupdate`: Is called in regular intervals adjustable by setting `grbl.poll_interval`. The default interval is 0.2 s (5Hz). `*data` will contain the string `state` and the 3-tuples `machine_pos` and `working_pos`.


## Development

    pyuic5 lib/qt/cnctoolbox/mainwindow.ui > lib/qt/cnctoolbox/ui_mainwindow.py