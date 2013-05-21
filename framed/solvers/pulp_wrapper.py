'''
Implementation a of PuLP based solver interface.
'''
from collections import OrderedDict
from pulp import LpProblem, LpMaximize, LpVariable, lpSum, LpStatusOptimal, LpStatusInfeasible, LpStatusUnbounded
from pulp.solvers import GUROBI, GUROBI_CMD, CPLEX_DLL, CPLEX_CMD, GLPK, GLPK_CMD

from .solver import Solver, Solution, Status


SELECTED_SOLVER = None
preference_order = [GUROBI, GUROBI_CMD, CPLEX_DLL, CPLEX_CMD, GLPK, GLPK_CMD]

for solver in preference_order:
    instance = solver(msg=False)
    if instance.available():
        SELECTED_SOLVER = instance
        break

if not SELECTED_SOLVER:
    raise Exception('No suitable solver found for PuLP.')

status_mapping = {LpStatusOptimal: Status.OPTIMAL,
                  LpStatusUnbounded: Status.UNBOUNDED,
                  LpStatusInfeasible: Status.UNFEASIBLE}


class PuLPSolver(Solver):
    """ Implements the solver interface using the PuLP library. """
    
    def __init__(self):
        Solver.__init__(self)
        
    def build_problem(self, model):
        """ Implements method from Solver class. """

        problem = LpProblem(sense=LpMaximize)
        problem.setSolver(SELECTED_SOLVER)
        
        #create variables
        lpvars = {r_id: LpVariable(r_id, lb, ub) for r_id, (lb, ub) in model.bounds.items()}
        
        #create constraints
        table = model.metabolite_reaction_lookup_table()
        for m_id in model.metabolites:
            problem += lpSum([coeff*lpvars[r_id] for r_id, coeff in table[m_id].items()]) == 0, m_id
        
        self.problem = problem
        self.var_ids = model.reactions.keys()
        self.constr_ids = model.metabolites.keys()
                
        
    def solve_lp(self, objective, model=None, constraints=None, get_shadow_prices=False, get_reduced_costs=False): 
        """ Implements method from Solver class. """
       
        if model: 
            self.build_problem(model)

        if self.problem:
            problem = self.problem
            lpvars = problem.variablesDict()
            lpcons = problem.constraints
        else:
            raise Exception('A model must be given if solver is used for the first time.')
        
        if constraints:
            old_constraints = {}
            for r_id, (lb, ub) in constraints.items():
                lpvar = lpvars[r_id]
                old_constraints[r_id] = (lpvar.lowBound, lpvar.upBound)
                lpvar.bounds(lb, ub)
        
        #create objective function
        problem += lpSum([f * lpvars[r_id] for r_id, f in objective.items() if f])
        
        try:      
            problem.solve()
        except:
            pass
        
        status = status_mapping[problem.status] if problem.status in status_mapping else Status.UNKNOWN

        if status == Status.OPTIMAL:
            fobj = problem.objective.value()
            values = OrderedDict([(r_id, lpvars[r_id].varValue) for r_id in self.var_ids])
            shadow_prices = OrderedDict([(m_id, lpcons[m_id].pi) for m_id in self.constr_ids]) if get_shadow_prices and hasattr(lpcons[self.constr_ids[0]], 'pi') else None
            reduced_costs = OrderedDict([(r_id, lpvars[r_id].dj) for r_id in self.var_ids]) if get_reduced_costs and hasattr(lpvars[self.var_ids[0]], 'dj') else None
            solution = Solution(status, fobj, values, shadow_prices, reduced_costs)
        else:
            solution = Solution(status=status)
        
        #reset old constraints because temporary constraints should not be persistent
        if constraints:
            for r_id, (lb, ub) in old_constraints.items():
                lpvars[r_id].bounds(lb, ub)
                
        return solution