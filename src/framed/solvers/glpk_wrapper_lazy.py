'''
Implementation of a Glpk based solver interface with lazy loading.

@author: Marta Matos

   Copyright 2013 Novo Nordisk Foundation Center for Biosustainability,
   Technical University of Denmark.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
   
   
   Note: to use this wrapper you need python-glpk, the instructions to 
   install it on Mac OS can be found on the framed/misc folder
'''

import tempfile
import os
from collections import OrderedDict
from .solver import Solver, Solution, Status, VarType
from glpk.glpkpi import *
from warnings import warn

status_mapping = {GLP_OPT: Status.OPTIMAL,
                  GLP_FEAS: Status.SUBOPTIMAL,
                  GLP_UNBND: Status.UNBOUNDED,
                  GLP_INFEAS: Status.INFEASIBLE,
                  GLP_NOFEAS: Status.INFEASIBLE,
                  GLP_UNDEF: Status.UNKNOWN}


class GlpkSolverLazy(Solver):

    """ Implements the solver interface using python-GLPK. """

    def __init__(self, tol_int=1e-9, time_limit=None):
        Solver.__init__(self)
        self.problem = glp_create_prob()
        glp_create_index(self.problem)
        self.set_presolve()

        # variable to store constraints matrix for lazy loading
        self.coefMatrix = {}

        # initialize variable for glpk LP parameters
        self.smcp = glp_smcp()
        glp_init_smcp(self.smcp)
        if time_limit != None:
            self.smcp.tm_lim = time_limit
        self.smcp.presolve = GLP_OFF

        # initialize variable for glpk MILP parameters
        self.iocp = glp_iocp()
        glp_init_iocp(self.iocp)
        if time_limit != None:
            self.iocp.tm_lim = time_limit
        if tol_int != "default":
            self.iocp.tol_int = 1e-9
        self.iocp.presolve = GLP_ON

        # glpk does not print any output
        glp_term_out(GLP_OFF)

    def __getstate__(self):
        tmp_file = tempfile.mktemp(suffix=".lp")
        glp_write_lp(self.problem, None, tmp_file)
        cplex_form = open(tmp_file).read()
        repr_dict = {'var_ids': self.var_ids, 'constr_ids':
                     self.constr_ids, 'cplex_form': cplex_form}
        return repr_dict

    def __setstate__(self, repr_dict):
        self.__init__()
        tmp_file = tempfile.mktemp(suffix=".lp")
        open(tmp_file, 'w').write(repr_dict['cplex_form'])
        self.empty_problem()
        glp_read_lp(self.problem, None, tmp_file)
        glp_create_index(self.problem)
        self.var_ids = repr_dict['var_ids']
        self.constr_ids = repr_dict['constr_ids']

    def add_variable(self, var_id, lb=None, ub=None, vartype=VarType.CONTINUOUS, persistent=True, update_problem=True):
        """ Add a variable to the current problem.

        Arguments:
            var_id : str -- variable identifier
            lb : float -- lower bound
            ub : float -- upper bound
            vartype : VarType -- variable type (default: CONTINUOUS)
            persistent : bool -- if the variable should be reused for multiple calls (default: true)
            update_problem : bool -- update problem immediately (default: True). update_problem is not
                              used in glpk, it is kept only for compatibility with the gurobi wrapper
        """

        var_type_mapping = {VarType.BINARY: GLP_BV,
                            VarType.INTEGER: GLP_IV,
                            VarType.CONTINUOUS: GLP_CV}

        if var_id in self.var_ids:
            ind_col = glp_find_col(self.problem, var_id)

        else:
            glp_add_cols(self.problem, 1)
            ind_col = glp_get_num_cols(self.problem)
            glp_set_col_name(self.problem, ind_col, var_id)
            self.var_ids.append(var_id)

        self.set_var_bounds(ind_col, lb, ub)
        glp_set_col_kind(self.problem, ind_col, var_type_mapping[vartype])

        if not persistent:
            self.temp_vars.add(var_id)

    def add_constraint(self, constr_id, lhs, sense='=', rhs=0, persistent=True, update_problem=True):
        """ Add a constraint to the current problem.

        Arguments:
            constr_id : str -- constraint identifier
            lhs : list [of (str, float)] -- variables and respective coefficients
            sense : {'<', '=', '>'} -- default '='
            rhs : float -- right-hand side of equation (default: 0)
            persistent : bool -- if the variable should be reused for multiple calls (default: True)
            update_problem : bool -- update problem immediately (default: True)
        """

        if constr_id in self.constr_ids:
            ind_row = glp_find_row(self.problem, constr_id)
            coef_ind, coef_val, n_vars = self.init_constr_arrays()

            for r_id, coeff in lhs:
                coef_ind_col = glp_find_col(self.problem, r_id)
                coef_val[coef_ind_col] = coeff

            glp_set_mat_row(self.problem, ind_row, n_vars, coef_ind, coef_val)

        else:
            glp_add_rows(self.problem, 1)
            ind_row = glp_get_num_rows(self.problem)
            glp_set_row_name(self.problem, ind_row, constr_id)
            self.constr_ids.append(constr_id)

            # if there are any entries in the constraint matrix, further constraints
            #  will be added to the matrix and not immediately to the problem
            if update_problem == False or self.coefMatrix != {}:
                for r_id, coeff in lhs:
                    if coeff != 0:
                        ind_col = glp_find_col(self.problem, r_id)
                        self.coefMatrix[(ind_row, ind_col)] = coeff

            else:
                coef_ind, coef_val, n_vars = self.init_constr_arrays()

                for r_id, coeff in lhs:
                    coef_ind_col = glp_find_col(self.problem, r_id)
                    coef_val[coef_ind_col] = coeff

                glp_set_mat_row(self.problem, ind_row, n_vars, coef_ind, coef_val)

        self.set_constr_bounds(ind_row, sense, rhs)

        if not persistent:
            self.temp_constrs.add(constr_id)

    def remove_variable(self, var_id):
        """ Remove a variable from the current problem.

        Arguments:
            var_id : str -- variable identifier
        """
        col_to_delete = intArray(2)
        col_to_delete[1] = glp_find_col(self.problem, var_id)

        entries_to_remove = []

        if var_id in self.var_ids:
            if self.coefMatrix != {}:
                for (row, col) in self.coefMatrix:
                    if col == col_to_delete[1]:
                        entries_to_remove.append((row, col))
                for row, col in entries_to_remove:
                    del self.coefMatrix[(row, col)]

            glp_del_cols(self.problem, 1, col_to_delete)
            self.var_ids.remove(var_id)

    def remove_constraint(self, constr_id):
        """ Remove a constraint from the current problem.

        Arguments:
            constr_id : str -- constraint identifier
        """

        row_to_delete = intArray(2)
        row_to_delete[1] = glp_find_row(self.problem, constr_id)

        entries_to_remove = []

        if constr_id in self.constr_ids:
            if self.coefMatrix != {}:
                for (row, col) in self.coefMatrix:
                    if row == row_to_delete[1]:
                        entries_to_remove.append((row, col))
                for row, col in entries_to_remove:
                    del self.coefMatrix[(row, col)]

            glp_del_rows(self.problem, 1, row_to_delete)
            self.constr_ids.remove(constr_id)



    def update(self):
        """ Update internal structure. Used for efficient lazy updating. """

        num_constraints = glp_get_num_rows(self.problem)
        coef_ind, coef_val, n_vars = self.init_constr_arrays()

        # if the constraint matrix is empty but constraints were added 
        #  to the problem, these are copied to the matrix, which will be
        #  loaded afterwards

        if self.coefMatrix == {} and num_constraints > 0:
            for i in range(1, num_constraints + 1):
                glp_get_mat_row(self.problem, i, coef_ind, coef_val)
                for j in range(1, n_vars + 1):
                    if coef_val[j] != 0:
                        self.coefMatrix[(i, coef_ind[j])] = coef_val[j]

        if self.coefMatrix != {}:
            nEntries = len(self.coefMatrix) + 1

            rows_ind = intArray(nEntries)
            cols_ind = intArray(nEntries)
            coeffs = doubleArray(nEntries)

            i = 1
            for entry in self.coefMatrix.items():
                rows_ind[i] = entry[0][0]
                cols_ind[i] = entry[0][1]
                coeffs[i] = entry[1]
                i += 1

            glp_load_matrix(self.problem, nEntries - 1, rows_ind, cols_ind, coeffs)


    def set_presolve(self, active=False):
        """ Set glpk presolver on or off

        Arguments:
            active : bool -- uses glpk presolver  (default: False)
        """
        self.presolve = active

    def solve_lp(self, objective, model=None, constraints=None, get_shadow_prices=False, get_reduced_costs=False):
        """ Solve an LP optimization problem.

        Arguments:
            objective : dict (of str to float) -- reaction ids in the objective function and respective
                        coefficients, the sense is maximization by default
            model : ConstraintBasedModel -- model (optional, leave blank to reuse previous model structure)
            constraints : dict (of str to (float, float)) -- environmental or additional constraints (optional)
            get_shadow_prices : bool -- return shadow price information if available (optional, default: False)
            get_reduced_costs : bool -- return reduced costs information if available (optional, default: False)
        Returns:
            Solution
        """

        return self._generic_solve(
            None, objective, GLP_MAX, model, constraints, get_shadow_prices,
            get_reduced_costs)

    def solve_qp(
        self, quad_obj, lin_obj, model=None, constraints=None, get_shadow_prices=False, get_reduced_costs=False):
        """ Solve a QP optimization problem. However, this is not possible with gurobi

        Arguments:
            quad_obj : dict (of (str, str) to float) -- map reaction pairs to respective coefficients
            lin_obj : dict (of str to float) -- map single reaction ids to respective linear coefficients
            model : ConstraintBasedModel -- model (optional, leave blank to reuse previous model structure)
            constraints : dict (of str to (float, float)) -- overriding constraints (optional)
            get_shadow_prices : bool -- return shadow price information if available (default: False)
            get_reduced_costs : bool -- return reduced costs information if available (default: False)

        Returns:
            Solution
        """

        # An exception is raised if the user attempts to solve a quadratic
        # program with GLPK
        raise Exception('GLPK does not solve quadratic programming problems')

    def _generic_solve(self, quad_obj, lin_obj, sense, model=None, constraints=None, get_shadow_prices=False,
                       get_reduced_costs=False):

        if model:
            self.build_problem(model)

        if not self.problem:
            raise Exception('A model must be given if solver is used for the first time.')

        if (self.coefMatrix) != {} and (glp_get_num_nz(self.problem) > len(self.coefMatrix)):
            self.update()

        if constraints:
            old_constraints = {}

            for r_id, (lb, ub) in constraints.items():
                ind_col = glp_find_col(self.problem, r_id)
                old_constraints[r_id] = (glp_get_col_lb(self.problem, ind_col), glp_get_col_ub(self.problem, ind_col))
                self.set_var_bounds(ind_col, lb, ub)

        if lin_obj:
            for r_id, f in lin_obj.items():
                if f:
                    ind_col = glp_find_col(self.problem, r_id)
                    glp_set_obj_coef(self.problem, ind_col, f)

        if quad_obj:
            warn('GLPK does not solve quadratic programming self.problems')

        glp_set_obj_dir(self.problem, sense)

        # check if self.problem is MILP or LP, if it is an MILP call mip generic solver
        nBin_var = glp_get_num_bin(self.problem)
        nInt_var = glp_get_num_int(self.problem)

        if nBin_var > 0 or nInt_var > 0:
            if constraints:
                return self._generic_solve_mip(old_constraints, get_shadow_prices, get_reduced_costs)
            else:
                return self._generic_solve_mip(None, get_shadow_prices, get_reduced_costs)

        if self.presolve:
            self.smcp.presolve = GLP_ON

        #glp_scale_prob(self.problem, GLP_SF_AUTO)
        glp_simplex(self.problem, self.smcp)

        self.problemStatus = glp_get_status(self.problem)

        status = status_mapping[
            self.problemStatus] if self.problemStatus in status_mapping else Status.UNKNOWN

        message = str(self.problemStatus)

        if status == Status.OPTIMAL:
            fobj = glp_get_obj_val(self.problem)

            values = OrderedDict([(r_id, glp_get_col_prim(self.problem, glp_find_col(self.problem, r_id)))
                                 for r_id in self.var_ids])

            # if metabolite is disconnected no constraint will exist
            shadow_prices = OrderedDict([(m_id, glp_get_row_dual(self.problem, glp_find_row(self.problem, m_id)))
                                         for m_id in self.constr_ids
                                         if glp_find_row(self.problem, m_id)]) if get_shadow_prices else None

            reduced_costs = OrderedDict([(r_id, glp_get_col_dual(self.problem, glp_find_col(self.problem, r_id)))
                                         for r_id in self.var_ids]) if get_reduced_costs else None

            solution = Solution(status, message, fobj, values, shadow_prices, reduced_costs)

        else:
            solution = Solution(status, message)

        #reset objective function
        num_cols = glp_get_num_cols(self.problem)
        for ind_col in range(0, num_cols + 1):
            glp_set_obj_coef(self.problem, ind_col, 0)

        #reset old constraints because temporary constraints should not be
        #persistent
        if constraints:
            for r_id, (lb, ub) in old_constraints.items():
                ind_col = glp_find_col(self.problem, r_id)
                self.set_var_bounds(ind_col, lb, ub)

        return solution

    def _generic_solve_mip(self, old_constraints=None, get_shadow_prices=False, get_reduced_costs=False):

        glp_intopt(self.problem, self.iocp)

        # take care of status mapping
        self.problemStatus = glp_mip_status(self.problem)
        status = status_mapping[
            self.problemStatus] if self.problemStatus in status_mapping else Status.UNKNOWN

        message = str(self.problemStatus)

        if status == Status.OPTIMAL:
            fobj = glp_mip_obj_val(self.problem)
            values = OrderedDict([(r_id, glp_mip_col_val(self.problem, glp_find_col(self.problem, r_id)))
                                 for r_id in self.var_ids])

            # i'm not sure if one can get shadow prices and reduced costs for glpk mip problem!!!!!!
            # if metabolite is disconnected no constraint will exist
            shadow_prices = OrderedDict([(m_id, glp_get_row_dual(self.problem, glp_find_row(self.problem, m_id)))
                                         for m_id in self.constr_ids
                                         if glp_find_row(self.problem, m_id)]) if get_shadow_prices else None

            reduced_costs = OrderedDict([(r_id, glp_get_col_dual(self.problem, glp_find_col(self.problem, r_id)))
                                         for r_id in self.var_ids]) if get_reduced_costs else None

            solution = Solution(status, message, fobj, values, shadow_prices, reduced_costs)

        else:
            solution = Solution(status, message)

        #reset objective function
        num_cols = glp_get_num_cols(self.problem)
        for ind_col in range(0, num_cols + 1):
            glp_set_obj_coef(self.problem, ind_col, 0)

        #reset old constraints because temporary constraints should not be
        #persistent
        if old_constraints:
            for r_id, (lb, ub) in old_constraints.items():
                ind_col = glp_find_col(self.problem, r_id)
                self.set_var_bounds(ind_col, lb, ub)

        return solution

    def set_var_bounds(self, ind_col, lb, ub):
        """ Defines the given column/variable lower and upper bounds.

        Arguments:
            ind_col : int -- the index of the column/variable whose bounds are to be defined 
            lb: float -- lower bound for the given variable
            ub : float -- upper bound for the given variable
        """

        if (lb is None or lb <= -10e6) and (ub is None or ub >= 10e6):
            glp_set_col_bnds(self.problem, ind_col, GLP_FR, -10e6, 10e6)
        elif (lb is None or lb <= -10e6) and ub is not None:
            glp_set_col_bnds(self.problem, ind_col, GLP_UP, -10e6, ub)
        elif lb is not None and (ub is None or ub >= 10e6):
            glp_set_col_bnds(self.problem, ind_col, GLP_LO, lb, 10e6)
        elif lb == ub:
            glp_set_col_bnds(self.problem, ind_col, GLP_FX, lb, ub)
        elif lb != ub:
            glp_set_col_bnds(self.problem, ind_col, GLP_DB, lb, ub)

    def set_constr_bounds(self, ind_row, sense, rhs):
        """ Defines then give row/constraint bounds.

        Arguments:
            ind_row : int -- the index of the row/constraint whose bounds are to be defined 
            sense: str -- the sense of the constraint, must be '>', '<', or "="
            rhs : float -- the right-hand side of the constraint
        """

        if rhs is not None:
            if (sense == '>'):
                glp_set_row_bnds(self.problem, ind_row, GLP_LO, rhs, 10e6)
            elif (sense == '<'):
                glp_set_row_bnds(self.problem, ind_row, GLP_UP, -10e6, rhs)
            elif (sense == '='):
                glp_set_row_bnds(self.problem, ind_row, GLP_FX, rhs, rhs)
        else:
            glp_set_row_bnds(self.problem, ind_row, GLP_FR, -10e6, 10e6)

    def init_constr_arrays(self):
        """ Initializes the arrays required to set the LP problem
        matrix row and returns them together with the number of
        variables in the problem.

        Returns:
            coef_ind : intArray -- the column indexes in the matrix row
            coef_val : doubleArray -- the entries in the matrix row
            n_vars: int --  the number of variables in the given problem
        """

        n_vars = glp_get_num_cols(self.problem)
        coef_ind = intArray(n_vars + 1)
        coef_val = doubleArray(n_vars + 1)

        for i in range(0, n_vars + 1):
            coef_ind[i] = i
            coef_val[i] = 0.

        return (coef_ind, coef_val, n_vars)
