import copy
import os
import math
import glob
import vtk

from director import ioUtils
from director import lcmUtils
from director.utime import getUtime
import director.objectmodel as om
from director import visualization as vis
from director import transformUtils
from director import segmentation

from debugVis import DebugData

import csv
import matplotlib.pyplot as plt
import numpy as np
import drc as lcmdrc
import bot_core as lcmbotcore

try:
    from sklearn.metrics import roc_curve, auc
    from scipy.spatial import distance
    from tabulate import tabulate
except ImportError:
    pass


global colors
colors = [
    [51/255.0, 160/255.0, 44/255.0],
    [166/255.0, 206/255.0, 227/255.0],
    [178/255.0, 223/255.0, 138/255.0],
    [31/255.0, 120/255.0, 180/255.0],
    [251/255.0, 154/255.0, 153/255.0],
    [227/255.0, 26/255.0, 28/255.0],
    [253/255.0, 191/255.0, 111/255.0],
    [106/255.0, 61/255.0, 154/255.0],
    [255/255.0, 127/255.0, 0/255.0],
    [202/255.0, 178/255.0, 214/255.0],
    [1.0, 0.0, 0.0],
    [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0],
    [1.0, 1.0, 0.0],
    [1.0, 0.0, 1.0],
    [0.0, 1.0, 1.0],
    [0.5, 1.0, 0.0],
    [1.0, 0.5, 0.0],
    [0.5, 0.0, 1.0],
    [1.0, 0.0, 0.5],
    [0.0, 0.5, 1.0],
    [0.0, 1.0, 0.5],
    [1.0, 0.5, 0.5],
    [0.5, 1.0, 0.5],
    [0.5, 0.5, 1.0],
    [0.5, 0.5, 1.0],
    [0.5, 1.0, 0.5],
    [0.5, 0.5, 1.0]]


