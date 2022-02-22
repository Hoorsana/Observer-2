open Beobachter.slx
set_param('Beobachter/Gain','Gain','B') 
modelworkspace1 = get_param('Beobachter','ModelWorkspace');
assignin(modelworkspace1,'B',Simulink.Parameter([0; 7.007]));
set_param('Beobachter','ParameterArgumentNames','B');
set_param('Beobachter/Gain3','Gain','C') 
modelworkspace2 = get_param('Beobachter','ModelWorkspace');
assignin(modelworkspace2,'C',Simulink.Parameter([1 0]));
set_param('Beobachter','ParameterArgumentNames','C');
set_param('Beobachter/Gain2','Gain','A') 
modelworkspace3 = get_param('Beobachter','ModelWorkspace');
assignin(modelworkspace3,'A',Simulink.Parameter([0 1; 0 0]));
set_param('Beobachter','ParameterArgumentNames','A');
set_param('Beobachter/Gain1','Gain','L') 
modelworkspace4 = get_param('Beobachter','ModelWorkspace');
assignin(modelworkspace4,'L',Simulink.Parameter([40 300]));
set_param('Beobachter','ParameterArgumentNames','L');
set_param('Beobachter/Gain4','Gain','K') 
modelworkspace5 = get_param('Beobachter','ModelWorkspace');
assignin(modelworkspace5,'K',Simulink.Parameter([0.4281 0.5708]));
set_param('Beobachter','ParameterArgumentNames','K');

