'''
File: rank.py
Description: rank reduce operation


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
    args = node.get(tt.OPVAR)
    if len(opvars) == 1 and len(args) == 2 and len(children) == 1 and \
         '[' in str(children[0].instantiation_value(opvars[0])) and ']' in str(children[0].instantiation_value(opvars[0])):
        operands = []
        try:
            operands = json.loads(children[0].instantiation_value(opvars[0]))            
            if not operands:
                return None
            data = [utils.get_number(x, 999999999999999) for x in operands]
            data = [x for x in data if x != 999999999999999]
            r = list(range(-len(data), len(data) + 1))
            index = max(min(max(r), args[1]), min(r))
            index = index - 1 if index > 0 else index
            sorted_data = sorted(data, reverse=True)
            result = sorted_data[index]
            node.instantiate_variable(opvars[0], result)

        except Exception as ex:
            print("Error in rank fn:" + str(ex))
            return None
    elif len(opvars) == 1 and len(args) == 2 and len(children) > 0:
        projvar = node.projection_variable_names()[0]
        try:
            data = {x: utils.get_number(x.instantiation_value(
              opvars[0]), 999999999999999) for x in children if x.instantiation_value(
               opvars[0])}
            data = {k:v for k,v in data.items() if v != 999999999999999}
            if data:
                r = list(range(-len(data), len(data) + 1))
                index = max(min(max(r), args[1]), min(r))
                index = index - 1 if index > 0 else index
                sorted_data = sorted(data.items(), key=lambda item:item[1], reverse=True)
                result_node, result_value = sorted_data[index]
                node.instantiate_variable(opvars[0], result_value)
                result = result_node.instantiation_value(projvar)
            else:
                return None
        except Exception as ex:
            print("Error in rank fn:" + str(ex))
            return None
    elif len(children) == 1 and node.get(tt.OP) == children[0].get(tt.OP):
        # get projected values from child nodes
        projected_vals = []
        for c in children:
            value = c.projected_value()
            if value:
                projected_vals.append(value)
        if len(projected_vals) == 1:
            # when node has one child with the same rank operation, then copy projected value from parent node.
            result = projected_vals[0]
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