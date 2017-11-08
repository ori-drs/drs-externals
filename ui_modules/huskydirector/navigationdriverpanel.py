import PythonQt
from PythonQt import QtCore, QtGui, QtUiTools
from director import applogic as app
from director.utime import getUtime
from director import transformUtils
from director import lcmUtils
from director import objectmodel as om

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



class NavigationDriverPanel(object):

    def __init__(self, driver,viewcolors):

        self.driver = driver

        loader = QtUiTools.QUiLoader()
        uifile = QtCore.QFile(os.path.join(os.path.dirname(__file__), 'ui/ddNavigationDriverPanel.ui'))
        assert uifile.open(uifile.ReadOnly)

        self.widget = loader.load(uifile)
        self.widget.setWindowTitle('Navigation Panel')
        self.ui = WidgetDict(self.widget.children())

        # Main Panel
        self.ui.enableFollowerButton.connect('pressed()', self.enableFollowerButton)
        self.ui.disableFollowerButton.connect('pressed()', self.disableFollowerButton)

        # AprilTag Follower
        self.ui.enableAprilTagFollowerButton.connect('pressed()', self.enableAprilTagFollowerButton)
        self.ui.disableAprilTagFollowerButton.connect('pressed()', self.disableAprilTagFollowerButton)

        self.ui.configureHyQButton.connect('pressed()', self.configureHyQ)

        self.viewcolors = viewcolors
        #print viewcolors.viewBackgroundLightHandler

    def enableFollowerButton(self):
        msg = lcmbotcore.utime_t()
        msg.utime = getUtime()
        lcmUtils.publish('ENABLE_PATH_FOLLOWER', msg)

    def disableFollowerButton(self):
        msg = lcmbotcore.utime_t()
        msg.utime = getUtime()
        lcmUtils.publish('DISABLE_PATH_FOLLOWER', msg)

    def enableAprilTagFollowerButton(self):
        msg = lcmbotcore.utime_t()
        msg.utime = getUtime()
        lcmUtils.publish('ENABLE_TAG_FOLLOWER', msg)

    def disableAprilTagFollowerButton(self):
        msg = lcmbotcore.utime_t()
        msg.utime = getUtime()
        lcmUtils.publish('DISABLE_TAG_FOLLOWER', msg)

    def configureHyQ(self):
        vo = om.findObjectByName('view options')
        vo.setProperty('Gradient background',True)
        vo.setProperty('Background color',[0.0, 0.0, 0.0])
        vo.setProperty('Background color 2',[0.3, 0.3, 0.3])

        grid = om.findObjectByName('grid')
        grid.setProperty('Surface Mode','Wireframe')
        grid.setProperty('Alpha',0.05)
        grid.setProperty('Color',[1.0, 1.0, 1.0])
        grid.setProperty('Color By',0)

        ms = om.findObjectByName('Multisense')
        ms.setProperty('Min Range', 0.7)
        ms.setProperty('Max Range', 30.0)
        ms.setProperty('Max Height', 1.5)
        ms.setProperty('Edge Filter Angle', 0.0)
        ms.setProperty('Point Size', 2.0)
        ms.setProperty('Color By', 'Z Coordinate')
    




def _getAction():

    actionName = 'ActionNavigationDriverPanel'
    action = app.getToolBarActions().get(actionName)

    if action is None:

        icon = QtGui.QIcon(os.path.join(os.path.dirname(__file__), 'images/compass_icon.png'))
        assert os.path.isfile(os.path.join(os.path.dirname(__file__), 'images/compass_icon.png'))

        action = QtGui.QAction(icon, 'Navigation Panel', None)
        action.objectName = 'ActionNavigationDriverPanel'
        action.checkable = True

        mainWindow = app.getMainWindow()
        toolbar = mainWindow.panelToolBar()

        toolbar.insertAction(toolbar.actions()[0], action)

    return action


def init(driver, viewcolors):

    global panel
    global dock

    panel = NavigationDriverPanel(driver, viewcolors)
    dock = app.addWidgetToDock(panel.widget, action=_getAction())
    dock.hide()

    return panel
