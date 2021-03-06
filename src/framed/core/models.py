""" This module defines base classes for metabolic modeling.

@author: Daniel Machado

TODO: Add self consistency check (e.g: no disconnected components)
TODO: Add explicit (graph-based) gene-reaction associations

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

"""

from collections import OrderedDict


class Metabolite:
    """ Base class for modeling metabolites. """


    def __init__(self, elem_id, name=None, compartment=None):
        """
        Arguments:
            elem_id : String -- a valid unique identifier
            name : String -- common metabolite name
            compartment : String -- compartment containing the metabolite
        """
        self.id = elem_id
        self.name = name
        self.compartment = compartment

    def __str__(self):
        return self.name if self.name else self.id


class Reaction:
    """ Base class for modeling reactions. """

    def __init__(self, elem_id, name=None, reversible=True):
        """
        Arguments:
            elem_id : String -- a valid unique identifier
            name : String -- common reaction name
        """
        self.id = elem_id
        self.name = name
        self.reversible = reversible

    def __str__(self):
        return self.name if self.name else self.id


class Gene:
    """ Base class for modeling genes. """

    def __init__(self, elem_id, name=None):
        """
        Arguments:
            elem_id : String -- a valid unique identifier
            name : String -- common gene name
        """
        self.id = elem_id
        self.name = name

    def __str__(self):
        return self.name if self.name else self.id


class Compartment:
    """ Base class for modeling compartments. """

    def __init__(self, elem_id, name=None):
        """
        Arguments:
            elem_id : String -- a valid unique identifier
            name : String -- compartment name
        """
        self.id = elem_id
        self.name = name

    def __str__(self):
        return self.name if self.name else self.id


