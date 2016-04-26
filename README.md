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

    git clone ...
    cd cnctoolbox
    git clone git@github.com:michaelfranzl/pyglpainter.git
    git clone git@github.com:michaelfranzl/gerbil.git
    
Get help on command line options:

    ./cnctoolbox.py -h
    
To start the GUI:

    ./cnctoolbox gui --path=/dev/ttyACM0


## Development

Convert Qt .ui file into Python class:

    pyuic5 lib/qt/cnctoolbox/mainwindow.ui > lib/qt/cnctoolbox/ui_mainwindow.py
    
    


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