# -*- coding: utf-8 -*-
'''Chemical Engineering Design Library (ChEDL). Utilities for process modeling.
Copyright (C) 2016, Caleb Bell <Caleb.Andrew.Bell@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.'''

from __future__ import division

__all__ = ['K_value', 'Wilson_K_value', 'flash_wilson', 'flash_Tb_Tc_Pc',
           'Rachford_Rice_flash_error', 
           'Rachford_Rice_solution',
           'Li_Johns_Ahmadi_solution', 'flash_inner_loop', 'NRTL', 'Wilson',
           'UNIQUAC', 'flash', 'dew_at_T',
           'bubble_at_T', 'identify_phase', 'mixture_phase_methods',
           'identify_phase_mixture', 'Pbubble_mixture', 'bubble_at_P',
           'Pdew_mixture']

from fluids.numerics import brenth, IS_PYPY, one_epsilon_larger, one_epsilon_smaller
from fluids.numerics import brenth, py_newton as newton # Always use this method for advanced features
from thermo.utils import exp, log
from thermo.utils import none_and_length_check
from thermo.utils import R
import numpy as np




def K_value(P=None, Psat=None, phi_l=None, phi_g=None, gamma=None, Poynting=1):
    r'''Calculates the equilibrium K-value assuming Raoult's law,
    or an equation of state model, or an activity coefficient model,
    or a combined equation of state-activity model.

    The calculation procedure will use the most advanced approach with the
    provided inputs:

        * If `P`, `Psat`, `phi_l`, `phi_g`, and `gamma` are provided, use the
          combined approach.
        * If `P`, `Psat`, and `gamma` are provided, use the modified Raoult's
          law.
        * If `phi_l` and `phi_g` are provided, use the EOS only method.
        * If `P` and `Psat` are provided, use Raoult's law.

    Definitions:

    .. math::
        K_i=\frac{y_i}{x_i}

    Raoult's law:

    .. math::
        K_i = \frac{P_{i}^{sat}}{P}

    Activity coefficient, no EOS (modified Raoult's law):

    .. math::
        K_i = \frac{\gamma_i P_{i}^{sat}}{P}

    Equation of state only:

    .. math::
        K_i = \frac{\phi_i^l}{\phi_i^v} = \frac{f_i^l}{f_i^v}

    Combined approach (liquid reference fugacity coefficient is normally
    calculated the saturation pressure for it as a pure species; vapor fugacity
    coefficient calculated normally):

    .. math::
        K_i = \frac{\gamma_i P_i^{sat} \phi_i^{l,ref}}{\phi_i^v P}

    Combined approach, with Poynting Correction Factor (liquid molar volume in
    the integral is for i as a pure species only):

    .. math::
        K_i = \frac{\gamma_i P_i^{sat} \phi_i^{l, ref} \exp\left[\frac{
        \int_{P_i^{sat}}^P V_i^l dP}{RT}\right]}{\phi_i^v P}

    Parameters
    ----------
    P : float
        System pressure, optional
    Psat : float
        Vapor pressure of species i, [Pa]
    phi_l : float
        Fugacity coefficient of species i in the liquid phase, either
        at the system conditions (EOS-only case) or at the saturation pressure
        of species i as a pure species (reference condition for the combined
        approach), optional [-]
    phi_g : float
        Fugacity coefficient of species i in the vapor phase at the system
        conditions, optional [-]
    gamma : float
        Activity coefficient of species i in the liquid phase, optional [-]
    Poynting : float
        Poynting correction factor, optional [-]

    Returns
    -------
    K : float
        Equilibrium K value of component i, calculated with an approach
        depending on the provided inputs [-]

    Notes
    -----
    The Poynting correction factor is normally simplified as follows, due to
    a liquid's low pressure dependency:

    .. math::
        K_i = \frac{\gamma_i P_i^{sat} \phi_i^{l, ref} \exp\left[\frac{V_l
        (P-P_i^{sat})}{RT}\right]}{\phi_i^v P}

    Examples
    --------
    Raoult's law:

    >>> K_value(101325, 3000.)
    0.029607698001480384

    Modified Raoult's law:

    >>> K_value(P=101325, Psat=3000, gamma=0.9)
    0.026646928201332347

    EOS-only approach:

    >>> K_value(phi_l=1.6356, phi_g=0.88427)
    1.8496613025433408

    Gamma-phi combined approach:

    >>> K_value(P=1E6, Psat=1938800, phi_l=1.4356, phi_g=0.88427, gamma=0.92)
    2.8958055544121137

    Gamma-phi combined approach with a Poynting factor:

    >>> K_value(P=1E6, Psat=1938800, phi_l=1.4356, phi_g=0.88427, gamma=0.92,
    ... Poynting=0.999)
    2.8929097488577016

    References
    ----------
    .. [1] Gmehling, Jurgen, Barbel Kolbe, Michael Kleiber, and Jurgen Rarey.
       Chemical Thermodynamics for Process Simulation. 1st edition. Weinheim:
       Wiley-VCH, 2012.
    .. [2] Skogestad, Sigurd. Chemical and Energy Process Engineering. 1st
       edition. Boca Raton, FL: CRC Press, 2008.
    '''
    try:
        if gamma:
            if phi_l:
                return gamma*Psat*phi_l*Poynting/(phi_g*P)
            return gamma*Psat*Poynting/P
        elif phi_l:
            return phi_l/phi_g
        return Psat/P
    except TypeError:
        raise Exception('Input must consist of one set from (P, Psat, phi_l, \
phi_g, gamma), (P, Psat, gamma), (phi_l, phi_g), (P, Psat)')


def Wilson_K_value(T, P, Tc, Pc, omega):
    r'''Calculates the equilibrium K-value for a component using Wilson's
    heuristic mode. This is very useful for initialization of stability tests
    and flashes.
    
    .. math::
        K_i = \frac{P_c}{P} \exp\left(5.37(1+\omega)\left[1 - \frac{T_c}{T}
        \right]\right)
        
    Parameters
    ----------
    T : float
        System temperature, [K]
    P : float
        System pressure, [Pa]
    Tc : float
        Critical temperature of fluid [K]
    Pc : float
        Critical pressure of fluid [Pa]
    omega : float
        Acentric factor for fluid, [-]

    Returns
    -------
    K : float
        Equilibrium K value of component, calculated via the Wilson heuristic
        [-]

    Notes
    -----
    There has been little literature exploration of other formlulas for the
    same purpose. This model may be useful even for activity coefficient 
    models.
    
    Note the K-values are independent of composition; the correlation is
    applicable up to 3.5 MPa.

    Examples
    --------
    Ethane at 270 K and 76 bar:
        
    >>> Wilson_K_value(270.0, 7600000.0, 305.4, 4880000.0, 0.098)
    0.2963932297479371
    
    References
    ----------
    .. [1] Wilson, Grant M. "A Modified Redlich-Kwong Equation of State, 
       Application to General Physical Data Calculations." In 65th National 
       AIChE Meeting, Cleveland, OH, 1969.
    '''
    return Pc/P*exp((5.37*(1.0 + omega)*(1.0 - Tc/T)))


def flash_wilson(zs, Tcs, Pcs, omegas, T=None, P=None, VF=None):
    r'''PVT flash model using Wilson's equation - useful for obtaining initial
    guesses for more rigorous models, or it can be used as its own model.
    Capable of solving with two of `T`, `P`, and `VF` for the other one;
    that results in three solve modes, but for `VF=1` and `VF=0`, there are 
    additional solvers; for a total of seven solvers implemented.
    
    This model uses `flash_inner_loop` to solve the Rachford-Rice problem.
    
    .. math::
        K_i = \frac{P_c}{P} \exp\left(5.37(1+\omega)\left[1 - \frac{T_c}{T}
        \right]\right)
    
    Parameters
    ----------
    zs : list[float]
        Mole fractions of the phase being flashed, [-]
    Tcs : list[float]
        Critical temperatures of all species, [K]
    Pcs : list[float]
        Critical pressures of all species, [Pa]
    omegas : list[float]
        Acentric factors of all species, [-]
    T : float, optional
        Temperature, [K]
    P : float, optional
        Pressure, [Pa]
    VF : float, optional
        Molar vapor fraction, [-]
        
    Returns
    -------
    T : float
        Temperature, [K]
    P : float
        Pressure, [Pa]
    VF : float
        Molar vapor fraction, [-]
    xs : list[float]
        Mole fractions of liquid phase, [-]
    ys : list[float]
        Mole fractions of vapor phase, [-]
    
    Notes
    -----
    For the cases where `VF` is 1 or 0 and T is known, an explicit solution is
    used. For the same cases where `P` and `VF` are known, there is no explicit
    solution available.
    
    There is an internal `Tmax` parameter, set to 50000 K; which, in the event
    of convergence of the Secant method, is used as a bounded for a bounded 
    solver. It is used in the PVF solvers. This typically allows pressures
    up to 2 GPa to be converged to. However, for narrow-boiling mixtures, the
    PVF failure may occur at much lower pressures.

    Examples
    --------
    >>> Tcs = [305.322, 540.13]
    >>> Pcs = [4872200.0, 2736000.0]
    >>> omegas = [0.099, 0.349]
    >>> zs = [0.4, 0.6]
    >>> flash_wilson(zs=zs, Tcs=Tcs, Pcs=Pcs, omegas=omegas, T=300, P=1e5)
    (300, 100000.0, 0.42219453293637355, [0.020938815080034565, 0.9790611849199654], [0.9187741856225791, 0.08122581437742094])
    '''
    T_MAX = 50000
    N = len(zs)
    cmps = range(N)
    # Assume T and P to begin with
    if T is not None and P is not None:
        Ks = [Wilson_K_value(T, P, Tc=Tcs[i], Pc=Pcs[i], omega=omegas[i]) for i in cmps]
        return (T, P) + flash_inner_loop(zs=zs, Ks=Ks)
    if T is not None and VF == 0:
        P_bubble = 0.0
        for i in cmps:
            P_bubble += zs[i]*Pcs[i]*exp((5.37*(1.0 + omegas[i])*(1.0 - Tcs[i]/T)))
        return flash_wilson(zs, Tcs, Pcs, omegas, T=T, P=P_bubble)
    if T is not None and VF == 1:
        P_dew = 0.
        for i in cmps:
            P_dew += zs[i]/(Pcs[i]*exp((5.37*(1.0 + omegas[i])*(1.0 - Tcs[i]/T))))
        P_dew = 1./P_dew
        return flash_wilson(zs, Tcs, Pcs, omegas, T=T, P=P_dew)
    elif T is not None and VF is not None:
        # Solve for in the middle of Pdew
        P_low = flash_wilson(zs, Tcs, Pcs, omegas, T=T, VF=1)[1]
        P_high = flash_wilson(zs, Tcs, Pcs, omegas, T=T, VF=0)[1]
        info = []
        def err(P):
            T_calc, P_calc, VF_calc, xs, ys = flash_wilson(zs, Tcs, Pcs, omegas, T=T, P=P)
            info[:] = T_calc, P_calc, VF_calc, xs, ys
            return VF_calc - VF
        P = brenth(err, P_low, P_high)
        return tuple(info)
    elif P is not None and VF == 1:
        def to_solve(T_guess):
            # Avoid some nasty unpleasantness in newton
            T_guess = abs(T_guess)
            P_dew = 0.
            for i in range(len(zs)):
                P_dew += zs[i]/(Pcs[i]*exp((5.37*(1.0 + omegas[i])*(1.0 - Tcs[i]/T_guess))))
            P_dew = 1./P_dew
