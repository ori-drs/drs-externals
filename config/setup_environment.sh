# retrieve the current dir
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )"/../../ && pwd )"
export DRS_BASE=$DIR
export DRC_BASE=$DIR


export PATH=$DRS_BASE/externals/build/bin:$PATH
export PKG_CONFIG_PATH=$DRS_BASE/externals/build/lib/pkgconfig:$PKG_CONFIG_PATH
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$DRS_BASE/externals/build/lib:$DRS_BASE/externals/build/lib64
export PYTHONPATH=$PYTHONPATH:$DRS_BASE/externals/build/lib/python2.7/dist-packages:$DRS_BASE/externals/build/lib/python2.7/site-packages
# bot_core requires glib and glibconfig
export CPATH=$CPATH:/usr/include/glib-2.0:/usr/lib/x86_64-linux-gnu/glib-2.0/include

# Disable the top plate of the husky
export HUSKY_TOP_PLATE_ENABLED=false


#this is disabled as it doesnt exist in the checked out codebase
#source $DRS_BASE/catkin_ws/devel/setup.bash

export GAZEBO_MODEL_PATH=$DRS_BASE/catkin_ws/src/rpg_gazebo_objects:$GAZEBO_MODEL_PATH

alias cdexternals="cd $DRS_BASE/externals"
alias director-husky="director -husky -c $DRS_BASE/externals/config/husky/robot.cfg --startup $DRS_BASE/externals/ui_modules/huskydirector/runstartup.py"
alias director-wildcat="director -husky -c $DRS_BASE/externals/config/wildcat/robot.cfg --startup $DRS_BASE/externals/ui_modules/huskydirector/runstartup.py"
alias director-husky-sim="director -husky -c $DRS_BASE/externals/config/husky_sim/robot.cfg --startup $DRS_BASE/externals/ui_modules/huskydirector/runstartup.py"
alias sshhusky="ssh administrator@husky" 
alias rungazebo='bot-procman-sheriff -l $DRS_BASE/externals/config/husky_sim/robot.pmd'
alias rungazingdemo='bot-procman-sheriff -l $DRS_BASE/externals/config/husky/husky-gazing-demo.pmd'
alias lcm_rec_logs='cd ~/logs/lcm/;lcm-logger';

