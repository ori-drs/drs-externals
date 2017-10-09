import numpy
import math

def rollFunctionPose(msg):
    '''roll'''
    return msg.utime, msg.roll* 180.0/math.pi
def pitchFunctionPose(msg):
    '''pitch'''
    return msg.utime, msg.pitch* 180.0/math.pi
def yawFunctionPose(msg):
    '''yaw'''
    return msg.utime, msg.yaw* 180.0/math.pi

addPlot(timeWindow=30, yLimits=[-1, 1])
addSignalFunction('OXTS', rollFunctionPose)

addPlot(timeWindow=30, yLimits=[-1, 1])
addSignalFunction('OXTS', pitchFunctionPose)

addPlot(timeWindow=30, yLimits=[-1, 1])
addSignalFunction('OXTS', yawFunctionPose)


addPlot(timeWindow=30, yLimits=[-1, 1])
addSignal('POSE_BODY', msg.utime, msg.pos[2])

