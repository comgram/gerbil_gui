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

Unfortunately this doesn't always work, so you may need to download svgwrite and pyparsing projects, and run `python3 setup.py install` for each of them.

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
    
    
### Non-Modal Commands

G4 P1
: Dwell 1 second

G10L2 
: Set Coordinate System

G10L20
: Set Coordinate System: Similar to G10 L2 except that instead of setting the offset/entry to the given value, it is set to a calculated value that makes the current coordinates become the given value.

G28
:Go to Predefined Position

G28.1
:Go to Predefined Position

G30
:Go to Predefined Position

G30.1
:Go to Predefined Position

G53
:Move in Machine Coordinates

G92
: Set Coordinate System Offset

G92.1
:Reset Coordinate System Offsets
  
  
### Motion Modes
G0
G1
G2
G3
G38.2
: probe toward workpiece, stop on contact, signal error if failure

G38.3
: probe toward workpiece, stop on contact

G38.4
: probe away from workpiece, stop on loss of contact, signal error if failure

G38.5
: probe away from workpiece, stop on loss of contact

G80
: canned cycle stop G80


### Feed Rate Modes

G93
: Inverse Time Mode

G94
: Units per Minute Mode

### Unit Modes
G20
: to use inches for length units

G21
: to use millimeters for length units



### Distance Modes

G90
: absolute distance mode

G91
: incremental distance mode

### Arc IJK Distance Modes

G91.1
: absolute distance mode for I, J & K offsets

### Plane Select Modes

G17
: Plane selection XY

G18
: Plane selection ZX

G19
: Plane selection YZ

### Tool Length Offset Modes

G43.1
: change subsequent motions by offsetting the Z and/or X offsets stored in the tool table.

G49
: cancels tool length compensation

### Cutter Compensation Modes
G40
: turn cutter compensation off

### Coordinate System Modes
G54 Select Coordinate System 1
G55
G56
G57
G58
G59

### Program Flow
M0
: Program Pause

M1
: Optional Pause

M2
: End Program

M30*
: End Program

### Coolant Control
M7*
M8
M9

### Spindle Control
M3
M4
M5

### Valid Non-Command Words

F, I, J, K, L, N, P, R, S, T, X, Y, Z



Go to Machine Zero: G53 G0 X0 Y0 Z0

Set coordinate for G54-G59: G10 L2 Px Xblah Yblah Zblah

# TODO

- Bug: only able to send 1 command from cmd line
- Bug: missing feed when feed override at start of file
- Feature: Auto-disconnect at startup
-Feature: Continue after errors
- 