#            print(P_dew - P, T_guess)
            return P_dew - P
        # 2/3 average critical point
        T_guess = sum([.666*Tcs[i]*zs[i] for i in cmps])
        try:
            T_dew = abs(newton(to_solve, T_guess, maxiter=50))
        except:
            T_dew = None
        if T_dew is None or T_dew > T_MAX*5.0: 
            # Went insanely high T, bound it with brenth
            T_low_guess = sum([.1*Tcs[i]*zs[i] for i in cmps])
            try:
                T_dew = brenth(to_solve, T_MAX, T_low_guess)
            except ValueError:
                raise Exception("Bisecting solver could not find a solution between %g K and %g K" %(T_MAX, T_low_guess))
        return flash_wilson(zs, Tcs, Pcs, omegas, T=T_dew, P=P)
    elif P is not None and VF == 0:
        def to_solve(T_guess):
            T_guess = abs(T_guess)
            P_bubble = 0.0
            for i in cmps:
                P_bubble += zs[i]*Pcs[i]*exp((5.37*(1.0 + omegas[i])*(1.0 - Tcs[i]/T_guess)))
            return P_bubble - P
        # 2/3 average critical point
        T_guess = sum([.55*Tcs[i]*zs[i] for i in cmps])
        T_bubble = abs(newton(to_solve, T_guess))
        if T_bubble > T_MAX*5.0: 
            # Went insanely high T, bound it with brenth
            T_low_guess = sum([.1*Tcs[i]*zs[i] for i in cmps])
            try:
                T_bubble = brenth(to_solve, T_MAX, T_low_guess)
            except ValueError:
                raise Exception("Bisecting solver could not find a solution between %g K and %g K" %(T_MAX, T_low_guess))
            
        return flash_wilson(zs, Tcs, Pcs, omegas, T=T_bubble, P=P)
    elif P is not None and VF is not None:
        # Solve for in the middle of Pdew
        T_low = flash_wilson(zs, Tcs, Pcs, omegas, P=P, VF=1)[0]
        T_high = flash_wilson(zs, Tcs, Pcs, omegas, P=P, VF=0)[0]
#        print(T_low, T_high)
        info = []
        def err(T):
            T_calc, P_calc, VF_calc, xs, ys = flash_wilson(zs, Tcs, Pcs, omegas, T=T, P=P)
#            if abs(VF_calc) > 100: # Did not work at all
#                VF_calc = abs(VF_calc)
            info[:] = T_calc, P_calc, VF_calc, xs, ys
#            print(T, VF_calc - VF)
            return VF_calc - VF
        # Nasty function for tolerance; the default works and is good enough, could remove some
        # iterations in the fuure
        P = brenth(err, T_low, T_high, xtol=1e-14)
        return tuple(info)
    else:
        raise ValueError("Provide two of P, T, and VF")


def flash_Tb_Tc_Pc(zs, Tbs, Tcs, Pcs, T=None, P=None, VF=None):
    r'''PVT flash model using a model published in [1]_, which provides a PT
    surface  using only each compound's boiling temperature and critical 
    temperature and pressure. This is useful for obtaining initial
    guesses for more rigorous models, or it can be used as its own model.
    Capable of solving with two of `T`, `P`, and `VF` for the other one;
    that results in three solve modes, but for `VF=1` and `VF=0`, there are 
    additional solvers; for a total of seven solvers implemented.
    
    This model uses `flash_inner_loop` to solve the Rachford-Rice problem.
    
    .. math::
        K_i = \frac{P_{c,i}^{\left(\frac{1}{T} - \frac{1}{T_{b,i}} \right) / 
        \left(\frac{1}{T_{c,i}} - \frac{1}{T_{b,i}} \right)}}{P}
        
    Parameters
    ----------
    zs : list[float]
        Mole fractions of the phase being flashed, [-]
    Tbs : list[float]
        Boiling temperatures of all species, [K]
    Tcs : list[float]
        Critical temperatures of all species, [K]
    Pcs : list[float]
        Critical pressures of all species, [Pa]
    T : float, optional
        Temperature, [K]
    P : float, optional
        Pressure, [Pa]
    VF : float, optional
        Molar vapor fraction, [-]
        
    Returns
    -------
    T : float
        Temperature, [K]
    P : float
        Pressure, [Pa]
    VF : float
        Molar vapor fraction, [-]
    xs : list[float]
        Mole fractions of liquid phase, [-]
    ys : list[float]
        Mole fractions of vapor phase, [-]
        
    Notes
    -----
    For the cases where `VF` is 1 or 0 and T is known, an explicit solution is
    used. For the same cases where `P` and `VF` are known, there is no explicit
    solution available.
    
    There is an internal `Tmax` parameter, set to 50000 K; which, in the event
    of convergence of the Secant method, is used as a bounded for a bounded 
    solver. It is used in the PVF solvers. This typically allows pressures
    up to 2 MPa to be converged to. Failures may still occur for other 
    conditions.

    Examples
    --------
    >>> Tcs = [305.322, 540.13]
    >>> Pcs = [4872200.0, 2736000.0]
    >>> Tbs = [184.55, 371.53]
    >>> zs = [0.4, 0.6]
    >>> flash_Tb_Tc_Pc(zs=zs, Tcs=Tcs, Pcs=Pcs, Tbs=Tbs, T=300, P=1e5)
    (300, 100000.0, 0.3807040748145384, [0.031157843036568357, 0.9688421569634317], [0.9999999998827085, 1.1729141887515062e-10])
    '''
    T_MAX = 50000
    N = len(zs)
    cmps = range(N)
    # Assume T and P to begin with
    if T is not None and P is not None:
        Ks = [Pcs[i]**((1.0/T - 1.0/Tbs[i])/(1.0/Tcs[i] - 1.0/Tbs[i]))/P for i in cmps]
        return (T, P) + flash_inner_loop(zs=zs, Ks=Ks)
    
    if T is not None and VF == 0:
        P_bubble = 0.0
        for i in cmps:
            P_bubble += zs[i]*Pcs[i]**((1.0/T - 1.0/Tbs[i])/(1.0/Tcs[i] - 1.0/Tbs[i]))
        return flash_Tb_Tc_Pc(zs, Tbs, Tcs, Pcs, T=T, P=P_bubble)
    if T is not None and VF == 1:
        # Checked to be working vs. PT implementation.
        P_dew = 0.
        for i in cmps:
            P_dew += zs[i]/( Pcs[i]**((1.0/T - 1.0/Tbs[i])/(1.0/Tcs[i] - 1.0/Tbs[i])) )
        P_dew = 1./P_dew
        return flash_Tb_Tc_Pc(zs, Tbs, Tcs, Pcs, T=T, P=P_dew)
    elif T is not None and VF is not None:
        # Solve for in the middle of Pdew
        P_low = flash_Tb_Tc_Pc(zs, Tbs, Tcs, Pcs, T=T, VF=1)[1]
        P_high = flash_Tb_Tc_Pc(zs, Tbs, Tcs, Pcs, T=T, VF=0)[1]
        info = []
        def err(P):
            T_calc, P_calc, VF_calc, xs, ys = flash_Tb_Tc_Pc(zs, Tbs, Tcs, Pcs, T=T, P=P)
            info[:] = T_calc, P_calc, VF_calc, xs, ys
            return VF_calc - VF
        P = brenth(err, P_low, P_high)
        return tuple(info)

    elif P is not None and VF == 1:
        def to_solve(T_guess):
            T_guess = abs(T_guess)
            P_dew = 0.
            for i in range(len(zs)):
                P_dew += zs[i]/( Pcs[i]**((1.0/T_guess - 1.0/Tbs[i])/(1.0/Tcs[i] - 1.0/Tbs[i])) )
            P_dew = 1./P_dew
            return P_dew - P

        Tc_pseudo = sum([Tcs[i]*zs[i] for i in cmps])
        T_guess = 0.666*Tc_pseudo
        try:
            T_dew = abs(newton(to_solve, T_guess, maxiter=50)) # , high=Tc_pseudo*3
        except:
            T_dew = None
        if T_dew is None or T_dew > T_MAX*5.0: 
            # Went insanely high T, bound it with brenth
            T_low_guess = sum([.1*Tcs[i]*zs[i] for i in cmps])
            try:
                T_dew = brenth(to_solve, T_MAX, T_low_guess)
            except ValueError:
                raise Exception("Bisecting solver could not find a solution between %g K and %g K" %(T_MAX, T_low_guess))
        return flash_Tb_Tc_Pc(zs, Tbs, Tcs, Pcs, T=T_dew, P=P)
    
    elif P is not None and VF == 0:
        def to_solve(T_guess):
            T_guess = abs(T_guess)
            P_bubble = 0.0
            for i in cmps:
                P_bubble += zs[i]*Pcs[i]**((1.0/T_guess - 1.0/Tbs[i])/(1.0/Tcs[i] - 1.0/Tbs[i]))
