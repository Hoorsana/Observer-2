A = [0 1; 0 0] ;

B = [0; 7.007];

C = [1 0];

p_Bsoll = 10*p;

L_T = place(A',C',p_Bsoll);

L = [[L_T(1,1)];[L_T(1,2)]];

K = acker(A,B,p);

