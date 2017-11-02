rpg_base = getenv('RPG_BASE')

javaaddpath([rpg_base '/code_externals/build/share/java/lcmtypes_visualization.jar'])
checkDependencyVis('lcm')

pub = ObjectCollectionPublisher('OBJECT_COLLECTION')

nparticles = 100;
pos_list = rand(nparticles ,3);
quat_list = [ones(nparticles ,1), zeros(nparticles ,3)];

for i=1:20
  % utime_list must be unique
  utime_list =1:nparticles  ;
  utime_list = utime_list + 100000*i;
  
  pos_list = rand(nparticles ,3);
  pos_list(:,1) =  pos_list(:,1) +i*2;
  
  % by changing true to false, the collections can be updated or deleted
  pub.publish(utime_list, pos_list, quat_list, 1, '100 poses', 5, true); 
  pause(0.25)
end