#            print(T_guess, P_bubble - P)
            return P_bubble - P
        # 2/3 average critical point
        Tc_pseudo = sum([Tcs[i]*zs[i] for i in cmps])
        T_guess = 0.55*Tc_pseudo
        try:
            T_bubble = abs(newton(to_solve, T_guess)) # , high=Tc_pseudo*4
        except:
            T_bubble = None
        if T_bubble is None or T_bubble > T_MAX*5.0: 
            # Went insanely high T (or could not converge because went too high), bound it with brenth
            T_low_guess = 0.1*Tc_pseudo
            try:
                T_bubble = brenth(to_solve, T_MAX, T_low_guess)
            except ValueError:
                raise Exception("Bisecting solver could not find a solution between %g K and %g K" %(T_MAX, T_low_guess))
            
        return flash_Tb_Tc_Pc(zs, Tbs, Tcs, Pcs, T=T_bubble, P=P)
    elif P is not None and VF is not None:
        T_low = flash_Tb_Tc_Pc(zs, Tbs, Tcs, Pcs, P=P, VF=1)[0]
        T_high = flash_Tb_Tc_Pc(zs, Tbs, Tcs, Pcs, P=P, VF=0)[0]
        info = []
        def err(T):
            T_calc, P_calc, VF_calc, xs, ys = flash_Tb_Tc_Pc(zs, Tbs, Tcs, Pcs, T=T, P=P)
            info[:] = T_calc, P_calc, VF_calc, xs, ys
            return VF_calc - VF
        P = brenth(err, T_low, T_high)
        return tuple(info)
    else:
        raise ValueError("Provide two of P, T, and VF")


### Solutions using a existing algorithms
def Rachford_Rice_flash_error(V_over_F, zs, Ks):
    r'''Calculates the objective function of the Rachford-Rice flash equation.
    This function should be called by a solver seeking a solution to a flash
    calculation. The unknown variable is `V_over_F`, for which a solution
    must be between 0 and 1.

    .. math::
        \sum_i \frac{z_i(K_i-1)}{1 + \frac{V}{F}(K_i-1)} = 0

    Parameters
    ----------
    V_over_F : float
        Vapor fraction guess [-]
    zs : list[float]
        Overall mole fractions of all species, [-]
    Ks : list[float]
        Equilibrium K-values, [-]

    Returns
    -------
    error : float
        Deviation between the objective function at the correct V_over_F
        and the attempted V_over_F, [-]

    Notes
    -----
    The derivation is as follows:

    .. math::
        F z_i = L x_i + V y_i

        x_i = \frac{z_i}{1 + \frac{V}{F}(K_i-1)}

        \sum_i y_i = \sum_i K_i x_i = 1

        \sum_i(y_i - x_i)=0

        \sum_i \frac{z_i(K_i-1)}{1 + \frac{V}{F}(K_i-1)} = 0

    Examples
    --------
    >>> Rachford_Rice_flash_error(0.5, zs=[0.5, 0.3, 0.2],
    ... Ks=[1.685, 0.742, 0.532])
    0.04406445591174976

    References
    ----------
    .. [1] Rachford, H. H. Jr, and J. D. Rice. "Procedure for Use of Electronic
       Digital Computers in Calculating Flash Vaporization Hydrocarbon
       Equilibrium." Journal of Petroleum Technology 4, no. 10 (October 1,
       1952): 19-3. doi:10.2118/952327-G.
    '''
    return sum([zi*(Ki-1.)/(1.+V_over_F*(Ki-1.)) for Ki, zi in zip(Ks, zs)])


def Rachford_Rice_solution(zs, Ks, fprime=False, fprime2=False):
    r'''Solves the objective function of the Rachford-Rice flash equation.
    Uses the method proposed in [2]_ to obtain an initial guess.

    .. math::
        \sum_i \frac{z_i(K_i-1)}{1 + \frac{V}{F}(K_i-1)} = 0

    Parameters
    ----------
    zs : list[float]
        Overall mole fractions of all species, [-]
    Ks : list[float]
        Equilibrium K-values, [-]
    fprime : bool, optional
        Whether or not to use the first derivative of the objective function
        in the solver (Newton-Raphson is used) or not (secant is used), [-]
    fprime2 : bool, optional
        Whether or not to use the second derivative of the objective function
        in the solver (parabolic Halley’s method is used if True) or not, [-]
        
    Returns
    -------
    V_over_F : float
        Vapor fraction solution [-]
    xs : list[float]
        Mole fractions of each species in the liquid phase, [-]
    ys : list[float]
        Mole fractions of each species in the vapor phase, [-]

    Notes
    -----
    The initial guess is the average of the following, as described in [2]_.

    .. math::
        \left(\frac{V}{F}\right)_{min} = \frac{(K_{max}-K_{min})z_{of\;K_{max}}
        - (1-K_{min})}{(1-K_{min})(K_{max}-1)}

        \left(\frac{V}{F}\right)_{max} = \frac{1}{1-K_{min}}

    Another algorithm for determining the range of the correct solution is
    given in [3]_; [2]_ provides a narrower range however. For both cases,
    each guess should be limited to be between 0 and 1 as they are often
    negative or larger than 1.

    .. math::
        \left(\frac{V}{F}\right)_{min} = \frac{1}{1-K_{max}}

        \left(\frac{V}{F}\right)_{max} = \frac{1}{1-K_{min}}

    If the `newton` method does not converge, a bisection method (brenth) is
    used instead. However, it is somewhat slower, especially as newton will
    attempt 50 iterations before giving up.
    
    In all benchmarks attempted, secant method provides better performance than
    Newton-Raphson or parabolic Halley’s method. This may not be generally
    true; but it is for Python and SciPy's implementation. They are implemented
    for benchmarking purposes.
    
    The first and second derivatives are:
        
    .. math::
        \frac{d \text{ obj}}{d \frac{V}{F}} = \sum_i \frac{-z_i(K_i-1)^2}
        {(1 + \frac{V}{F}(K_i-1))^2} 
        
        \frac{d^2 \text{ obj}}{d (\frac{V}{F})^2} = \sum_i \frac{2z_i(K_i-1)^3}
        {(1 + \frac{V}{F}(K_i-1))^3} 

    Examples
    --------
    >>> Rachford_Rice_solution(zs=[0.5, 0.3, 0.2], Ks=[1.685, 0.742, 0.532])
    (0.6907302627738542, [0.3394086969663436, 0.3650560590371706, 0.2955352439964858], [0.571903654388289, 0.27087159580558057, 0.15722474980613044])

    References
    ----------
    .. [1] Rachford, H. H. Jr, and J. D. Rice. "Procedure for Use of Electronic
       Digital Computers in Calculating Flash Vaporization Hydrocarbon
       Equilibrium." Journal of Petroleum Technology 4, no. 10 (October 1,
       1952): 19-3. doi:10.2118/952327-G.
    .. [2] Li, Yinghui, Russell T. Johns, and Kaveh Ahmadi. "A Rapid and Robust
       Alternative to Rachford-Rice in Flash Calculations." Fluid Phase
       Equilibria 316 (February 25, 2012): 85-97.
       doi:10.1016/j.fluid.2011.12.005.
    .. [3] Whitson, Curtis H., and Michael L. Michelsen. "The Negative Flash."
       Fluid Phase Equilibria, Proceedings of the Fifth International
       Conference, 53 (December 1, 1989): 51-71.
       doi:10.1016/0378-3812(89)80072-X.
    '''
    Kmin = min(Ks)
    Kmax = max(Ks)
    z_of_Kmax = zs[Ks.index(Kmax)]

    V_over_F_min = ((Kmax-Kmin)*z_of_Kmax - (1.- Kmin))/((1.- Kmin)*(Kmax- 1.))
    V_over_F_max = 1./(1.-Kmin)

    V_over_F_min2 = V_over_F_min if V_over_F_min > 0.0 else 0.0
    V_over_F_max2 = V_over_F_max if V_over_F_max < 1.0 else 1.0
