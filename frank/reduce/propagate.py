'''
File: propagate.py
Description: Operation to propagate child alists to parents


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


def projections(parent: Alist, alists_to_propagate):
    ''' propagate projection from selected child alist to its parent [in place]'''

    # copy projection vars of min alist to parent
    for c in alists_to_propagate:
        projVars = c.projection_variables()
        if projVars:
            for pvkey, pv in projVars.items():
                parent.instantiate_variable(
                    pvkey, c.instantiation_value(pvkey), insert_missing=True)
