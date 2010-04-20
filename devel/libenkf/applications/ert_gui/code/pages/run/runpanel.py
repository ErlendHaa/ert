from PyQt4 import QtGui, QtCore
import ertwrapper

from widgets.helpedwidget import HelpedWidget, ContentModel
from widgets.util import resourceIcon, ListCheckPanel, ValidatedTimestepCombo, createSpace, getItemsFromList, frange
import threading
import time
import widgets
import math
from widgets.cogwheel import Cogwheel
from pages.run.simulationlist import SimulationList, SimulationItemDelegate, SimulationItem, Simulation
from pages.run.legend import Legend
from pages.run.jobsdialog import JobsDialog

class RunWidget(HelpedWidget):
    run_mode_type = {"ENKF_ASSIMILATION" : 1, "ENSEMBLE_EXPERIMENT" : 2, "ENSEMBLE_PREDICTION" : 3, "INIT_ONLY" : 4}
    state_enum = {"UNDEFINED" : 0, "SERIALIZED" : 1, "FORECAST" : 2, "ANALYZED" : 4, "BOTH" : 6}

    def __init__(self, parent=None):
        HelpedWidget.__init__(self, parent, widgetLabel="", helpLabel="widget_run")

        self.membersList = QtGui.QListWidget(self)
        self.membersList.setSelectionMode(QtGui.QAbstractItemView.MultiSelection)

        self.membersList.setViewMode(QtGui.QListView.IconMode)
        self.membersList.setMovement(QtGui.QListView.Static)
        self.membersList.setResizeMode(QtGui.QListView.Adjust)
        self.membersList.setGridSize(QtCore.QSize(32, 16))
        self.membersList.setSelectionRectVisible(False)

        memberLayout = QtGui.QFormLayout()
        memberLayout.setLabelAlignment(QtCore.Qt.AlignRight)

        self.runpathLabel = QtGui.QLabel("")
        font = self.runpathLabel.font()
        font.setWeight(QtGui.QFont.Bold)
        self.runpathLabel.setFont(font)

        memberLayout.addRow("Runpath:", self.runpathLabel)

        membersCheckPanel = ListCheckPanel(self.membersList)
        #membersCheckPanel.insertWidget(0, QtGui.QLabel("Members"))

        self.simulateFrom = ValidatedTimestepCombo(parent, fromLabel="Start", toLabel="End of history")
        self.simulateTo = ValidatedTimestepCombo(parent, fromLabel="End of history", toLabel="End of prediction")

        self.startState = QtGui.QComboBox(self)
        self.startState.setMaximumWidth(100)
        self.startState.setToolTip("Select state")
        self.startState.addItem("Analyzed")
        self.startState.addItem("Forecast")

        startLayout = QtGui.QHBoxLayout()
        startLayout.addWidget(self.simulateFrom)
        startLayout.addWidget(self.startState)

        memberLayout.addRow("Run simulation from: ", startLayout)
        memberLayout.addRow("Run simulation to: ", self.simulateTo)
        memberLayout.addRow("Mode: ", self.createRadioButtons())
        memberLayout.addRow(membersCheckPanel)
        memberLayout.addRow("Members:", self.membersList)

        self.actionButton = QtGui.QPushButton("Run simulation")

        self.connect(self.actionButton, QtCore.SIGNAL('clicked()'), self.run)

        actionLayout = QtGui.QHBoxLayout()
        actionLayout.addStretch(1)
        actionLayout.addWidget(self.actionButton)
        actionLayout.addStretch(1)

        memberLayout.addRow(createSpace(10))
        memberLayout.addRow(actionLayout)

        self.addLayout(memberLayout)


        self.setRunpath("...")

        self.modelConnect("ensembleResized()", self.fetchContent)
        self.modelConnect("runpathChanged()", self.fetchContent)

        self.rbAssimilation.toggle()


    def run(self):
        ert = self.getModel()
        selectedMembers = getItemsFromList(self.membersList)

        selectedMembers = [int(member) for member in selectedMembers]

        if len(selectedMembers) == 0:
            QtGui.QMessageBox.warning(self, "Missing data", "At least one member must be selected!")
            return

        simFrom = self.simulateFrom.getSelectedValue()
        simTo = self.simulateTo.getSelectedValue()

        if self.rbAssimilation.isChecked():
            mode = self.run_mode_type["ENKF_ASSIMILATION"]
        else:
            if simTo == -1: # -1 == End
                mode = self.run_mode_type["ENSEMBLE_PREDICTION"]
            else:
                mode = self.run_mode_type["ENSEMBLE_EXPERIMENT"]

        state = self.state_enum["ANALYZED"]
        if self.startState.currentText() == "Forecast" and not simFrom == 0:
            state = self.state_enum["FORECAST"]

        init_step_parameter = simFrom

        #if mode == run_mode_type["ENKF_ASSIMILATION"]:
        #    init_step_parameter = simFrom
        #elif mode == run_mode_type["ENSEMBLE_EXPERIMENT"]:
        #    init_step_parameter = 0
        #else:
        #    init_step_parameter = self.historyLength

        jobsdialog = JobsDialog(self)
        jobsdialog.start(ert = ert,
                         memberCount = self.membersList.count(),
                         selectedMembers = selectedMembers,
                         simFrom = simFrom,
                         simTo = simTo,
                         mode = mode,
                         state = state,
                         init_step_parameter = init_step_parameter)



    

        self.runthread.setDaemon(True)
        self.runthread.run = action                        

        self.pollthread = threading.Thread(name="polling_thread")
        def poll():
            while not ert.enkf.site_config_queue_is_running(ert.site_config):
                time.sleep(0.5)

            while(self.runthread.isAlive()):
                for member in selectedMembers:
                    state = ert.enkf.enkf_main_iget_state(ert.main, member)
                    status = ert.enkf.enkf_state_get_run_status(state)

                    if not status == Simulation.job_status_type_reverse["JOB_QUEUE_NOT_ACTIVE"]:
                        #start_time = ert.enkf.enkf_state_get_start_time(state)
                        #print time.ctime(start_time), start_time
                        pass

                    simulations[member].simulation.setStatus(status)
                    simulations[member].updateSimulation()

                totalCount = len(simulations.keys())
                succesCount = 0
                for key in simulations.keys():
                    if simulations[key].simulation.finishedSuccesfully():
                        succesCount+=1

                count = (100 * succesCount / totalCount)
                self.simulationProgress.emit(QtCore.SIGNAL("setValue(int)"), count)

                time.sleep(0.5)

        self.pollthread.setDaemon(True)
        self.pollthread.run = poll

        self.runthread.start()
        self.pollthread.start()


    def updateProgress(self, value):
        self.simulationProgress.setValue(value)

    def setRunpath(self, runpath):
        #self.runpathLabel.setText("Runpath: " + runpath)
        self.runpathLabel.setText(runpath)

    def fetchContent(self):
        data = self.getFromModel()

        self.historyLength = data["history_length"]

        self.membersList.clear()

        for member in data["members"]:
            self.membersList.addItem("%03d" % (member))
        #self.membersList.addItem(str(member))

        self.setRunpath(data["runpath"])

        self.simulateFrom.setHistoryLength(self.historyLength)
        self.simulateTo.setFromValue(self.historyLength)
        self.simulateTo.setToValue(-1)
        self.simulateTo.setMinTimeStep(0)
        self.simulateTo.setMaxTimeStep(self.historyLength)

        self.membersList.selectAll()


    def initialize(self, ert):
        ert.setTypes("enkf_main_get_ensemble_size", ertwrapper.c_int)
        ert.setTypes("enkf_main_get_history_length", ertwrapper.c_int)
        ert.setTypes("model_config_get_runpath_as_char", ertwrapper.c_char_p)        


    def getter(self, ert):
        members = ert.enkf.enkf_main_get_ensemble_size(ert.main)
        historyLength = ert.enkf.enkf_main_get_history_length(ert.main)
        runpath = ert.enkf.model_config_get_runpath_as_char(ert.model_config)

        return {"members" : range(members), "history_length" : historyLength, "runpath" : runpath}


    def rbToggle(self):
        if self.rbAssimilation.isChecked():
            self.membersList.setSelectionEnabled(False)
            self.membersList.selectAll()
        else:
            self.membersList.setSelectionEnabled(True)

    def createRadioButtons(self):
        radioLayout = QtGui.QVBoxLayout()
        radioLayout.setSpacing(2)
        self.rbAssimilation = QtGui.QRadioButton("EnKF assimilation")
        radioLayout.addWidget(self.rbAssimilation)
        self.rbExperiment = QtGui.QRadioButton("Ensemble experiment")
        radioLayout.addWidget(self.rbExperiment)

        self.connect(self.rbAssimilation, QtCore.SIGNAL('toggled(bool)'), lambda : self.rbToggle())
        self.connect(self.rbExperiment, QtCore.SIGNAL('toggled(bool)'), lambda : self.rbToggle())

        return radioLayout


class RunPanel(QtGui.QFrame):
    def __init__(self, parent):
        QtGui.QFrame.__init__(self, parent)
        self.setFrameShape(QtGui.QFrame.Panel)
        self.setFrameShadow(QtGui.QFrame.Raised)

        panelLayout = QtGui.QVBoxLayout()
        self.setLayout(panelLayout)

        #        button = QtGui.QPushButton("Refetch")
        #        self.connect(button, QtCore.SIGNAL('clicked()'), ContentModel.updateObservers)
        #        panelLayout.addWidget(button)

        panelLayout.addWidget(RunWidget())



        