class StoichiometricModel:
    """ Base class for all metabolic models implemented as a bipartite network.
    Contains the list of metabolites, reactions, compartments, and stoichiometry.
    """

    def __init__(self, model_id):
        """
        Arguments:
            model_id : String -- a valid unique identifier
        """
        self.id = model_id
        self.metabolites = OrderedDict()
        self.reactions = OrderedDict()
        self.compartments = OrderedDict()
        self.stoichiometry = OrderedDict()
        self._clear_temp()

    def _clear_temp(self):
        self._m_r_lookup = None
        self._r_m_lookup = None
        self._s_matrix = None


    def add_metabolites(self, metabolites):
        """ Add a list of metabolites to the model.

        Arguments:
            metabolites : list of Metabolite
        """
        for metabolite in metabolites:
            self.add_metabolite(metabolite)

    def add_metabolite(self, metabolite):
        """ Add a single metabolite to the model.
        If a metabolite with the same id exists, it will be replaced.
        If the metabolite compartment is defined, then it must exist in the model.

        Arguments:
            metabolite : Metabolite
        """
        if metabolite.compartment in self.compartments or not metabolite.compartment:
            self.metabolites[metabolite.id] = metabolite
            self._clear_temp()

    def add_reactions(self, reactions):
        """ Add a list of reactions to the model.

        Arguments:
            reactions : list of Reaction
        """
        for reaction in reactions:
            self.add_reaction(reaction)
            self._clear_temp()

    def add_reaction(self, reaction):
        """ Add a single reaction to the model.
        If a reaction with the same id exists, it will be replaced.

        Arguments:
            reaction : Reaction
        """
        self.reactions[reaction.id] = reaction
        self._clear_temp()

    def add_compartments(self, compartments):
        """ Add a list of compartments to the model.

        Arguments:
            compartments : list of Compartment
        """
        for compartment in compartments:
            self.add_compartment(compartment)

    def add_compartment(self, compartment):
        """ Add a single compartment to the model.
        If a compartment with the same id exists, it will be replaced.

        Arguments:
            compartment : Compartment
        """
        self.compartments[compartment.id] = compartment

    def add_stoichiometry(self, stoichiometry, replace=False):
        """ Add stoichiometric coefficients (weighted edges between metabolites and reactions).
        Negative coefficients represent consumption, positive coefficients represent production.
        If coefficients for the same metabolite-reaction pairs exist in the model, they will be replaced.

        Arguments:
            stoichiometry : list of (str, str, float) -- metabolite id, reaction id, coefficient
            replace : bool -- replace old coefficient with new instead of adding (default: False)
        """
        for m_id, r_id, coeff in stoichiometry:
            if m_id in self.metabolites and r_id in self.reactions:
                if (m_id, r_id) not in self.stoichiometry or replace:
                    self.stoichiometry[(m_id, r_id)] = coeff
                else:
                    coeff += self.stoichiometry[(m_id, r_id)]
                    if coeff:
                        self.stoichiometry[(m_id, r_id)] = coeff
                    else:
                        del self.stoichiometry[(m_id, r_id)]

        self._clear_temp()

    def remove_metabolites(self, id_list):
        """ Remove a list of metabolites from the model.
        Also removes all the edges connected to the metabolites.

        Arguments:
            id_list : list of str -- metabolite ids
        """
        for m_id in id_list:
            if m_id in self.metabolites:
                del self.metabolites[m_id]
        for (m2_id, r_id) in self.stoichiometry:
            if m2_id in id_list:
                del self.stoichiometry[(m2_id, r_id)]
        self._clear_temp()

    def remove_metabolite(self, m_id):
        """ Remove a single metabolite from the model.
        Also removes all the edges connected to the metabolite.

        Arguments:
            m_id : str -- metabolite id
        """
        self.remove_metabolites([m_id])

    def remove_reactions(self, id_list):
        """ Remove a list of reactions from the model.
        Also removes all the edges connected to the reactions.

        Arguments:
            id_list : list of str -- reaction ids
        """
        for r_id in id_list:
            if r_id in self.reactions:
                del self.reactions[r_id]
        for (m_id, r2_id) in self.stoichiometry:
            if r2_id in id_list:
                del self.stoichiometry[(m_id, r2_id)]
        self._clear_temp()

    def remove_reaction(self, r_id):
        """ Remove a single reaction from the model.
        Also removes all the edges connected to the reaction.

        Arguments:
            r_id : str -- reaction id
        """
        self.remove_reactions([r_id])


    def remove_compartment(self, c_id, delete_metabolites=True):
        """ Remove a compartment from the model.
        Removes also all the metabolites in that compartment.

        Arguments:
            c_id : str -- compartment id
            delete_metabolites : Bool -- True (default)
        """
        if c_id in self.compartments:
            del self.compartments[c_id]

            if delete_metabolites:
                self.remove_metabolites([m_id for m_id, metabolite in self.metabolites.items()
                                         if metabolite.compartment == c_id])


    def get_reaction_substrates(self, r_id):
        """ Return the list of substrates for one reaction

        Arguments:
            r_id: str -- reaction id

        Returns:
            list [of str] -- substrates list
        """
        table = self.reaction_metabolite_lookup_table()
        return [m_id for m_id, coeff in table[r_id].items() if coeff < 0]


    def get_reaction_products(self, r_id):
        """ Return the list of products for one reaction

        Arguments:
            r_id: str -- reaction id

        Returns:
            list [of str] -- products list
        """
        table = self.reaction_metabolite_lookup_table()
        return [m_id for m_id, coeff in table[r_id].items() if coeff > 0]


    def get_reaction_neighbours(self, r_id):
        """ Return the list of metabolites connected to a reaction

        Arguments:
            r_id: str -- reaction id

        Returns:
            list [of str] -- metabolites list
        """
        table = self.reaction_metabolite_lookup_table()
        return [m_id for m_id, coeff in table[r_id].items() if coeff != 0]


    def get_metabolite_inputs(self, m_id):
        """ Return the list of input reactions for one metabolite

        Arguments:
            m_id: str -- metabolite id

        Returns:
            list [of str] -- input reactions list
        """
        table = self.metabolite_reaction_lookup_table()
        return [r_id for r_id, coeff in table[m_id].items() if coeff > 0]


    def get_metabolite_outputs(self, m_id):
        """ Return the list of output reactions for one metabolite

        Arguments:
            m_id: str -- metabolite id

        Returns:
            list [of str] -- output reactions list
        """
        table = self.metabolite_reaction_lookup_table()
        return [r_id for r_id, coeff in table[m_id].items() if coeff < 0]


    def get_metabolite_neighbours(self, m_id):
        """ Return the list of reactions connected to a metabolite

        Arguments:
            m_id: str -- metabolite id

        Returns:
            list [of str] -- reactions list
        """
        table = self.metabolite_reaction_lookup_table()
        return [r_id for r_id, coeff in table[m_id].items() if coeff != 0]


    def metabolite_reaction_lookup_table(self):
        """ Return the network topology as a nested map: metabolite id -> reaction id -> coefficient

        Returns:
            OrderedDict (of str to OrderedDict of str to float) -- lookup table
        """

        if not self._m_r_lookup:
            self._m_r_lookup = OrderedDict([(m_id, OrderedDict()) for m_id in self.metabolites])

            for (m_id, r_id), coeff in self.stoichiometry.items():
                self._m_r_lookup[m_id][r_id] = coeff

        return self._m_r_lookup


    def reaction_metabolite_lookup_table(self):
        """ Return the network topology as a nested map: reaction id -> metabolite id -> coefficient

        Returns:
            OrderedDict (of str to OrderedDict of str to float) -- lookup table
        """

        if not self._r_m_lookup:
            self._r_m_lookup = OrderedDict([(r_id, OrderedDict()) for r_id in self.reactions])

            for (m_id, r_id), coeff in self.stoichiometry.items():
                self._r_m_lookup[r_id][m_id] = coeff

        return self._r_m_lookup


    def stoichiometric_matrix(self):
        """ Return the full stoichiometric matrix represented by the network topology

        Returns:
            list (of list of float) -- stoichiometric matrix
        """

        if not self._s_matrix:
            self._s_matrix = [[self.stoichiometry[(m_id, r_id)] if (m_id, r_id) in self.stoichiometry else 0
                               for r_id in self.reactions]
                              for m_id in self.metabolites]

        return self._s_matrix


    def print_reaction(self, r_id, reaction_names=False, metabolite_names=False):
        """ Print a reaction to a text based representation.

        Arguments:
            r_id : str -- reaction id
            reaction_names : bool -- print reaction names instead of ids (default: False)
            metabolite_names : bool -- print metabolite names instead of ids (default: False)

        Returns:
            str -- reaction string
        """

        table = self.reaction_metabolite_lookup_table()

        r_repr = self.reactions[r_id].name if reaction_names else r_id
        m_repr = lambda m_id: self.metabolites[m_id].name if metabolite_names else m_id

        res = r_repr + ': '
        res += ' + '.join([m_repr(m_id) if coeff == -1.0 else str(-coeff) + ' ' + m_repr(m_id)
                           for m_id, coeff in table[r_id].items() if coeff < 0])
        res += ' <-> ' if self.reactions[r_id].reversible else ' --> '
        res += ' + '.join([m_repr(m_id) if coeff == 1.0 else str(coeff) + ' ' + m_repr(m_id)
                           for m_id, coeff in table[r_id].items() if coeff > 0])
        return res

    def to_string(self, reaction_names=False, metabolite_names=False):
        """ Print the model to a text based representation.

        Returns:
            str -- model string
        """
        return '\n'.join([self.print_reaction(r_id, reaction_names, metabolite_names)
                          for r_id in self.reactions])

    def __str__(self):
        return self.to_string()


