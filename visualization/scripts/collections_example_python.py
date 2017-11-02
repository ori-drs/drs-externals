import os,sys
import lcm
import time
import numpy as np
import time

from vs.object_t import object_t
from vs.object_collection_t import object_collection_t


lc = lcm.LCM()


for counter in np.arange(0,100): # for each time stamp
  print counter

  col = object_collection_t()
  col.id = 0; # unique id
  col.name = "test";
  col.type = 5;
  col.reset = True # reset with every new publish  **** TRY CHANGIN ME ***


  for i in range(0,10): # for each particle

    obj = object_t()
    obj.id = counter + 100*i # unique within this message

    obj.x= float(counter)/10
    obj.y=i
    obj.z=0
    obj.qw=1
    obj.qx=0
    obj.qy=0
    obj.qz=0
    col.objects.append(obj)



  col.nobjects = len(col.objects)
  lc.publish("OBJECT_COLLECTION",col.encode())  
  time.sleep( 0.2 )