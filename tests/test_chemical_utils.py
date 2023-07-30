'''Chemical Engineering Design Library (ChEDL). Utilities for process modeling.
Copyright (C) 2023 Caleb Bell <Caleb.Andrew.Bell@gmail.com>

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
SOFTWARE.
'''

from math import *

import pytest
from chemicals.elements import periodic_table
from chemicals.identifiers import pubchem_db
from fluids.constants import R
from fluids.numerics import assert_close
from thermo.chemical_utils import standard_state_ideal_gas_formation

from thermo.chemical import Chemical

def test_standard_state_ideal_gas_formation_water():
    c = Chemical('water') # H2O
    Ts = [1e-10, 100, 200, 298.15, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 2000, 2100, 2200, 2300, 2400, 2500, 2600, 2700, 2800, 2900, 3000, 3100, 3200, 3300, 3400, 3500, 3600, 3700, 3800, 3900, 4000, 4100, 4200, 4300, 4400, 4500, 4600, 4700, 4800, 4900, 5000, 5100, 5200, 5300, 5400, 5500, 5600, 5700, 5800, 5900, 6000]
    Ts = Ts[1:]
    dHs_Janaf = [-238.921, -240.083, -240.9, -241.826, -241.844, -242.846, -243.826, -244.758, -245.632, -246.443, -247.185, -247.857, -248.46, -248.997, -249.473, -249.894, -250.265, -250.592, -250.881, -251.138, -251.368, -251.575, -251.762, -251.934, -252.092, -252.239, -252.379, -252.513, -252.643, -252.771, -252.897, -253.024, -253.152, -253.282, -253.416, -253.553, -253.696, -253.844, -253.997, -254.158, -254.326, -254.501, -254.684, -254.876, -255.078, -255.288, -255.508, -255.738, -255.978, -256.229, -256.491, -256.763, -257.046, -257.338, -257.639, -257.95, -258.268, -258.595, -258.93, -259.272, -259.621, -259.977]
    dHs_Janaf = [v*1000 for v in dHs_Janaf[1:]]

    for T, dH_janaf in zip(Ts, dHs_Janaf):
        dH_calc = standard_state_ideal_gas_formation(c, T)[0]
        if T < 1000:
            rtol = 1e-3
        elif T < 2000:
            rtol = 1e-3
        else:
            rtol = .12
        assert_close(dH_calc, dH_janaf, rtol=rtol)

