% Beispiel Kapitel 2.3 Ball and Beam
% Mechanische Systeme - Rotation
% mit Reglerentwurf
%% Systembeschreibung
% Eingangsgröße: Stellwinkel alpha [°]
% Ausgangsgröße: Weg x(t) [m]
% Parameter
g = 9.81; %kg m/s^2 Gravitationskonstante
% Anfangsbedingungen
x0 = 0.3; %m Anfangsauslenkung der Kugel
dx0 = 0; %m/s Anfangsgeschwindigkeit der Kugel
%% Reglerentwurf
K_R = 0.5; % Verstärkungsfaktor
T_D = 1; % Zeitkonstante des Differentialzweiges
T_1 = 0.1; % Zeitverzögerung (Realisierbarkeit des Reglers)
%New Version


