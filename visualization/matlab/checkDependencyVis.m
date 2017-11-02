function ok = checkDependencyTest(dep,command)
% Drake code which depends on an external library or program should
% check that dependency by calling this function.
%   example:
%     checkDependency('snopt')
% or
%     if (~checkDependency('snopt')) error('my error'); end
%
% @param dep the name of the dependency to check
% @param command can be 'disable', 'enable'
%  % todo: consider supporting a minimum_version

persistent conf;

ldep = lower(dep);
conf_var = [ldep,'_enabled'];

if (nargin>1)
  if strcmp(command,'disable')
    conf.(conf_var) = false;
    return;
  elseif strcmp(command,'enable')
    conf.(conf_var) = [];
  end
end

already_checked = isfield(conf,conf_var) && ~isempty(conf.(conf_var));
if already_checked
  ok = conf.(conf_var);
else % then try to evaluate the dependency now...
  switch(ldep)

    case 'lcm'
      conf.lcm_enabled = logical(exist('lcm.lcm.LCM','class'));
      if (~conf.lcm_enabled)
        lcm_java_classpath = getCMakeParamVis('lcm_java_classpath');
        if ~isempty(lcm_java_classpath)
          javaaddpathProtectGlobals(lcm_java_classpath);
          disp(' Added the lcm jar to your javaclasspath (found via cmake)');
          conf.lcm_enabled = logical(exist('lcm.lcm.LCM','class'));
        end

        if (~conf.lcm_enabled)
          [retval,cp] = system(['export PKG_CONFIG_PATH=$PKG_CONFIG_PATH:',fullfile(getCMakeParamVis('CMAKE_INSTALL_PREFIX'),'lib','pkgconfig'),' && pkg-config --variable=classpath lcm-java']);
          if (retval==0 && ~isempty(cp))
            disp(' Added the lcm jar to your javaclasspath (found via pkg-config)');
            %javaaddpathProtectGlobals(strtrim(cp));
            javaaddpath(strtrim(cp));
          end

          conf.lcm_enabled = logical(exist('lcm.lcm.LCM','class'));
        end

        if (conf.lcm_enabled)
          [retval,info] = systemWCmakeEnvVis(fullfile(getDrakePathVis(),'util','check_multicast_is_loopback.sh'));
          if (retval)
            info = strrep(info,'ERROR: ','');
            info = strrep(info,'./',[getDrakePathVis,'/util/']);
            warning('Drake:BroadcastingLCM','Currently all of your LCM traffic will be broadcast to the network, because:\n%s',info);
          end
        elseif nargout<1
          disp(' ');
          disp(' LCM not found.  LCM support will be disabled.');
          disp(' To re-enable, add lcm-###.jar to your matlab classpath');
          disp(' (e.g., by putting javaaddpath(''/usr/local/share/java/lcm-0.9.2.jar'') into your startup.m .');
          disp(' ');
        end
      end


    otherwise

      % todo: call ver(dep) here?
      % and/or addpath_dep?

      error(['Drake:UnknownDependency:',dep],['Don''t know how to add dependency: ', dep]);
  end

  ok = conf.(conf_var);
end

if (nargout<1 && ~ok)
  error(['Drake:MissingDependency:',dep],['Cannot find required dependency: ',dep]);
end

end