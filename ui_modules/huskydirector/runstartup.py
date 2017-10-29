sys.path.append(os.path.join(director.getDRCBaseDir(), 'code_externals/ui_modules'))

import huskydirector.startup
huskydirector.startup.startup(robotSystem, globals())
