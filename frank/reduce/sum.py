'''
File: sum.py
Description: Sum reduce operation


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
    if not isinstance(opvars,list):
        return
    operands = []
    opvarval = {}
    if len(opvars) > 1:
        for ov in opvars:
            for c in children:
                opvarval[ov] = utils.get_number(c.instantiation_value(ov), 0)
        operands = [opvarval[x] for x in opvars if opvarval[x] != None]
    elif len(opvars) == 1 and len(children)==1 and '[' in str(children[0].instantiation_value(opvars[0])) and ']' in str(children[0].instantiation_value(opvars[0])):
        try:
            operands = json.loads(children[0].instantiation_value(opvars[0])) 
            operands = list(map(lambda x: utils.get_number(x, 0), operands))           
        except:
            print("Error in sum fn")
            return None

    node.instantiate_variable(opvars,operands)

    result = 0
    if operands: 
        result = sum(operands)
    else:
         return None
      
    node.instantiate_variable(
        node.projection_variable_names()[0], 
        result)
    node.instantiate_variable(tt.OPVALUE, result)

    return node