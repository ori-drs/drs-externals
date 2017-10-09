# retrieve the current dir
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )"/../../ && pwd )"
export DRC_BASE=$DIR
export PATH=$DRC_BASE/software/build/bin:$PATH  
# Currently required for dloopdetector
export PKG_CONFIG_PATH=$DRC_BASE/software/build/lib/pkgconfig:$DRC_BASE/software/build/lib64/pkgconfig:$PKG_CONFIG_PATH
# bot_core requires glib and glibconfig
export CPATH=$CPATH:$DRC_BASE/catkin_ws/devel/include:/usr/include/glib-2.0:/usr/lib/x86_64-linux-gnu/glib-2.0/include

# python path
export PYTHONPATH=$PYTHONPATH:$DRC_BASE/software/build/lib/python2.7/site-packages:$DRC_BASE/software/build/lib/python2.7/dist-packages


# Disable the top plate of the husky
export HUSKY_TOP_PLATE_ENABLED=false

#source /opt/ros/kinetic/setup.bash

#this is disabled as it doesnt exist in the checked out codebase
#source $DRC_BASE/catkin_ws/devel/setup.bash

export GAZEBO_MODEL_PATH=$DRC_BASE/catkin_ws/src/rpg_gazebo_objects:$GAZEBO_MODEL_PATH

alias cdrpg="cd $DRC_BASE/software"
alias director-husky="director -husky -c $DRC_BASE/software/config/husky/robot.cfg --startup $DRC_BASE/software/ui_modules/huskydirector/runstartup.py"
alias director-wildcat="director -husky -c $DRC_BASE/software/config/wildcat/robot.cfg --startup $DRC_BASE/software/ui_modules/huskydirector/runstartup.py"
alias director-husky-sim="director -husky -c $DRC_BASE/software/config/husky_sim/robot.cfg --startup $DRC_BASE/software/ui_modules/huskydirector/runstartup.py"
alias sshhusky="ssh administrator@husky" 
alias rungazebo='bot-procman-sheriff -l $DRC_BASE/software/config/husky_sim/robot.pmd'
alias rungazingdemo='bot-procman-sheriff -l $DRC_BASE/software/config/husky/husky-gazing-demo.pmd'
alias lcm_rec_logs='cd ~/logs/lcm/;lcm-logger';
