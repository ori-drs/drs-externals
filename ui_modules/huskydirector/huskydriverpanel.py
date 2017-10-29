import PythonQt
from PythonQt import QtCore, QtGui, QtUiTools
from director import applogic as app
from director.utime import getUtime
from director import transformUtils
from director import lcmUtils
from director import pointpicker

import os
import bot_core as lcmbotcore
import drc as lcmdrc

def addWidgetsToDict(widgets, d):

    for widget in widgets:
        if widget.objectName:
            d[str(widget.objectName)] = widget
        addWidgetsToDict(widget.children(), d)


class WidgetDict(object):

    def __init__(self, widgets):
        addWidgetsToDict(widgets, self.__dict__)



class HuskyDriverPanel(object):

    def __init__(self, driver):

        self.driver = driver

        loader = QtUiTools.QUiLoader()
        uifile = QtCore.QFile(os.path.join(os.path.dirname(__file__), 'ui/ddHuskyDriverPanel.ui'))
        assert uifile.open(uifile.ReadOnly)

        self.widget = loader.load(uifile)
        self.widget.setWindowTitle('Husky Driver Panel')
        self.ui = WidgetDict(self.widget.children())

        # Main Panel
        #self.ui.linearVelocitySpinBox.connect('valueChanged(double)', self.onLinearVelocitySpinBox)
        #self.wholeBodyMode='Whole Body'

        # Control the Husky
        self.ui.forwardCommandButton.connect('pressed()', self.forwardCommandButton)
        self.ui.backwardCommandButton.connect('pressed()', self.backwardCommandButton)
        self.ui.leftTurnCommandButton.connect('pressed()', self.leftTurnCommandButton)
        self.ui.rightTurnCommandButton.connect('pressed()', self.rightTurnCommandButton)


        self.ui.resetLinearVelocityButton.connect('pressed()', self.resetLinearVelocityButton)
        self.ui.resetAngularVelocityButton.connect('pressed()', self.resetAngularVelocityButton)

        #self.widget.ledOnCheck.clicked.connect(self.ledOnCheckChange)

        # Control the PTU
        self.ui.neckUpCommandButton.connect('pressed()', self.neckUpCommandButton)
        self.ui.neckZeroCommandButton.connect('pressed()', self.neckZeroCommandButton)
        self.ui.neckLeftCommandButton.connect('pressed()', self.neckLeftCommandButton)
        self.ui.neckRightCommandButton.connect('pressed()', self.neckRightCommandButton)
        self.ui.neckDownCommandButton.connect('pressed()', self.neckDownCommandButton)


        self.ui.resetTiltPTUButton.connect('pressed()', self.resetTiltPTUButton)
        self.ui.resetPanPTUButton.connect('pressed()', self.resetPanPTUButton)

        # ptu state message
        self.lastPTUStateMessage = None
        self.ptuSub = lcmUtils.addSubscriber('PTU_STATE', lcmbotcore.joint_state_t, self.onPTUState)

        # Control the Point Picker
        self.pointPicker = None
        self.ui.startPointPicker.connect('pressed()', self.startPointPicker)
        self.ui.stopPointPicker.connect('pressed()', self.stopPointPicker)

        # Control the Point Picker
        self.ui.quadRotateAnticlockwiseButton.connect('pressed()', self.quadRotateAnticlockwiseButton)
        self.ui.quadRotateClockwiseButton.connect('pressed()', self.quadRotateClockwiseButton)
        self.ui.resetQuatRotateButton.connect('pressed()', self.resetQuatRotateButton)

    def onPTUState(self, message):
        self.lastPTUStateMessage = message

    def getComboText(self, combo):
        return str(combo.currentText)

    def onLinearVelocitySpinBox(self):
        print "onLinearVelocitySpinBox changed"
        print self.ui.linearVelocitySpinBox
        print self.ui.linearVelocitySpinBox.value
        #self.wholeBodyMode = self.getComboText(self.ui.modeBox)

    # Husky Control
    def forwardCommandButton(self):
        self.sendCommand( self.ui.linearVelocitySpinBox.value, 0)
    def backwardCommandButton(self):
        self.sendCommand(-self.ui.linearVelocitySpinBox.value, 0)
    def leftTurnCommandButton(self):
        self.sendCommand(0, self.ui.angularVelocitySpinBox.value)
    def rightTurnCommandButton(self):
        self.sendCommand(0, -self.ui.angularVelocitySpinBox.value)

    # These reset values are duplicated from the ui file
    def resetLinearVelocityButton(self):
        self.ui.linearVelocitySpinBox.value = 0.2
    def resetAngularVelocityButton(self):
        self.ui.angularVelocitySpinBox.value = 0.3

    def sendCommand(self, linearVelocity, angularVelocity):
        command = lcmbotcore.twist_t()
        # no utime timestamp - there should be!
        command.linear_velocity.x = linearVelocity
        command.linear_velocity.y = 0
        command.linear_velocity.z = 0
        command.angular_velocity.x = 0
        command.angular_velocity.y = 0
        command.angular_velocity.z = angularVelocity
        lcmUtils.publish('HUSKY_CMD', command)

    # Husky PTU Control
    def neckUpCommandButton(self):
        self.sendPTUCommand( self.ui.tiltPTUSpinBox.value, 0)
    def neckDownCommandButton(self):
        self.sendPTUCommand( -self.ui.tiltPTUSpinBox.value, 0)
    def neckRightCommandButton(self):
        self.sendPTUCommand(0, self.ui.panPTUSpinBox.value)
    def neckLeftCommandButton(self):
        self.sendPTUCommand(0, -self.ui.panPTUSpinBox.value)
    def neckZeroCommandButton(self):
        ptuCommand = lcmbotcore.joint_state_t()

        ptuCommand.num_joints = self.lastPTUStateMessage.num_joints
        ptuCommand.joint_name = self.lastPTUStateMessage.joint_name
        ptuCommand.joint_position = [0, 0]
        ptuCommand.joint_effort = [0, 0]
        ptuCommand.joint_velocity = [0.6, 0.6]

        lcmUtils.publish('FLIR_PTU_CMD', ptuCommand)


    # These reset values are duplicated from the ui file
    def resetTiltPTUButton(self):
        self.ui.tiltPTUSpinBox.value = 0.1
    def resetPanPTUButton(self):
        self.ui.panPTUSpinBox.value = 0.5


    def sendPTUCommand(self, tilt, pan):
        ptuCommand = lcmbotcore.joint_state_t()
        # no utime timestamp - there should be!
        ptuCommand.num_joints = self.lastPTUStateMessage.num_joints
        ptuCommand.joint_name = self.lastPTUStateMessage.joint_name
        ptuCommand.joint_position = [self.lastPTUStateMessage.joint_position[0] + pan, self.lastPTUStateMessage.joint_position[1] + tilt]
        ptuCommand.joint_effort = [0, 0]
        ptuCommand.joint_velocity = [0.6, 0.6]

        lcmUtils.publish('FLIR_PTU_CMD', ptuCommand)

    def pointPickerCallback(self, p):
        pointPickerMsg = lcmbotcore.double_array_t()

        pointPickerMsg.utime = getUtime()
        pointPickerMsg.num_values = len(p)
        pointPickerMsg.values = p
        
        lcmUtils.publish('PP_POINT', pointPickerMsg)

    def startPointPicker(self):
        self.pointPicker = pointpicker.PointPicker(view=app.getCurrentRenderView(), numberOfPoints=1, callback=self.pointPickerCallback)
        self.pointPicker.start()

    def stopPointPicker(self):
        self.pointPicker.stop()




    # Husky PTU Control
    def quadRotateAnticlockwiseButton(self):
        self.sendCommandQuadRotate( 0, -self.ui.quadRotateSpinBox.value)
    def quadRotateClockwiseButton(self):
        self.sendCommandQuadRotate( 0, self.ui.quadRotateSpinBox.value)

    def sendCommandQuadRotate(self, linearVelocity, angularVelocity):
        command = lcmbotcore.twist_t()
        # no utime timestamp - there should be!
        command.linear_velocity.x = 0#linearVelocity
        command.linear_velocity.y = 0
        command.linear_velocity.z = 0
        command.angular_velocity.x = 0
        command.angular_velocity.y = 0
        command.angular_velocity.z = angularVelocity
        lcmUtils.publish('QUAD_ROTATE_CMD', command)

    def resetQuatRotateButton(self):
        self.ui.quadRotateSpinBox.value = 0.5



def _getAction():

    actionName = 'ActionHuskyDriverPanel'
    action = app.getToolBarActions().get(actionName)

    if action is None:

        icon = QtGui.QIcon(os.path.join(os.path.dirname(__file__), 'images/husky.png'))
        assert os.path.isfile(os.path.join(os.path.dirname(__file__), 'images/husky.png'))

        action = QtGui.QAction(icon, 'Husky Driver Panel', None)
        action.objectName = 'ActionHuskyDriverPanel'
        action.checkable = True

        mainWindow = app.getMainWindow()
        toolbar = mainWindow.panelToolBar()

        toolbar.insertAction(toolbar.actions()[0], action)

    return action


def init(driver):

    global panel
    global dock

    panel = HuskyDriverPanel(driver)
    dock = app.addWidgetToDock(panel.widget, action=_getAction())
    dock.hide()

    return panel
