sys.path.append(os.path.join(director.getDRCBaseDir(), 'software/ui_modules'))

import huskydirector.startup
huskydirector.startup.startup(robotSystem, globals())
