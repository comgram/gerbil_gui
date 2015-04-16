import sys,traceback
import os
import math
import numpy
import logging
import collections
import time

from classes.highlighter import Highlighter
from classes.grbl import GRBL
from classes.glwidget2 import GLWidget
from classes.commandlineedit import CommandLineEdit
import compiler.gcode as COMPILER

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import pyqtSignal, QPoint, QSize, Qt, QCoreApplication, QTimer
from PyQt5.QtGui import QColor,QPalette
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QMessageBox, QSlider, QLabel, QPushButton, QWidget, QDialog, QMainWindow, QFileDialog, QLineEdit, QSpacerItem, QListWidgetItem)

from lib.qt.cnctoolbox.ui_mainwindow import Ui_MainWindow
from lib import gcodetools
from lib import utility

log_format = '%(asctime)s %(levelname)s %(message)s'
logging.basicConfig(level=100, format=log_format)

#G91 G0 Y1 G90
#G10 P0 L20 X0 Y0 Z0



class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, path):
        super(MainWindow, self).__init__()
        
        _logbuffer_size = 200
        
        self.setupUi(self)
        self.setupScripting()
        
        self.grbl = GRBL("mygrbl", path)
        
        COMPILER.receiver(self.grbl)
        COMPILER.Settings['log_callback'] = lambda str: self._add_to_loginput(str)
        
        self.grbl.poll_interval = 0.1
        self.grbl.set_callback(self.on_grbl_event)
        
        self.filename = None
        
        self.changed_state = False
        self.changed_loginput = False
        
        self.logbuffer = collections.deque(maxlen=_logbuffer_size)
        for i in range(1, _logbuffer_size):
            self.logbuffer.append("")
        
        self._rx_buffer_fill = 0
        self._rx_buffer_fill_last = 0
        
        self._progress_percent = 0
        self._progress_percent_last = 0
        
        
        # UI SETUP
        #=glWidget.add_vertex((0.5,0.5))
        self.glWidget = GLWidget()
        self.gridLayout_glwidget_container.addWidget(self.glWidget)
        
        self.pushButton_connect.clicked.connect(self.cnect)
        self.pushButton_disconnect.clicked.connect(self.disconnect)
        self.pushButton_homing.clicked.connect(self.grbl.homing)
        self.pushButton_killalarm.clicked.connect(self.grbl.killalarm)
        
        self.pushButton_filestream.clicked.connect(self.stream_file)
        self.pushButton_fileload.clicked.connect(self.pick_file)
        
        self.pushButton_hold.clicked.connect(self.grbl.hold)
        self.pushButton_resume.clicked.connect(self.grbl.resume)
        self.pushButton_abort.clicked.connect(self.abort)
        
        self.pushButton_zeroxyz.clicked.connect(self.zero_xyz)
        self.pushButton_zeroxy.clicked.connect(self.zero_xy)
        self.pushButton_zeroz.clicked.connect(self.zero_z)
        
        self.pushButton_check.clicked.connect(self.check)
        
        self.pushButton_w2mcoord.clicked.connect(self.w2mcoord)
        #self.pushButton_g0wzerosafe.clicked.connect(self.g0wzerosafe)
        self.pushButton_g0wzero.clicked.connect(self.g0wzero)
        
        self.pushButton_xminus.clicked.connect(self.xminus)
        self.pushButton_xplus.clicked.connect(self.xplus)
        self.pushButton_yminus.clicked.connect(self.yminus)
        self.pushButton_yplus.clicked.connect(self.yplus)
        self.pushButton_zminus.clicked.connect(self.zminus)
        self.pushButton_zplus.clicked.connect(self.zplus)
        
        self.horizontalSlider_feed_override.valueChanged.connect(self._feedoverride_value_changed)
        self.checkBox_feed_override.stateChanged.connect(self._feedoverride_changed)
        
        self.checkBox_incremental.stateChanged.connect(self._incremental_changed)

        self.lineEdit_cmdline = CommandLineEdit(self, self._cmd_line_callback)

        #self.line_edit_devicePath.setText("/dev/ttyACM0")

        self.verticalLayout_cmd.addWidget(self.lineEdit_cmdline)
    
        self.listWidget_logoutput.itemDoubleClicked.connect(self._on_logoutput_item_double_clicked)
        self.listWidget_logoutput.itemClicked.connect(self._on_logoutput_item_clicked)
        self.listWidget_logoutput.currentItemChanged.connect(self._on_logoutput_current_item_changed)
        self.logoutput_items = []
        self.logoutput_current_index = -1
        
        self.setWindowTitle("cnctoolbox")
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(30)
        
        self.pushButton_disconnect.setEnabled(False)
        self.pushButton_connect.setEnabled(True)
        
        #self.widget_jog.mouseMoveEvent.connect(self._on_jog_mousemove)
        
        
        #QFont f( "Cantarell", 10, QFont::Bold);
        #textLabel->setFont( f);
        
        self.label_loginput = QLabel()
        self.label_loginput.setTextFormat(Qt.RichText)
        self.scrollArea_loginput.setWidget(self.label_loginput)
        self.label_loginput.setAlignment(Qt.AlignBottom | Qt.AlignLeft)
        self.label_loginput.setStyleSheet("font: 9pt")
        #self.label_loginput.setText("<b style='color: red'>blah</b>")
        
        #self.progressBar_buffer.setValue(50)
        
        
        #self._add_to_logoutput("G0 X0 Y0 Z0")
        #self._add_to_logoutput("G0 X100")
        #self._add_to_logoutput("G0 Y100")
        #self._add_to_logoutput("G0 Z100")
        
        return
    
        self.xSlider = self.createSlider()
        self.ySlider = self.createSlider()
        self.zSlider = self.createSlider()
        self.xPanSlider = self.createSlider()
        self.yPanSlider = self.createSlider()
        self.zPanSlider = self.createSlider()

        self.xSlider.valueChanged.connect(self.glWidget.setXRotation)
        self.glWidget.xRotationChanged.connect(self.xSlider.setValue)
        self.ySlider.valueChanged.connect(self.glWidget.setYRotation)
        self.glWidget.yRotationChanged.connect(self.ySlider.setValue)
        self.zSlider.valueChanged.connect(self.glWidget.setZRotation)
        self.glWidget.zRotationChanged.connect(self.zSlider.setValue)
        self.xPanSlider.valueChanged.connect(self.glWidget.setXPan)
        self.yPanSlider.valueChanged.connect(self.glWidget.setYPan)
        self.zPanSlider.valueChanged.connect(self.glWidget.setZPan)

        mainLayout = QHBoxLayout()
        mainLayout.addWidget(self.label_mpos)
        mainLayout.addWidget(self.btn_poll)
        mainLayout.addWidget(self.btn_run)
        mainLayout.addWidget(self.btn_quit)
        mainLayout.addWidget(self.glWidget)
        mainLayout.addWidget(self.xSlider)
        mainLayout.addWidget(self.ySlider)
        mainLayout.addWidget(self.zSlider)
        mainLayout.addWidget(self.xPanSlider)
        mainLayout.addWidget(self.yPanSlider)
        mainLayout.addWidget(self.zPanSlider)
        self.setLayout(mainLayout)

        self.xSlider.setValue(1 * 16)
        self.ySlider.setValue(355 * 16)
        self.zSlider.setValue(1 * 16)
        
        self.setUpdatesEnabled(True)
        
    def setupScripting(self):
        print("Setting up Scripting Tab")
        p = self.scriptTextEdit.palette();
        
        self.scriptTextEdit.setStyleSheet("QPlainTextEdit { background-color: rgb(51, 51, 51); color: rgb(255,255,255); }");
        self.highlighter = Highlighter(self.scriptTextEdit.document())
        self.filenameLineEdit.setText("./compiler/examples.py")
        self.filenameLineEdit.setDisabled(False)
        self.linesToExecute.setDisabled(False)
        self.loadScriptButton.clicked.connect(self.load_script_clicked)
        self.saveScriptFileButton.clicked.connect(self.save_script_clicked)
        self.executeScriptButton.clicked.connect(self.execute_script_clicked)
    def execute_script_clicked(self,item):
        code = self.scriptTextEdit.toPlainText()
        COMPILER.evaluate(code)
    def load_script_clicked(self,item):
        fname = self.filenameLineEdit.text()
        with open(fname, 'r') as content_file:
            content = content_file.read()
        self.scriptTextEdit.setPlainText(content)
    def save_script_clicked(self,item):
        fname = self.filenameLineEdit.text()
        with open(fname, 'w') as content_file:
            content_file.write(self.scriptTextEdit.toPlainText())
        self._add_to_loginput("File {} written.".format(fname))

        
    def on_grbl_event(self, event, *data):
        if event == "on_stateupdate":
            self.state = data[0]
            self.mpos = data[1]
            self.wpos = data[2]
            if self.grbl.connected:
                self.changed_state = True
            
        elif event == "on_send_command":
            pass
            #logging.log(300, "GRBL event: %s, %s", event, data)
            #gcodeblock = data[0]
            #self.logbuffer.append(gcodeblock)
            
        elif event == "on_processed_command":
            self._add_to_loginput("<span style='color: green'>Line {}: {}</span>".format(data[0], data[1]))
            
        elif event == "on_error":
            self._add_to_loginput("<span style='color: red'><b>{}</b></span>".format(data[0]))
            self._add_to_loginput("<span style='color: red'><b>Error was in line {}: {}</b></span>".format(data[2], data[1]))
            
        elif event == "on_alarm":
            self._add_to_loginput("<span style='color: orange'>" + data[0] + "</span>")
            
        elif event == "on_read":
            self._add_to_loginput("<span style='color: blue'>{}</span>".format(data[0]))
            
        elif event == "on_log":
            self._add_to_loginput("<i>" + data[0] + "</i>")
            
        elif event == "on_rx_buffer_percentage":
            self._rx_buffer_fill = data[0]
            
        elif event == "on_progress_percent":
            self._progress_percent = data[0]
            
        elif event == "on_linear_distance_mode_change":
            self.label_distancemode.setText(data[0])
            
        elif event == "on_arc_distance_mode_change":
            self.label_arcdistancemode.setText(data[0])
            
        elif event == "on_feed_change":
            self.horizontalSlider_feed.setValue(data[0])
            
        elif event == "on_streaming_complete":
            self.grbl.set_incremental_streaming(True)
            
        elif event == "on_boot":
            self.pushButton_disconnect.setEnabled(True)
            self.pushButton_connect.setEnabled(False)
            
        elif event == "on_disconnected":
            self.pushButton_disconnect.setEnabled(False)
            self.pushButton_connect.setEnabled(True)
            self.lcdNumber_mx.display("{:0.2f}".format(8888.88))
            self.lcdNumber_my.display("{:0.2f}".format(8888.88))
            self.lcdNumber_mz.display("{:0.2f}".format(8888.88))
            self.lcdNumber_wx.display("{:0.2f}".format(8888.88))
            self.lcdNumber_wy.display("{:0.2f}".format(8888.88))
            self.lcdNumber_wz.display("{:0.2f}".format(8888.88))
            self.label_state.setText("disconnected")
            self._add_to_loginput("<i>Successfully disconnected!</i>")
            self._add_to_loginput("")
        
        else:
            self._add_to_loginput("Grbl event {} not yet implemented".format(event))
            
            
    def _render_logbuffer(self):
        self.label_loginput.setText("<br />".join(self.logbuffer))
        self.scrollArea_loginput.verticalScrollBar().setValue(self.scrollArea_loginput.verticalScrollBar().maximum())
            
        
    def refresh(self):
        self.glWidget.updateGL()
        
        if self.changed_state:
            self.lcdNumber_mx.display("{:0.2f}".format(self.mpos[0]))
            self.lcdNumber_my.display("{:0.2f}".format(self.mpos[1]))
            self.lcdNumber_mz.display("{:0.2f}".format(self.mpos[2]))
            self.lcdNumber_wx.display("{:0.2f}".format(self.wpos[0]))
            self.lcdNumber_wy.display("{:0.2f}".format(self.wpos[1]))
            self.lcdNumber_wz.display("{:0.2f}".format(self.wpos[2]))
            self.glWidget.mpos = self.mpos
            self.glWidget.add_vertex((self.wpos[0],self.wpos[1]))
            self.glWidget.paintGL()
            

            if self.state == "Idle":
                color = "green"
            elif self.state == "Run":
                color = "blue"
            elif self.state == "Check":
                color = "orange"
            elif self.state == "Hold":
                color = "yellow"
            elif self.state == "Alarm":
                color = "red"
                
            self.label_state.setText("<span style='color: {}'>{}</span>".format(color, self.state))
            
            self.changed_state = False
            
        if self.changed_loginput == True:
            self._render_logbuffer()
            self.changed_loginput = False
            
        if self._rx_buffer_fill_last != self._rx_buffer_fill:
            self.progressBar_buffer.setValue(self._rx_buffer_fill)
            self._rx_buffer_fill_last = self._rx_buffer_fill
            
        if self._progress_percent_last != self._progress_percent:
            self.progressBar_job.setValue(self._progress_percent)
            self._progress_percent_last = self._progress_percent
        

    def _add_to_loginput(self, line):
        self.logbuffer.append(line)
        self.changed_loginput = True
        
    def _add_to_logoutput(self, line):
        item = QListWidgetItem(line, self.listWidget_logoutput)
        self.logoutput_items.append(item)
        self.listWidget_logoutput.setCurrentItem(item)
        self.listWidget_logoutput.scrollToBottom()
        self.logoutput_at_end = True
    
    def _exec_cmd(self, cmd):
        cmd = cmd.strip()
        if len(cmd) == 0:
            return
        
        self._add_to_logoutput(cmd)
        self.lineEdit_cmdline.setText("")
        
        if cmd[0] == "=":
            # dynamically executed python code must begin with an equal sign
            # "self." is prepended for convenience
            if cmd[1] == "=":
                kls = "COMPILER"
                cmd = cmd[2:]
            else:
                kls = "self" 
                cmd = cmd[1:]
            cmd = "%s.%s" % (kls,cmd)
            try:
                self._add_to_loginput("Executing: %s" % cmd)
                exec(cmd)
            except:
                self._add_to_loginput("Error during dynamic python execution:<br />{}".format(sys.exc_info()))
                print("Exception in user code:")
                traceback.print_exc(file=sys.stdout)
        else:
            self.grbl.send(cmd)

        
    # UI SLOTS
    
    def _cmd_line_callback(self, data):
        if data == "Enter":
            cmd = self.lineEdit_cmdline.text()
            self._exec_cmd(cmd)
        elif data == "UP":
            if self.logoutput_at_end:
                itemcount = len(self.logoutput_items) - 1
                row = itemcount
                self.logoutput_at_end = False
            else:
                row = self.listWidget_logoutput.currentRow()
                row -= 1
            row = 0 if row < 0 else row
            item = self.logoutput_items[row]
            self.listWidget_logoutput.setCurrentItem(item)
            self.lineEdit_cmdline.setText(item.text())
            
        elif data == "DOWN":
            row = self.listWidget_logoutput.currentRow()
            itemcount = len(self.logoutput_items) - 1
            row += 1
            row = itemcount if row > itemcount else row
            item = self.logoutput_items[row]
            self.listWidget_logoutput.setCurrentItem(item)
            self.lineEdit_cmdline.setText(item.text())
            
    
    def _on_logoutput_item_double_clicked(self, item):
        self._exec_cmd(item.text())
        
    def _on_logoutput_item_clicked(self, item):
        self.lineEdit_cmdline.setText(item.text())
        
    def _on_logoutput_current_item_changed(self, item_current, item_previous):
        self.lineEdit_cmdline.setText(item_current.text())
        self.logoutput_at_end = False

    def pick_file(self):
        filename_tuple = QFileDialog.getOpenFileName(self, "Open File", os.getcwd(), "GCode Files (*.ngc *.gcode *.nc)")
        self.filename = filename_tuple[0]
        #self.pushButton_filestream.setText(self.filename)
        #self.plainTextEdit_log()
        
    
    def xminus(self):
        step = - self.doubleSpinBox_jogstep.value()
        self.grbl.send("G91")
        self.grbl.send("G0 X" + str(step))
        self.grbl.send("G90")
        
        
    def xplus(self):
        step = self.doubleSpinBox_jogstep.value()
        self.grbl.send("G91")
        self.grbl.send("G0 X" + str(step))
        self.grbl.send("G90")
        
    
    def yminus(self):
        step = - self.doubleSpinBox_jogstep.value()
        self.grbl.send("G91")
        self.grbl.send("G0 Y" + str(step))
        self.grbl.send("G90")
        
        
    def yplus(self):
        step = self.doubleSpinBox_jogstep.value()
        self.grbl.send("G91")
        self.grbl.send("G0 Y" + str(step))
        self.grbl.send("G90")
        
    
    def zminus(self):
        step = - self.doubleSpinBox_jogstep.value()
        self.grbl.send("G91")
        self.grbl.send("G0 Z" + str(step))
        self.grbl.send("G90")
        
        
    def zplus(self):
        step = self.doubleSpinBox_jogstep.value()
        self.grbl.send("G91")
        self.grbl.send("G0 Z" + str(step))
        self.grbl.send("G90")
        
        
    def _feedoverride_value_changed(self):
        val = self.horizontalSlider_feed.value()
        self.lcdNumber_feed.display(val)
        self.grbl.request_feed(val)
        
    def _feedoverride_changed(self, val):
        val = False if val == 0 else True
        # first write feed to Grbl
        self._feedoverride_value_changed()
        # next set the boolean flag
        self.grbl.set_feed_override(val)
        
    def _incremental_changed(self, val):
        val = False if val == 0 else True
        self.grbl.set_incremental_streaming(val)
                  
    def abort(self):
        #self.label_loginputline.setText("")
        self.grbl.abort()
        
        
    def reset(self):
        #self.label_loginputline.setText("")
        self.grbl.abort()
        
    
    def stream_file(self):
        #self.grbl.set_feed_override(self.checkBox_feedoverride.isChecked())
        #self.grbl.set_feed(self.horizontalSlider_feed.value())
        self.grbl.send("f:" + self.filename)
        
        
    def check(self):
        self.grbl.send("$C")
        
        
    def zero_xyz(self):
        self.grbl.send("G92 X0 Y0 Z0")
        
        
    def zero_xy(self):
        self.grbl.send("G92 X0 Y0")
        
        
    def zero_z(self):
        self.grbl.send("G92 Z0")
        
        
    def w2mcoord(self):
        self.grbl.send("G92.1")
        
        
    #def g0wzerosafe(self):
        #self.grbl.send("G0 Z20")
        #self.grbl.send("G0 X0 Y0")
        
        
    def g0wzero(self):
        self.grbl.send("G0 X0 Y0 Z0")
        
        
    def cnect(self):
        self.pushButton_connect.setEnabled(False)
        #self.pushButton_disconnect.setEnabled(False)
        self.grbl.cnect()
        
        #self.horizontalSlider_feed.setValue(100)
        #self.checkBox_feedoverride.setChecked(False)
        
        
    def disconnect(self):
        #self.pushButton_connect.setEnabled(False)
        self.pushButton_disconnect.setEnabled(False)
        self.grbl.disconnect()
        
        #self.horizontalSlider_feed.setValue(100)
        #self.checkBox_feedoverride.setChecked(False)
        
        
    # call: =bbox(True)
    def bbox(self, move_z=False, gcode=None):
        if gcode:
            movements = gcodetools.draw_bbox(gcode, move_z)
        elif self.filename:
            gcode = utility.read_file_to_linearray(self.filename)
            movements = gcodetools.draw_bbox(gcode, move_z)
        else:
            self._add_to_loginput("<i>No file set and no gcode provided.</i>")
            return
        
        self.grbl.send(movements)
        
        
    def createSlider(self):
        slider = QSlider(Qt.Vertical)

        slider.setRange(0, 360 * 16)
        slider.setSingleStep(16)
        slider.setPageStep(15 * 16)
        slider.setTickInterval(15 * 16)
        slider.setTickPosition(QSlider.TicksRight)

        return slider


    def _on_jog_mousemove(self, event):
        print("MOVE", event.pos.x(), event.pos.y())

