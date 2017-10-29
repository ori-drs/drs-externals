cmake_minimum_required(VERSION 2.6.0)

# pull in the pods macros. See cmake/pods.cmake for documentation
set(POD_NAME motion_estimate)
include(cmake/pods.cmake)

# automatically build LCM types.  This also defines a number of CMake
# variables, see cmake/lcmtypes.cmake for details
#include(cmake/lcmtypes.cmake)
#lcmtypes_build()

#add_subdirectory(src/control)
#add_subdirectory(src/gaze_following)
#add_subdirectory(src/joints2frames)

#pods_install_python_script(state-sync-husky python/state-sync-husky.py)
#pods_install_python_script(husky-send-a-pose python/send_a_pose.py)
#pods_install_python_script(husky-send-a-goal python/send_a_gaze_goal.py)
#pods_install_python_script(multisense-cmd-husky python/multisense-cmd-husky.py)
#pods_install_python_script(republish-hyq-joints python/republish_joints.py)