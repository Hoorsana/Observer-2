open ZRM.slx
set_param('ZRM/Gain','Gain','B') 
modelworkspace1 = get_param('ZRM','ModelWorkspace');
assignin(modelworkspace1,'B',Simulink.Parameter([0; 7.007]));
set_param('ZRM','ParameterArgumentNames','B');
set_param('ZRM/Gain1','Gain','C') 
modelworkspace2 = get_param('ZRM','ModelWorkspace');
assignin(modelworkspace2,'C',Simulink.Parameter([1 0]));
set_param('ZRM','ParameterArgumentNames','C');
set_param('ZRM/Gain2','Gain','A') 
modelworkspace3 = get_param('ZRM','ModelWorkspace');
assignin(modelworkspace3,'A',Simulink.Parameter([0 1; 0 0]));
set_param('ZRM','ParameterArgumentNames','A');
set_param('ZRM/Integrator','InitialCondition','x0') 
modelworkspace4 = get_param('ZRM','ModelWorkspace');
assignin(modelworkspace4,'B',Simulink.Parameter(0.3));
set_param('ZRM','ParameterArgumentNames','B');