#    print(V_over_F_min2, V_over_F_max2)
    
    x0 = (V_over_F_min2 + V_over_F_max2)*0.5
    
    K_minus_1 = [Ki - 1.0 for Ki in Ks]
    zs_k_minus_1 = [zi*Kim1 for zi, Kim1 in zip(zs, K_minus_1)]
    
    def err(V_over_F):
#        print(V_over_F)
        return sum([num/(1. + V_over_F*Kim1) for num, Kim1 in zip(zs_k_minus_1, K_minus_1)])
    
    if fprime or fprime2:
        zs_k_minus_1_2 = [-first*Kim1 for first, Kim1 in zip(zs_k_minus_1, K_minus_1)]
        def fprime_obj(V_over_F):
            denom = [V_over_F*Kim1 + 1.0 for Kim1 in K_minus_1]
            denom2 = [d1*d1 for d1 in denom]
            return sum([num/deno for num, deno in zip(zs_k_minus_1_2, denom2)])
        
    if fprime2:
        zs_k_minus_1_3 = [-2.0*second*Kim1 for second, Kim1 in zip(zs_k_minus_1_2, K_minus_1)]
        def fprime2_obj(V_over_F):
            denom = [V_over_F*Kim1 + 1.0 for Kim1 in K_minus_1]
            denom2 = [d1*d1 for d1 in denom]
            denom3 = [d2*d1 for d1, d2 in zip(denom, denom2)]
            return sum([num/deno for num, deno in zip(zs_k_minus_1_3, denom3)])
        
    try:
        if fprime and fprime2:
            V_over_F = newton(err, x0, fprime=fprime_obj, fprime2=fprime2_obj)
        elif fprime:
            V_over_F = newton(err, x0, fprime=fprime_obj)
        else:
            V_over_F = newton(err, x0, high=V_over_F_max*one_epsilon_smaller,
                              low=V_over_F_min*one_epsilon_larger)
        
#        assert V_over_F >= V_over_F_min2
#        assert V_over_F <= V_over_F_max2
    except Exception as e:
#        print(zs, Ks, e)
        V_over_F = brenth(err, V_over_F_max*one_epsilon_smaller, V_over_F_min*one_epsilon_larger)
                
    xs = [zi/(1.+V_over_F*(Ki-1.)) for zi, Ki in zip(zs, Ks)]
    ys = [Ki*xi for xi, Ki in zip(xs, Ks)]
    return V_over_F, xs, ys


def Rachford_Rice_solution_numpy(zs, Ks):
    '''Undocumented version of Rachford_Rice_solution which works with numpy
    instead. Can be up to 15x faster for cases of 30000+ compounds;
    typically 7-10 x faster.
    '''
    zs, Ks = np.array(zs), np.array(Ks)

    Kmin = Ks.min()
    Kmax = Ks.max()
    
    z_of_Kmax = zs[Ks == Kmax][0]

    V_over_F_min = ((Kmax-Kmin)*z_of_Kmax - (1.-Kmin))/((1.-Kmin)*(Kmax-1.))
    V_over_F_max = 1./(1.-Kmin)

    V_over_F_min2 = max(0., V_over_F_min)
    V_over_F_max2 = min(1., V_over_F_max)

    x0 = (V_over_F_min2 + V_over_F_max2)*0.5
    
    K_minus_1 = Ks - 1.0
    zs_k_minus_1 = zs*K_minus_1
    def err(V_over_F):
        return float((zs_k_minus_1/(1.0 + V_over_F*K_minus_1)).sum())
    try:
        V_over_F = newton(err, x0)
    except:
        V_over_F = brenth(err, V_over_F_max*one_epsilon_smaller, V_over_F_min*one_epsilon_larger)
        
    xs = zs/(1.0 + V_over_F*K_minus_1)
    ys = Ks*xs
    return float(V_over_F), xs.tolist(), ys.tolist()


def Li_Johns_Ahmadi_solution(zs, Ks):
    r'''Solves the objective function of the Li-Johns-Ahmadi flash equation.
    Uses the method proposed in [1]_ to obtain an initial guess.

    .. math::
        0 = 1 + \left(\frac{K_{max}-K_{min}}{K_{min}-1}\right)x_{max} + \sum_{i=2}^{n-1}
        \frac{K_i-K_{min}}{K_{min}-1}
        \left[\frac{z_i(K_{max}-1)x_{max}}{(K_i-1)z_{max} + (K_{max}-K_i)x_{max}}\right]
        
    Parameters
    ----------
    zs : list[float]
        Overall mole fractions of all species, [-]
    Ks : list[float]
        Equilibrium K-values, [-]

    Returns
    -------
    V_over_F : float
        Vapor fraction solution [-]
    xs : list[float]
        Mole fractions of each species in the liquid phase, [-]
    ys : list[float]
        Mole fractions of each species in the vapor phase, [-]

    Notes
    -----
    The initial guess is the average of the following, as described in [1]_.
    Each guess should be limited to be between 0 and 1 as they are often
    negative or larger than 1. `max` refers to the corresponding mole fractions
    for the species with the largest K value.

    .. math::
        \left(\frac{1-K_{min}}{K_{max}-K_{min}}\right)z_{max}\le x_{max} \le
        \left(\frac{1-K_{min}}{K_{max}-K_{min}}\right)

    If the `newton` method does not converge, a bisection method (brenth) is
    used instead. However, it is somewhat slower, especially as newton will
    attempt 50 iterations before giving up.

    This method does not work for problems of only two components.
    K values are sorted internally. Has not been found to be quicker than the
    Rachford-Rice equation.

    Examples
    --------
    >>> Li_Johns_Ahmadi_solution(zs=[0.5, 0.3, 0.2], Ks=[1.685, 0.742, 0.532])
    (0.6907302627738544, [0.33940869696634357, 0.3650560590371706, 0.2955352439964858], [0.5719036543882889, 0.27087159580558057, 0.15722474980613044])

    References
    ----------
    .. [1] Li, Yinghui, Russell T. Johns, and Kaveh Ahmadi. "A Rapid and Robust
       Alternative to Rachford-Rice in Flash Calculations." Fluid Phase
       Equilibria 316 (February 25, 2012): 85-97.
       doi:10.1016/j.fluid.2011.12.005.
    '''
    # Re-order both Ks and Zs by K value, higher coming first
    p = sorted(zip(Ks,zs), reverse=True)
    Ks_sorted, zs_sorted = [K for (K,z) in p], [z for (K,z) in p]


    # Largest K value and corresponding overall mole fraction
    k1 = Ks_sorted[0]
    z1 = zs_sorted[0]
    # Smallest K value
    kn = Ks_sorted[-1]

    x_min = (1. - kn)/(k1 - kn)*z1
    x_max = (1. - kn)/(k1 - kn)

    x_min2 = max(0., x_min)
    x_max2 = min(1., x_max)

    x_guess = (x_min2 + x_max2)*0.5

    length = len(zs)-1
    kn_m_1 = kn-1.
    k1_m_1 = (k1-1.)
    t1 = (k1-kn)/(kn-1.)
    
    def objective(x1):
        return 1. + t1*x1 + sum([(ki-kn)/(kn_m_1) * zi*k1_m_1*x1 /( (ki-1.)*z1 + (k1-ki)*x1) for ki, zi in zip(Ks_sorted[1:length], zs_sorted[1:length])])

    try:
        x1 = newton(objective, x_guess)
        # newton skips out of its specified range in some cases, finding another solution
        # Check for that with asserts, and use brenth if it did
        # Must also check that V_over_F is right.
        assert x1 >= x_min2
        assert x1 <= x_max2
        V_over_F = (-x1 + z1)/(x1*(k1 - 1.))
        assert 0.0 <= V_over_F <= 1.0
    except:
        x1 = brenth(objective, x_min, x_max)
        V_over_F = (-x1 + z1)/(x1*(k1 - 1.))
    xs = [zi/(1.+V_over_F*(Ki-1.)) for zi, Ki in zip(zs, Ks)]
    ys = [Ki*xi for xi, Ki in zip(xs, Ks)]
    return V_over_F, xs, ys


FLASH_INNER_ANALYTICAL = 'Analytical'
FLASH_INNER_SECANT = 'Rachford-Rice (Secant)'
FLASH_INNER_NR = 'Rachford-Rice (Newton-Raphson)'
FLASH_INNER_HALLEY = 'Rachford-Rice (Halley)'
FLASH_INNER_NUMPY = 'Rachford-Rice (NumPy)'
FLASH_INNER_LJA = 'Li-Johns-Ahmadi'

flash_inner_loop_methods = [FLASH_INNER_ANALYTICAL, 
                            FLASH_INNER_SECANT, FLASH_INNER_SECANT,
                            FLASH_INNER_NR, FLASH_INNER_HALLEY,
                            FLASH_INNER_NUMPY, FLASH_INNER_LJA]

def flash_inner_loop_list_methods(l):
    methods = []
    if l in (2,3):
        methods.append(FLASH_INNER_ANALYTICAL)
    if l >= 10 and not IS_PYPY:
        methods.append(FLASH_INNER_NUMPY)
    if l >= 2:
        methods.extend([FLASH_INNER_SECANT, FLASH_INNER_NR, FLASH_INNER_HALLEY])
        if l < 10 and not IS_PYPY:
            methods.append(FLASH_INNER_NUMPY)
    if l >= 3:
        methods.append(FLASH_INNER_LJA)
    return methods


