# retrieve the current dir
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )"/../../ && pwd )"
export DRS_BASE=$DIR

source /opt/ros/kinetic/setup.bash
source $DRS_BASE/code/devel/setup.bash

export PATH=$DRS_BASE/code_externals/build/bin:$PATH
export PKG_CONFIG_PATH=$DRS_BASE/code_externals/build/lib/pkgconfig:$PKG_CONFIG_PATH
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$DRS_BASE/code_externals/build/lib:$DRS_BASE/code_externals/build/lib64
export PYTHONPATH=$PYTHONPATH:$DRS_BASE/code_externals/build/lib/python2.7/dist-packages:$DRS_BASE/code_externals/build/lib/python2.7/site-packages
 

export PATH=$DRS_BASE/software/build/bin:$PATH  
# Currently required for dloopdetector
export PKG_CONFIG_PATH=$DRS_BASE/software/build/lib/pkgconfig:$DRS_BASE/software/build/lib64/pkgconfig:$PKG_CONFIG_PATH
# bot_core requires glib and glibconfig
export CPATH=$CPATH:$DRS_BASE/catkin_ws/devel/include:/usr/include/glib-2.0:/usr/lib/x86_64-linux-gnu/glib-2.0/include

# python path
export PYTHONPATH=$PYTHONPATH:$DRS_BASE/software/build/lib/python2.7/site-packages:$DRS_BASE/software/build/lib/python2.7/dist-packages


# Disable the top plate of the husky
export HUSKY_TOP_PLATE_ENABLED=false


#this is disabled as it doesnt exist in the checked out codebase
#source $DRS_BASE/catkin_ws/devel/setup.bash

export GAZEBO_MODEL_PATH=$DRS_BASE/catkin_ws/src/rpg_gazebo_objects:$GAZEBO_MODEL_PATH

alias cdrpg="cd $DRS_BASE/software"
alias director-husky="director -husky -c $DRS_BASE/software/config/husky/robot.cfg --startup $DRS_BASE/software/ui_modules/huskydirector/runstartup.py"
alias director-wildcat="director -husky -c $DRS_BASE/software/config/wildcat/robot.cfg --startup $DRS_BASE/software/ui_modules/huskydirector/runstartup.py"
alias director-husky-sim="director -husky -c $DRS_BASE/software/config/husky_sim/robot.cfg --startup $DRS_BASE/software/ui_modules/huskydirector/runstartup.py"
alias sshhusky="ssh administrator@husky" 
alias rungazebo='bot-procman-sheriff -l $DRS_BASE/software/config/husky_sim/robot.pmd'
alias rungazingdemo='bot-procman-sheriff -l $DRS_BASE/software/config/husky/husky-gazing-demo.pmd'
alias lcm_rec_logs='cd ~/logs/lcm/;lcm-logger';

export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$DRS_BASE/software/build/lib
export PATH=$PATH:/home/ori/code/director/build/install/bin