def test_standard_state_ideal_gas_formation_methane():
    Ts = [100.0, 200.0, 250.0, 298.15, 300.0, 350.0, 400.0, 450.0, 500.0, 600.0, 700.0, 800.0, 900.0, 1000.0, 1100.0, 1200.0, 1300.0, 1400.0, 1500.0, 1600.0, 1700.0, 1800.0, 1900.0, 2000.0, 2100.0, 2200.0, 2300.0, 2400.0, 2500.0, 2600.0, 2700.0, 2800.0, 2900.0, 3000.0, 3100.0, 3200.0, 3300.0, 3400.0, 3500.0, 3600.0, 3700.0, 3800.0, 3900.0, 4000.0, 4100.0, 4200.0, 4300.0, 4400.0, 4500.0, 4600.0, 4700.0, 4800.0, 4900.0, 5000.0, 5100.0, 5200.0, 5300.0, 5400.0, 5500.0, 5600.0, 5700.0, 5800.0, 5900.0, 6000.0]
    dH_janafs = [-69644.0, -72027.0, -73426.0, -74873.0, -74929.0, -76461.0, -77969.0, -79422.0, -80802.0, -83308.0, -85452.0, -87238.0, -88692.0, -89849.0, -90750.0, -91437.0, -91945.0, -92308.0, -92553.0, -92703.0, -92780.0, -92797.0, -92770.0, -92709.0, -92624.0, -92521.0, -92409.0, -92291.0, -92174.0, -92060.0, -91954.0, -91857.0, -91773.0, -91705.0, -91653.0, -91621.0, -91609.0, -91619.0, -91654.0, -91713.0, -91798.0, -91911.0, -92051.0, -92222.0, -92422.0, -92652.0, -92914.0, -93208.0, -93533.0, -93891.0, -94281.0, -94702.0, -95156.0, -95641.0, -96157.0, -96703.0, -97278.0, -97882.0, -98513.0, -99170.0, -99852.0, -100557.0, -101284.0, -102032.0]
    dG_janafs = [-64352.99999999999, -58161.0, -54536.0, -50768.0, -50618.0, -46445.0, -42054.0, -37476.0, -32741.0, -22887.0, -12643.0, -2115.0, 8616.0, 19492.0, 30472.0, 41524.0, 52626.0, 63761.0, 74918.0, 86088.0, 97265.0, 108445.0, 119624.0, 130801.99999999999, 141975.0, 153144.0, 164308.0, 175467.0, 186622.0, 197771.0, 208916.0, 220058.0, 231196.0, 242332.0, 253465.0, 264598.0, 275730.0, 286861.0, 297993.0, 309127.0, 320262.0, 331401.0, 342542.0, 353687.0, 364838.0, 375993.0, 387155.0, 398322.0, 409497.0, 420679.0, 431869.0, 443069.0, 454277.0, 465495.0, 476722.0, 487961.0, 499210.0, 510470.0, 521741.0, 533025.0, 544320.0, 555628.0, 566946.0, 578279.0]
    c = Chemical('methane')
    c.HeatCapacityGas.method = 'WEBBOOK_SHOMATE'
    dH_mean_err = 0
    dG_mean_err = 0

    for T, dH_janaf, dG_janaf in zip(Ts, dH_janafs, dG_janafs):
        dH_calc, dS_calc, dG_calc = standard_state_ideal_gas_formation(c, T)
        if T == 100:
            rtol = .02
        else:
            rtol = .01
        assert_close(dH_calc, dH_janaf, rtol=rtol)
        dH_mean_err += abs(dH_calc-dH_janaf)
        dG_mean_err += abs(dG_calc-dG_janaf)
    #     assert_close(dG_calc, dG_janaf, rtol=rtol)
    #     print(T, dG_calc/dG_janaf)

    dH_mean_err = dH_mean_err/len(Ts)
    dG_mean_err = dG_mean_err/len(Ts)
    assert dG_mean_err < 300

def test_standard_state_ideal_gas_formation_CF4():
    Ts = [100.0, 200.0, 250.0, 298.15, 300.0, 350.0, 400.0, 450.0, 500.0, 600.0, 700.0, 800.0, 900.0, 1000.0, 1100.0, 1200.0, 1300.0, 1400.0, 1500.0, 1600.0, 1700.0, 1800.0, 1900.0, 2000.0, 2100.0, 2200.0, 2300.0, 2400.0, 2500.0, 2600.0, 2700.0, 2800.0, 2900.0, 3000.0, 3100.0, 3200.0, 3300.0, 3400.0, 3500.0, 3600.0, 3700.0, 3800.0, 3900.0, 4000.0, 4100.0, 4200.0, 4300.0, 4400.0, 4500.0, 4600.0, 4700.0, 4800.0, 4900.0, 5000.0, 5100.0, 5200.0, 5300.0, 5400.0, 5500.0, 5600.0, 5700.0, 5800.0, 5900.0, 6000.0]
    dH_janafs = [-929755.0, -931896.0, -932645.0, -933199.0, -933218.0, -933651.0, -933970.0, -934198.0, -934351.0, -934485.0, -934451.0, -934298.0, -934065.0, -933778.0, -933456.0, -933115.0, -932766.0, -932417.0, -932075.0, -931744.0, -931428.0, -931125.0, -930835.0, -930556.0, -930283.0, -930011.0, -929735.0, -929449.0, -929146.0, -928821.0, -928466.0, -928077.0, -927649.0, -927177.0, -926656.0, -926084.0, -925458.0, -924775.0, -924034.0, -923233.0, -922372.0, -921450.0, -920468.0, -919425.0, -918322.0, -917160.0, -915940.0, -914663.0, -913330.0, -911943.0, -910503.0, -909011.0, -907470.0, -905880.0, -904243.0, -902562.0, -900837.0, -899069.0, -897262.0, -895416.0, -893532.0, -891613.0, -889659.0, -887672.0]
    dG_janafs = [-916822.0, -902995.0, -895679.0, -888507.0, -888229.0, -880695.0, -873107.0, -865485.0, -857841.0, -842523.0, -827197.0, -811884.0, -796596.0, -781337.0, -766108.0, -750909.0, -735739.0, -720597.0, -705479.0, -690383.0, -675308.0, -660251.0, -645210.0, -630184.0, -615173.0, -600174.0, -585187.0, -570213.0, -555251.0, -540302.0, -525365.0, -510442.0, -495534.0, -480642.0, -465766.0, -450907.0, -436068.0, -421248.0, -406449.0, -391671.0, -376918.0, -362188.0, -347483.0, -332804.0, -318153.0, -303528.0, -288932.0, -274365.0, -259827.0, -245321.0, -230844.0, -216399.0, -201986.0, -187604.0, -173255.0, -158937.0, -144653.0, -130402.99999999999, -116185.0, -102000.0, -87849.0, -73731.0, -59645.0, -45595.0]

    c = Chemical('CF4')
    c.HeatCapacityGas.method = 'WEBBOOK_SHOMATE'
    dH_mean_err = 0
    dG_mean_err = 0

    for T, dH_janaf, dG_janaf in zip(Ts, dH_janafs, dG_janafs):
        dH_calc, dS_calc, dG_calc = standard_state_ideal_gas_formation(c, T)
        if T < 5000:
            rtol = .01
        else:
            rtol = .05
        assert_close(dH_calc, dH_janaf, rtol=rtol)
        dH_mean_err += abs(dH_calc-dH_janaf)
        dG_mean_err += abs(dG_calc-dG_janaf)
        assert_close(dG_calc, dG_janaf, rtol=rtol)
    #     print(T, dG_calc/dG_janaf)
        # print(T, dH_janaf, dH_calc)

