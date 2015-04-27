import sys,traceback
import os
import math
import numpy
import logging
import collections
import time
import re

from classes.highlighter import Highlighter
from gerbil.gerbil import Gerbil
from classes.simulator import Simulator
from classes.jogwidget import JogWidget
from classes.commandlineedit import CommandLineEdit
import compiler.gcode as COMPILER

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import pyqtSignal, QPoint, QSize, Qt, QCoreApplication, QTimer
from PyQt5.QtGui import QColor,QPalette
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QMessageBox, QSlider, QLabel, QPushButton, QWidget, QDialog, QMainWindow, QFileDialog, QLineEdit, QSpacerItem, QListWidgetItem, QMenuBar, QMenu, QAction, QTableWidgetItem

from lib.qt.cnctoolbox.ui_mainwindow import Ui_MainWindow
from lib import gcodetools
from lib import utility

#module_logger = logging.getLogger('cnctoolbox.window')

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, path):
        super(MainWindow, self).__init__()
        self.logger = logging.getLogger('cnctoolbox.window')
        
        _logbuffer_size = 200
        
        self.grbl = Gerbil("mygrbl", path)
        
        self.setupUi(self)
        
        self.modifyUi()
        self.setupScripting()
        
        # GENERIC SETUP BEGIN -----
        self.setWindowTitle("cnctoolbox")
        self.lcdNumber_feed_current.display("---")
        # GENERIC SETUP END -----
        
        ## LOGGING SETUP BEGIN ------
        # setup ring buffer for logging
        self.changed_loginput = False
        self.logoutput_items = []
        self.logoutput_current_index = -1
        self.logbuffer = collections.deque(maxlen=_logbuffer_size)
        
        for i in range(1, _logbuffer_size):
            self.logbuffer.append("")
            
        self.label_loginput = QLabel()
        self.label_loginput.setTextFormat(Qt.RichText)
        self.scrollArea_loginput.setWidget(self.label_loginput)
        self.label_loginput.setAlignment(Qt.AlignBottom | Qt.AlignLeft)
        self.label_loginput.setStyleSheet("font: 9pt")
        ## LOGGING SETUP END ------       
        
        
        # STATE VARIABLES BEGIN -----
        self.changed_state = False
        self._current_grbl_line_number = 0
        self._rx_buffer_fill = 0
        self._rx_buffer_fill_last = 0
        self._progress_percent = 0
        self._progress_percent_last = 0
        # STATE VARIABLES END -----
        
        



        ## MENU BAR SETUP BEGIN ----------
        self.menuBar = QMenuBar(self)
        self.action_file_set = QAction("Set", self)
        self.action_file_set.triggered.connect(self._pick_file)
        self.action_file_quit = QAction("Quit", self)
        self.action_file_quit.triggered.connect(self._quit)
        self.action_grbl_connect = QAction("Connect", self)
        self.action_grbl_connect.triggered.connect(self.cnect)
        self.action_grbl_disconnect = QAction("Disconnect", self)
        self.action_grbl_disconnect.triggered.connect(self.disconnect)
        self.menu_file = self.menuBar.addMenu("File")
        self.menu_grbl = self.menuBar.addMenu("Grbl")
        self.menu_file.addAction(self.action_file_set)
        self.menu_file.addAction(self.action_file_quit)
        self.menu_grbl.addAction(self.action_grbl_connect)
        self.menu_grbl.addAction(self.action_grbl_disconnect)
        self.action_grbl_disconnect.setEnabled(False)
        self.action_grbl_connect.setEnabled(True)
        ## MENU BAR SETUP END ----------
        
       
        
        ## SIGNALS AND SLOTS BEGIN-------
        self.comboBox_target.currentIndexChanged.connect(self._target_selected)
        self.pushButton_homing.clicked.connect(self.homing)
        self.pushButton_killalarm.clicked.connect(self.grbl.killalarm)
        self.pushButton_stream_start.clicked.connect(self.stream_start)
        self.pushButton_stream_stop.clicked.connect(self.stream_stop)
        self.pushButton_stream_clear.clicked.connect(self.grbl.stream_clear)
        self.pushButton_show_buffer.clicked.connect(self._show_buffer)
        self.pushButton_hold.clicked.connect(self.grbl.hold)
        self.pushButton_resume.clicked.connect(self.grbl.resume)
        self.pushButton_abort.clicked.connect(self.abort)
        self.pushButton_check.clicked.connect(self.check)
        self.pushButton_clearz.setDisabled(True)
        self.pushButton_clearxy.setDisabled(True)
        self.pushButton_clearz.clicked.connect(self.clearz)
        self.pushButton_clearxy.clicked.connect(self.clearxy)
        self.pushButton_g0xyorigin.clicked.connect(self.g0xyorigin)
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
        self.verticalLayout_cmd.addWidget(self.lineEdit_cmdline)
        self.listWidget_logoutput.itemDoubleClicked.connect(self._on_logoutput_item_double_clicked)
        self.listWidget_logoutput.itemClicked.connect(self._on_logoutput_item_clicked)
        self.listWidget_logoutput.currentItemChanged.connect(self._on_logoutput_current_item_changed)
        self.checkBox_sim_enable.stateChanged.connect(self._sim_enabled_changed)
        self.pushButton_sim_wipe.clicked.connect(self._sim_wipe)
        self.spinBox_start_line.valueChanged.connect(self._current_grbl_line_number_changed)
        self.pushButton_settings_download_grbl.clicked.connect(self.grbl.request_settings)
        self.pushButton_settings_save_file.clicked.connect(self.settings_save_into_file)
        self.pushButton_settings_load_file.clicked.connect(self.settings_load_from_file)
        self.pushButton_settings_upload_grbl.clicked.connect(self.settings_upload_to_grbl)
        ## SIGNALS AND SLOTS END-------
        
        
        ## TIMER SETUP BEGIN ----------
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(100)
        ## TIMER SETUP END ----------
        
        

        

        ## CS SETUP BEGIN ---------
        self._cs_names = {
            1: "G54",
            2: "G55",
            3: "G56",
            4: "G57",
            5: "G58",
            6: "G59",
                }
        self.pushButton_current_cs_setzero.clicked.connect(self._current_cs_setzero)
        
        for key, val in self._cs_names.items():
            self.comboBox_coordinate_systems.insertItem(key, val)
        self.comboBox_coordinate_systems.currentIndexChanged.connect(self._cs_selected)
        ## CS SETUP END ---------
        
        
        ## SIMULATOR SETUP BEGIN -------------
        self._sim_enabled = True
        self.simulator = Simulator()
        self.gridLayout_glwidget_container.addWidget(self.simulator)
        ## SIMULATOR SETUP END -------------
        
        self._add_to_logoutput("G0 X0 Y0")
        self._add_to_logoutput("=bbox()")
        
        self.on_job_completed_callback = None
        
        # GRBL SETUP BEGIN -----
        self.grbl.poll_interval = 0.1
        self.grbl.set_callback(self.on_grbl_event)
        self.grbl.set_target("serialport")
        self.grbl.cnect()
        self.comboBox_target.insertItem(0, "serialport")
        self.comboBox_target.insertItem(1, "simulator")
        self.comboBox_target.insertItem(2, "file")
        # GRBL SETUP END -----
        
        # COMPILER SETUP BEGIN -----
        COMPILER.receiver(self.grbl)
        COMPILER.Settings['log_callback'] = lambda str: self._add_to_loginput(str)
        # COMPILER SETUP END -----
        
        self.tableWidget_settings.setColumnWidth(2, 300)
        for row in range(0, 32):
            self.tableWidget_settings.setRowHeight(row, 15)
            
        
        
        ## JOG WIDGET SETUP BEGIN -------------
        self.jogWidget = JogWidget(self, self.grbl.send_with_queue)
        self.gridLayout_jog_container.addWidget(self.jogWidget)
        ## JOG WIDGET SETUP END -------------
        
        
    def modifyUi(self):
        self.pushButton_homing.setStyleSheet("background-color: rgb(102,217,239);")
        self.pushButton_resume.setStyleSheet("background-color: rgb(166,226,46);")
        self.pushButton_killalarm.setStyleSheet("background-color: rgb(198,31,31);color: white;")
        self.pushButton_hold.setStyleSheet("background-color: rgb(219,213,50);")
        self.pushButton_check.setStyleSheet("background-color: rgb(235,122,9);")
               
        
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
        

    # CALLBACKS
        
    def on_grbl_event(self, event, *data):
        if event == "on_stateupdate":
            self.state = data[0]
            self.mpos = data[1]
            self.wpos = data[2]
            if self.grbl.connected:
                self.changed_state = True
                
        elif event == "on_gcode_parser_stateupdate":
            gps = data[0]
            
            mm_string = "G" + gps[0]
            self.label_motionmode.setText(mm_string)
            
            cs_string = "G" + gps[1]
            ivd = {v: k for k, v in self._cs_names.items()}
            cs_nr = ivd[cs_string]
            self.set_cs(cs_nr)

            pm_string = "G" + gps[2]
            self.label_planemode.setText(pm_string)
            
            um_string = "G" + gps[3]
            self.label_unitmode.setText(um_string)
            
            dm_string = "G" + gps[4]
            self.label_distmode.setText(dm_string)
            
            fm_string = "G" + gps[5]
            self.label_feedmode.setText(fm_string)
            
            pm_string = "M" + gps[6]
            self.label_programmode.setText(pm_string)
            
            um_string = "M" + gps[7]
            self.label_spindle_state.setText(um_string)
            
            um_string = gps[11]
            self.label_current_rpm.setText(um_string)
            
        elif event == "on_send_command":
            pass
            #logging.log(300, "GRBL event: %s, %s", event, data)
            #gcodeblock = data[0]
            #self.logbuffer.append(gcodeblock)
            
        elif event == "on_processed_command":
            self._add_to_loginput("<span style='color: green'>Line {}: {}</span>".format(data[0], data[1]))
            self._current_grbl_line_number = int(data[0]) + 1
            
        elif event == "on_line_number_change":
            self._current_grbl_line_number = int(data[0]) + 1
            
        elif event == "on_error":
            self._add_to_loginput("<span style='color: red'><b>{}</b></span>".format(data[0]))
            self._add_to_loginput("<span style='color: red'><b>Error was in line {}: {}</b></span>".format(data[2], data[1]))
            
        elif event == "on_alarm":
            self._add_to_loginput("<span style='color: orange'>" + data[0] + "</span>")
            
        elif event == "on_read":
            self._add_to_loginput("<span style='color: blue'>{}</span>".format(data[0]))
            
        elif event == "on_log":
            self._add_to_loginput("<i>" + data[0] + "</i>")
            
        elif event == "on_bufsize_change":
            #what = data[0]
            msg = "{:d} Lines".format(data[1])
            
            self._current_grbl_buffer_size = int(data[1])
            self.label_bufsize.setText(msg)
            
            #enabled = self._current_grbl_buffer_size == 0
            #self.lineEdit_cmdline.setEnabled(enabled)
            #self.listWidget_logoutput.setEnabled(enabled)
            
        elif event == "on_rx_buffer_percentage":
            self._rx_buffer_fill = data[0]
            
        elif event == "on_progress_percent":
            self._progress_percent = data[0]
            
        elif event == "on_feed_change":
            feed = data[0]
            if feed == 0:
                self.lcdNumber_feed_current.display("---")
            else:
                self.lcdNumber_feed_current.display("{:d}".format(int(feed)))
                
        elif event == "on_streaming_complete":
            self.grbl.set_incremental_streaming(True)
            
        elif event == "on_boot":
            self.action_grbl_disconnect.setEnabled(True)
            self.action_grbl_connect.setEnabled(False)
            self.grbl.poll_start()
            
        elif event == "on_disconnected":
            self.action_grbl_disconnect.setEnabled(False)
            self.action_grbl_connect.setEnabled(True)
            self.lcdNumber_mx.display("{:0.2f}".format(8888.88))
            self.lcdNumber_my.display("{:0.2f}".format(8888.88))
            self.lcdNumber_mz.display("{:0.2f}".format(8888.88))
            self.lcdNumber_wx.display("{:0.2f}".format(8888.88))
            self.lcdNumber_wy.display("{:0.2f}".format(8888.88))
            self.lcdNumber_wz.display("{:0.2f}".format(8888.88))
            self.label_state.setText("disconnected")
            self._add_to_loginput("<i>Successfully disconnected!</i>")
            self._add_to_loginput("")
            
        elif event == "on_settings_downloaded":
            settings = self.grbl.get_settings()
            self.dict_into_settings_table(settings)
        
        elif event == "on_job_completed":
            self._add_to_loginput("JOB COMPLETED")
            if self.on_job_completed_callback:
                self.on_job_completed_callback()
        
        else:
            self._add_to_loginput("Grbl event {} not yet implemented".format(event))
            
    
    def refresh(self):
        self.label_current_line_number.setText(str(self._current_grbl_line_number))
        
        if self.changed_state:
            mx = self.mpos[0]
            my = self.mpos[1]
            mz = self.mpos[2]
            wx = self.wpos[0]
            wy = self.wpos[1]
            wz = self.wpos[2]
            self.lcdNumber_mx.display("{:0.2f}".format(mx))
            self.lcdNumber_my.display("{:0.2f}".format(my))
            self.lcdNumber_mz.display("{:0.2f}".format(mz))
            self.lcdNumber_wx.display("{:0.2f}".format(wx))
            self.lcdNumber_wy.display("{:0.2f}".format(wy))
            self.lcdNumber_wz.display("{:0.2f}".format(wz))
            
            self.jogWidget.wx_current = wx
            self.jogWidget.wy_current = wy
            self.jogWidget.wz_current = wz
            
            # simulator update
            if self._sim_enabled == True:
                self.simulator.mpos = self.mpos
                self.simulator.add_vertex((wx, wy, wz))
            
            if self.state == "Idle":
                color = "green"
                self.jogWidget.onIdle()
                self.grbl.request_gcode_parser_state()
                if self._rx_buffer_fill == 0:
                    self.listWidget_logoutput.setEnabled(True)
                    self.lineEdit_cmdline.setEnabled(True)
                    self.spinBox_start_line.setValue(self._current_grbl_line_number)
                    self.spinBox_start_line.setEnabled(True)
                
            elif self.state == "Run":
                color = "blue"
                self.spinBox_start_line.setEnabled(False)
                self.lineEdit_cmdline.setEnabled(False)
                self.listWidget_logoutput.setEnabled(False)
                
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
    
    
    # UI SLOTS
    
    def settings_save_into_file(self):
        filename_tuple = QFileDialog.getOpenFileName(self, "Open File", os.getcwd(), "")
        filepath = filename_tuple[0]
       
        settings_string = self.settings_table_to_str()
        with open(filepath, 'w') as f:
            f.write(settings_string)
            
            
    def settings_load_from_file(self):
        filename_tuple = QFileDialog.getOpenFileName(self, "Open File", os.getcwd(), "")
        filepath = filename_tuple[0]
        
        settings = {}
        with open(filepath, 'r') as f:
            for line in f:
                m = re.match("\$(.*)=(.*) \((.*)\)", line)
                if m:
                    key = int(m.group(1))
                    val = m.group(2)
                    comment = m.group(3)
                    settings[key] = {
                        "val" : val,
                        "cmt" : comment
                        }
                    
        self.dict_into_settings_table(settings)
            
        

    
    def settings_upload_to_grbl(self):
        settings_string = self.settings_table_to_str()
        was_incremental = self.checkBox_incremental.isChecked()
        
        self._add_to_loginput("<i>Stashing current buffer</i>")
        self.grbl.buffer_stash()
        self.grbl.set_incremental_streaming(True) # need this faster
        self.checkBox_incremental.setChecked(True)
        
        def settings_upload_complete():
            self.checkBox_incremental.setChecked(was_incremental)
            self._add_to_loginput("<i>Successfully uploaded settings!</i>")
            self.on_job_completed_callback = None
            self._add_to_loginput("<i>Unstashing previous buffer</i>")
            self.grbl.buffer_unstash()
        
        self.on_job_completed_callback = settings_upload_complete
        self._add_to_loginput("<i>Sending settings...</i>")
        self.grbl.send_with_queue(settings_string)
        
    
    def _current_grbl_line_number_changed(self, nr):
        self.grbl.set_current_line_number(int(nr) - 1)
    
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
    
    
    def _on_logoutput_item_double_clicked(self, item):
        self._exec_cmd(item.text())
        
        
    def _on_logoutput_item_clicked(self, item):
        self.lineEdit_cmdline.setText(item.text())
        
        
    def _on_logoutput_current_item_changed(self, item_current, item_previous):
        self.lineEdit_cmdline.setText(item_current.text())
        self.logoutput_at_end = False
        
        
    def _quit(self):
        self.grbl.disconnect()
        QApplication.quit()


    def _pick_file(self):
        filename_tuple = QFileDialog.getOpenFileName(self, "Open File", os.getcwd(), "GCode Files (*.ngc *.gcode *.nc)")
        self.grbl.load_file(filename_tuple[0])
    
    
    def xminus(self):
        step = - self.doubleSpinBox_jogstep.value()
        self.grbl.send_immediately("G91")
        self.grbl.send_immediately("G0 X" + str(step))
        self.grbl.send_immediately("G90")
        
        
    def xplus(self):
        step = self.doubleSpinBox_jogstep.value()
        self.grbl.send_immediately("G91")
        self.grbl.send_immediately("G0 X" + str(step))
        self.grbl.send_immediately("G90")
        
    
    def yminus(self):
        step = - self.doubleSpinBox_jogstep.value()
        self.grbl.send_immediately("G91")
        self.grbl.send_immediately("G0 Y" + str(step))
        self.grbl.send_immediately("G90")
        
        
    def yplus(self):
        step = self.doubleSpinBox_jogstep.value()
        self.grbl.send_immediately("G91")
        self.grbl.send_immediately("G0 Y" + str(step))
        self.grbl.send_immediately("G90")
        
    
    def zminus(self):
        step = - self.doubleSpinBox_jogstep.value()
        self.grbl.send_immediately("G91")
        self.grbl.send_immediately("G0 Z" + str(step))
        self.grbl.send_immediately("G90")
        
        
    def zplus(self):
        step = self.doubleSpinBox_jogstep.value()
        self.grbl.send_immediately("G91")
        self.grbl.send_immediately("G0 Z" + str(step))
        self.grbl.send_immediately("G90")
        
        
    def _feedoverride_value_changed(self):
        val = self.horizontalSlider_feed_override.value()
        self.lcdNumber_feed_override.display(val)
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
        self.grbl.abort()
       
       
    def reset(self):
        self.grbl.abort()
        
        
    def stream_start(self):
        line_nr = self.spinBox_start_line.value()
        self.grbl.stream_start(line_nr - 1)
    
    
    def stream_stop(self):
        self.grbl.stream_stop()
        
    
    def stream_play(self):
        self.grbl.stream_start()
        
        
    def check(self):
        self.grbl.send_immediately("$C")
        
        
    def g0xyorigin(self):
        self.grbl.send_immediately("G0 X0 Y0")
        
        
    def clearz(self):
        self.grbl.send_immediately("G53 Z-10")
        
        
    def clearxy(self):
        """
        TODO: Make this configurable. Right now is the approx middle of our machine
        """
        self.grbl.send_immediately("G53 X-400 Y-600")
        
        
    def cnect(self):
        self.action_grbl_connect.setEnabled(False)
        self.grbl.cnect()
        
        
    def disconnect(self):
        self.action_grbl_disconnect.setEnabled(False)
        self.grbl.disconnect()
        
        

    def _show_buffer(self):
        self.plainTextEdit_job.setPlainText("\n".join(self.grbl.get_buffer()))
 

    def _cs_selected(self, idx):
        self._current_cs = idx + 1
        self.grbl.send_immediately(self._cs_names[self._current_cs])
        
        
    def _target_selected(self, idx):
        pass
    
        
    def _current_cs_setzero(self):
        self.grbl.send_immediately("G10 L2 P{:d} X{:f} Y{:f} Z{:f}".format(self._current_cs, self.mpos[0], self.mpos[1], self.mpos[2]))

    
    def _sim_enabled_changed(self, val):
        val = False if val == 0 else True
        self._sim_enabled = val
        
        
    def _sim_wipe(self):
        self.simulator.wipe()
        #self.simulator.paintGL()
        
        

    ## UTILITY FUNCTIONS
    
    def dict_into_settings_table(self, d):
        self.tableWidget_settings.clear()
        row = 0
        for key, val in sorted(d.items()):
            cell_a = QTableWidgetItem("$" + str(key))
            cell_b = QTableWidgetItem(val["val"])
            cell_c = QTableWidgetItem(val["cmt"])
            self.tableWidget_settings.setItem(row, 0, cell_a)
            self.tableWidget_settings.setItem(row, 1, cell_b)
            self.tableWidget_settings.setItem(row, 2, cell_c)
            self.tableWidget_settings.setRowHeight(row, 15)
            row += 1
    
    def settings_table_to_str(self):
        row_count = self.tableWidget_settings.rowCount()
        settings_string = ""
        for row in range(0, row_count):
            key = self.tableWidget_settings.item(row, 0).text()
            key = "$" + key.replace("$", "").strip()
            val = self.tableWidget_settings.item(row, 1).text().strip()
            cmt = self.tableWidget_settings.item(row, 2).text().strip()
            settings_string += key + "=" + val + " (" + cmt + ")\n"
        return settings_string
    
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
            self.grbl.send_immediately(cmd)

    def set_cs(self, nr):
        """
        A convenience function to select CS 1-6 and update the UI at the same time
        """
        self._current_cs = nr
        self.label_current_cs.setText(self._cs_names[self._current_cs])
        self.comboBox_coordinate_systems.setCurrentIndex(nr - 1)
        #self._cs_names[self._current_cs]
        

    def bbox(self, move_z=False):
        was_incremental = self.checkBox_incremental.isChecked()
        was_buf = self.grbl.get_buffer()
        
        movements = gcodetools.draw_bbox(was_buf, move_z)
        
        self.grbl.stream_clear()
        
        self.grbl.set_incremental_streaming(True)
        self.checkBox_incremental.setChecked(True)
        
        self.grbl.send_with_queue(movements)
        
        #self.grbl.set_incremental_streaming(was_incremental)
        #self.checkBox_incremental.setChecked(was_incremental)
        
        #self.grbl.stream_clear()
        #self.grbl.write("\n".join(was_buf))
        
    def _render_logbuffer(self):
        self.label_loginput.setText("<br />".join(self.logbuffer))
        self.scrollArea_loginput.verticalScrollBar().setValue(self.scrollArea_loginput.verticalScrollBar().maximum())

    def _add_to_loginput(self, line):
        self.logbuffer.append(line)
        self.changed_loginput = True
        
    def _add_to_logoutput(self, line):
        item = QListWidgetItem(line, self.listWidget_logoutput)
        self.logoutput_items.append(item)
        self.listWidget_logoutput.setCurrentItem(item)
        self.listWidget_logoutput.scrollToBottom()
        self.logoutput_at_end = True
        
    def homing(self):
        self.pushButton_clearz.setDisabled(False)
        self.pushButton_clearxy.setDisabled(False)
        self.grbl.homing()
        
    def _slider_model_rotate_moved(self, val):
        self.simulator.model_rotation = val