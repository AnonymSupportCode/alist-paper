'''
File: lte.py
Description: less-than-or-equal-to reduce operation


'''
from typing import List
from graph.alist import Alist
from graph.alist import Attributes as tt
from graph.alist import VarPrefix as vx
from graph.alist import Branching as br
from graph.alist import States as states
from graph.alist import Contexts as ctx
from graph.alist import NodeTypes as nt
from graph.inference_graph import InferenceGraph

from frank.util import utils
from frank.uncertainty.aggregateUncertainty import estimate_uncertainty
from frank.reduce import propagate
from graph.inference_graph import InferenceGraph


def reduce(node: Alist, children: List[Alist], G: InferenceGraph):
    # get projected values from child nodes
    opvars = node.getOpVar()
    if not isinstance(opvars,list):
        return
    operands = []
    opvarval = {}
    for ov in opvars:
        for c in children:
            opvarval[ov] = c.instantiation_value(ov)
    operands = [opvarval[x] for x in opvars if opvarval[x] != None]

    node.instantiate_variable(opvars,operands)

    result = True
    if len(operands) == 2:       
        result = operands[0] <= operands[1]
        result = str(result).lower()
    elif len(children) == 1 and node.get(tt.OP) == children[0].get(tt.OP):
        # get projected values from child nodes
        projected_vals = []
        for c in children:
            value = c.projected_value()
            if value:
                projected_vals.append(value)
        if len(projected_vals) == 1:
            # when node has one child with the same comparison operation, then copy projected value from  parent node.
            result = projected_vals[0]
    else:
         return None      

    node.instantiate_variable(
        node.projection_variable_names()[0], 
        result)
    node.instantiate_variable(tt.OPVALUE, result)

    return node
