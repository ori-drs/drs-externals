import huskydriver
import huskydriverpanel

import navigationdriver
import navigationdriverpanel

import diftdriver
import diftdriverpanel

from director import tasklaunchpanel
from director import applogic
from director import teleoppanel
import director.objectmodel as om

from director import viewcolors
from director import cameraview
from director import pointcloudlcm


def startup(robotSystem, globalsDict=None):
    rs = robotSystem

    viewBackgroundLightHandler = globalsDict['viewBackgroundLightHandler']

    huskyDriver = huskydriver.HuskyDriver()
    huskyDriverPanel = huskydriverpanel.init(huskyDriver)

    #atlasPanelAction = applogic.getToolBarActions()['ActionAtlasDriverPanel']
    #applogic.getMainWindow().panelToolBar().removeAction(atlasPanelAction)

    navigationDriver = navigationdriver.NavigationDriver()
    navigationDriverPanel = navigationdriverpanel.init(navigationDriver, viewcolors)

    diftDriver = diftdriver.DiftDriver()
    diftDriverPanel = diftdriverpanel.init(diftDriver, viewcolors, applogic.getDRCView(), viewBackgroundLightHandler)


    def doHuskySpecificModifications():
        ms = om.findObjectByName('Multisense')
        if ms is not None:
            ms.setProperty('Max Range', 29)
            ms.setProperty('Edge Filter Angle', 0)
            ms.setProperty('Color By', 2) # Z-height

        ss = om.findObjectByName('SICK_SCAN')
        if ss is not None:
            ss.setProperty('Max Range', 78)
            ss.setProperty('Edge Filter Angle', 0)
            ss.setProperty('Color By', 1) # Intensities
            ss.setProperty('Number of Scan Lines', 2000)

        hs = om.findObjectByName('HORIZONTAL_SCAN')
        if hs is not None:
            hs.setProperty('Max Range', 78)
            hs.setProperty('Color By', 2) # Z-height

        # TODO: revert the z change in startup.py
        #gridUpdater.setZOffset(0.13)


    # Export variables to globals so that they can be accessed from the console
    if globalsDict is not None:
        globalsDict['huskyDriver'] = huskyDriver
        globalsDict['huskyDriverPanel'] = huskyDriverPanel

        globalsDict['navigationDriver'] = navigationDriver
        globalsDict['navigationDriverPanel'] = navigationDriverPanel

        globalsDict['doHuskySpecificModifications'] = doHuskySpecificModifications

        globalsDict['dift'] = diftDriver
        globalsDict['diftDriverPanel'] = diftDriverPanel


