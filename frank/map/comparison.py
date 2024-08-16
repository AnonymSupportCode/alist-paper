'''
File: comparison.py
Description: Comparison decomposition of Alist


'''

from graph.alist import Alist
from graph.alist import Attributes as tt
from graph.alist import VarPrefix as vx
from graph.alist import Branching as br
from graph.alist import States as states
from graph.alist import Contexts as ctx
from graph.alist import NodeTypes as nt
from graph.inference_graph import InferenceGraph
from .map import Map
import frank.context


class Comparison(Map):
    def __init__(self):
        pass

    def decompose(self, alist: Alist, G: InferenceGraph=None):
        opvars = alist.getOpVar()
        # check for comparison operations: eq, lt, gt, lte, gte and for multiple variables in operation variable
        if alist.get(tt.OP).lower() not in ['eq', 'lt', 'gt', 'lte', 'gte'] \
                or len(opvars) < 2:
            return None

        attrs_exclude = []
        contains_default_proj = alist.has_default_projection_variable()
        if contains_default_proj:
            attrs_exclude = [vx.PROJECTION + alist.get(tt.OP)] # do copy the default proj var to successors
        
        map_op = 'compare'
        map_op_node = alist.copy()
        reduce_op = "list"
        context = map_op_node.get(tt.CONTEXT)

        map_op_node.set(tt.OP, map_op)
        map_op_node.cost = alist.cost + 1
        map_op_node.branch_type = br.AND
        map_op_node.state = states.EXPLORED
        map_op_node.parent_decomposition = 'compare'
        map_op_node.node_type = nt.HNODE

        reduce_op_node = map_op_node.copy()
        reduce_op_node.set(tt.OP, alist.get(tt.OP))

        successors = []
        for v in opvars:
            opvar_value = alist.get(v)
            if isinstance(opvar_value, dict):
                child = Alist(**opvar_value)
                child.cost = map_op_node.cost + 1
                child.node_type = nt.ZNODE
                child.set(tt.CONTEXT, map_op_node.get(tt.CONTEXT))
                frank.context.flush(child, [tt.TIME])
                child.check_variables()
                successors.append(child)
            else:
                child = Alist()
                child.set(tt.OP, "value")
                child.set(tt.OPVAR, v)
                child.set(v, opvar_value)
                child.cost = map_op_node.cost + 1
                child.node_type = nt.ZNODE
                child.set(tt.CONTEXT, map_op_node.get(tt.CONTEXT))
                frank.context.flush(child, [tt.TIME])
                child.check_variables()
                successors.append(child)
        return (map_op_node, [reduce_op_node], successors)
