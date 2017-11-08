import copy
import math

from director import lcmUtils
from director.utime import getUtime
import director.objectmodel as om
from director import visualization as vis
from director import transformUtils

import drc as lcmdrc
import bot_core as lcmbotcore

class NavigationDriver(object):

    def __init__(self):

        x = 0
    def sendWholeBodyCommand(self, wholeBodyMode):
        
        print "sendWholeBodyCommand"


def init():

    global driver
    driver = NavigationDriver()

    return driver
