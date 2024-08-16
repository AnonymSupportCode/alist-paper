'''
File: min.py
Description: minimum reduce operation


'''

from typing import List
import json
from graph.alist import Alist
from graph.alist import Attributes as tt
from graph.alist import VarPrefix as vx
from graph.alist import Branching as br
from graph.alist import States as states
from graph.alist import NodeTypes as nt
from frank.util import utils
from frank.uncertainty.aggregateUncertainty import estimate_uncertainty
from frank.reduce import propagate
from graph.inference_graph import InferenceGraph


def reduce(node: Alist, children: List[Alist], G: InferenceGraph):
    opvars = node.getOpVar()
    if len(opvars) > 1:
        operands = []
        opvarval = {}
        for ov in opvars:
            for c in children:
                opvarval[ov] = utils.get_number(c.instantiation_value(ov), 0)
        operands = [opvarval[x] for x in opvars if opvarval[x] != None]
        node.instantiate_variable(opvars,operands)
        if operands: 
            result = min(operands)
        else:
            return None
    elif len(opvars) == 1 and len(children) == 1 and '[' in str(children[0].instantiation_value(opvars[0])) and ']' in str(children[0].instantiation_value(opvars[0])):
        operands = []
        opvarval = {}
        try:
            values = json.loads(children[0].instantiation_value(opvars[0]))
            if values:
                result = min(values)
            else:
                return None
        except:
            print("Error in min fn")
            return None
            
    else:
        projvar = node.projection_variable_names()[0]
        data = {x: utils.get_number(x.instantiation_value(
        node.get(tt.OPVAR)), 999999999999999) for x in children if x.instantiation_value(
          node.get(tt.OPVAR))}
        if data:
            minNode = min(data, key=data.get)
            minValue = data[minNode]
            node.instantiate_variable(node.get(tt.OPVAR), minValue)
            result = minNode.get(projvar)
        else:
            return None

    node.instantiate_variable(
        node.projection_variable_names()[0], 
        result)

    node.instantiate_variable(tt.OPVALUE, result)


    node.instantiate_variable(tt.COV, estimate_uncertainty(
        children, True, node.get(tt.OP), len(children)
    ))
    return node
