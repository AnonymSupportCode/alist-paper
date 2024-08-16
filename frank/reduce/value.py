'''
File: value.py
Description: Value reduce operation that reduces multiple values to a single 
             one in the absence of a specified aggregation operation.


'''
import json
from typing import List
from collections import Counter
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
    total = 0.0
    numList = []
    nonNumList = []
    inst_vars = node.instantiated_attributes().keys()
    for c in children:
        for k, v in c.instantiated_attributes().items():
            if k not in inst_vars and k in node.attributes and k != tt.OP:
                c.instantiate_variable(k, v)

        # opVarValue = c.operation_value()
        opVarValue = c.get(tt.OPVALUE)
        if isinstance(opVarValue, str) and opVarValue[0] == '[' and opVarValue[-1] == ']':
            try:
                opVarValue = json.loads(opVarValue)
            except:
                pass
        else:
            opVarValue = [opVarValue]
        

        for opval in opVarValue:
            if utils.is_numeric(opval):
                total += float(opval)
                numList.append(float(opval))
            else:
                 nonNumList.append(opval)

    if not isinstance(node.get(tt.OPVAR), list):
        if numList or nonNumList:
            if len(numList) >= len(nonNumList):
                opVar = node.get(tt.OPVAR)
                valueToReturn = total / len(numList)
                if opVar == node.get(tt.TIME):
                    valueToReturn = str(int(valueToReturn))            
                node.instantiate_variable(opVar, valueToReturn)
                node.instantiate_variable(tt.OPVALUE, valueToReturn)
                if node.projection_variable_names() == [tt.PRJVAR]:
                    node.instantiate_variable(tt.PRJVAR, valueToReturn)
            else:
                # get modal value
                counts = dict(Counter(nonNumList))
                counts_set = set(counts.values())
                max_val = max(counts_set)
                items = [x for x,y in counts.items() if y == max_val]
                valueToReturn = json.dumps(items)
                node.instantiate_variable(node.get(tt.OPVAR), valueToReturn)
                node.instantiate_variable(tt.OPVALUE, valueToReturn)
                if node.projection_variable_names() == [tt.PRJVAR]:
                    node.instantiate_variable(tt.PRJVAR, valueToReturn)
        else:
            return None
    else:
        if opVarValue:            
            valueToReturn = json.dumps(opVarValue)
            node.instantiate_variable(node.get(tt.OPVAR), valueToReturn)
            node.instantiate_variable(tt.OPVALUE, valueToReturn)
            if node.projection_variable_names() == [tt.PRJVAR]:
                node.instantiate_variable(tt.PRJVAR, valueToReturn)
        else:
            return None


    node.instantiate_variable(tt.COV, estimate_uncertainty(
        children, len(numList) == len(
            children), node.get(tt.OP), len(children)
    ))
    return node