class ConstraintBasedModel(StoichiometricModel):
    """ Base class for constraint-based models.
    Extends StoichiometricModel with flux bounds.
    """

    def __init__(self, model_id):
        """
        Arguments:
            model_id : String -- a valid unique identifier
        """
        StoichiometricModel.__init__(self, model_id)
        self.bounds = OrderedDict()
        self.objective = OrderedDict()
        self.biomass_reaction = None

    def set_bounds(self, bounds_list):
        """ Define flux bounds for a set of reactions

        Arguments:
            bounds_list : list (of str, float, float) -- reaction id, lower bound, upper bound
        """
        for r_id, lb, ub in bounds_list:
            self.set_flux_bounds(r_id, lb, ub)

    def set_flux_bounds(self, r_id, lb, ub):
        """ Define flux bounds for one reaction

        Arguments:
            r_id : str -- reaction id
            lb : float -- lower bound (use None to represent negative infinity)
            ub : float -- upper bound (use None to represent positive infinity)
        """
        if r_id in self.reactions:
            self.bounds[r_id] = (lb, ub)

    def set_lower_bound(self, r_id, lb):
        """ Define lower bound for one reaction

        Arguments:
            r_id : str -- reaction id
            lb : float -- lower bound (use None to represent negative infinity)
        """
        if r_id in self.reactions:
            _, ub = self.bounds[r_id]
            self.bounds[r_id] = lb, ub

    def set_upper_bound(self, r_id, ub):
        """ Define upper bound for one reaction

        Arguments:
            r_id : str -- reaction id
            ub : float -- upper bound (use None to represent positive infinity)
        """
        if r_id in self.reactions:
            lb, _ = self.bounds[r_id]
            self.bounds[r_id] = lb, ub

    def set_objective_coefficients(self, coefficients):
        """ Define objective coefficients for a list of reactions

        Arguments:
            coefficients : list (of str, float) -- reaction id, coefficient
        """
        for r_id, coeff, in coefficients:
            self.set_reaction_objective(r_id, coeff)

    def set_reaction_objective(self, r_id, coeff=0):
        """ Define objective coefficient for a single reaction

        Arguments:
            r_id : str -- reaction id
            coeff : float -- reaction objective (default: 0)
        """
        if r_id in self.reactions:
            self.objective[r_id] = coeff


    def add_reaction(self, reaction, lb=None, ub=None, coeff=0):
        """ Add a single reaction to the model.
        If a reaction with the same id exists, it will be replaced.

        Arguments:
            reaction : Reaction
            lb : float -- lower bound (default: None)
            ub : float -- upper bound (default: None)
            coeff : float -- objective coefficient (default: 0)
        """
        StoichiometricModel.add_reaction(self, reaction)

        if lb == None and not reaction.reversible:
            lb = 0

        self.bounds[reaction.id] = (lb, ub)
        self.objective[reaction.id] = coeff

    def remove_reactions(self, id_list):
        """ Remove a list of reactions from the model.
        Also removes all the edges connected to the reactions.

        Arguments:
            id_list : list of str -- reaction ids
        """
        StoichiometricModel.remove_reactions(self, id_list)
        for r_id in id_list:
            del self.bounds[r_id]
            del self.objective[r_id]

    def print_reaction(self, r_id, reaction_names=False, metabolite_names=False):
        """ Print a reaction to a text based representation.

        Arguments:
            r_id : str -- reaction id

        Returns:
            str -- reaction string
        """
        res = StoichiometricModel.print_reaction(self, r_id, reaction_names, metabolite_names)
        lb, ub = self.bounds[r_id]
        rev = self.reactions[r_id].reversible
        if lb != None and (rev or lb != 0.0) or ub != None:
            res += ' [{}, {}]'.format(lb if lb != None else '',
                                      ub if ub != None else '')
        coeff = self.objective[r_id]
        if coeff:
            res += ' @{}'.format(coeff)

        return res

    def detect_biomass_reaction(self):
        """ Detects biomass reaction in the model (searches by objective coefficient)

        Returns:
            str -- first reaction that matches (or else None)
        """

        if not self.biomass_reaction:
            matches = [r_id for r_id, coeff in self.objective.items() if coeff]

            if matches:
                self.biomass_reaction = matches[0]
                if len(matches) == 1:
                    print 'Biomass reaction detected:', self.biomass_reaction
                else:
                    print 'Multiple biomass reactions detected (first selected):', " ".join(matches)
            else:
                print 'No biomass reaction detected.'

        return self.biomass_reaction


