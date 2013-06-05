"""
Example: Dynamic Flux Balance Analysis of Diauxic Growth of E. coli in Batch Bioreactor

@Author: Kai Zhuang
"""
__author__ = 'kaizhuang'


import matplotlib.pyplot as plt

from framed.io_utils.sbml import load_sbml_model, CONSTRAINT_BASED
from framed.core.fixes import fix_bigg_model
from framed.analysis.dfba import *
from framed.bioreactor.bioreactor import *


### Basic Setup
SMALL_TEST_MODEL = 'models/Ec_iAF1260_gene_names.xml'
ec1260 = load_sbml_model(SMALL_TEST_MODEL, kind=CONSTRAINT_BASED)
fix_bigg_model(ec1260)

print ec1260.reactions.keys()
### Defining the Ecoli class
# In the Ecoli class, the method update(), which is an abstract method in the superclass Organism, is defined.
# The update() method describes how Ecoli will respond to changes in metabolite concentrations in its environment.
# Usually, the relevant FBA uptake constraints are calculated and updated in the update() method.


class Ecoli(Organism):

    def update(self):
        BR = self.environment

        # calculating and updating the glucose uptake constraint
        rid = BR.metabolites.index('R_EX_glc_e_')
        vlb_glc = float(-10 * BR.S[rid] / (BR.S[rid] + 1))
        self.fba_constraints['R_EX_glc_e_'] = (vlb_glc, 0)

        self.fba_constraints['R_EX_ac_e_'] = (0, None)
        self.fba_constraints['R_EX_o2_e_'] = (-15, None)


### Main Program
# creating an instance of Ecoli
ec = Ecoli(ec1260)

# creating a batch bioreactor containing Ecoli, glucose, acetate, and oxygen
fedbatch_bioreactor = IdealFedbatch(ec, ['R_EX_glc_e_', 'R_EX_ac_e_'], Sfeed=[1000, 0], volume_max=10)


# set initial conditions
Vinit = [1]             # liquid volume
Xinit = [0.005]          # cell concentration
Sinit = [10, 0]      # concentrations of glucose, acetate, and oxygen
fedbatch_bioreactor.set_initial_conditions(Vinit, Xinit, Sinit)

# set simulation time interval
t0 = 0
tf = 20
dt = 0.1

# run dFBA simulation
t, y = dFBA(fedbatch_bioreactor, t0, tf, dt, solver='dopri5', verbose=True)

plt.figure(1)
plt.subplot(221)
plt.plot(t, y[:, 1])
plt.title('E. coli')
plt.subplot(222)
plt.plot(t, y[:, 2])
plt.title('Glucose')
plt.subplot(223)
plt.plot(t, y[:, 3])
plt.title('Acetate')
plt.subplot(224)
plt.plot(t, y[:, 0])
plt.title('Volume')
plt.show()