def test_standard_state_ideal_gas_formation_C2N2():
    Ts = [100.0, 200.0, 250.0, 298.15, 300.0, 350.0, 400.0, 450.0, 500.0, 600.0, 700.0, 800.0, 900.0, 1000.0, 1100.0, 1200.0, 1300.0, 1400.0, 1500.0, 1600.0, 1700.0, 1800.0, 1900.0, 2000.0, 2100.0, 2200.0, 2300.0, 2400.0, 2500.0, 2600.0, 2700.0, 2800.0, 2900.0, 3000.0, 3100.0, 3200.0, 3300.0, 3400.0, 3500.0, 3600.0, 3700.0, 3800.0, 3900.0, 4000.0, 4100.0, 4200.0, 4300.0, 4400.0, 4500.0, 4600.0, 4700.0, 4800.0, 4900.0, 5000.0, 5100.0, 5200.0, 5300.0, 5400.0, 5500.0, 5600.0, 5700.0, 5800.0, 5900.0, 6000.0]
    dH_janafs = [307303.0, 308042.0, 308558.0, 309072.0, 309092.0, 309606.0, 310079.0, 310495.0, 310850.0, 311392.0, 311752.0, 311982.0, 312117.0, 312184.0, 312199.0, 312171.0, 312109.0, 312015.0, 311895.0, 311748.0, 311577.0, 311382.0, 311165.0, 310925.0, 310663.0, 310379.0, 310073.0, 309746.0, 309397.0, 309026.0, 308634.0, 308220.0, 307785.0, 307328.0, 306850.0, 306350.0, 305828.0, 305285.0, 304720.0, 304134.0, 303526.0, 302896.0, 302244.0, 301571.0, 300876.0, 300159.0, 299420.0, 298659.0, 297877.0, 297073.0, 296247.0, 295398.0, 294528.0, 293635.0, 292720.0, 291783.0, 290824.0, 289842.0, 288837.0, 287811.0, 286761.0, 285688.0, 284592.0, 283472.0]
    dG_janafs = [304362.0, 301183.0, 299409.0, 297601.0, 297529.0, 295561.0, 293522.0, 291427.0, 289288.0, 284922.0, 280479.0, 275995.0, 271487.0, 266969.0, 262446.0, 257923.99999999997, 253406.0, 248894.0, 244389.0, 239893.0, 235407.0, 230932.0, 226469.0, 222017.0, 217578.0, 213152.0, 208740.0, 204341.0, 199956.0, 195586.0, 191230.0, 186889.0, 182563.0, 178253.0, 173958.0, 169680.0, 165417.0, 161170.0, 156939.0, 152725.0, 148528.0, 144347.0, 140183.0, 136036.0, 131906.0, 127794.0, 123699.0, 119621.0, 115561.0, 111518.0, 107493.0, 103486.0, 99497.0, 95525.0, 91572.0, 87637.0, 83720.0, 79822.0, 75942.0, 72080.0, 68237.0, 64413.0, 60607.0, 56820.0]

    c = Chemical('Ethanedinitrile')
    c.HeatCapacityGas.method = 'WEBBOOK_SHOMATE'

    for T, dH_janaf, dG_janaf in zip(Ts, dH_janafs, dG_janafs):
        dH_calc, dS_calc, dG_calc = standard_state_ideal_gas_formation(c, T)
        if T < 4500:
            rtol = .01
        else:
            rtol = .03
        assert_close(dH_calc, dH_janaf, rtol=rtol)
        assert_close(dG_calc, dG_janaf, rtol=rtol)

