#!/usr/bin/python
import os,sys
home_dir =os.getenv("HOME")
#print home_dir
sys.path.append(home_dir + "/drc/software/build/lib/python2.7/site-packages")
sys.path.append(home_dir + "/drc/software/build/lib/python2.7/dist-packages")

import lcm
from multisense.command_t import command_t
import time

def timestamp_now (): return int (time.time () * 1000000)
# sleep for a few seconds to give driver or simulator some time to start
time.sleep(5)

msg = command_t()
msg.utime = timestamp_now()
# Indoor testing without gain control on 46:
msg.fps = 15
msg.gain = 2
msg.exposure_us = 40000
msg.rpm = 15
msg.agc = True
msg.leds_flash = False
msg.leds_duty_cycle = 10.0

lc = lcm.LCM()
lc.publish("MULTISENSE_COMMAND", msg.encode())
print "Publishing Multisense command to spin at 15rpm and set the camera FTS to 15."
