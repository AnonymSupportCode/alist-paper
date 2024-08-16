'''
File: count.py
Description: Count reduce operation


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
from graph.inference_graph import InferenceGraph

# FIXME opvars and getting instantiations of variables
def reduce(alist: Alist, children: List[Alist], G: InferenceGraph):
    variables = alist.variables()
    data = [x.instantiation_value(alist.get(tt.OPVAR)) for x in children
            if (x not in list(variables.keys()) and x not in list(variables.values()))]
    item_count = len(data)
    try:
        if item_count == 1 and children[0].get(tt.OP) == 'list':
            item_count = len(json.loads(data[0])) # parse string to list and get list len
    except:
        print("Count error")
    alist.instantiate_variable(alist.get(tt.OPVAR), item_count)

    alist.instantiate_variable(tt.COV, estimate_uncertainty(
        children, False, alist.get(tt.OP), len(children)
    ))
    return alist