def flash_inner_loop(zs, Ks, AvailableMethods=False, Method=None):
    r'''This function handles the solution of the inner loop of a flash
    calculation, solving for liquid and gas mole fractions and vapor fraction
    based on specified overall mole fractions and K values. As K values are
    weak functions of composition, this should be called repeatedly by an outer
    loop. Will automatically select an algorithm to use if no Method is
    provided. Should always provide a solution.

    The automatic algorithm selection will try an analytical solution, and use
    the Rachford-Rice method if there are 4 or more components in the mixture.

    Parameters
    ----------
    zs : list[float]
        Overall mole fractions of all species, [-]
    Ks : list[float]
        Equilibrium K-values, [-]

    Returns
    -------
    V_over_F : float
        Vapor fraction solution [-]
    xs : list[float]
        Mole fractions of each species in the liquid phase, [-]
    ys : list[float]
        Mole fractions of each species in the vapor phase, [-]
    methods : list, only returned if AvailableMethods == True
        List of methods which can be used to obtain a solution with the given
        inputs

    Other Parameters
    ----------------
    Method : string, optional
        The method name to use. Accepted methods are 'Analytical',
        'Rachford-Rice (Secant)', 'Rachford-Rice (Newton-Raphson)', 
        'Rachford-Rice (Halley)', 'Rachford-Rice (NumPy)', and 
        'Li-Johns-Ahmadi'. All valid values are also held
        in the list `flash_inner_loop_methods`.
    AvailableMethods : bool, optional
        If True, function will determine which methods can be used to obtain
        a solution for the desired chemical, and will return methods instead of
        `V_over_F`, `xs`, and `ys`.

    Notes
    -----
    A total of six methods are available for this function. They are:

        * 'Analytical', an exact solution derived with SymPy, applicable only
          only to mixtures of two or three components
        * 'Rachford-Rice (Secant)', 'Rachford-Rice (Newton-Raphson)', 
          'Rachford-Rice (Halley)', or 'Rachford-Rice (NumPy)',
          which numerically solves an objective function
          described in :obj:`Rachford_Rice_solution`.
        * 'Li-Johns-Ahmadi', which numerically solves an objective function
          described in :obj:`Li_Johns_Ahmadi_solution`.

    Examples
    --------
    >>> flash_inner_loop(zs=[0.5, 0.3, 0.2], Ks=[1.685, 0.742, 0.532])
    (0.6907302627738537, [0.3394086969663437, 0.36505605903717053, 0.29553524399648573], [0.5719036543882892, 0.2708715958055805, 0.1572247498061304])
    '''
    if AvailableMethods:
        l = len(zs)
        return flash_inner_loop_list_methods(l)
    elif Method is None:
        l = len(zs)
        Method = FLASH_INNER_ANALYTICAL if l < 4 else (FLASH_INNER_NUMPY if (not IS_PYPY and l >= 10) else FLASH_INNER_SECANT)
    if Method == FLASH_INNER_SECANT:
        return Rachford_Rice_solution(zs, Ks)
    elif Method == FLASH_INNER_ANALYTICAL:
        l = len(zs)
        if l == 2:
            z1, z2 = zs
            K1, K2 = Ks
            try:
                V_over_F = (-K1*z1 - K2*z2 + z1 + z2)/(K1*K2*z1 + K1*K2*z2 - K1*z1 - K1*z2 - K2*z1 - K2*z2 + z1 + z2)
            except ZeroDivisionError:
                return Rachford_Rice_solution(zs=zs, Ks=Ks)
        elif l == 3:
            z1, z2, z3 = zs
            K1, K2, K3 = Ks
            V_over_F = (-K1*K2*z1/2 - K1*K2*z2/2 - K1*K3*z1/2 - K1*K3*z3/2 + K1*z1 + K1*z2/2 + K1*z3/2 - K2*K3*z2/2 - K2*K3*z3/2 + K2*z1/2 + K2*z2 + K2*z3/2 + K3*z1/2 + K3*z2/2 + K3*z3 - z1 - z2 - z3 - (K1**2*K2**2*z1**2 + 2*K1**2*K2**2*z1*z2 + K1**2*K2**2*z2**2 - 2*K1**2*K2*K3*z1**2 - 2*K1**2*K2*K3*z1*z2 - 2*K1**2*K2*K3*z1*z3 + 2*K1**2*K2*K3*z2*z3 - 2*K1**2*K2*z1*z2 + 2*K1**2*K2*z1*z3 - 2*K1**2*K2*z2**2 - 2*K1**2*K2*z2*z3 + K1**2*K3**2*z1**2 + 2*K1**2*K3**2*z1*z3 + K1**2*K3**2*z3**2 + 2*K1**2*K3*z1*z2 - 2*K1**2*K3*z1*z3 - 2*K1**2*K3*z2*z3 - 2*K1**2*K3*z3**2 + K1**2*z2**2 + 2*K1**2*z2*z3 + K1**2*z3**2 - 2*K1*K2**2*K3*z1*z2 + 2*K1*K2**2*K3*z1*z3 - 2*K1*K2**2*K3*z2**2 - 2*K1*K2**2*K3*z2*z3 - 2*K1*K2**2*z1**2 - 2*K1*K2**2*z1*z2 - 2*K1*K2**2*z1*z3 + 2*K1*K2**2*z2*z3 + 2*K1*K2*K3**2*z1*z2 - 2*K1*K2*K3**2*z1*z3 - 2*K1*K2*K3**2*z2*z3 - 2*K1*K2*K3**2*z3**2 + 4*K1*K2*K3*z1**2 + 4*K1*K2*K3*z1*z2 + 4*K1*K2*K3*z1*z3 + 4*K1*K2*K3*z2**2 + 4*K1*K2*K3*z2*z3 + 4*K1*K2*K3*z3**2 + 2*K1*K2*z1*z2 - 2*K1*K2*z1*z3 - 2*K1*K2*z2*z3 - 2*K1*K2*z3**2 - 2*K1*K3**2*z1**2 - 2*K1*K3**2*z1*z2 - 2*K1*K3**2*z1*z3 + 2*K1*K3**2*z2*z3 - 2*K1*K3*z1*z2 + 2*K1*K3*z1*z3 - 2*K1*K3*z2**2 - 2*K1*K3*z2*z3 + K2**2*K3**2*z2**2 + 2*K2**2*K3**2*z2*z3 + K2**2*K3**2*z3**2 + 2*K2**2*K3*z1*z2 - 2*K2**2*K3*z1*z3 - 2*K2**2*K3*z2*z3 - 2*K2**2*K3*z3**2 + K2**2*z1**2 + 2*K2**2*z1*z3 + K2**2*z3**2 - 2*K2*K3**2*z1*z2 + 2*K2*K3**2*z1*z3 - 2*K2*K3**2*z2**2 - 2*K2*K3**2*z2*z3 - 2*K2*K3*z1**2 - 2*K2*K3*z1*z2 - 2*K2*K3*z1*z3 + 2*K2*K3*z2*z3 + K3**2*z1**2 + 2*K3**2*z1*z2 + K3**2*z2**2)**0.5/2)/(K1*K2*K3*z1 + K1*K2*K3*z2 + K1*K2*K3*z3 - K1*K2*z1 - K1*K2*z2 - K1*K2*z3 - K1*K3*z1 - K1*K3*z2 - K1*K3*z3 + K1*z1 + K1*z2 + K1*z3 - K2*K3*z1 - K2*K3*z2 - K2*K3*z3 + K2*z1 + K2*z2 + K2*z3 + K3*z1 + K3*z2 + K3*z3 - z1 - z2 - z3)
        else:
            raise Exception('Only solutions of one or two variables are available analytically')
        # Need to avoid zero divisions here
        xs = [zi/(1.+V_over_F*(Ki-1.)) for zi, Ki in zip(zs, Ks) if zi != 0.0]
        ys = [Ki*xi for xi, Ki in zip(xs, Ks)]
        return V_over_F, xs, ys
    elif Method == FLASH_INNER_NUMPY:
        return Rachford_Rice_solution_numpy(zs=zs, Ks=Ks)
    elif Method == FLASH_INNER_NR:
        return Rachford_Rice_solution(zs=zs, Ks=Ks, fprime=True)
    elif Method == FLASH_INNER_HALLEY:
        return Rachford_Rice_solution(zs=zs, Ks=Ks, fprime=True, fprime2=True)
    
    elif Method == FLASH_INNER_LJA:
        return Li_Johns_Ahmadi_solution(zs=zs, Ks=Ks)
    else:
        raise Exception('Incorrect Method input')


