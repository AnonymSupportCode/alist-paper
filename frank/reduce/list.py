'''
File: list.py
Description: Reduce operation that returns a list of values.


'''
import json
from typing import List
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
    data = []
    for x in children:
        opvs = []
        opv = node.getOpVar()
        if isinstance(opv, str):
            opvs.append(opv)
        elif isinstance(opv, list):
            opvs = opv

        for ov in opvs:
            v = x.instantiation_value(ov)
            if v and type(v) == str and v[0] == '[' and v[-1] == ']':
                try:
                    v = json.loads(v)
                    data.extend(v)
                except:
                    pass
            else:
                data.append(v)
       
    data_str = json.dumps(data)
    node.instantiate_variable(node.getOpVar(), data_str)
    node.instantiate_variable(tt.OPVALUE, data_str)
    node.instantiate_variable(
        node.projection_variable_names()[0], 
        data_str)

    # TODO: port code for cov calculations
    node.instantiate_variable(tt.COV, estimate_uncertainty(
        children, False, node.get(tt.OP), len(children)
    ))
    return node
