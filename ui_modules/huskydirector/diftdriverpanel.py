import PythonQt
from PythonQt import QtCore, QtGui, QtUiTools
from director import applogic as app
from director.utime import getUtime
from director import transformUtils
from director import lcmUtils
from director import objectmodel as om
from director import visualization as vis
from director import pointpicker
from director import cameracontrol
from director.tasks.robottasks import UserPromptTask

import numpy as np
import json
import os
import vtk
import glob
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

class PolyDataFrameConverter(cameracontrol.TargetFrameConverter):

    def __init__(self, obj):
        if obj is not None:
            vis.addChildFrame(obj)
            self.targetFrame = obj.getChildFrame()
        else:
            self.targetFrame = None

    @classmethod
    def canConvert(cls, obj):
        return hasattr(obj, 'getChildFrame')


class DiftDriverPanel(object):

    def __init__(self, driver,viewcolors, view, viewBackgroundLightHandler):
        self.driver = driver
        self.view = view


        loader = QtUiTools.QUiLoader()
        uifile = QtCore.QFile(os.path.join(os.path.dirname(__file__), 'ui/ddDiftDriverPanel.ui'))
        assert uifile.open(uifile.ReadOnly)

        self.widget = loader.load(uifile)
        self.widget.setWindowTitle('Dift Panel')
        self.ui = WidgetDict(self.widget.children())

        self.ui.overheadButton.connect('pressed()', self.overheadButton)
        self.ui.drawSegmentsButton.connect('pressed()', self.drawSegments)

        self.ui.targetColorCheckBox.clicked.connect(self.targetColorCheckBox)
        self.ui.transformedTargetColorCheckBox.clicked.connect(self.transformedTargetColorCheckBox)
        self.ui.sourceColorCheckBox.clicked.connect(self.sourceColorCheckBox)
        self.ui.centroidsCheckBox.clicked.connect(self.toggleCentroidMode)

        self.ui.gridSizeSpinBox.connect('valueChanged(double)', self.gridSizeSpinBox)
        self.ui.mapXOffsetSpinBox.connect('valueChanged(double)', self.mapXOffsetSpinBox)
        self.ui.mapYOffsetSpinBox.connect('valueChanged(double)', self.mapYOffsetSpinBox)
        self.ui.mapZOffsetSpinBox.connect('valueChanged(double)', self.mapZOffsetSpinBox)
        self.ui.sourceOffsetSpinBox.connect('valueChanged(double)', self.sourceOffsetSpinBox)

        self.ui.visualizeProposalsButton.setEnabled(False)
        self.ui.resetVisualizationButton.setEnabled(False)
        self.ui.visualizeFeatureSpaceButton.setEnabled(False)

        self.ui.setTargetButton.connect('clicked()', self.onSetTarget)
        self.ui.setSourceCloud.connect('clicked()', self.labelOnSetSource)
        self.ui.setTargetCloud.connect('clicked()', self.labelOnSetTarget)
        self.ui.setSourceCloud.setShortcut(QtGui.QKeySequence('Shift+S'))
        self.ui.setTargetCloud.setShortcut(QtGui.QKeySequence('Shift+T'))
        self.ui.previewLabelButton.connect('clicked()', self.previewLabel)
        self.ui.previewLabelButton.setShortcut(QtGui.QKeySequence('Shift+W'))
        self.ui.confirmLabelButton.connect('clicked()', self.confirmLabel)
        self.ui.confirmLabelButton.setShortcut(QtGui.QKeySequence('Shift+C'))
        self.ui.cancelLabelButton.connect('clicked()', self.cancelLabel)
        self.ui.cancelLabelButton.setShortcut(QtGui.QKeySequence('Shift+E'))
        self.ui.saveLabelButton.connect('clicked()', self.saveLabelsPermanentOverwrite)
        self.ui.previewLabelledDataButton.connect('clicked()', self.previewLabelledData)
        self.ui.exitPreviewLabelledDataButton.connect('clicked()', self.exitPreviewLabelledData)
        self.ui.deleteMatchButton.setShortcut(QtGui.QKeySequence('Shift+D'))
        self.ui.deleteMatchButton.connect('clicked()', self.deletePreviewedLabel)
        self.ui.undoDeleteMatchButton.setShortcut(QtGui.QKeySequence('Shift+U'))
        self.ui.undoDeleteMatchButton.connect('clicked()', self.undoDeleteMatch)
        self.ui.nextMatchButton.connect('clicked()', self.previewNextMatch)
        self.ui.nextMatchButton.setShortcut(QtGui.QKeySequence('Shift+X'))
        self.ui.previousMatchButton.connect('clicked()', self.previewPreviousMatch)
        self.ui.previousMatchButton.setShortcut(QtGui.QKeySequence('Shift+V'))
        self.ui.saveLabelledMatchesButton.connect('clicked()', self.saveLabelledMatches)

        self.ui.viewTableStatsButton.connect('clicked()', self.driver.viewStats)

        self.ui.previewLabelButton.setEnabled(False)
        self.ui.confirmLabelButton.setEnabled(False)
        self.ui.cancelLabelButton.setEnabled(False)
        self.ui.nextMatchButton.setEnabled(False)
        self.ui.previousMatchButton.setEnabled(False)
        self.ui.exitPreviewLabelledDataButton.setEnabled(False)
        self.ui.deleteMatchButton.setEnabled(False)
        self.ui.undoDeleteMatchButton.setEnabled(False)
        self.ui.saveLabelledMatchesButton.setEnabled(False)

        # style the delete button
        self.ui.deleteMatchButton.setStyleSheet('background-color: rgb(255,0,0);color: #FFF')

        self.objectPicker = pointpicker.ObjectPicker(self.view)
        self.objectPicker.callbackFunc = self.onPickObject
        self.objectPicker.abortFunc = self.onAbortPick

        self.labelSourcePicker = pointpicker.ObjectPicker(self.view)
        self.labelSourcePicker.callbackFunc = self.labelOnPickSourceCloud
        self.labelSourcePicker.abortFunc = self.labelOnAbortPickSource

        self.labelTargetPicker = pointpicker.ObjectPicker(self.view)
        self.labelTargetPicker.callbackFunc = self.labelOnPickTargetCloud
        self.labelTargetPicker.abortFunc = self.labelOnAbortPickTarget

        self.ui.visualizeProposalsButton.connect('clicked()', self.visualizeProposals)
        self.ui.resetVisualizationButton.connect('clicked()', self.resetProposals)
        self.ui.visualizeFeatureSpaceButton.connect('clicked()', self.driver.visualizeFeatureSpace)

        self.ui.loadSegmentsLocationButton.connect('clicked()', self.onChooseRunInputDir)

        self.ui.saveConfig.connect('clicked()', self.saveCfg)



        self.viewcolors = viewcolors
        self.viewBackgroundLightHandler = viewBackgroundLightHandler

        self.cameraPos = ([2.8875499656443444, 0.0, 0.43048973013823366])
        self.cameraFocalPoint = ([-3.5406048731756457e-07, 0.0, 0.43048973013823366])
        self.cameraViewUp = ([0.0, 0.0, 1.0])

        self.tempFocalPoint = self.cameraFocalPoint
        self.tempViewUp = self.cameraViewUp
        self.tempPos = self.cameraPos
        #print viewcolors.viewBackgroundLightHandler

        # initially the robot state is visible
        self.rs_visible = True

        self.prevBg = 1 # light initially

        self.parseConfig()

    def parseConfig(self):
        if os.path.isfile(os.path.join(self.driver.getDiftLoc(),'.director_config.json')):
            with open(os.path.join(self.driver.getDiftLoc(),'.director_config.json')) as fd:
                cfg = json.load(fd)
                # visually set the values in the interface
                self.ui.gridSizeSpinBox.setValue(cfg["grid_size"])
                self.ui.mapXOffsetSpinBox.setValue(cfg["map_offset"][0])
                self.ui.mapYOffsetSpinBox.setValue(cfg["map_offset"][1])
                self.ui.mapZOffsetSpinBox.setValue(cfg["map_offset"][2])
                self.ui.sourceOffsetSpinBox.setValue(cfg["map_rotation"][2])
                self.ui.targetColorCheckBox.setChecked(cfg["colours"][0])
                self.ui.transformedTargetColorCheckBox.setChecked(cfg["colours"][1])
                self.ui.sourceColorCheckBox.setChecked(cfg["colours"][2])
                if cfg["light"]:
                    self.setLightBg()
                else:
                    self.setDarkBg()

                self.cameraPos = cfg['camera_position']
                self.cameraFocalPoint = cfg['camera_focal_point']
                self.cameraViewUp = cfg['camera_view_up']


                self.driver.targetOffset = cfg["map_offset"]
                self.driver.sourceYawOffset = cfg["map_rotation"][2]

    def previewLabelledData(self):
        # if labelled data doesn't exist - display a message and do nothing
        labelsPath = self.driver.getDiftLoc() + 'labelled_matches.csv'
        if not os.path.isfile(labelsPath):
            print "No labelled data detected. Please make sure you saved the labels before trying to preview them."
        else:
            # check if the user wants to continue, as this would wipe all their current manually added matches
            self.checkPreviewLabels()

    def checkPreviewLabels(self):
        labelsPath = self.driver.getDiftLoc() + '.labelled_matches.csv'
        if os.path.isfile(labelsPath):
            task = UserPromptTask(message='File ' + labelsPath + ' exists. All your current changes will be lost. Do you want to continue?')
            task.showDialog()
            task.d.connect('accepted()', self.previewLabelledDataYes)
        else:
            self.previewLabelledDataYes()

    def previewLabelledDataYes(self):
        labelsPath = self.driver.getDiftLoc() + 'labelled_matches.csv'
        if os.path.isfile(labelsPath):
            # hide all clusters initially
            self.driver.hideAllSegments()
            self.driver.parseSavedLabels()

            # save the current camera params
            c = self.view.camera()
            self.tempFocalPoint = c.GetFocalPoint()
            self.tempViewUp = c.GetViewUp()
            self.tempPos = c.GetPosition()

            # save the current background type (light or dark)
            vo = om.getOrCreateContainer('view options')
            if vo.getProperty('Background color') == [0.0, 0.0, 0.0]:
                self.prevBg = 0 # dark
            elif vo.getProperty('Background color') == (0.3, 0.3, 0.35):
                self.prevBg = 1 # light

            self.setDarkBg()

            # load the current matching segments
            self.previewNextMatch()

            # hide the robot state model
            rs = om.findObjectByName('robot state model')
            if rs.getProperty('Visible'):
                rs.setProperty('Visible', False)
            else:
                self.rs_visible = False

            self.cameraPos = ([28.674186992478145, -15.80024316444052, 13.431677110958429])
            self.cameraFocalPoint = ([-3.5406048731756457e-07, 0.0, 0.43048973013823366])
            self.cameraViewUp = ([0.0, 0.0, 1.0])

            self.setCameraParams()

            # disable everthing else and enable only functions that matter
            self.ui.loadSegmentsLocationButton.setEnabled(False)
            self.ui.overheadButton.setEnabled(False)
            self.ui.drawSegmentsButton.setEnabled(False)
            self.ui.targetColorCheckBox.setEnabled(False)
            self.ui.transformedTargetColorCheckBox.setEnabled(False)
            self.ui.sourceColorCheckBox.setEnabled(False)
            self.ui.centroidsCheckBox.setEnabled(False)
            self.ui.setTargetButton.setEnabled(False)
            self.ui.setSourceCloud.setEnabled(False)
            self.ui.setTargetCloud.setEnabled(False)
            self.ui.hideSourceLabelCheckBox.setEnabled(False)
            self.ui.saveLabelButton.setEnabled(False)
            self.ui.gridSizeSpinBox.setEnabled(False)
            self.ui.mapXOffsetSpinBox.setEnabled(False)
            self.ui.mapYOffsetSpinBox.setEnabled(False)
            self.ui.mapZOffsetSpinBox.setEnabled(False)
            self.ui.sourceOffsetSpinBox.setEnabled(False)
            self.ui.saveConfig.setEnabled(False)
            self.ui.viewTableStatsButton.setEnabled(False)

            self.ui.previewLabelledDataButton.setEnabled(False)
            self.ui.exitPreviewLabelledDataButton.setEnabled(True)
            self.ui.nextMatchButton.setEnabled(True)
            self.ui.previousMatchButton.setEnabled(False)
            self.ui.deleteMatchButton.setEnabled(True)
            self.ui.saveLabelledMatchesButton.setEnabled(True)

    def exitPreviewLabelledData(self):
        # remove everything before now
        labelled = om.getOrCreateContainer('Labelled matches')
        om.removeFromObjectModel(labelled)

        self.ui.loadSegmentsLocationButton.setEnabled(True)
        self.ui.overheadButton.setEnabled(True)
        self.ui.drawSegmentsButton.setEnabled(True)
        self.ui.targetColorCheckBox.setEnabled(True)
        self.ui.transformedTargetColorCheckBox.setEnabled(True)
        self.ui.sourceColorCheckBox.setEnabled(True)
        self.ui.centroidsCheckBox.setEnabled(True)
        self.ui.setTargetButton.setEnabled(True)
        self.ui.setSourceCloud.setEnabled(True)
        self.ui.setTargetCloud.setEnabled(True)
        self.ui.hideSourceLabelCheckBox.setEnabled(True)
        self.ui.saveLabelButton.setEnabled(True)
        self.ui.gridSizeSpinBox.setEnabled(True)
        self.ui.mapXOffsetSpinBox.setEnabled(True)
        self.ui.mapYOffsetSpinBox.setEnabled(True)
        self.ui.mapZOffsetSpinBox.setEnabled(True)
        self.ui.sourceOffsetSpinBox.setEnabled(True)
        self.ui.saveConfig.setEnabled(True)
        self.ui.viewTableStatsButton.setEnabled(True)

        self.ui.previewLabelledDataButton.setEnabled(True)
        self.ui.exitPreviewLabelledDataButton.setEnabled(False)
        self.ui.nextMatchButton.setEnabled(False)
        self.ui.previousMatchButton.setEnabled(False)
        self.ui.deleteMatchButton.setEnabled(False)
        self.ui.undoDeleteMatchButton.setEnabled(False)
        self.ui.saveLabelledMatchesButton.setEnabled(False)
        self.ui.labelledDataSwatheIdLabel.setText('None')
        self.ui.labelledDataShownSegments.setText('None')

        # restore the robot state model
        if self.rs_visible:
            rs = om.findObjectByName('robot state model')
            rs.setProperty('Visible', True)

        # restore BG
        self.setLightBg() if self.prevBg else self.setDarkBg()

        # show all the segments
        self.driver.showAllSegments()

        # restore the camera params
        self.cameraFocalPoint = self.tempFocalPoint
        self.cameraViewUp = self.tempViewUp
        self.cameraPos = self.tempPos
        self.setCameraParams()

    def previewNextMatch(self):
        if not self.driver.loadNextMatch():
            self.ui.nextMatchButton.setEnabled(False)
        else:
            self.ui.previousMatchButton.setEnabled(True)
        self.ui.labelledDataSwatheIdLabel.setText(self.driver.loadedLabels[len(self.driver.loadedLabels)-1][2])
        self.ui.labelledDataShownSegments.setText(str(len(self.driver.loadedLabels))+'/'+str(len(self.driver.labels)))

    def previewPreviousMatch(self):
        if not self.driver.loadPrevMatch():
            self.ui.previousMatchButton.setEnabled(False)
        else:
            self.ui.nextMatchButton.setEnabled(True)
        self.ui.labelledDataSwatheIdLabel.setText(self.driver.loadedLabels[len(self.driver.loadedLabels)-1][2])
        self.ui.labelledDataShownSegments.setText(str(len(self.driver.loadedLabels))+'/'+str(len(self.driver.labels)))

    def deletePreviewedLabel(self):
        # enable undo functionality
        self.ui.undoDeleteMatchButton.setEnabled(True)
        self.driver.deleteCurrentMatch()
        self.previewNextMatch()

    def undoDeleteMatch(self):
        self.driver.undoDeleteMatch()
        if len(self.driver.tempLabelledData) == 0:
            self.ui.undoDeleteMatchButton.setEnabled(False)

        self.ui.labelledDataSwatheIdLabel.setText(self.driver.loadedLabels[len(self.driver.loadedLabels)-1][2])
        self.ui.labelledDataShownSegments.setText(str(len(self.driver.loadedLabels))+'/'+str(len(self.driver.labels)))

    def setLightBg(self):
        vo = om.getOrCreateContainer('view options')
        if vo.getProperty('Background color') == [0.0, 0.0, 0.0]:
            self.triggerBackgroundLight()

    def setDarkBg(self):
        vo = om.getOrCreateContainer('view options')
        if vo.getProperty('Background color') == (0.3, 0.3, 0.35):
            self.triggerBackgroundLight()

    def triggerBackgroundLight(self):
        self.viewBackgroundLightHandler.action.trigger()

    def saveCfg(self):
        if self.driver.getDiftLoc():
            cfg = {}
            cfg['grid_size'] = self.ui.gridSizeSpinBox.value
            cfg['map_offset'] = [self.ui.mapXOffsetSpinBox.value,self.ui.mapYOffsetSpinBox.value,self.ui.mapZOffsetSpinBox.value]
            cfg['map_rotation'] = [0,0,self.ui.sourceOffsetSpinBox.value]
            cfg['colours'] = [self.ui.targetColorCheckBox.checked, self.ui.transformedTargetColorCheckBox.checked, self.ui.sourceColorCheckBox.checked]
            vo = om.getOrCreateContainer('view options')
            cfg['light'] = vo.getProperty('Background color') != [0.0, 0.0, 0.0]
            c = self.view.camera()
            cfg['camera_focal_point'] = c.GetFocalPoint()
            cfg['camera_view_up'] = c.GetViewUp()
            cfg['camera_position'] = c.GetPosition()
            with open(self.driver.getDiftLoc()+'.director_config.json', 'w') as outfile:
                json.dump(cfg, outfile)

    def runInputDirectory(self):
        return os.path.expanduser(self.ui.loadSegmentsLocationText.text)

    def chooseDirectory(self):
        return QtGui.QFileDialog.getExistingDirectory(app.getMainWindow(), "Choose directory...", self.runInputDirectory())

    def onChooseRunInputDir(self):
        newDir = self.chooseDirectory()
        if newDir:
            # check if there's a director config and load the values, if so
            self.ui.loadSegmentsLocationText.text = self.getShorterNameLast(newDir)
            self.driver.setDiftLoc(newDir+'/')
            self.parseConfig()

    def drawSegments(self):
        # if we do not have a cfg file
        if not os.path.isfile(os.path.join(self.driver.getDiftLoc(),'.director_config.json')):
            self.ui.targetColorCheckBox.setChecked(False)
            self.ui.transformedTargetColorCheckBox.setChecked(False)
            self.ui.sourceColorCheckBox.setChecked(False)

        self.ui.centroidsCheckBox.setChecked(False)

        # apply the driver changes
        self.driver.drawSegments()
        self.driver.changeYawOffset()
        self.driver.changeTargetOffset()
        self.view.render()

        # color the segments (if needed)
        self.targetColorCheckBox()
        self.transformedTargetColorCheckBox()
        self.sourceColorCheckBox()

        # set some default camera params
        self.setCameraParams()

    def onPickObject(self, objs):
        if objs:
            self.setTarget(objs[0])
        else:
            self.onAbortPick()

    def onAbortPick(self):
        self.ui.selectedObjectNameLabel.setText('')
        self.ui.setTargetButton.setVisible(True)
        self.objectPicker.stop()

    def onSetTarget(self):
        self.ui.setTargetButton.setVisible(False)
        self.ui.selectedObjectNameLabel.setText('Click an object in the view...')
        self.objectPicker.start()

    def labelOnPickSourceCloud(self, objs):
        if objs:
            self.labelSetSource(objs[0])
        else:
            self.labelOnAbortPickSource()

    def labelOnAbortPickSource(self):
        self.ui.setSourceCloud.setEnabled(True)
        self.ui.selectedSourceSegmentLabel.setText('None')
        self.ui.selectedSourceSegmentSwatheLabel.setText('None')
        self.labelSourcePicker.stop()

    def labelOnSetSource(self):
        self.ui.setSourceCloud.setEnabled(False)
        self.ui.selectedSourceSegmentLabel.setText('Click a source cloud in the view...')
        self.labelSourcePicker.start()

    def labelOnPickTargetCloud(self, objs):
        if objs:
            self.labelSetTarget(objs[0])
        else:
            self.labelOnAbortPickTarget()

    def labelOnAbortPickTarget(self):
        self.ui.setTargetCloud.setEnabled(True)
        self.ui.selectedTargetSegmentLabel.setText('None')
        self.labelTargetPicker.stop()

    def labelOnSetTarget(self):
        self.ui.setTargetCloud.setEnabled(False)
        self.ui.selectedTargetSegmentLabel.setText('Click a target cloud in the view...')
        self.labelTargetPicker.start()

    def previewLabel(self):
        self.ui.previewLabelButton.setEnabled(False)
        # remove everything before now
        labelling = om.getOrCreateContainer('Labelling matches')
        om.removeFromObjectModel(labelling)
        labelling = om.getOrCreateContainer('Labelling matches')

        # get the two objects and zero-center them
        target_obj = om.findObjectByName('cloud_cluster_'+str(self.driver.getLabelTarget()))
        source_obj = om.findObjectByName('cloud_cluster_'+str(self.driver.getLabelSource()))
        target_centroid_obj = om.findObjectByName('cloud_cluster_centroid_'+str(self.driver.getLabelTarget()))
        source_centroid_obj = om.findObjectByName('cloud_cluster_centroid_'+str(self.driver.getLabelSource()))


        source_pts = vtk.vtkPoints()
        source_verts = vtk.vtkCellArray()

        target_pts = vtk.vtkPoints()
        target_verts = vtk.vtkCellArray()

        offset_point =[-200, 0, 0]

        for i in range(source_obj.polyData.GetNumberOfPoints()):
            id = source_pts.InsertNextPoint(tuple(np.sum([np.subtract(source_obj.polyData.GetPoint(i), source_centroid_obj.polyData.GetPoint(0)), offset_point], axis=0)))
            source_verts.InsertNextCell(1)
            source_verts.InsertCellPoint(id)

        for i in range(target_obj.polyData.GetNumberOfPoints()):
            id = target_pts.InsertNextPoint(tuple(np.sum([np.subtract(target_obj.polyData.GetPoint(i), target_centroid_obj.polyData.GetPoint(0)), offset_point], axis=0)))
            target_verts.InsertNextCell(1)
            target_verts.InsertCellPoint(id)

        centered_source_pd = vtk.vtkPolyData()
        centered_source_pd.SetPoints(source_pts)
        centered_source_pd.SetVerts(source_verts)

        centered_target_pd = vtk.vtkPolyData()
        centered_target_pd.SetPoints(target_pts)
        centered_target_pd.SetVerts(target_verts)

        vis.showPolyData(centered_source_pd, 'cloud_cluster_centered_'+str(self.driver.getLabelSource()), parent=labelling, color=[0.2,0.9,0.2])
        vis.showPolyData(centered_target_pd, 'cloud_cluster_centered_'+str(self.driver.getLabelTarget()), parent=labelling, color=[0.9,0.2,0.2])

        # save the current camera params
        c = self.view.camera()
        self.tempFocalPoint = c.GetFocalPoint()
        self.tempViewUp = c.GetViewUp()
        self.tempPos = c.GetPosition()

        # hide the robot state model
        rs = om.findObjectByName('robot state model')
        if rs.getProperty('Visible'):
            rs.setProperty('Visible', False)
        else:
            self.rs_visible = False

        self.cameraPos = ([-158.02316176213432, -41.36537729751036, 49.99001550909116])
        self.cameraFocalPoint = ([-201.51273924432255, -1.4152897943406941, 5.366002953779059])
        self.cameraViewUp = ([0.0, 0.0, 1.0])

        self.setCameraParams()

        # show pop up
        self.ui.confirmLabelButton.setEnabled(True)
        self.ui.cancelLabelButton.setEnabled(True)

    def confirmLabel(self):
        self.ui.previewLabelButton.setEnabled(False)
        self.ui.confirmLabelButton.setEnabled(False)
        self.ui.cancelLabelButton.setEnabled(False)
        self.ui.selectedSourceSegmentLabel.setText('None')
        self.ui.selectedSourceSegmentSwatheLabel.setText('None')
        self.ui.selectedTargetSegmentLabel.setText('None')

        # remove the centered point clouds
        om.findObjectByName('cloud_cluster_centered_'+str(self.driver.getLabelSource())).removeFromAllViews()
        om.findObjectByName('cloud_cluster_centered_'+str(self.driver.getLabelTarget())).removeFromAllViews()

        # restore the robot state model
        if self.rs_visible:
            rs = om.findObjectByName('robot state model')
            rs.setProperty('Visible', True)

        # restore the view point
        self.cameraFocalPoint = self.tempFocalPoint
        self.cameraViewUp = self.tempViewUp
        self.cameraPos = self.tempPos
        self.setCameraParams()

        # hide the original source segment, meaning it's labelled
        # with the case of the velodyne, we can have multiple source segments matching 1 target segment, thus, the target must stay visible
        om.findObjectByName('cloud_cluster_'+str(self.driver.getLabelSource())).setProperty('Visible', False)
        om.findObjectByName('cloud_cluster_centroid_'+str(self.driver.getLabelSource())).setProperty('Visible', False)
        # om.findObjectByName('cloud_cluster_'+str(self.driver.getLabelTarget())).setProperty('Visible', False)
        # om.findObjectByName('cloud_cluster_centroid_'+str(self.driver.getLabelTarget())).setProperty('Visible', False)
        self.driver.addLabelledMatch()


    def cancelLabel(self):
        # remove everything before now
        labelling = om.getOrCreateContainer('Labelling matches')
        om.removeFromObjectModel(labelling)

        self.ui.previewLabelButton.setEnabled(True)
        self.ui.confirmLabelButton.setEnabled(False)
        self.ui.cancelLabelButton.setEnabled(False)

        # restore the robot state model
        if self.rs_visible:
            rs = om.findObjectByName('robot state model')
            rs.setProperty('Visible', True)

        # hide the source label if desired
        if self.ui.hideSourceLabelCheckBox.checked:
            om.findObjectByName('cloud_cluster_'+str(self.driver.getLabelSource())).setProperty('Visible', False)
            om.findObjectByName('cloud_cluster_centroid_'+str(self.driver.getLabelSource())).setProperty('Visible', False)

            # remove the match from the drive
            if not self.driver.labelSetSource('None'):
                self.ui.selectedSourceSegmentLabel.setText('None')
                self.ui.selectedSourceSegmentSwatheLabel.setText('None')


        # restore the camera params
        self.cameraFocalPoint = self.tempFocalPoint
        self.cameraViewUp = self.tempViewUp
        self.cameraPos = self.tempPos
        self.setCameraParams()

    def saveLabelsPermanentOverwrite(self):
        labelsPath = self.driver.getDiftLoc() + 'labelled_matches.csv'
        if os.path.isfile(labelsPath):
            self.saveLabelsPermanent('File ' + labelsPath + ' exists. Do you want me to overwrite the file?')

    def saveLabelledMatches(self):
        msg = "This behaviour will overwrite the current changes. You have currently deleted "+str(len(self.driver.tempLabelledData))+ " matches. Are you sure you want write this to disk?"
        self.saveLabelsPermanent(msg)

    def saveLabelsPermanent(self, message):
        task = UserPromptTask(message=message)
        task.showDialog()
        task.d.connect('accepted()', self.driver.saveLabelsPermanentYes)

    def getShorterName(self, name):
        if len(name) > 30:
            name=name[:15] + '...'

        return name

    def getShorterNameLast(self, name):
        if len(name) > 30:
            name='...'+name[len(name)-20:]

        return name

    def setTarget(self, obj):

        self.onAbortPick()

        converters = [PolyDataFrameConverter]

        for converter in converters:
            if converter.canConvert(obj):
                converter = converter(obj)
                break
        else:
            obj = None
            converter = None


        name = obj.getProperty('Name') if obj else 'None'
        self.driver.setTarget(name)
        self.ui.selectedProposalSourceCloudText.setText(self.getShorterName(name))
        self.ui.selectedProposalSwatheText.setText(self.driver.getTargetSwathe())
        self.ui.visualizeProposalsButton.setEnabled(obj is not None)
        self.ui.resetVisualizationButton.setEnabled(obj is not None)
        self.ui.visualizeFeatureSpaceButton.setEnabled(obj is not None)

    def labelSetSource(self, obj):

        self.labelOnAbortPickSource()

        converters = [PolyDataFrameConverter]

        for converter in converters:
            if converter.canConvert(obj):
                converter = converter(obj)
                break
        else:
            obj = None
            converter = None


        name = obj.getProperty('Name') if obj else 'None'
        parent_name = obj.parent().getProperty('Name') if obj and obj.parent() else 'None'
        if self.driver.labelSetSource(name):
            self.ui.selectedSourceSegmentLabel.setText(self.getShorterName(name))
            self.ui.selectedSourceSegmentSwatheLabel.setText('Swathe '+self.driver.getLabelSourceSwathe())
        if self.driver.getLabelSource() and self.driver.getLabelTarget():
            self.ui.previewLabelButton.setEnabled(obj is not None)

    def labelSetTarget(self, obj):

        self.labelOnAbortPickTarget()

        converters = [PolyDataFrameConverter]

        for converter in converters:
            if converter.canConvert(obj):
                converter = converter(obj)
                break
        else:
            obj = None
            converter = None


        name = obj.getProperty('Name') if obj else 'None'
        if self.driver.labelSetTarget(name):
            self.ui.selectedTargetSegmentLabel.setText(self.getShorterName(name))
        if self.driver.getLabelSource() and self.driver.getLabelTarget():
            self.ui.previewLabelButton.setEnabled(obj is not None)

    def resetProposals(self):
        self.driver.redrawView();
        self.targetColorCheckBox()
        self.transformedTargetColorCheckBox()
        self.sourceColorCheckBox()
        self.ui.centroidsCheckBox.setChecked(False)

    def visualizeProposals(self):
        self.driver.drawProposals()

    def toggleCentroidMode(self):
        self.driver.toggleCentroids(self.ui.centroidsCheckBox.checked)

    def getCameraCopy(self):
        camera = vtk.vtkCamera()
        camera.DeepCopy(self.view.camera())
        return camera

    def overheadButton(self):

        #c = self.getCameraCopy()
        c = self.view.camera()

        #c.SetFocalPoint([0,0,2])
        #c.SetViewUp([0.0, 0.0, 1.0])
        #c.SetPosition([0,0.1,1500])

        self.cameraFocalPoint = ([45.0, -139.0, 0])
        self.cameraViewUp = ([0.0, 0.0, 1.0])
        self.cameraPos = ([46, -139, 340])

        self.ui.gridSizeSpinBox.setValue(10)
        self.setCameraParams()

    def setCameraParams(self):
        c = self.view.camera()
        c.SetFocalPoint(self.cameraFocalPoint)
        c.SetViewUp(self.cameraViewUp)
        c.SetPosition(self.cameraPos)
        self.view.render()

    def targetColorCheckBox(self):
        self.driver.toggleColor('Target map segments', self.driver.targetContainer, self.ui.targetColorCheckBox.checked)
        self.driver.toggleColor('Target map segments centroids', self.driver.targetContainer, self.ui.targetColorCheckBox.checked)
    def transformedTargetColorCheckBox(self):
        self.driver.toggleColor('Transformed Target', self.driver.diftContainer, self.ui.transformedTargetColorCheckBox.checked)
    def sourceColorCheckBox(self):
        os.chdir(self.driver.getDiftLoc())
        for swathe in sorted(glob.glob("swathe*")):
            counter = swathe.split('_')[1]
            self.driver.toggleColor('Source Swathe '+counter,  self.driver.sourceContainer, self.ui.sourceColorCheckBox.checked)
            self.driver.toggleColor('Source Swathe '+counter+' centroids',  self.driver.sourceContainer, self.ui.sourceColorCheckBox.checked)

    def gridSizeSpinBox(self):
        #print "gridSizeSpinBox changed"
        #print self.ui.gridSizeSpinBox
        #print self.ui.gridSizeSpinBox.value
        obj = om.findObjectByName('grid')
        obj.gridSource.SetScale(self.ui.gridSizeSpinBox.value)
        self.view.render()

    def sourceOffsetSpinBox(self):
        self.driver.sourceYawOffset = self.ui.sourceOffsetSpinBox.value
        self.driver.changeYawOffset()
        self.view.render()

    def mapXOffsetSpinBox(self):
        self.driver.targetOffset[0] = self.ui.mapXOffsetSpinBox.value
        self.driver.changeTargetOffset()
        self.view.render()

    def mapYOffsetSpinBox(self):
        self.driver.targetOffset[1] = self.ui.mapYOffsetSpinBox.value
        self.driver.changeTargetOffset()
        self.view.render()

    def mapZOffsetSpinBox(self):
        self.driver.targetOffset[2] = self.ui.mapZOffsetSpinBox.value
        self.driver.changeTargetOffset()
        self.view.render()

def _getAction():

    actionName = 'ActionDiftDriverPanel'
    action = app.getToolBarActions().get(actionName)

    if action is None:

        icon = QtGui.QIcon(os.path.join(os.path.dirname(__file__), 'images/map_icon.png'))
        assert os.path.isfile(os.path.join(os.path.dirname(__file__), 'images/map_icon.png'))

        action = QtGui.QAction(icon, 'Dift Panel', None)
        action.objectName = 'ActionDiftDriverPanel'
        action.checkable = True

        mainWindow = app.getMainWindow()
        toolbar = mainWindow.panelToolBar()

        toolbar.insertAction(toolbar.actions()[0], action)

    return action


def init(driver, viewcolors, view, viewBackgroundLightHandler):

    global panel
    global dock

    panel = DiftDriverPanel(driver, viewcolors, view, viewBackgroundLightHandler)
    dock = app.addWidgetToDock(panel.widget, action=_getAction())
    dock.hide()

    return panel