def NRTL(xs, taus, alphas):
    r'''Calculates the activity coefficients of each species in a mixture
    using the Non-Random Two-Liquid (NRTL) method, given their mole fractions,
    dimensionless interaction parameters, and nonrandomness constants. Those
    are normally correlated with temperature in some form, and need to be
    calculated separately.

    .. math::
        \ln(\gamma_i)=\frac{\displaystyle\sum_{j=1}^{n}{x_{j}\tau_{ji}G_{ji}}}
        {\displaystyle\sum_{k=1}^{n}{x_{k}G_{ki}}}+\sum_{j=1}^{n}
        {\frac{x_{j}G_{ij}}{\displaystyle\sum_{k=1}^{n}{x_{k}G_{kj}}}}
        {\left ({\tau_{ij}-\frac{\displaystyle\sum_{m=1}^{n}{x_{m}\tau_{mj}
        G_{mj}}}{\displaystyle\sum_{k=1}^{n}{x_{k}G_{kj}}}}\right )}

        G_{ij}=\text{exp}\left ({-\alpha_{ij}\tau_{ij}}\right )

    Parameters
    ----------
    xs : list[float]
        Liquid mole fractions of each species, [-]
    taus : list[list[float]]
        Dimensionless interaction parameters of each compound with each other,
        [-]
    alphas : list[list[float]]
        Nonrandomness constants of each compound interacting with each other, [-]

    Returns
    -------
    gammas : list[float]
        Activity coefficient for each species in the liquid mixture, [-]

    Notes
    -----
    This model needs N^2 parameters.

    One common temperature dependence of the nonrandomness constants is:

    .. math::
        \alpha_{ij}=c_{ij}+d_{ij}T

    Most correlations for the interaction parameters include some of the terms
    shown in the following form:

    .. math::
        \tau_{ij}=A_{ij}+\frac{B_{ij}}{T}+\frac{C_{ij}}{T^{2}}+D_{ij}
        \ln{\left ({T}\right )}+E_{ij}T^{F_{ij}}
        
    The original form of this model used the temperature dependence of taus in 
    the form (values can be found in the literature, often with units of
    calories/mol):
        
    .. math::
        \tau_{ij}=\frac{b_{ij}}{RT}

    For this model to produce ideal acitivty coefficients (gammas = 1),
    all interaction parameters should be 0; the value of alpha does not impact
    the calculation when that is the case.

    Examples
    --------
    Ethanol-water example, at 343.15 K and 1 MPa:

    >>> NRTL(xs=[0.252, 0.748], taus=[[0, -0.178], [1.963, 0]],
    ... alphas=[[0, 0.2974],[.2974, 0]])
    [1.9363183763514304, 1.1537609663170014]

    References
    ----------
    .. [1] Renon, Henri, and J. M. Prausnitz. "Local Compositions in
       Thermodynamic Excess Functions for Liquid Mixtures." AIChE Journal 14,
       no. 1 (1968): 135-144. doi:10.1002/aic.690140124.
    .. [2] Gmehling, Jurgen, Barbel Kolbe, Michael Kleiber, and Jurgen Rarey.
       Chemical Thermodynamics for Process Simulation. 1st edition. Weinheim:
       Wiley-VCH, 2012.
    '''
    gammas = []
    cmps = range(len(xs))
    Gs = [[exp(-alphas[i][j]*taus[i][j]) for j in cmps] for i in cmps]
    for i in cmps:
        tn1, td1, total2 = 0., 0., 0.
        Gsi = Gs[i]
        tausi = taus[i]
        for j in cmps:
            # Term 1, numerator and denominator
            tn1 += xs[j]*taus[j][i]*Gs[j][i]
            td1 +=  xs[j]*Gs[j][i]
            # Term 2
            tn2 = xs[j]*Gsi[j]
            
            td2 = td3 = sum([xs[k]*Gs[k][j] for k in cmps])
            
            tn3 = sum([xs[m]*taus[m][j]*Gs[m][j] for m in cmps])
            
            total2 += tn2/td2*(tausi[j] - tn3/td3)
        gamma = exp(tn1/td1 + total2)
        gammas.append(gamma)
    return gammas


def Wilson(xs, params):
    r'''Calculates the activity coefficients of each species in a mixture
    using the Wilson method, given their mole fractions, and
    dimensionless interaction parameters. Those are normally correlated with
    temperature, and need to be calculated separately.

    .. math::
        \ln \gamma_i = 1 - \ln \left(\sum_j^N \Lambda_{ij} x_j\right)
        -\sum_j^N \frac{\Lambda_{ji}x_j}{\displaystyle\sum_k^N \Lambda_{jk}x_k}

    Parameters
    ----------
    xs : list[float]
        Liquid mole fractions of each species, [-]
    params : list[list[float]]
        Dimensionless interaction parameters of each compound with each other,
        [-]

    Returns
    -------
    gammas : list[float]
        Activity coefficient for each species in the liquid mixture, [-]

    Notes
    -----
    This model needs N^2 parameters.

    The original model correlated the interaction parameters using the standard
    pure-component molar volumes of each species at 25°C, in the following form:

    .. math::
        \Lambda_{ij} = \frac{V_j}{V_i} \exp\left(\frac{-\lambda_{i,j}}{RT}\right)

    However, that form has less flexibility and offered no advantage over
    using only regressed parameters.

    Most correlations for the interaction parameters include some of the terms
    shown in the following form:

    .. math::
        \ln \Lambda_{ij} =a_{ij}+\frac{b_{ij}}{T}+c_{ij}\ln T + d_{ij}T
        + \frac{e_{ij}}{T^2} + h_{ij}{T^2}

    The Wilson model is not applicable to liquid-liquid systems.
    
    For this model to produce ideal acitivty coefficients (gammas = 1),
    all interaction parameters should be 1.

    Examples
    --------
    Ethanol-water example, at 343.15 K and 1 MPa:

    >>> Wilson([0.252, 0.748], [[1, 0.154], [0.888, 1]])
    [1.8814926087178843, 1.1655774931125487]

    References
    ----------
    .. [1] Wilson, Grant M. "Vapor-Liquid Equilibrium. XI. A New Expression for
       the Excess Free Energy of Mixing." Journal of the American Chemical
       Society 86, no. 2 (January 1, 1964): 127-130. doi:10.1021/ja01056a002.
    .. [2] Gmehling, Jurgen, Barbel Kolbe, Michael Kleiber, and Jurgen Rarey.
       Chemical Thermodynamics for Process Simulation. 1st edition. Weinheim:
       Wiley-VCH, 2012.
    '''
    gammas = []
    cmps = range(len(xs))
    for i in cmps:
        tot1 = log(sum([params[i][j]*xs[j] for j in cmps]))
        tot2 = 0.
        for j in cmps:
            tot2 += params[j][i]*xs[j]/sum([params[j][k]*xs[k] for k in cmps])

        gamma = exp(1. - tot1 - tot2)
        gammas.append(gamma)
    return gammas


def UNIQUAC(xs, rs, qs, taus):
    r'''Calculates the activity coefficients of each species in a mixture
    using the Universal quasi-chemical (UNIQUAC) equation, given their mole
    fractions, `rs`, `qs`, and dimensionless interaction parameters. The
    interaction parameters are normally correlated with temperature, and need
    to be calculated separately.

    .. math::
        \ln \gamma_i = \ln \frac{\Phi_i}{x_i} + \frac{z}{2} q_i \ln
        \frac{\theta_i}{\Phi_i}+ l_i - \frac{\Phi_i}{x_i}\sum_j^N x_j l_j
        - q_i \ln\left( \sum_j^N \theta_j \tau_{ji}\right)+ q_i - q_i\sum_j^N
        \frac{\theta_j \tau_{ij}}{\sum_k^N \theta_k \tau_{kj}}

        \theta_i = \frac{x_i q_i}{\displaystyle\sum_{j=1}^{n} x_j q_j}

         \Phi_i = \frac{x_i r_i}{\displaystyle\sum_{j=1}^{n} x_j r_j}

         l_i = \frac{z}{2}(r_i - q_i) - (r_i - 1)

    Parameters
    ----------
    xs : list[float]
        Liquid mole fractions of each species, [-]
    rs : list[float]
        Van der Waals volume parameters for each species, [-]
    qs : list[float]
        Surface area parameters for each species, [-]
    taus : list[list[float]]
        Dimensionless interaction parameters of each compound with each other,
        [-]

    Returns
    -------
    gammas : list[float]
        Activity coefficient for each species in the liquid mixture, [-]

    Notes
    -----
    This model needs N^2 parameters.

    The original expression for the interaction parameters is as follows:

    .. math::
        \tau_{ji} = \exp\left(\frac{-\Delta u_{ij}}{RT}\right)

    However, it is seldom used. Most correlations for the interaction
    parameters include some of the terms shown in the following form:

    .. math::
        \ln \tau{ij} =a_{ij}+\frac{b_{ij}}{T}+c_{ij}\ln T + d_{ij}T
        + \frac{e_{ij}}{T^2}

    This model is recast in a slightly more computationally efficient way in
    [2]_, as shown below:

    .. math::
        \ln \gamma_i = \ln \gamma_i^{res} + \ln \gamma_i^{comb}

        \ln \gamma_i^{res} = q_i \left(1 - \ln\frac{\sum_j^N q_j x_j \tau_{ji}}
        {\sum_j^N q_j x_j}- \sum_j \frac{q_k x_j \tau_{ij}}{\sum_k q_k x_k
        \tau_{kj}}\right)

        \ln \gamma_i^{comb} = (1 - V_i + \ln V_i) - \frac{z}{2}q_i\left(1 -
        \frac{V_i}{F_i} + \ln \frac{V_i}{F_i}\right)

        V_i = \frac{r_i}{\sum_j^N r_j x_j}

        F_i = \frac{q_i}{\sum_j q_j x_j}


    There is no global set of parameters which will make this model yield
    ideal acitivty coefficients (gammas = 1) for this model.
    
    Examples
    --------
    Ethanol-water example, at 343.15 K and 1 MPa:

    >>> UNIQUAC(xs=[0.252, 0.748], rs=[2.1055, 0.9200], qs=[1.972, 1.400],
    ... taus=[[1.0, 1.0919744384510301], [0.37452902779205477, 1.0]])
    [2.35875137797083, 1.2442093415968987]

    References
    ----------
    .. [1] Abrams, Denis S., and John M. Prausnitz. "Statistical Thermodynamics
       of Liquid Mixtures: A New Expression for the Excess Gibbs Energy of
       Partly or Completely Miscible Systems." AIChE Journal 21, no. 1 (January
       1, 1975): 116-28. doi:10.1002/aic.690210115.
    .. [2] Gmehling, Jurgen, Barbel Kolbe, Michael Kleiber, and Jurgen Rarey.
       Chemical Thermodynamics for Process Simulation. 1st edition. Weinheim:
       Wiley-VCH, 2012.
    .. [3] Maurer, G., and J. M. Prausnitz. "On the Derivation and Extension of
       the Uniquac Equation." Fluid Phase Equilibria 2, no. 2 (January 1,
       1978): 91-99. doi:10.1016/0378-3812(78)85002-X.
    '''
    cmps = range(len(xs))
    rsxs = [rs[i]*xs[i] for i in cmps]
    rsxs_sum = sum(rsxs)
    phis = [rsxs[i]/rsxs_sum for i in cmps]
    qsxs = [qs[i]*xs[i] for i in cmps]
    qsxs_sum = sum(qsxs)
    vs = [qsxs[i]/qsxs_sum for i in cmps]

    Ss = [sum([vs[j]*taus[j][i] for j in cmps]) for i in cmps]
    VsSs = [vs[j]/Ss[j] for j in cmps]

    ans = []
    for i in cmps:
        x1 = phis[i]/xs[i]
        x2 = phis[i]/vs[i]
        loggammac = log(x1) + 1.0 - x1 - 5.0*qs[i]*(log(x2) + 1.0 - x2)
        loggammar = qs[i]*(1.0 - log(Ss[i]) - sum([taus[i][j]*VsSs[j] for j in cmps]))
        ans.append(exp(loggammac + loggammar))
    return ans