class GPRConstrainedModel(ConstraintBasedModel):
    """ Base class for constraint-based models with GPR associations.
    Extends ConstraintBasedModel with genes and rules
    """

    def __init__(self, model_id):
        """
        Arguments:
            model_id : String -- a valid unique identifier
        """
        ConstraintBasedModel.__init__(self, model_id)
        self.genes = OrderedDict()
        self.rules = OrderedDict()
        self.rule_functions = OrderedDict()

    def add_genes(self, genes):
        """ Add a list of genes to the model.

        Arguments:
            genes : list of Gene
        """
        for gene in genes:
            self.add_gene(gene)

    def add_gene(self, gene):
        """ Add a gene metabolite to the model.
        If a gene with the same id exists, it will be replaced.

        Arguments:
            gene : Gene
        """
        self.genes[gene.id] = gene

    def add_reaction(self, reaction, lb=None, ub=None, rule=''):
        """ Add a single reaction to the model.
        If a reaction with the same id exists, it will be replaced.

        Arguments:
            reaction : Reaction
            lb : float -- lower bound (default: None)
            ub : float -- upper bound (default: None)
            rule : str -- GPR association rule (default: None)
        """
        ConstraintBasedModel.add_reaction(self, reaction, lb, ub)
        self.set_rule(reaction.id, rule)

    def remove_reactions(self, id_list):
        """ Remove a list of reactions from the model.
        Also removes all the edges connected to the reactions.

        Arguments:
            id_list : list of str -- reaction ids
        """
        ConstraintBasedModel.remove_reactions(self, id_list)
        for r_id in id_list:
            del self.rules[r_id]
            del self.rule_functions[r_id]

    def set_rules(self, rules):
        """ Define GPR association rules for a set of reactions

        Arguments:
            rules : list (of (str, str)) -- reaction id, rule
        """
        for r_id, rule in rules:
            self.set_rule(r_id, rule)

    def set_rule(self, r_id, rule):
        """ Define GPR association rule for one reaction

        Arguments:
            r_id : str -- reaction id
            rule : str -- GPR association rule
        """
        if r_id in self.reactions:
            self.rules[r_id] = rule
            self.rule_functions[r_id] = self._rule_to_function(rule)


    def eval_GPR(self, active_genes):
        """ Evaluate the GPR associations.

        Arguments:
            active_genes : list (of str) -- set of active genes

        Returns:
            list (of str) -- set of active reactions
        """
        genes_state = {gene: gene in active_genes for gene in self.genes}
        return [r_id for r_id, f in self.rule_functions.items() if f(genes_state)]


    def _rule_to_function(self, rule):
        if not rule:
            rule = 'True'
        else:
            rule = ' ' + rule.replace('(', '( ').replace(')', ' )') + ' '
            for gene in self.genes:
                rule = rule.replace(' ' + gene + ' ', ' x[\'' + gene + '\'] ')
        return eval('lambda x: ' + rule)


