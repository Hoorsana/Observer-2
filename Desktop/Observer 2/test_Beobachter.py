from __future__ import annotations

import pytest

from pylab.core import timeseries
from pylab.core import loader
from pylab.core import testing
from pylab.simulink import simulink

from pylab.simulink import _engine

import scipy
import matplotlib.pylab as plt
from scipy.interpolate import InterpolatedUnivariateSpline
import scipy.integrate
import numpy
import numpy as np
from numpy import trapz
from scipy import integrate
from collections import Counter
from collections import defaultdict

_engine.import_matlab_engine("R2021b")


def test_experiment():
    info = loader.load_test("test.yml")
    details = simulink.load_details("matlab_detail.yml")
    prelude = details.prelude
    ps = [
        _engine.to_textbox([[-1, -3]]),
        _engine.to_textbox([[-3, -9]]),
        _engine.to_textbox([[-1, -15]]),
    ]
    Ueberschwing_Alpha = []
    Ueberschwing_X = []
    Schwing_Alpha = []
    Schwing_X = []
    E_Alpha = []
    Vorzeichen_A = []
    Vorzeichen_X = []
    Zero_Estimation_A = []
    Zero_Estimation_X = []
    E_X = []
    Z1 = []
    Z2 = []
    Konvergenz_Alpha = []
    Konvergenz_X = []
    for p in ps:
        details.prelude = f"p = {p};\n" + prelude
        experiment = simulink.create(info, details)
        report = experiment.execute()
        if report.failed:
            raise AssertionError(report.what)
                                                             # TODO Alpha
        result = report.results["ZRM.Alpha"]
        alpha = result.pretty_string()
        alpha_V = result.values
        alpha_T = result.time
                                                         # TODO Schwingweite Alpha
        Ueberschwing1 = max(alpha_V)
        Schwingweite1 = max(result.values) + abs(min(result.values))
        Ueberschwing_Alpha.append(Ueberschwing1)
        Schwing_Alpha.append(Schwingweite1)
                                                         # TODO Energie von Alpha
        f_Alpha = InterpolatedUnivariateSpline(alpha_T, alpha_V, k=1)
        Energie_Alpha = scipy.integrate.quad_vec(lambda t: np.absolute(f_Alpha(t)), 0, alpha_T[-1])
        E_Alpha.append(Energie_Alpha)
                                                       # TODO Anzahl der Nullstellen
        z1 = timeseries.zero_crossings(result, 1e-9)
        Z1.append(z1)
                                                     # TODO Abschaetzung der Nullstellen
        asign = np.sign(alpha_V)
        signchange = ((np.roll(asign, 1) - asign) != 0).astype(int)
        A1 = signchange
        V1 = [np.where(A1 == 1)]
        Vorzeichen_A.append(V1)
                                                         # TODO Geschwindigkeit
        Konvergenz_a = timeseries.converges_to(result, 0.0, 1e-8)
        Konvergenz_Alpha.append(Konvergenz_a)
                                                             # TODO X_Ist
        result1 = report.results["ZRM.Y"]
        x_Ist = result1.pretty_string()
        x_V = result1.values
        x_T = result1.time
                                                       # TODO Schwingweite X_Ist
        Ueberschwing2 = max(result1.values)
        Schwingweite2 = max(result1.values) + abs(min(result1.values))
        Ueberschwing_X.append(Ueberschwing2)
        Schwing_X.append(Schwingweite2)
                                                       # TODO Energie von X_Ist
        f_X = InterpolatedUnivariateSpline(x_T, x_V, k=1)
        Energie_X = scipy.integrate.quad_vec(lambda t: np.absolute(f_X(t)), 0, x_T[-1])
        E_X.append(Energie_X)
                                                       # TODO Zero Crossing
        z2 = timeseries.zero_crossings(result1, 1e-9)
        Z2.append(z2)
                                                  # TODO Abschätzung der Nullstellen
        asign = np.sign(x_V)
        signchange = ((np.roll(asign, 1) - asign) != 0).astype(int)
        A2 = signchange
        V2 = [np.where(A2 == 1)]
        Vorzeichen_X.append(V2)
                                                     # TODO Geschwindigkeit
        Konvergenz_x = timeseries.converges_to(result1, 0.0, 1e-7)
        Konvergenz_X.append(Konvergenz_x)

    print("Zero Crossings_Alpha:", Z1)
    print("Zero Crossings_Xist:", Z2)
    print("Uberschwingweite von Alpha:", Ueberschwing_Alpha)
    print("Uberschwingweite von x_Ist:", Ueberschwing_X)
    print("Schwingweite von Alpha:", Schwing_Alpha)
    print("Schwingweite von x_Ist:", Schwing_X)
    print("Energei von Alpha:", E_Alpha)
    print("Energei von x_Ist:", E_X)
    print("Zeitpunkt der Konvergenz von Alpha:", Konvergenz_Alpha)
    print("Zeitpunkt der Konvergenz von X:", Konvergenz_X)
    print("Abschätyung der Nullstellen X:", Vorzeichen_A)
    print("Abschaetzung der Nullstellen X:", Vorzeichen_X)
    K1 = ps[Ueberschwing_Alpha.index(min(Ueberschwing_Alpha))]
    K2 = ps[Ueberschwing_X.index(min(Ueberschwing_X))]
    K3 = ps[E_Alpha.index(min(E_Alpha))]
    K4 = ps[E_X.index(min(E_X))]
    K5 = ps[Z1.index(min(Z1))]
    K6 = ps[Z2.index(min(Z2))]
    P_list = [K1, K2, K3, K4, K5, K6]
    print(P_list)