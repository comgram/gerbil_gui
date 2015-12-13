import sys,traceback
import os
import math
import numpy
import logging
import collections
import time
import re

from classes.highlighter import Highlighter
from classes.jogwidget import JogWidget
from classes.commandlineedit import CommandLineEdit
from classes.simulatordialog import SimulatorDialog
from gerbil.gerbil import Gerbil

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import pyqtSignal, QPoint, QSize, Qt, QCoreApplication, QTimer
from PyQt5.QtGui import QColor,QPalette
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QMessageBox, QSlider, QLabel, QPushButton, QWidget, QDialog, QMainWindow, QFileDialog, QLineEdit, QSpacerItem, QListWidgetItem, QMenuBar, QMenu, QAction, QTableWidgetItem, QDialog

from lib.qt.cnctoolbox.ui_mainwindow import Ui_MainWindow
from lib import gcodetools
from lib import utility
from lib import compiler
from lib import pixel2laser

        

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
        
        self.state = None
        self.state_hash = None
        self.state_hash_dirty = False
        self.state_cs_dirty = False
        self.state_stage_dirty = False
        
        self.wpos = (0, 0, 0)
        self.mpos = (0, 0, 0)
        
        self.job_run_timestamp = time.time()
        
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
        self.label_loginput.setTextInteractionFlags(Qt.TextSelectableByMouse)
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
        
        self.action_script_load = QAction("Open Script...", self)
        self.action_script_load.triggered.connect(self._pick_script)
        
        self.action_script_save = QAction("Save Script!", self)
        self.action_script_save.triggered.connect(self._save_script)
        
        self.action_script_save_as = QAction("Save Script As...", self)
        self.action_script_save_as.triggered.connect(self._save_script_as)
        
        self.action_file_set = QAction("Load G-Code...", self)
        self.action_file_set.triggered.connect(self._pick_file)
        
        self.action_file_quit = QAction("Quit!", self)
        self.action_file_quit.triggered.connect(self._quit)
        
        self.action_grbl_connect = QAction("Connect", self)
        self.action_grbl_connect.triggered.connect(self.cnect)
        self.action_grbl_disconnect = QAction("Disconnect", self)
        self.action_grbl_disconnect.triggered.connect(self.disconnect)
        
        self.menu_file = self.menuBar.addMenu("File")
        self.menu_grbl = self.menuBar.addMenu("Grbl")
        
        self.menu_file.addAction(self.action_script_load)
        self.menu_file.addAction(self.action_script_save)
        self.menu_file.addAction(self.action_script_save_as)
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
        self.pushButton_job_run.clicked.connect(self.job_run)
        self.pushButton_job_halt.clicked.connect(self.job_halt)
        self.pushButton_job_new.clicked.connect(self.new_job)
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
        self.spinBox_start_line.valueChanged.connect(self._current_grbl_line_number_changed)
        self.pushButton_settings_download_grbl.clicked.connect(self.grbl.request_settings)
        self.pushButton_settings_save_file.clicked.connect(self.settings_save_into_file)
        self.pushButton_settings_load_file.clicked.connect(self.settings_load_from_file)
        self.pushButton_settings_upload_grbl.clicked.connect(self.settings_upload_to_grbl)
        self.tableWidget_variables.cellChanged.connect(self._variables_edited)
        ## SIGNALS AND SLOTS END-------
        

        
        
        ## TIMER SETUP BEGIN ----------
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(20)
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
        
        self.sim_dialog = SimulatorDialog(self)
        self.sim_dialog.show()

        self._add_to_logoutput("=bbox()")
        self._add_to_logoutput("=remove_tracer()")
        self._add_to_logoutput("G0 X0 Y0")
        
        self.on_job_completed_callback = None
        
        # GRBL SETUP BEGIN -----
        self.grbl.setup_logging()
        self.grbl.poll_interval = 0.1
        self.grbl.callback = self.on_grbl_event
        self.grbl.cnect()
        
        self.targets = ["firmware", "simulator", "file"]
        self.comboBox_target.insertItem(0, self.targets[0])
        self.comboBox_target.insertItem(1, self.targets[1])
        self.comboBox_target.insertItem(2, self.targets[2])
        self.set_target("simulator")
        # GRBL SETUP END -----
        
        # compiler SETUP BEGIN -----
        compiler.receiver(self.grbl)
        compiler.Settings['log_callback'] = lambda msg: print("<b>COMPILER:</b> {}".format(msg))
        # compiler SETUP END -----
        
        self.tableWidget_settings.setColumnWidth(2, 300)
        for row in range(0, 32):
            self.tableWidget_settings.setRowHeight(row, 15)
            
        with open("examples/scripts/blank.py", 'r') as f: c = f.read()
        self.plainTextEdit_script.setPlainText(c)
        
        ## JOG WIDGET SETUP BEGIN -------------
        self.jogWidget = JogWidget(self, self.grbl.stream)
        self.gridLayout_jog_container.addWidget(self.jogWidget)
        ## JOG WIDGET SETUP END -------------
        
        
    def closeEvent(self, event):
        """
        Overloaded Qt function
        """
        print("GRACEFUL EXIT")
        self.grbl.disconnect()
        self.sim_dialog.close()
        #event.ignore()
        event.accept()
       
    # =log(self.grbl.travel_dist_buffer)
    def log(self, msg, color="black"):
        self._add_to_loginput(msg, color)
        
    #def conosole_log(self, msg):
        
        
    def new_job(self):
        self.grbl.job_new()
        self.spinBox_start_line.setValue(1)
        self.sim_dialog.simulator_widget.cleanup_stage()
        
        
    # modify whatever was hardcoded in the Qt Form Editor
    def modifyUi(self):
        self.pushButton_homing.setStyleSheet("background-color: rgb(102,217,239);")
        self.pushButton_resume.setStyleSheet("background-color: rgb(166,226,46);")
        self.pushButton_killalarm.setStyleSheet("color: black;")
        self.pushButton_abort.setStyleSheet("background-color: rgb(198,31,31);color: white;")
        self.pushButton_hold.setStyleSheet("background-color: rgb(219,213,50);")
        self.pushButton_check.setStyleSheet("background-color: rgb(235,122,9);")
        
        self.pushButton_homing.setText("⌂ Run Homing")
        self.pushButton_abort.setText("☠ ABORT/RESET")
        self.pushButton_killalarm.setText("⚐ Kill Alarm")
        self.pushButton_job_new.setText("✧ New")
        self.pushButton_job_halt.setText("⌛ Pause")
               
        
    def setupScripting(self):
        print("Setting up Scripting Tab")
        p = self.plainTextEdit_script.palette();
        
        self.plainTextEdit_script.setStyleSheet("QPlainTextEdit { background-color: rgb(51, 51, 51); color: rgb(255,255,255); }");
        self.highlighter = Highlighter(self.plainTextEdit_script.document())

        self.pushButton_script_run.clicked.connect(self.execute_script_clicked)
        
    # to be used by scripting only
    def set_target(self, targetname):
        idx = self.targets.index(targetname)
        self.comboBox_target.setCurrentIndex(idx)

    # CALLBACKS
        
    def on_grbl_event(self, event, *data):
        if event == "on_stateupdate":
            self.state = data[0]
            self.mpos = data[1]
            self.wpos = data[2]
            
            if self.grbl.connected:
                self.changed_state = True
                
        elif event == "on_hash_stateupdate":
            self.state_hash = data[0]
            self.state_hash_dirty = True
          
                
        elif event == "on_gcode_parser_stateupdate":
            gps = data[0]
            
            mm_string = "G" + gps[0]
            self.label_motionmode.setText(mm_string)
            
            # current coordinate system
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
            
            ss_string = "M" + gps[7]
            self.label_spindle_state.setText(ss_string)
            
            cr_string = gps[11]
            self.label_current_rpm.setText(cr_string)
            
        elif event == "on_processed_command":
            self._add_to_loginput("✓ Line{}: {}".format(data[0], data[1]), "green")
            self._current_grbl_line_number = int(data[0]) + 1
            
        elif event == "on_line_number_change":
            self._current_grbl_line_number = int(data[0]) + 1
            
        elif event == "on_eta_change":
            secs = int(data[0])
            hours = math.floor(secs / 3600)
            secs = secs - hours * 3600
            
            mins = math.floor(secs / 60)
            secs = secs - mins * 60
            
            self.label_time.setText("ETA {:02d}:{:02d}:{:02d}".format(hours, mins, secs))
            
        elif event == "on_error":
            self._add_to_loginput("<b>◀ {}</b>".format(data[0]), "red")
            if data[2] > -1:
                self._add_to_loginput("<b>✗ Error was in line {}: {}</b>".format(data[2], data[1]), "red")
            
        elif event == "on_alarm":
            self._add_to_loginput("☹ " + data[0], "orange")
            
        elif event == "on_read":
            self._add_to_loginput("◀ {}".format(data[0]), "#000099")
            
        elif event == "on_write":
            self._add_to_loginput("▶ {}".format(data[0]), "#990099")
            
        elif event == "on_log":
            colors = {
                0: "black", # notset
                10: "#999999", # debug
                20: "#555555", # info
                30: "orange", # warning
                40: "red", # error
                50: "red", # critical
                }
            lr = data[0] # LogRecord instance
            message = lr.msg % lr.args
            level = lr.levelno
            levelname = lr.levelname
            filename = lr.filename
            funcname = lr.funcName
            lineno = lr.lineno
            
            color = colors[level]
            
            if level >= 40:
                txt = "{}: {} ({}:{}:{})".format(levelname, message, filename, funcname, lineno)
            else:
                txt = message
            
            
            
            self._add_to_loginput("✎ " + message, color)
            
        elif event == "on_bufsize_change":
            #what = data[0]
            msg = "{:d} Lines".format(data[0])
            
            self._current_grbl_buffer_size = int(data[0])
            self.label_bufsize.setText(msg)
            
            #enabled = self._current_grbl_buffer_size == 0
            #self.lineEdit_cmdline.setEnabled(enabled)
            #self.listWidget_logoutput.setEnabled(enabled)
            
        elif event == "on_rx_buffer_percent":
            self._rx_buffer_fill = data[0]
            
        elif event == "on_progress_percent":
            self._progress_percent = data[0]
            
        elif event == "on_preprocessor_feed_change":
            feed = data[0]
            if feed == None:
                self.lcdNumber_feed_current.display("---")
            else:
                self.lcdNumber_feed_current.display("{:d}".format(int(feed)))
                
        elif event == "on_streaming_complete":
            self.grbl.incremental_streaming = True
            
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
            settings = data[0] #self.grbl.get_settings()
            self.dict_into_settings_table(settings)
            self.state_stage_dirty = True
        
        elif event == "on_job_completed":
            diff = time.time() - self.job_run_timestamp
            #self._add_to_loginput("JOB COMPLETED in {:.2f} sec".format(diff))
            if self.on_job_completed_callback:
                self.on_job_completed_callback()
                
        elif event == "on_vars_change":
            keys = data[0]
            self.var_keys_into_var_table(keys)
            
        elif event == "on_simulation_finished":
            gcode = data[0]
            cwpos = self.wpos
            ccs = self._cs_names[self._current_cs]
            self.sim_dialog.simulator_widget.draw_gcode(gcode, cwpos, ccs)
            self._current_grbl_line_number = self.grbl._current_line_nr
            self.spinBox_start_line.setValue(self._current_grbl_line_number)
            
        elif event == "on_line_sent":
            line_number = data[0]
            line_str = data[1]
            self.sim_dialog.simulator_widget.highlight_gcode_line(line_number)
        
        else:
            self._add_to_loginput("Grbl event {} not yet implemented".format(event))
            
    
    def remove_tracer(self):
        self.sim_dialog.simulator_widget.remove_item("tracer")
        
    def refresh(self):
        self.label_current_line_number.setText(str(self._current_grbl_line_number))
        
        if self.state_hash_dirty == True:
            # used to draw/update origins of coordinate systems (after $# command)
            for key, tpl in self.state_hash.items():
                if re.match("G5[4-9].*", key):
                    self.sim_dialog.simulator_widget.draw_coordinate_system(key, tpl)
            self.state_hash_dirty = False
            
        if self.state_stage_dirty == True:
            # used to draw/update the workarea (stage) (after $$ command)
            workarea_x = int(float(self.grbl.settings[130]["val"]))
            workarea_y = int(float(self.grbl.settings[131]["val"]))
            self.sim_dialog.simulator_widget.draw_stage(workarea_x, workarea_y)
            self.state_stage_dirty = False
            
            
        if self.state_cs_dirty == True:
            # used to highlight coordinate systems (after $G command)
            for idx, val in self._cs_names.items():
                do_highlight = val == self._cs_names[self._current_cs]
                cs_item = self.sim_dialog.simulator_widget.items[val]
                cs_item.highlight(do_highlight)
                
            #self.sim_dialog.simulator_widget.cleanup_stage()
            
            self.sim_dialog.simulator_widget.draw_asap = True
            self.state_cs_dirty = False
        
        if self.changed_state:
            # used to update the opengl tool, and UI displays
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
            self.sim_dialog.simulator_widget.draw_tool(self.mpos)
            
            if self.state == "Idle":
                color = "green"
                self.jogWidget.onIdle()
                self.grbl.gcode_parser_state_requested = True
                self.grbl.hash_state_requested = True
                if self._rx_buffer_fill == 0:
                    self.listWidget_logoutput.setEnabled(True)
                    self.lineEdit_cmdline.setEnabled(True)
                    self.spinBox_start_line.setValue(self._current_grbl_line_number)
                    self.spinBox_start_line.setEnabled(True)
                
            elif self.state == "Run":
                color = "blue"
                self.spinBox_start_line.setEnabled(False)
                #self.lineEdit_cmdline.setEnabled(False) #xxx
                #self.listWidget_logoutput.setEnabled(False)
                
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
        self.grbl.incremental_streaming = True
        self.checkBox_incremental.setChecked(True)
        
        def settings_upload_complete():
            self.checkBox_incremental.setChecked(was_incremental)
            self._add_to_loginput("<i>Successfully uploaded settings!</i>")
            self.on_job_completed_callback = None
            self._add_to_loginput("<i>Unstashing previous buffer</i>")
            self.grbl.buffer_unstash()
        
        self.on_job_completed_callback = settings_upload_complete
        self._add_to_loginput("<i>Sending settings...</i>")
        self.grbl.stream(settings_string)
        
    
    def _current_grbl_line_number_changed(self, nr):
        self.grbl.current_line_number = int(nr) - 1
    
    def execute_script_clicked(self,item):
        code = self.plainTextEdit_script.toPlainText()
        try:
            exec(code)
        except:
            txt = traceback.format_exc()
            txt = re.sub(r"\n", "<br/>", txt)
            self._add_to_loginput(txt)
        #compiler.evaluate(code)
    
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
        
    def _pick_script(self):
        filename_tuple = QFileDialog.getOpenFileName(self, "Open Script", os.getcwd() + "/examples/scripts", "Python3 Files (*.py)")
        fname = filename_tuple[0]
        with open(fname, 'r') as content_file: content = content_file.read()
        self.plainTextEdit_script.setPlainText(content)
        self.label_script_filename.setText(fname)
        
    def _save_script(self):
        fname = self.label_script_filename.text()
        if fname == "New file":
            self._save_script_as()
            return
        
        with open(fname, 'w') as content_file:
            content_file.write(self.plainTextEdit_script.toPlainText())
        self._add_to_loginput("File {} written.".format(fname))
        self.label_script_filename.setText(fname)
        
    def _save_script_as(self):
        filename_tuple = QFileDialog.getSaveFileName(self, "Save Script", os.getcwd())
        fname = filename_tuple[0]
        #fname = self.label_script_filename.text()
        with open(fname, 'w') as content_file:
            content_file.write(self.plainTextEdit_script.toPlainText())
        self._add_to_loginput("File {} written.".format(fname))
        self.label_script_filename.setText(fname)
        

    
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
        self.grbl.incremental_streaming = val
             
             
    def abort(self):
        self.grbl.abort()
       
       
    def reset(self):
        self.grbl.abort()
        
        
    def job_run(self):
        line_nr = self.spinBox_start_line.value()
        self.job_run_timestamp = time.time()
        self.grbl.job_run(line_nr - 1)
    
    
    def job_halt(self):
        self.grbl.job_halt()
        
    
    def stream_play(self):
        self.grbl.job_run()
        
        
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
        self.grbl.send_immediately("$#")
        
    # callback for the drop-down
    def _target_selected(self, idx):
        self.current_target = self.targets[idx]
        self.grbl.target = self.current_target
        self.pushButton_job_run.setText("➾ {}".format(self.current_target))
        if self.current_target == "firmware":
            self.pushButton_job_run.setText("⚒ RUN MACHINE ⚠")
            self.pushButton_job_run.setStyleSheet("background-color: rgb(198,31,31); color: white;")
        else:
            self.pushButton_job_run.setStyleSheet("background-color: none; color: black;")
            
    
        
    def _current_cs_setzero(self):
        self.grbl.send_immediately("G10 L2 P{:d} X{:f} Y{:f} Z{:f}".format(self._current_cs, self.mpos[0], self.mpos[1], self.mpos[2]))
        self.grbl.send_immediately("$#")

    def _variables_edited(self, row, col):
        d = self._var_table_to_dict()
        self.grbl.preprocessor.set_vars(d)

        
        

    ## UTILITY FUNCTIONS
    
    def _var_table_to_dict(self):
        row_count = self.tableWidget_variables.rowCount()
        vars = {}
        for row in range(0, row_count):
            cell_a = self.tableWidget_variables.item(row, 0)
            
            if cell_a == None:
                continue 
            
            key = cell_a.text().strip()
            key = key.replace("#", "")
            
            cell_b = self.tableWidget_variables.item(row, 1)
            if cell_b:
                val = cell_b.text().strip()
                if val == "":
                    val = None
            else:
                val = None
                
            vars[key] = val
            
        return vars
        
        
    
    def var_keys_into_var_table(self, keys):
        self.tableWidget_variables.clear()
        row = 0
        for key in sorted(keys):
            cell_a = QTableWidgetItem("#" + key)
            self.tableWidget_variables.setItem(row, 0, cell_a)
            row += 1
    
    
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
            self.grbl.gcode_parser_state_requested = True

    def set_cs(self, nr):
        """
        A convenience function update the UI for CS
        """
        self._current_cs = nr
        current_cs_text = self._cs_names[self._current_cs]
        self.label_current_cs.setText(current_cs_text)
        self.comboBox_coordinate_systems.setCurrentIndex(nr - 1)
        
        self.state_cs_dirty = True
        

    def bbox(self, move_z=False):
        was_incremental = self.checkBox_incremental.isChecked()
        was_buf = self.grbl.get_buffer()
        
        movements = gcodetools.bbox(was_buf, move_z)
        
        self.grbl.job_new()
        
        self.grbl.incremental_streaming = True
        self.checkBox_incremental.setChecked(True)
        
        self.grbl.stream(movements)
        
        #self.grbl.set_incremental_streaming(was_incremental)
        #self.checkBox_incremental.setChecked(was_incremental)
        
        #self.grbl.job_new()
        #self.grbl.write("\n".join(was_buf))
        
    def _render_logbuffer(self):
        self.label_loginput.setText("<br />".join(self.logbuffer))
        self.scrollArea_loginput.verticalScrollBar().setValue(self.scrollArea_loginput.verticalScrollBar().maximum())

    def _add_to_loginput(self, msg, color="black"):
        html = "<span style='color: {}'>{}</span>".format(color, msg)
        #print(html)
        self.logbuffer.append(html)
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