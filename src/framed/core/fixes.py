'''
Fixes to clean up common models from different sources/groups.

@author: Daniel Machado

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
   
'''
from framed.core.models import GPRConstrainedModel


def fix_bigg_model(model, boundary_metabolites=True, reversibility=True, bounds=True, bigg_ids=True):
    """ Fix models from BiGG.
    
    Arguments:
        boundary_metabolites : bool -- remove boundary metabolites (ending with '_b') (default: True) 
        reversibility : bool -- make reaction reversibility consistent with the bounds (default: True) 
        clean_bounds : bool -- remove artificially large bounds (unbounded = no bounds) (default: True) 
        bigg_ids : bool -- remove _LPAREN_, _RPAREN_, _DASH_ from the ids (default: True) 
    """
    if boundary_metabolites:
        remove_boundary_metabolites(model)
    if reversibility:
        fix_reversibility(model)
    if bounds:
        clean_bounds(model)
    if bigg_ids:
        clean_bigg_ids(model)


def remove_boundary_metabolites(model):
    """ Remove remove boundary metabolites (ending with '_b'). """

    drains = filter(lambda m_id: m_id.endswith('_b'), model.metabolites)
    model.remove_metabolites(drains)


def fix_reversibility(model):
    """ Make reaction reversibility consistent with the bounds. """

    for r_id, (lb, _) in model.bounds.items():
        model.reactions[r_id].reversibility = True if lb is None else lb < 0


def clean_bounds(model, threshold=1000):
    """ Remove artificially large bounds (unbounded = no bounds). """

    for r_id, (lb, ub) in model.bounds.items():
        model.bounds[r_id] = (lb if lb > -threshold else None, ub if ub < threshold else None)


def clean_bigg_ids(model):
    clean = lambda x: x.replace('_LPAREN_', '_').replace('_RPAREN_', '_').replace('_DASH_', '_').rstrip('_')

    def key_replace(ord_dict, key, new_key):
        item = ord_dict[key]
        del ord_dict[key]
        ord_dict[new_key] = item


    for m_id, metabolite in model.metabolites.items():
        metabolite.id = clean(m_id)
        key_replace(model.metabolites, m_id, metabolite.id)

    for r_id, reaction in model.reactions.items():
        reaction.id = clean(r_id)
        key_replace(model.reactions, r_id, reaction.id)
        key_replace(model.bounds, r_id, reaction.id)
        key_replace(model.objective, r_id, reaction.id)

        if isinstance(model, GPRConstrainedModel):
            key_replace(model.rules, r_id, reaction.id)
            key_replace(model.rule_functions, r_id, reaction.id)

    for (m_id, r_id) in model.stoichiometry.keys():
        key_replace(model.stoichiometry, (m_id, r_id), (clean(m_id), clean(r_id)))
        