def test_standard_state_ideal_gas_formation_CFN():
    # This test case is pretty messed up. 
    # https://atct.anl.gov/Thermochemical%20Data/version%201.124/species/?species_number=216
    # The JANAF data from 1969 disagrees with modern data extremely bad.
    # No check on G is implemented, and the Hf value has to be from JANAF.
    Ts = [100.0, 200.0, 250.0, 298.15, 300.0, 350.0, 400.0, 450.0, 500.0, 600.0, 700.0, 800.0, 900.0, 1000.0, 1100.0, 1200.0, 1300.0, 1400.0, 1500.0, 1600.0, 1700.0, 1800.0, 1900.0, 2000.0, 2100.0, 2200.0, 2300.0, 2400.0, 2500.0, 2600.0, 2700.0, 2800.0, 2900.0, 3000.0, 3100.0, 3200.0, 3300.0, 3400.0, 3500.0, 3600.0, 3700.0, 3800.0, 3900.0, 4000.0, 4100.0, 4200.0, 4300.0, 4400.0, 4500.0, 4600.0, 4700.0, 4800.0, 4900.0, 5000.0, 5100.0, 5200.0, 5300.0, 5400.0, 5500.0, 5600.0, 5700.0, 5800.0, 5900.0, 6000.0]
    dH_janafs = [35477.0, 35638.0, 35808.0, 35982.0, 35989.0, 36161.0, 36314.0, 36441.0, 36542.0, 36670.0, 36721.0, 36719.0, 36677.0, 36608.0, 36516.0, 36406.0, 36279.0, 36136.0, 35977.0, 35804.0, 35616.0, 35415.0, 35200.0, 34973.0, 34736.0, 34489.0, 34234.0, 33974.0, 33708.0, 33440.0, 33171.0, 32902.0, 32634.0, 32369.0, 32107.0, 31850.0, 31598.0, 31352.0, 31112.0, 30878.0, 30652.0, 30432.0, 30218.0, 30012.0, 29812.0, 29618.0, 29430.0, 29248.0, 29072.0, 28901.0, 28735.0, 28572.0, 28414.0, 28259.0, 28108.0, 27959.0, 27812.0, 27667.0, 27523.0, 27380.0, 27238.0, 27095.0, 26952.0, 26808.0]
    dG_janafs = [33468.0, 31424.0, 30352.0, 29285.0, 29243.0, 28105.0, 26944.0, 25764.0, 24573.0, 22165.0, 19743.0, 17317.0, 14894.0, 12477.0, 10068.0, 7668.0, 5279.0, 2899.0, 531.0, -1827.0, -4173.0, -6508.0, -8831.0, -11143.0, -13443.0, -15731.0, -18008.0, -20274.0, -22529.0, -24773.0, -27007.0, -29231.0, -31445.0, -33650.0, -35847.0, -38035.0, -40215.0, -42387.0, -44552.0, -46711.0, -48863.0, -51009.0, -53149.0, -55284.0, -57414.0, -59539.0, -61660.0, -63776.0, -65888.0, -67997.0, -70101.0, -72203.0, -74300.0, -76395.0, -78487.0, -80575.0, -82661.0, -84744.0, -86824.0, -88902.0, -90978.0, -93050.0, -95120.0, -97188.0]

    c = Chemical('Cyanogen fluoride')
    c.HeatCapacityGas.method = 'WEBBOOK_SHOMATE'
    for T, dH_janaf, dG_janaf in zip(Ts, dH_janafs, dG_janafs):
        dH_calc, dS_calc, dG_calc = standard_state_ideal_gas_formation(c, T, Hf=35980.0, Sf=21.8)
        rtol = .01
        assert_close(dH_calc, dH_janaf, rtol=rtol)
