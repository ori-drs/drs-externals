classdef ObjectCollectionPublisher
    properties
        lc;
        channel;
    end
    methods
        function obj = ObjectCollectionPublisher(channel)
            obj.channel = channel;
            obj.lc = lcm.lcm.LCM.getSingleton();
        end
        function publish(obj,utime_list, pos_list, quat_list, id, name, type, reset)
            % TODO: add better type checking
            % quat_list is assumed to be wxyz ordering
            % id - a unique number for the collection
            % name - the name you want collection to be given in viewer
            % type - 5 means 3d axis. 4 means 3d triangle
            
            nobjects = size(utime_list(:),1);
            objects = [];
            for i=1:nobjects
                o = vs.object_t();
                o.id = utime_list(i);
                o.x = pos_list(i,1);
                o.y = pos_list(i,2);
                o.z = pos_list(i,3);
                
                o.qw = quat_list(i,1);
                o.qx = quat_list(i,2);
                o.qy = quat_list(i,3);
                o.qz = quat_list(i,4);
                objects = [objects,o];
            end
            
            oc = vs.object_collection_t();
            oc.objects = objects;
            oc.nobjects = size(objects,1);
            
            oc.name = name;
            oc.id = id;
            oc.type = type;
            oc.reset = reset;
            obj.lc.publish(obj.channel,oc);
        end
    end % end methods
end