class DiftDriver(object):

    def __init__(self):
        self.sourceSegment = None
        self.targetProposalsRF = None
        self.targetProposalsKNN = None
        self.sourceSwathe = None
        self.sourceSegmentCorrespondence = None
        self.sourceFeatures = None
        self.featureLabels = None
        self.diftLoc = '/tmp/dift/'
        self.targetOffset = [0,0,0]
        self.sourceYawOffset = 0
        self.labelSource = None
        self.labelSourceSwathe = None
        self.labelTarget = None
        self.labels = []
        self.tempLabelledData = []
        self.diftContainer = om.getOrCreateContainer('DIFT')
        self.targetContainer = om.getOrCreateContainer('Target', parentObj=self.diftContainer)
        self.sourceContainer = om.getOrCreateContainer('Source', parentObj=self.diftContainer)

    def setDiftLoc(self, loc):
        self.diftLoc = loc

    def getDiftLoc(self):
        return self.diftLoc

    def add_subplot_zoom(self,figure):

        # temporary store for the currently zoomed axes. Use a list to work around
        # python's scoping rules
        zoomed_axes = [None]

        def on_click(event):
            ax = event.inaxes

            if ax is None:
                # occurs when a region not in an axis is clicked...
                return

            # we want to allow other navigation modes as well. Only act in case
            # shift was pressed and the correct mouse button was used
            if event.key != 'shift' or event.button != 1:
                return

            if zoomed_axes[0] is None:
                # not zoomed so far. Perform zoom

                # store the original position of the axes
                zoomed_axes[0] = (ax, ax.get_position())
                ax.set_position([0.1, 0.1, 0.85, 0.85])
                ax.tick_params(labelsize=16)
                font = {'size': 32}
                ax.set_ylabel(ax.get_ylabel(),fontdict=font)
                ax.set_xlabel(ax.get_xlabel(),fontdict=font)

                # hide all the other axes...
                for axis in event.canvas.figure.axes:
                    if axis is not ax:
                        axis.set_visible(False)

            else:
                # restore the original state
                font = {'size': 10}
                zoomed_axes[0][0].set_ylabel(ax.get_ylabel(), fontdict=font)
                zoomed_axes[0][0].set_xlabel(ax.get_xlabel(), fontdict=font)
                zoomed_axes[0][0].tick_params(labelsize=1)
                zoomed_axes[0][0].set_position(zoomed_axes[0][1])
                zoomed_axes[0] = None

                # make other axes visible again
                for axis in event.canvas.figure.axes:
                    axis.set_visible(True)

            # redraw to make changes visible.
            event.canvas.draw()

        figure.canvas.mpl_connect('button_press_event', on_click)

    def match_segments(self, candidate_matches_loc):
        # first pass the labelled matches
        labels={}
        labels_counter=0
        with open(self.getDiftLoc()+'labelled_matches.csv') as f:
            for line in f:
                tokens = line.split(',')
                if tokens[0] != 'target_id':
                    labels[labels_counter] = tuple((int(tokens[0]), int(tokens[1]), int(tokens[2])))
                    labels_counter+=1

        # pass the proposals
        proposals={}
        dict_counter=0
        for swathe in [os.path.basename(x) for x in sorted(glob.glob(self.getDiftLoc()+'swathe*'), key=lambda name: int(os.path.basename(name).split('_')[1]))]:
            swathe_id = swathe.split('_')[1]
            with open(self.getDiftLoc()+'swathe_'+swathe_id+"/"+candidate_matches_loc) as f:
                for line in f:
                    tokens = line.split(',')
                    if tokens[0][0] != '#':
                        proposals[dict_counter] = tuple((int(tokens[0]), int(tokens[1]), int(swathe_id), float(tokens[len(tokens)-1])))
                        dict_counter+=1

        print str(len(proposals)) + " candidates parsed. Normalizing..."
        # normalize the proposals scores
        norm_proposals={}
        all_scores = [prop_value[3] for prop_key,prop_value in proposals.iteritems()]

        min_score = min(all_scores)
        max_score = max(all_scores)
        max_min_score_diff = max_score - min_score
        for prop_key, proposal in proposals.iteritems():
            if max_min_score_diff == 0:
                normalized_val = 0
            else:
                normalized_val = (proposal[3]-min_score)/(max_min_score_diff)
            norm_proposals[prop_key] = tuple((int(proposal[0]), int(proposal[1]), int(proposal[2]), float(normalized_val)))

        print str(len(proposals)) + " candidates normalized. Splitting into labels and scores..."

        labels_output = []
        scores_output = []
        # matching
        for prop_key, proposal in proposals.iteritems():
            if tuple((int(proposal[0]), int(proposal[1]), int(proposal[2]))) in labels.values():
                labels_output.append(1)
            else:
                labels_output.append(0)
            scores_output.append(float(proposal[3]))

        print "  Done."

        return labels_output, scores_output

    def getCentroidsStats(self):
        radiuses = []
        obj = om.findObjectByName('Accepted Matches')
        for pair in obj.children():
            nameArr = pair.getProperty('Name').split(' ')
            source_cloud_id = int(nameArr[0].split('_')[2])
            target_cloud_id = int(nameArr[1].split('_')[2])
            source_swathe_obj = om.findObjectByName('cloud_cluster_'+str(source_cloud_id)).parent()
            source_swathe_id = int(source_swathe_obj.getProperty('Name').split(' ')[2])
            source_centroid = ()
            target_centroid = ()
            with open(dift.getDiftLoc()+'swathe_'+str(source_swathe_id)+'/csv/features.csv') as f:
                for line in f:
                    tokens = line.split(",")
                    if tokens[0][0] != '#':
                        if int(tokens[0]) == source_cloud_id:
                            source_centroid = tuple((( (float(tokens[9])), (float(tokens[10])), (float(tokens[11][:-1])) )))
            with open(dift.getDiftLoc()+'target_map_segments/csv/features.csv') as f:
                for line in f:
                    tokens = line.split(",")
                    if tokens[0][0] != '#':
                        if int(tokens[0]) == target_cloud_id:
                            target_centroid = tuple((( (float(tokens[9])), (float(tokens[10])), (float(tokens[11][:-1])) )))
            radiuses.append(distance.euclidean(source_centroid,target_centroid))
        print "max radius: " + str(max(radiuses))
        print "min radius: " + str(min(radiuses))
        print "mean radius: " + str(sum(radiuses)/len(radiuses))

    def viewStats(self):
        labelsPath = self.getDiftLoc() + 'labelled_matches.csv'
        if os.path.isfile(labelsPath):
            labels = []
            # parse the corespondance matches
            with open(labelsPath) as f:
                for line in f:
                    tokens = line.split(",")
                    if tokens[0] != "target_id":
                        labels.append(tuple((int(tokens[0]),int(tokens[1]),int(tokens[2]))))

            # parse the segments
            self.total_segments_per_swathe = {}
            # calculate total per swathe segments
            for swathe in [os.path.basename(x) for x in sorted(glob.glob(self.getDiftLoc()+'swathe*'), key=lambda name: int(os.path.basename(name).split('_')[1]))]:
                counter = int(swathe.split('_')[1])
                self.total_segments_per_swathe[counter] = []
                for segment in [os.path.basename(x) for x in sorted(glob.glob(self.getDiftLoc()+'swathe_'+str(counter)+'/cloud_cluster_*'), key=lambda name: int(os.path.basename(name).split('_')[2].split('.')[0]))]:
                    segmentNameArr = segment.split('_')
                    child_id = segmentNameArr[len(segmentNameArr)-1].split('.')[0]
                    self.total_segments_per_swathe[counter].append(int(child_id))

            # calculate how many have we labelled
            usable_segments_table = []
            usable_segments_table.append(["Swathe ID", "Total Segments", "Labelled Segments", "KNN Recognised", "RF Recognised"])
            knn_percent = []
            rf_percent = []
            usable_segments_per_swathe = {}
            for swathe in self.total_segments_per_swathe.items():
                usable_segments = set([x[1] for x in labels]).intersection(set(swathe[1]))
                knn_recognised_source_segments = []
                rf_recognised_source_segments = []
                for source_segment_id in usable_segments:
                    correct_correspondence = [x[0] for x in labels if x[1] == source_segment_id]
                    correct_correspondence = correct_correspondence[0]
                    with open(self.getDiftLoc() + 'swathe_' + str(swathe[0]) + '/' + 'knn_candidate_matches.csv') as f:
                        for line in f:
                            tokens = line.split(',')
                            if tokens[0][0] != '#':
                                if int(tokens[1]) == int(source_segment_id) and int(tokens[0]) == int(correct_correspondence):
                                    knn_recognised_source_segments.append(source_segment_id)
                    with open(self.getDiftLoc() + 'swathe_' + str(swathe[0]) + '/' + 'candidate_matches.csv') as f:
                        for line in f:
                            tokens = line.split(',')
                            if tokens[0][0] != '#':
                                if int(tokens[1]) == int(source_segment_id) and int(tokens[0]) == int(correct_correspondence):
                                    rf_recognised_source_segments.append(source_segment_id)

                knn_percent.append(round(float(len(knn_recognised_source_segments))/float(len(usable_segments)),2) if len(usable_segments) != 0 else 0)
                rf_percent.append(round(float(len(rf_recognised_source_segments))/float(len(usable_segments)),2) if len(usable_segments) != 0 else 0)
                usable_segments_per_swathe[int(swathe[0])-1] = usable_segments
                usable_segments_table.append(["Swathe "+str(swathe[0]), str(len(swathe[1])), str(len(usable_segments)), str(len(knn_recognised_source_segments))+"("+str(knn_percent[len(knn_percent)-1]) +")", str(len(rf_recognised_source_segments)) + "(" + str(rf_percent[len(rf_percent)-1]) +")"])

            non_zero_knn_percent = []
            non_zero_rf_percent = []
            total_labelled_segments = 0
            for swathe_index, segments in usable_segments_per_swathe.iteritems():
                if len(segments) != 0:
                    non_zero_knn_percent.append(knn_percent[swathe_index])
                    non_zero_rf_percent.append(rf_percent[swathe_index])

                total_labelled_segments += len(segments)


            usable_segments_table.append(["Total", str(len(np.sum(self.total_segments_per_swathe.values()))), str(total_labelled_segments), str(round(np.mean(non_zero_knn_percent),2)), str(round(np.mean(non_zero_rf_percent),2))])

            # show out of the labelled ones, how many passed the KNN test
            # show out of the KNN ones, how many passed the RF test
            print tabulate(usable_segments_table)

            # print "non_zero knn_percent:"
            # print non_zero_knn_percent

            # print "non_zero rf_percent:"
            # print non_zero_rf_percent

            # # estimate the average filtering percentage of KNN and RF
            # print "Mean percentage of filtered segments by KNN: " + str(np.mean(non_zero_knn_percent))
            # print "Mean percentage of filtered segments by RF: " + str(np.mean(non_zero_rf_percent))
            # print "Total segments: " + str(len(np.sum(self.total_segments_per_swathe.values())))
            # print "Total labelled segments: " + 

            # now visualize the ROC curve
            print "Processing RF labels:"
            rf_labels, rf_scores = self.match_segments("roc_candidate_matches_second_stage.csv")
            print "Processing KNN labels:"
            knn_labels, knn_scores = self.match_segments("roc_candidate_matches_first_stage.csv")

            fpr_rf, tpr_rf, _ = roc_curve(rf_labels, rf_scores)
            roc_auc_rf = auc(fpr_rf, tpr_rf)

            fpr_knn, tpr_knn, _ = roc_curve(knn_labels, knn_scores)
            roc_auc_knn = auc(fpr_knn, tpr_knn)

            plt.figure()
            lw = 2
            plt.plot(fpr_rf, tpr_rf, color='blue',
                     lw=lw, label='RF ROC curve (area = %0.2f)' % roc_auc_rf)
            plt.plot(fpr_knn, tpr_knn, color='black',
                     lw=lw, label='L2 ROC curve (area = %0.2f)' % roc_auc_knn)
            plt.xlim([0.0, 1.0])
            plt.ylim([0.0, 1.05])
            plt.xlabel('False Positive Rate')
            plt.ylabel('True Positive Rate')
            plt.title('Receiver Operating Characteristic')
            plt.legend(loc="lower right")
            plt.ion()
            plt.show()

    def visualizeFeatureSpace(self):
        # find the dimension of the feature space
        if self.sourceSwathe and self.sourceSegment and self.targetProposalsRF:
            feature_dim = 0
            self.featureLabels = []
            self.sourceFeatures = []
            with open(self.getDiftLoc()+'swathe_'+self.sourceSwathe+'/csv/features.csv') as f:
                tokens = f.readline().split(',')
                # the first is the segment id
                # the last 3 are the centroid
                feature_dim = len(tokens)-4
                for i in range(feature_dim):
                    self.featureLabels.append(tokens[1+i])
                for line in f:
                    tokens = line.split(',')
                    if int(tokens[0]) == int(self.sourceSegment):
                        self.sourceFeatures = map(float, tokens[1:feature_dim+1])

            if feature_dim == 0 or not self.sourceFeatures or not self.featureLabels:
                return

            if feature_dim > 10:
                print "The feature dimension is too high:" + str(feature_dim)
                print "Please reduce this to at most 10 and try again."
                return

            self.targetProposalsFeatures = {}
            with open(self.getDiftLoc()+'target_map_segments/csv/features.csv') as f:
                for line in f:
                    tokens = line.split(',')
                    if tokens[0][0] != '#':
                        if int(tokens[0]) in [int(i[0]) for i in self.targetProposalsRF]:
                            self.targetProposalsFeatures[int(tokens[0])] = map(float, tokens[1:feature_dim+1])

            # it could be the case that there's no match for this source segment
            targetCorrespondenceFeatures = []
            if self.sourceSegmentCorrespondence:
                targetCorrespondenceFeatures = self.targetProposalsFeatures[self.sourceSegmentCorrespondence]
                del self.targetProposalsFeatures[self.sourceSegmentCorrespondence]

            self.targetProposalsFeaturesMatrix = np.ndarray((len(self.targetProposalsFeatures), len(self.targetProposalsFeatures.values()[0])))
            for index, val in enumerate(self.targetProposalsFeatures.values()):
                self.targetProposalsFeaturesMatrix[index] = val

            # now we need to plot the feature and the target proposals
            f, axarr = plt.subplots(feature_dim, feature_dim)
            for i in range(feature_dim):
                for j in range(feature_dim):
                    # axarr[i, j].set_title(self.featureLabels[i]+" vs "+self.featureLabels[j])
                    axarr[i, j].scatter(self.targetProposalsFeaturesMatrix[:,j], self.targetProposalsFeaturesMatrix[:,i], c='r', s=100, edgecolor='r')
                    if self.sourceSegmentCorrespondence and targetCorrespondenceFeatures:
                        axarr[i, j].scatter(targetCorrespondenceFeatures[j], targetCorrespondenceFeatures[i], c='b', s=100, edgecolor='b', marker='x', linewidth=5)
                    axarr[i, j].scatter(self.sourceFeatures[j], self.sourceFeatures[i], c='orange', s=100, edgecolor='orange', marker='x', linewidth=5)
                    axarr[i, j].set_xlabel(self.featureLabels[j])
                    axarr[i, j].set_ylabel(self.featureLabels[i])
            self.add_subplot_zoom(f)
            plt.ion()
            plt.show()

    def redrawView(self):
        containers = ['Target map segments', 'Transformed Target', 'Accepted Matches', 'Target map segments centroids']
        for c in containers:
            obj = om.findObjectByName(c)
            if obj:
                obj.setProperty('Visible', True)
                for cloud in obj.children():
                    cloud.setProperty('Visible', True)
                    cloud.setProperty('Alpha', 1.0)
        for swathe in [os.path.basename(x) for x in sorted(glob.glob(self.getDiftLoc()+'swathe*'), key=lambda name: int(os.path.basename(name).split('_')[1]))]:
            counter = swathe.split('_')[1]
            contrs = ['Source Swathe '+counter, 'Source Swathe '+counter+' centroids']

            for c in contrs:
                sourceObj = om.findObjectByName(c)
                sourceObj.setProperty('Visible', True)
                for cloud in sourceObj.children():
                    cloud.setProperty('Visible', True)

    def removeCurrentDiftData(self):
        for obj in om.getObjects():
            nameArr = obj.getProperty('Name').split(' ')
            if not obj.parent() and (nameArr[0] == "Source" or nameArr[0] == "Target" or nameArr[0] == "Transformed" or nameArr[0] == "Accepted"):
                om.removeFromObjectModel(obj)


    def drawSegments(self):
        self.diftContainer = om.getOrCreateContainer('DIFT')
        self.targetContainer = om.getOrCreateContainer('Target', parentObj=self.diftContainer)
        self.sourceContainer = om.getOrCreateContainer('Source', parentObj=self.diftContainer)

        # remove the current objects
        self.removeCurrentDiftData()
        self.drawSegmentsMain(self.getDiftLoc()+'target_map_segments/','Target map segments', self.targetContainer, 0)
        self.drawSegmentsMain(self.getDiftLoc()+'target_map/','Target Full Map', self.targetContainer, 0) # add the full map
        self.drawSourceSegmentsMain(self.getDiftLoc(),'Source Swathe', self.targetOffset[2])
        self.drawSegmentsMain(self.getDiftLoc()+'transformed_target_segments/','Transformed Target', self.diftContainer,  self.targetOffset[2])

        self.drawLines()

        # reset the labelled matches list
        self.labels = []

    def changeYawOffset(self):
        folders = []
        for swathe in [os.path.basename(x) for x in sorted(glob.glob(self.getDiftLoc()+'swathe*'), key=lambda name: int(os.path.basename(name).split('_')[1]))]:
            counter = swathe.split('_')[1]
            folders.append('Source Swathe ' + counter)
            folders.append('Source Swathe ' + counter + ' centroids')

        for directory in folders:
            d = om.getOrCreateContainer(directory, parentObj=self.sourceContainer)
            for cloud in d.children():
                offsetTransform=transformUtils.frameFromPositionAndRPY([0,0,self.sourceVerticalOffset], [0,0,self.sourceYawOffset])
                cloud.actor.SetUserTransform(offsetTransform)

        self.drawLines()

    def changeTargetOffset(self):
        folders = ['Target map segments', 'Target map segments centroids', 'Target Full Map']
        for dir in folders:
            folder = om.getOrCreateContainer(dir, parentObj=self.targetContainer)
            for cloud in folder.children():
                offsetTransform = transformUtils.frameFromPositionAndRPY([self.targetOffset[0],self.targetOffset[1],self.targetOffset[2]],[0,0,0])
                cloud.actor.SetUserTransform(offsetTransform)

        # folder = om.getOrCreateContainer('Transformed Target')
        # for cloud in folder.children():
        #     offsetTransform = transformUtils.frameFromPositionAndRPY([0,0,verticalOffset],[0,0,0])
        #     cloud.actor.SetUserTransform(offsetTransform)

        self.drawLines()

    def drawSourceSegmentsMain(self, topLevelDir, dirName, verticalOffset):
        self.sourceVerticalOffset = verticalOffset
        try:
            for swathe in [os.path.basename(x) for x in sorted(glob.glob(topLevelDir+'swathe*'), key=lambda name: int(os.path.basename(name).split('_')[1]))]:
                counter = swathe.split('_')[1]
                self.drawSegmentsMain(topLevelDir+swathe+'/', dirName+" "+ counter, self.sourceContainer, verticalOffset)
        except ValueError as e:
            print "Wrong source  segments directories"
            print "Exception:"
            print e

    def getLabelSource(self):
        return self.labelSource

    def getLabelTarget(self):
        return self.labelTarget

    def labelSetSource(self, sourceCloud):
        obj = om.findObjectByName(sourceCloud)
        if obj:
            if obj.parent():
                parentNameArr = obj.parent().getProperty('Name').split(' ')
                if parentNameArr[0] == "Source":
                    nameArr = sourceCloud.split('_')
                    self.labelSource = nameArr[len(nameArr)-1]
                    self.labelSourceSwathe = parentNameArr[2]
                    return True
        self.labelSource = None
        self.labelSourceSwathe = None
        return False

    def getLabelSourceSwathe(self):
        return self.labelSourceSwathe

    def labelSetTarget(self, targetCloud):
        obj = om.findObjectByName(targetCloud)
        parentNameArr = obj.parent().getProperty('Name').split(' ')
        if parentNameArr[0] == "Target":
            nameArr = targetCloud.split('_')
            self.labelTarget = nameArr[len(nameArr)-1]
            return True
        self.labelTarget = None
        return False

    def addLabelledMatch(self):
        self.labels.append(tuple(( int(self.labelTarget), int(self.labelSource), int(self.labelSourceSwathe))))
        self.labelSource = None
        self.labelSourceSwathe = None
        self.labelTarget = None

        with open(self.getDiftLoc()+'.labelled_matches.csv', 'wb') as outfile:
            csv_out=csv.writer(outfile)
            csv_out.writerow(['target_id','source_id','swathe_id'])
            for row in self.labels:
                csv_out.writerow(row)

        print "Matches so far:"
        print self.labels

    def saveLabelsPermanentYes(self):
        labelsPath = self.getDiftLoc() + 'labelled_matches.csv'
        print "Saving matches to: " + labelsPath
        with open(labelsPath, 'wb') as outfile:
            csv_out=csv.writer(outfile)
            csv_out.writerow(['target_id','source_id','swathe_id'])
            for row in self.labels:
                csv_out.writerow(row)

    def parseSavedLabels(self):
        labelsPath = self.getDiftLoc() + 'labelled_matches.csv'
        tempLabelsPath = self.getDiftLoc() + '.labelled_matches.csv'
        if os.path.isfile(tempLabelsPath):
            os.remove(tempLabelsPath)
        self.labels = []
        print "Opening matches from: " + labelsPath
        with open(labelsPath) as f:
            for line in f:
                tokens = line.split(',')
                if tokens[0] != "target_id":
                    self.labels.append(tuple((int(tokens[0]), int(tokens[1]), int(tokens[2]))))
        # sort by swathe id
        self.labels = sorted(self.labels, key=lambda name: (int(name[2]), int(name[0]), int(name[1])))
        self.loadedLabels = []

    def loadNextMatch(self):
        nextLabelId = len(self.loadedLabels)
        if nextLabelId < len(self.labels):
            # hide the current labelled match
            labelled = om.getOrCreateContainer('Labelled matches', parentObj=self.diftContainer)
            if labelled.children():
                for cloud in labelled.children():
                    om.removeFromObjectModel(cloud)

            source_loc = self.getDiftLoc()+'swathe_'+str(self.labels[nextLabelId][2])+'/'
            source_centroid = []
            with open(source_loc+'csv/features.csv') as f:
                for line in f:
                    tokens = line.split(',')
                    if tokens[0][0] != '#':
                        if int(tokens[0]) == self.labels[nextLabelId][1]:
                            source_centroid = tuple(([float(tokens[9]), float(tokens[10]), float(tokens[11][:-1])]))

            if not source_centroid:
                return
            source_polyData = ioUtils.readPolyData(source_loc+'cloud_cluster_'+str(self.labels[nextLabelId][1])+'.pcd')
            source_color = [0.2,0.9,0.2]
            source_fileRoot = 'labelled_cloud_cluster_'+str(self.labels[nextLabelId][1])

            source_pts = vtk.vtkPoints()
            source_verts = vtk.vtkCellArray()

            for i in range(source_polyData.GetNumberOfPoints()):
                id = source_pts.InsertNextPoint(tuple(np.subtract(source_polyData.GetPoint(i), source_centroid)))
                source_verts.InsertNextCell(1)
                source_verts.InsertCellPoint(id)

            centered_source_pd = vtk.vtkPolyData()
            centered_source_pd.SetPoints(source_pts)
            centered_source_pd.SetVerts(source_verts)

            target_loc = self.getDiftLoc()+'target_map_segments/'
            target_centroid = []
            with open(target_loc+'csv/features.csv') as f:
                for line in f:
                    tokens = line.split(',')
                    if tokens[0][0] != '#':
                        if int(tokens[0]) == self.labels[nextLabelId][0]:
                            target_centroid = tuple(([float(tokens[9]), float(tokens[10]), float(tokens[11][:-1])]))

            if not target_centroid:
                return
            target_polyData = ioUtils.readPolyData(target_loc+'cloud_cluster_'+str(self.labels[nextLabelId][0])+'.pcd')
            target_color = [0.9,0.2,0.2]
            target_fileRoot = 'labelled_cloud_cluster_'+str(self.labels[nextLabelId][0])

            target_pts = vtk.vtkPoints()
            target_verts = vtk.vtkCellArray()

            for i in range(target_polyData.GetNumberOfPoints()):
                id = target_pts.InsertNextPoint(tuple(np.subtract(target_polyData.GetPoint(i), target_centroid)))
                target_verts.InsertNextCell(1)
                target_verts.InsertCellPoint(id)

            centered_target_pd = vtk.vtkPolyData()
            centered_target_pd.SetPoints(target_pts)
            centered_target_pd.SetVerts(target_verts)

            vis.showPolyData(centered_source_pd, source_fileRoot, parent=labelled, color=source_color)
            vis.showPolyData(centered_target_pd, target_fileRoot, parent=labelled, color=target_color)

            self.loadedLabels.append(self.labels[nextLabelId])
            # when the last segment is shown - return false, so that the next button is disabled
            if len(self.loadedLabels) == len(self.labels):
                return False
            # otherwise true
            return True
        # fail-safe scenario - false
        return False

    def loadPrevMatch(self):
        if len(self.loadedLabels) <= 2:
            del self.loadedLabels[-2:]
            self.loadNextMatch()
            return False
        else:
            del self.loadedLabels[-2:]
            return self.loadNextMatch()

    def saveMatch(self, id):
        self.tempLabelledData.append(self.labels[id])

    def deleteCurrentMatch(self):
        currentMatchID = len(self.loadedLabels)-1
        self.saveMatch(currentMatchID)
        del self.labels[currentMatchID]
        del self.loadedLabels[currentMatchID]

    def undoDeleteMatch(self):
        if len(self.tempLabelledData) > 0:
            self.labels.append(self.tempLabelledData[len(self.tempLabelledData)-1])
            self.loadedLabels.append(self.tempLabelledData[len(self.tempLabelledData)-1])
            self.labels = sorted(self.labels, key=lambda name: (int(name[2]), int(name[0]), int(name[1])))
            self.loadedLabels = sorted(self.loadedLabels, key=lambda name: (int(name[2]), int(name[0]), int(name[1])))
            del self.tempLabelledData[-1]
            return True
        return False

    # this refers to target being the selected target for RF/KNN preview
    def setTarget(self, targetName):
        obj = om.findObjectByName(targetName)
        parentNameArr = obj.parent().getProperty('Name').split(' ')
        targetNameArr = targetName.split('_')
        if len(parentNameArr) > 2 and len(targetNameArr) > 2:
            self.sourceSegment = targetNameArr[2]
            self.sourceSwathe = parentNameArr[2]
            print "Parsing proposals for source segment " + self.sourceSegment + " in swathe " + self.sourceSwathe + " with all accepted matches from that swathe"
            self.targetProposalsRF = []
            os.chdir(self.getDiftLoc()+'swathe_'+self.sourceSwathe+'/')
            with open('candidate_matches.csv') as f:
                for line in f:
                    tokens = line.split(',')
                    if tokens[1] == self.sourceSegment:
                        self.targetProposalsRF.append(tuple((int(tokens[0]), float(tokens[len(tokens)-1]))))

            self.targetProposalsKNN = []
            with open('knn_candidate_matches.csv') as f:
                for line in f:
                    tokens = line.split(',')
                    if tokens[1] == self.sourceSegment:
                        self.targetProposalsKNN.append(tuple((int(tokens[0]), float(tokens[len(tokens)-1]))))

            self.sourceSegmentCorrespondence = None
            with open(self.getDiftLoc()+'swathe_'+self.sourceSwathe+'/filtered_matches.csv') as f:
                for line in f:
                    tokens = line.split(',')
                    if tokens[0][0] != '#':
                        if int(tokens[1]) == int(self.sourceSegment):
                            self.sourceSegmentCorrespondence = int(tokens[0])
                            break
        else:
            self.sourceSegment = None
            self.sourceSwathe = None
            self.targetProposalsRF = None
            self.targetProposalsKNN = None
            self.sourceSegmentCorrespondence = None

    def getTargetSwathe(self):
        if self.sourceSwathe:
            return "Swathe "+self.sourceSwathe
        else:
            return "None"

    def hideAllSegments(self):
        containers = ['Target map segments', 'Transformed Target', 'Accepted Matches', 'Target map segments centroids']
        for c in containers:
            obj = om.findObjectByName(c)
            if obj:
                obj.setProperty('Visible', False)
                for cloud in obj.children():
                    cloud.setProperty('Visible', False)
        for swathe in [os.path.basename(x) for x in sorted(glob.glob(self.getDiftLoc()+'swathe*'), key=lambda name: int(os.path.basename(name).split('_')[1]))]:
            counter = swathe.split('_')[1]
            contrs = []
            # remove if you want to only show the matched source segments
            if counter != self.sourceSwathe:
                contrs = ['Source Swathe '+counter, 'Source Swathe '+counter+' centroids']

            for c in contrs:
                sourceObj = om.findObjectByName(c)
                if sourceObj:
                    sourceObj.setProperty('Visible', False)
                    if sourceObj.children():
                        for cloud in sourceObj.children():
                            cloud.setProperty('Visible', False)

    def showAllSegments(self):
        containers = ['Target map segments', 'Transformed Target', 'Accepted Matches', 'Target map segments centroids']
        for c in containers:
            obj = om.findObjectByName(c)
            if obj:
                obj.setProperty('Visible', True)
                for cloud in obj.children():
                    cloud.setProperty('Visible', True)
        for swathe in [os.path.basename(x) for x in sorted(glob.glob(self.getDiftLoc()+'swathe*'), key=lambda name: int(os.path.basename(name).split('_')[1]))]:
            counter = swathe.split('_')[1]
            contrs = []
            # remove if you want to only show the matched source segments
            if counter != self.sourceSwathe:
                contrs = ['Source Swathe '+counter, 'Source Swathe '+counter+' centroids']

            for c in contrs:
                sourceObj = om.findObjectByName(c)
                if sourceObj:
                    sourceObj.setProperty('Visible', True)
                    if sourceObj.children():
                        for cloud in sourceObj.children():
                            cloud.setProperty('Visible', True)



    def drawProposals(self):
        if self.sourceSegment and self.sourceSwathe:

            self.hideAllSegments()

            # view of the selected source segment, as well as the other matches from the same swathe
            matches = {}
            with open(self.getDiftLoc()+'swathe_'+self.sourceSwathe+'/filtered_matches.csv') as f:
                counter = 0
                for line in f:
                    tokens = line.split(',')
                    if tokens[0][0] != '#':
                        matches[counter] = (tokens[0],tokens[1])
                        counter+=1

            for i,(proposal,confidence) in enumerate(self.targetProposalsKNN):
                obj = om.findObjectByName('cloud_cluster_'+str(proposal)).setProperty('Visible', True)
                obj = om.findObjectByName('cloud_cluster_centroid_'+str(proposal)).setProperty('Visible', True)
                obj = om.findObjectByName('cloud_cluster_'+str(proposal)).setProperty('Alpha', 1.0)
                obj = om.findObjectByName('cloud_cluster_centroid_'+str(proposal)).setProperty('Alpha', 1.0)
                obj = om.findObjectByName('cloud_cluster_'+str(proposal)).setProperty('Color', [0.63,0.125,0.94])
                obj = om.findObjectByName('cloud_cluster_centroid_'+str(proposal)).setProperty('Color', [0.63,0.125,0.94])

            for i,(proposal,confidence) in enumerate(self.targetProposalsRF):
                obj = om.findObjectByName('cloud_cluster_'+str(proposal)).setProperty('Visible', True)
                obj = om.findObjectByName('cloud_cluster_centroid_'+str(proposal)).setProperty('Visible', True)
                if max(self.targetProposalsRF, key = lambda t: t[1])[1] == min(self.targetProposalsRF, key = lambda t: t[1])[1]:
                    normConfidence = 0.01
                else:
                    normConfidence = (float(confidence)-min(self.targetProposalsRF, key = lambda t: t[1])[1]) / (max(self.targetProposalsRF, key = lambda t: t[1])[1] - min(self.targetProposalsRF, key = lambda t: t[1])[1])
                    if normConfidence == 0.0:
                        normConfidence = 0.01
                obj = om.findObjectByName('cloud_cluster_'+str(proposal)).setProperty('Alpha', float(normConfidence))
                obj = om.findObjectByName('cloud_cluster_centroid_'+str(proposal)).setProperty('Alpha', float(normConfidence))
                obj = om.findObjectByName('cloud_cluster_'+str(proposal)).setProperty('Color', [0.9,0.2,0.2])
                obj = om.findObjectByName('cloud_cluster_centroid_'+str(proposal)).setProperty('Color', [0.9,0.2,0.2])


            # display all the matches with their correspondences
            for match in matches.itervalues():
                om.findObjectByName('cloud_cluster_'+match[1]).setProperty('Visible', True)
                om.findObjectByName('cloud_cluster_centroid_'+match[1]).setProperty('Visible', True)
                # and the target ones
                om.findObjectByName('cloud_cluster_'+match[0]).setProperty('Visible', True)
                om.findObjectByName('cloud_cluster_centroid_'+match[0]).setProperty('Visible', True)
                om.findObjectByName('cloud_cluster_'+match[0]).setProperty('Color',[0.9,0.65,0.2])
                om.findObjectByName('cloud_cluster_centroid_'+match[0]).setProperty('Color',[0.9,0.65,0.2])


                om.findObjectByName('transformed_target_segment_'+match[0]+'_to_match_source_'+match[1]).setProperty('Visible', True)
                om.findObjectByName('cloud_cluster_'+match[1]+' '+'cloud_cluster_'+match[0]).setProperty('Visible', True)

            # color the selected segment distinguishably
            objs = om.findObjectByName('cloud_cluster_'+self.sourceSegment)
            objs.setProperty('Color', [1.0, 0.75, 0.8])
            objs_centroid = om.findObjectByName('cloud_cluster_centroid_'+self.sourceSegment)
            objs_centroid.setProperty('Color', [1.0, 0.75, 0.8])

    def drawSegmentsMain(self, dataDirectory, folderName, parentName, verticalOffset):
        folder = om.getOrCreateContainer(folderName, parentObj=parentName)
        sortable_by = 2
        if folderName.split(" ")[0] == "Transformed":
            sortable_by = 3
        om.collapse(folder)
        counter = 0
        for filename in [os.path.basename(x) for x in sorted(glob.glob(dataDirectory+'*.pcd'), key=lambda name: int(os.path.basename(name).split('_')[sortable_by].split('.')[0]))]:
            print(filename)
            polyData = ioUtils.readPolyData(os.path.join(dataDirectory, filename))

            # Method 1: indvidually move the points
            #if (verticalOffset>0):
            #    offsetTransform = transformUtils.frameFromPositionAndRPY([0,0,verticalOffset],[0,0,0])
            #    polyData = segmentation.transformPolyData(polyData, offsetTransform)

            if folderName == "Target Full Map":
                color=[255,255,255]
                pointAlpha=0.01
            else:
                color = colors[counter%len(colors)]
                pointAlpha=1
            fileRoot = os.path.splitext(filename)[0]
            obj = vis.showPolyData(polyData, fileRoot, parent=folder, color=color, alpha=pointAlpha)

            # Method 2: the following moves the entire polyData in the ui using an internal coordinate frame - but not the individual points
            offsetTransform = transformUtils.frameFromPositionAndRPY([0,0,verticalOffset],[0,0,0])
            obj.actor.SetUserTransform(offsetTransform)

            counter = counter + 1
            #if (counter > 10):
            #    break

        if folderName != "Transformed Target" and folderName != "Target Full Map":
            color = [0.0, 0.0, 0.0]
            if folderName == "Target map segments":
                color = [0.9,0.2,0.2]
            else:
                color = [0.2,0.9,0.2]
            centroid_dir = om.getOrCreateContainer(folderName+" centroids", parentObj=parentName)
            om.collapse(centroid_dir)
            # displayed the centroids in a separate cloud with thicker points
            try:
                with open(dataDirectory+'csv/features.csv') as f:
                    for line in f:
                        tokens = line.split(',')
                        if tokens[0][0] != '#':
                            centroid = [float(tokens[9]), float(tokens[10]), float(tokens[11][:-1])]

                            pts = vtk.vtkPoints()
                            id = pts.InsertNextPoint(centroid)
                            verts = vtk.vtkCellArray()
                            verts.InsertNextCell(1)
                            verts.InsertCellPoint(id)
                            polyData = vtk.vtkPolyData()
                            polyData.SetPoints(pts)
                            polyData.SetVerts(verts)

                            # if int(tokens[0]) == 301:
                            #     print "Centroid should be at: "
                            #     print centroid
                            #     print "poyldata:"
                            #     print polyData

                            obj = vis.showPolyData(polyData, 'cloud_cluster_centroid_'+tokens[0], parent=centroid_dir, color=color)
                            obj.setProperty('Point Size', 10)

                            offsetTransform = transformUtils.frameFromPositionAndRPY([0,0,verticalOffset],[0,0,0])
                            obj.actor.SetUserTransform(offsetTransform)
            except IOError as e:
                print "Centroids folder not found, not drawing centroids."
                print "Exception: "
                print e



    def toggleCentroids(self, centroidsMode):
        if centroidsMode:
            # disable all visible segments
            containers = ['Target map segments']
            for c in containers:
                obj = om.findObjectByName(c)
                obj.setProperty('Visible', not centroidsMode)
                for cloud in obj.children():
                    cloud.setProperty('Visible', not centroidsMode)
            for swathe in [os.path.basename(x) for x in sorted(glob.glob(self.getDiftLoc()+'swathe*'), key=lambda name: int(os.path.basename(name).split('_')[1]))]:
                counter = swathe.split('_')[1]
                contrs = ['Source Swathe '+counter]

                for c in contrs:
                    sourceObj = om.findObjectByName(c)
                    sourceObj.setProperty('Visible', not centroidsMode)
                    for cloud in sourceObj.children():
                        cloud.setProperty('Visible', not centroidsMode)
        else:
            toBeDisplayed = []
            containers = ['Target map segments centroids']
            for swathe in [os.path.basename(x) for x in sorted(glob.glob(self.getDiftLoc()+'swathe*'), key=lambda name: int(os.path.basename(name).split('_')[1]))]:
                counter = swathe.split('_')[1]
                containers.append('Source Swathe '+counter+' centroids')

            for c in containers:
                obj = om.findObjectByName(c)
                for cloud in obj.children():
                    nameArr = cloud.getProperty('Name').split('_')
                    if cloud.getProperty('Visible'):
                        toBeDisplayed.append(nameArr[len(nameArr)-1])

            for segment in toBeDisplayed:
                obj = om.findObjectByName('cloud_cluster_'+segment)
                obj.setProperty('Visible', not centroidsMode)

    def toggleColor(self, folderName, parentName, colorMode):
        folder = om.getOrCreateContainer(folderName, parentObj=parentName)
        counter = 0
        for cloud in folder.children():
            #print 'Color Mode'
            #print folderName
            #print cloud.properties.getProperty('Name')
            if (colorMode):
                if (folderName == "Target map segments" or folderName == "Target map segments centroids"):
                    cloud.setProperty('Color',[0.9,0.2,0.2])
                elif (folderName == "Transformed Target"):
                    cloud.setProperty('Color',[0.2,0.2,0.9])
                else:
                    cloud.setProperty('Color',[0.2,0.9,0.2])
            else:
                color = colors[counter%len(colors)]
                cloud.setProperty('Color',color)

            counter = counter + 1


    def drawLines(self):
        folder = om.getOrCreateContainer('Transformed Target', parentObj=self.diftContainer)
        for cloud in folder.children():
            cloudNameArr = cloud.getProperty('Name').split('_');
            source_id = cloudNameArr[len(cloudNameArr)-1]
            target_id = cloudNameArr[3]
            self.drawLineBetweenCenters('cloud_cluster_'+source_id,'cloud_cluster_'+target_id)


    def drawLineBetweenCenters(self, polyNameFrom, polyNameTo):
        centerFrom = self.computeCenterOfCloud(polyNameFrom)
        centerTo = self.computeCenterOfCloud(polyNameTo)

        d = DebugData()
        d.addLine(centerFrom, centerTo, radius=0.1)
        geometry = d.getPolyData()
        folder = om.getOrCreateContainer("Accepted Matches", parentObj=self.diftContainer)
        om.collapse(folder)

        lineName = polyNameFrom + " " + polyNameTo
        obj = vis.updatePolyData(geometry, lineName, parent=folder, color=[1,0,0], visible=True)

    def computeCenterOfCloud(self, polyName):
        obj = om.findObjectByName(polyName)

        clusterId = None
        # centroid is combined with the object's user transform
        offsetTransform = obj.actor.GetUserTransform()
        centroid = []
        # retrieve the centroid from a file location
        parentName = obj.parent().getProperty('Name')
        objNameArr = obj.getProperty('Name').split('_')
        if parentName == "Target map segments" or parentName == "Transformed Target":
            os.chdir(self.getDiftLoc()+'target_map_segments/csv/')
            if parentName == "Target map segments":
                clusterId = objNameArr[2]
            else:
                clusterId = objNameArr[3]
        else:
            clusterId = objNameArr[2]
            parentNameArr = parentName.split(" ")
            os.chdir(self.getDiftLoc()+'swathe_'+parentNameArr[2]+'/csv/')
        with open('features.csv') as f:
            for line in f:
                tokens = line.split(',')
                if tokens[0] == clusterId:
                    centroid.append(float(tokens[9]))
                    centroid.append(float(tokens[10]))
                    centroid.append(float(tokens[11][:-1]))
                    centroid = np.array(centroid)
                    break
        centroid = offsetTransform.GetPosition() + centroid

        return centroid



def init():

    global driver
    driver = DiftDriver()

    return driver
