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
    
    python3 -m pip install doxypy --user


### Get source:

    git clone gitrepos@cinderella.thebigrede.net:~/cnctoolbox.git
    cd cnctoolbox
    
Clone separate Gerbil repository:

    git clone gitrepos@cinderella.thebigrede.net:~/gerbil.git
    
    
Get help on command line options:

    ./cnctoolbox.py -h
    
To start the GUI:

    ./cnctoolbox gui /dev/ttyACM0
    
    

## How to script GRBL

Example for python3 console:

Initialize and connect to Grbl:
    
    grbl = GRBL("mygrbl", "/dev/ttyACM0")
    grbl.cnect()

TODO: Document the API, ideally via PyDoc


## Development

Convert Qt .ui file into Python class:

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
:Reset Coordinate System Offset 
  
  
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



Move in machine coordinates: G53 G0 X10 Y10 Z10

Set working coordinate systems 1-6 or G54-G59:
G10 L2 Px Xblah Yblah Zblah
G10 L2 P3 X3Y3Z3
G10 L2 P1 X0Y0Z0


Set offset for all 6 coordinate systems, relative from current coordinate system position. Will be zero after reset:
G92 X11Y11Z11

# TODO

Todo

# Resources

http://www.oberlin.edu/math/faculty/bosch/making-tspart-page.html