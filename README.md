# gerbil_gui - Graphical User Interface for the "grbl" CNC controller

Python scripting and realtime OpenGL 3D visualization of gcode plus
streaming to the [grbl](https://github.com/grbl/grbl) CNC controller,
implemented in Python3 with Qt5 bindings.


## Installation

Your graphics hardware and drivers need to support at least OpenGL version 3.0 with GLSL version 1.30.

You also need an Arduino board with a recent version of grbl flashed onto it.

Get and install Python3 and git for your OS. Then:

    git clone https://github.com/michaelfranzl/gerbil_gui
    cd gerbil_gui
    git clone https://github.com/michaelfranzl/gerbil.git
    git clone https://github.com/michaelfranzl/pyglpainter.git
    git clone https://github.com/michaelfranzl/gcode_machine.git
    
Start the GUI (the path to a serial port on Windows is "COMx" where x is a number):

    python ./gerbil_gui.py gui --path=/dev/ttyACM0


### Dependencies on Windows

    pip install pyserial
    pip install svgwrite
    pip install PyQt5
    pip install numpy
    pip install PyOpenGL
    pip insatll Pillow
    
The installation of the next two may not work via `pip` because you would
need to set up all compilation dependencies and compilers on Windows.

    pip install numpy
    pip install scipy
    
If the installation of numpy and scipy via the `pip` method doesn't work, download precompiled packages (matching with your Python version and architecture) from http://www.lfd.uci.edu/~gohlke/pythonlibs. Then do the following instead:

    pip install "numpy-1.11.0+mkl-cp35-cp35m-win_amd64.whl"
    pip install "scipy-0.17.0-cp35-none-win_amd64.whl"
    
This may require an upgrade of pip:

    python -m pip install --upgrade pip


    

### Dependencies on Debian Jessie

    apt-get install python3 python3-pip python3-serial python3-pil python3-numpy python3-pyqt5 
    python3-pyqt5.qtopengl python3-opengl
    
    pip install svgwrite
    
    
    
    
    

## License

Copyright (c) 2015 Michael Franzl

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.