def flash(P, zs, Psats):
#    if not fugacities:
#        fugacities = [1 for i in range(len(zs))]
#    if not gammas:
#        gammas = [1 for i in range(len(zs))]
    if not none_and_length_check((zs, Psats)):
        raise Exception('Input dimentions are inconsistent or some input parameters are missing.')
    Ks = [K_value(P=P, Psat=Psats[i]) for i in range(len(zs))]
    def valid_range(zs, Ks):
        valid = True
        if sum([zs[i]*Ks[i] for i in range(len(Ks))]) < 1:
            valid = False
        if sum([zs[i]/Ks[i] for i in range(len(Ks))]) < 1:
            valid = False
        return valid
    if not valid_range(zs, Ks):
        raise Exception('Solution does not exist')

    V_over_F, xs, ys = flash_inner_loop(zs=zs, Ks=Ks)
    if V_over_F < 0:
        raise Exception('V_over_F is negative!')
    return xs, ys, V_over_F




def dew_at_T(zs, Psats, fugacities=None, gammas=None):
    '''
    >>> dew_at_T([0.5, 0.5], [1400, 7000])
    2333.3333333333335
    >>> dew_at_T([0.5, 0.5], [1400, 7000], gammas=[1.1, .75])
    2381.443298969072
    >>> dew_at_T([0.5, 0.5], [1400, 7000], gammas=[1.1, .75], fugacities=[.995, 0.98])
    2401.621874512658
    '''
    if fugacities is None and gammas is None:
        try:
            return 1.0/sum([zs[i]/Psats[i] for i in range(len(zs))])
        except Exception as e:
            if not none_and_length_check((Psats,)):
                raise Exception('Input dimentions are inconsistent or some input parameters are missing.')
            raise e
    elif gammas is not None and fugacities is None:
        try:
            return 1.0/sum([zs[i]/(Psats[i]*gammas[i]) for i in range(len(zs))])
        except Exception as e:
            if not none_and_length_check((Psats, gammas)):
                raise Exception('Input dimentions are inconsistent or some input parameters are missing.')
            raise e
    elif fugacities is not None and gammas is None:
        try:
            return 1.0/sum([zs[i]*fugacities[i]/Psats[i] for i in range(len(zs))])
        except Exception as e:
            if not none_and_length_check((Psats, fugacities)):
                raise Exception('Input dimentions are inconsistent or some input parameters are missing.')
            raise e
    elif fugacities is not None and gammas is not None:
        try:
            return 1.0/sum([zs[i]*fugacities[i]/(Psats[i]*gammas[i]) for i in range(len(zs))])
        except Exception as e:
            if not none_and_length_check((zs, Psats, fugacities, gammas)):
                raise Exception('Input dimentions are inconsistent or some input parameters are missing.')
            raise e
    return ValueError
    
    
    
    
    
#    if not fugacities:
#        fugacities = [1 for i in range(len(Psats))]
#    if not gammas:
#        gammas = [1 for i in range(len(Psats))]
#    if not none_and_length_check((zs, Psats, fugacities, gammas)):
#        raise Exception('Input dimentions are inconsistent or some input parameters are missing.')
#    P = 1/sum(zs[i]*fugacities[i]/Psats[i]/gammas[i] for i in range(len(zs)))
#    return P
#

def bubble_at_T(zs, Psats, fugacities=None, gammas=None):
    '''
    >>> bubble_at_T([0.5, 0.5], [1400, 7000])
    4200.0
    >>> bubble_at_T([0.5, 0.5], [1400, 7000], gammas=[1.1, .75])
    3395.0
    >>> bubble_at_T([0.5, 0.5], [1400, 7000], gammas=[1.1, .75], fugacities=[.995, 0.98])
    3452.440775305097
    '''
    l = len(zs)
    if fugacities is None and gammas is None:
        try:
            return sum([zs[i]*Psats[i] for i in range(l)])
        except Exception as e:
            if not none_and_length_check((Psats,)):
                raise Exception('Input dimentions are inconsistent or some input parameters are missing.')
            raise e
    elif gammas is not None and fugacities is None:
        try:
            return sum([zs[i]*Psats[i]*gammas[i] for i in range(l)])
        except Exception as e:
            if not none_and_length_check((Psats, gammas)):
                raise Exception('Input dimentions are inconsistent or some input parameters are missing.')
            raise e
    elif fugacities is not None and gammas is None:
        try:
            return sum([zs[i]*Psats[i]/fugacities[i] for i in range(l)])
        except Exception as e:
            if not none_and_length_check((Psats, fugacities)):
                raise Exception('Input dimentions are inconsistent or some input parameters are missing.')
            return e
    elif fugacities is not None and gammas is not None:
        try:
            return sum([zs[i]*Psats[i]*gammas[i]/fugacities[i] for i in range(l)])
        except Exception as e:
            if not none_and_length_check((zs, Psats, fugacities, gammas)):
                raise Exception('Input dimentions are inconsistent or some input parameters are missing.')
            return e
    else:
        raise ValueError


def identify_phase(T, P, Tm=None, Tb=None, Tc=None, Psat=None):
    r'''Determines the phase of a one-species chemical system according to
    basic rules, using whatever information is available. Considers only the
    phases liquid, solid, and gas; does not consider two-phase
    scenarios, as should occurs between phase boundaries.

    * If the melting temperature is known and the temperature is under or equal
      to it, consider it a solid.
    * If the critical temperature is known and the temperature is greater or
      equal to it, consider it a gas.
    * If the vapor pressure at `T` is known and the pressure is under or equal
      to it, consider it a gas. If the pressure is greater than the vapor
      pressure, consider it a liquid.
    * If the melting temperature, critical temperature, and vapor pressure are
      not known, attempt to use the boiling point to provide phase information.
      If the pressure is between 90 kPa and 110 kPa (approximately normal),
      consider it a liquid if it is under the boiling temperature and a gas if
      above the boiling temperature.
    * If the pressure is above 110 kPa and the boiling temperature is known,
      consider it a liquid if the temperature is under the boiling temperature.
    * Return None otherwise.

    Parameters
    ----------
    T : float
        Temperature, [K]
    P : float
        Pressure, [Pa]
    Tm : float, optional
        Normal melting temperature, [K]
    Tb : float, optional
        Normal boiling point, [K]
    Tc : float, optional
        Critical temperature, [K]
    Psat : float, optional
        Vapor pressure of the fluid at `T`, [Pa]

    Returns
    -------
    phase : str
        Either 's', 'l', 'g', or None if the phase cannot be determined

    Notes
    -----
    No special attential is paid to any phase transition. For the case where
    the melting point is not provided, the possibility of the fluid being solid
    is simply ignored.

    Examples
    --------
    >>> identify_phase(T=280, P=101325, Tm=273.15, Psat=991)
    'l'
    '''
    if Tm and T <= Tm:
        return 's'
    elif Tc and T >= Tc:
        # No special return value for the critical point
        return 'g'
    elif Psat:
        # Do not allow co-existence of phases; transition to 'l' directly under
        if P <= Psat:
            return 'g'
        elif P > Psat:
            return 'l'
    elif Tb:
        # Crude attempt to model phases without Psat
        # Treat Tb as holding from 90 kPa to 110 kPa
        if 9E4 < P < 1.1E5:
            if T < Tb:
                return  'l'
            else:
                return 'g'
        elif P > 1.1E5 and T <= Tb:
            # For the higher-pressure case, it is definitely liquid if under Tb
            # Above the normal boiling point, impossible to say - return None
            return 'l'
        else:
            return None
    else:
        return None


mixture_phase_methods = ['IDEAL_VLE', 'SUPERCRITICAL_T', 'SUPERCRITICAL_P', 'IDEAL_VLE_SUPERCRITICAL']

def identify_phase_mixture(T=None, P=None, zs=None, Tcs=None, Pcs=None,
                           Psats=None, CASRNs=None,
                           AvailableMethods=False, Method=None):  # pragma: no cover
    '''
    >>> identify_phase_mixture(T=280, P=5000., zs=[0.5, 0.5], Psats=[1400, 7000])
    ('l', [0.5, 0.5], None, 0)
    >>> identify_phase_mixture(T=280, P=3000., zs=[0.5, 0.5], Psats=[1400, 7000])
    ('two-phase', [0.7142857142857143, 0.2857142857142857], [0.33333333333333337, 0.6666666666666666], 0.5625000000000001)
    >>> identify_phase_mixture(T=280, P=800., zs=[0.5, 0.5], Psats=[1400, 7000])
    ('g', None, [0.5, 0.5], 1)
    >>> identify_phase_mixture(T=280, P=800., zs=[0.5, 0.5])
    (None, None, None, None)
    '''
    def list_methods():
        methods = []
        if Psats and none_and_length_check((Psats, zs)):
            methods.append('IDEAL_VLE')
        if Tcs and none_and_length_check([Tcs]) and all([T >= i for i in Tcs]):
            methods.append('SUPERCRITICAL_T')
        if Pcs and none_and_length_check([Pcs]) and all([P >= i for i in Pcs]):
            methods.append('SUPERCRITICAL_P')
        if Tcs and none_and_length_check([zs, Tcs]) and any([T > Tc for Tc in Tcs]):
            methods.append('IDEAL_VLE_SUPERCRITICAL')
        methods.append('NONE')
        return methods
    if AvailableMethods:
        return list_methods()
    if not Method:
        Method = list_methods()[0]
    # This is the calculate, given the method section
    xs, ys, phase, V_over_F = None, None, None, None
    if Method == 'IDEAL_VLE':
        Pdew = dew_at_T(zs, Psats)
        Pbubble = bubble_at_T(zs, Psats)
        if P >= Pbubble:
            phase = 'l'
            ys = None
            xs = zs
            V_over_F = 0
        elif P <= Pdew:
            phase = 'g'
            ys = zs
            xs = None
            V_over_F = 1
        elif Pdew < P < Pbubble:
            xs, ys, V_over_F = flash(P, zs, Psats)
            phase = 'two-phase'
    elif Method == 'SUPERCRITICAL_T':
        if all([T >= i for i in Tcs]):
            phase = 'g'
        else: # The following is nonsensical
            phase = 'two-phase'
    elif Method == 'SUPERCRITICAL_P':
        if all([P >= i for i in Pcs]):
            phase = 'g'
        else: # The following is nonsensical
            phase = 'two-phase'
    elif Method == 'IDEAL_VLE_SUPERCRITICAL':
        Psats = list(Psats)
        for i in range(len(Psats)):
            if not Psats[i] and Tcs[i] and Tcs[i] <= T:
                Psats[i] = 1E8
        Pdew = dew_at_T(zs, Psats)
        Pbubble = 1E99
        if P >= Pbubble:
            phase = 'l'
            ys = None
            xs = zs
            V_over_F = 0
        elif P <= Pdew:
            phase = 'g'
            ys = zs
            xs = None
            V_over_F = 1
        elif Pdew < P < Pbubble:
            xs, ys, V_over_F = flash(P, zs, Psats)
            phase = 'two-phase'

    elif Method == 'NONE':
        pass
    else:
        raise Exception('Failure in in function')
    return phase, xs, ys, V_over_F


def Pbubble_mixture(T=None, zs=None, Psats=None, CASRNs=None,
                   AvailableMethods=False, Method=None):  # pragma: no cover
    '''
    >>> Pbubble_mixture(zs=[0.5, 0.5], Psats=[1400, 7000])
    4200.0
    '''
    def list_methods():
        methods = []
        if none_and_length_check((Psats, zs)):
            methods.append('IDEAL_VLE')
        methods.append('NONE')
        return methods
    if AvailableMethods:
        return list_methods()
    if not Method:
        Method = list_methods()[0]
    # This is the calculate, given the method section
    if Method == 'IDEAL_VLE':
        Pbubble = bubble_at_T(zs, Psats)
    elif Method == 'NONE':
        Pbubble = None
    else:
        raise Exception('Failure in in function')
    return Pbubble


def bubble_at_P(P, zs, vapor_pressure_eqns, fugacities=None, gammas=None):
    '''Calculates bubble point for a given pressure

    Parameters
    ----------
    P : float
        Pressure, [Pa]
    zs : list[float]
        Overall mole fractions of all species, [-]
    vapor_pressure_eqns : list[functions]
        Temperature dependent function for each specie, Returns Psat, [Pa]
    fugacities : list[float], optional
        fugacities of each species, defaults to list of ones, [-]
    gammas : list[float], optional
        gammas of each species, defaults to list of ones, [-]

    Returns
    -------
    Tbubble : float, optional
        Temperature of bubble point at pressure `P`, [K]

    '''

    def bubble_P_error(T):
        Psats = [VP(T) for VP in vapor_pressure_eqns]
        Pcalc = bubble_at_T(zs, Psats, fugacities, gammas)

        return P - Pcalc

    T_bubble = newton(bubble_P_error, 300)

    return T_bubble


def Pdew_mixture(T=None, zs=None, Psats=None, CASRNs=None,
                 AvailableMethods=False, Method=None):  # pragma: no cover
    '''
    >>> Pdew_mixture(zs=[0.5, 0.5], Psats=[1400, 7000])
    2333.3333333333335
    '''
    def list_methods():
        methods = []
        if none_and_length_check((Psats, zs)):
            methods.append('IDEAL_VLE')
        methods.append('NONE')
        return methods
    if AvailableMethods:
        return list_methods()
    if not Method:
        Method = list_methods()[0]
    # This is the calculate, given the method section
    if Method == 'IDEAL_VLE':
        Pdew = dew_at_T(zs, Psats)
    elif Method == 'NONE':
        Pdew = None
    else:
        raise Exception('Failure in in function')
    return Pdew




def get_T_bub_est(P, zs, Tbs, Tcs, Pcs):
    T_bub_est = 0.7*sum([zi*Tci for zi, Tci in zip(zs, Tcs)])
    T_LO = T_HI = 0.0
    for i in range(1000):
        Ks = [Pc**((1./T_bub_est - 1./Tb)/(1./Tc - 1./Tb))/P for Tb, Tc, Pc in zip(Tbs, Tcs, Pcs)]
        y_bub_sum = sum([zi*Ki for zi, Ki in zip(zs, Ks)])
        if y_bub_sum < 1.:
            T_LO = T_bub_est
            y_LO_sum = y_bub_sum - 1.
            T_new = T_bub_est*1.1
        elif y_bub_sum > 1.:
            T_HI = T_bub_est
            y_HI_sum = y_bub_sum - 1.
            T_new = T_bub_est/1.1
        else:
            return T_bub_est
        if T_LO*T_HI > 0.0:
            T_new = (y_HI_sum*T_LO - y_LO_sum*T_HI)/(y_HI_sum - y_LO_sum)

        if abs(T_bub_est - T_new) < 1E-3:
            return T_bub_est
        elif abs(y_bub_sum - 1.) < 1E-5:
            return T_bub_est
        else:
            T_bub_est = T_new
#get_T_bub_est(1E6, zs=[0.5, 0.5], Tbs=[194.67, 341.87], Tcs=[304.2, 507.4], Pcs=[7.38E6, 3.014E6])


def get_T_dew_est(P, zs, Tbs, Tcs, Pcs, T_bub_est=None):
    if T_bub_est is None:
        T_bub_est = get_T_bub_est(P, zs, Tbs, Tcs, Pcs)
    T_dew_est = 1.1*T_bub_est
    T_LO = T_HI = 0.0
    for i in range(10000):
        Ks = [Pc**((1./T_dew_est - 1./Tb)/(1./Tc - 1./Tb))/P for Tb, Tc, Pc in zip(Tbs, Tcs, Pcs)]
        x_dew_sum = sum([zi/Ki for zi, Ki in zip(zs, Ks)])
        if x_dew_sum < 1.:
            T_LO = T_dew_est
            x_LO_sum = x_dew_sum - 1.
            T_new = T_dew_est/1.1
        elif x_dew_sum > 1.:
            T_HI = T_dew_est
            x_HI_sum = x_dew_sum - 1.
            T_new = T_dew_est*1.1
        else:
            return T_dew_est
        if T_LO*T_HI > 0.0:
            T_new = (x_HI_sum*T_LO - x_LO_sum*T_HI)/(x_HI_sum - x_LO_sum)

        if abs(T_dew_est - T_new) < 1E-3:
            return T_dew_est
        elif abs(x_dew_sum - 1.) < 1E-5:
            return T_dew_est
        else:
            T_dew_est = T_new
#get_T_dew_est(1E6, zs=[0.5, 0.5], Tbs=[194.67, 341.87], Tcs=[304.2, 507.4], Pcs=[7.38E6, 3.014E6], T_bub_est = 290.6936541653881)


def get_P_dew_est(T, zs, Tbs, Tcs, Pcs):
    def err(P):
        e = get_T_dew_est(P, zs, Tbs, Tcs, Pcs) - T
        return e
    try:
        return brenth(err, 1E-2, 1e8)
    except:
        return brenth(err, 1E-3, 1E12)


def get_P_bub_est(T, zs, Tbs, Tcs, Pcs):
    def err(P):
        e = get_T_bub_est(P, zs, Tbs, Tcs, Pcs) - T
        return e
    try:
        return brenth(err, 1E-2, 1e8)
    except:
        return brenth(err, 1E-3, 1E12)
