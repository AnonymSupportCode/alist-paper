'''
File: temporal.py
Description: Temporal decomposition of Alist


'''

# import _context
import datetime
import math
import frank.config as config
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


class Temporal(Map):

    def decompose(self, alist: Alist, G:InferenceGraph=None):
        map_op = 'temporal'
        successors = []
        current_year = datetime.datetime.now().year
        branch_factor = config.config["temporal_branching_factor"]
        parent_year = None
        if alist.get(tt.TIME).startswith(vx.NESTING) or \
                not alist.get(tt.TIME):
            return (None, None, None)
        else:

            parent_year = datetime.datetime.strptime(alist.get(tt.TIME), '%Y')

        count = 0
        map_op_node = alist.copy()
        reduce_op = "regress"
        context = map_op_node.get(tt.CONTEXT)
        if context:
            if context[0]:
                if ctx.accuracy in context[0] and context[0][ctx.accuracy] == 'high':
                    op = 'gpregress'
                    if branch_factor <= 10:
                        # increase number of data points for regression
                        branch_factor = 20

            # if context[1] and ctx.datetime in context[1]:
            #     # use the ctx.datetime as current year if specified in context
            #     current_year = datetime.datetime.strptime(context[1][ctx.datetime], '%Y-%m-%d %H:%M:%S').year

        # flush context: needed to clear any query time context value
        #   whose corresponding alist attribute (t) has been modified
        frank.context.flush(map_op_node, [tt.TIME])

        map_op_node.set(tt.OP, map_op)
        map_op_node.cost = alist.cost + 2.0
        map_op_node.branch_type = br.AND
        map_op_node.state = states.EXPLORED
        map_op_node.parent_decomposition = 'temporal'
        map_op_node.node_type = nt.HNODE

        reduce_op_node = map_op_node.copy()
        reduce_op_node.set(tt.OP, reduce_op)

        reduce_op_node2 = map_op_node.copy()
        reduce_op_node2.set(tt.OP, reduce_op)

        # G.link(alist, op_node, op_node.parent_decomposition)
        if (current_year - parent_year.year) > branch_factor/2:
            for i in range(1, math.ceil(branch_factor/2)):
                child_a = alist.copy()
                child_a.set(tt.TIME, str(parent_year.year + i))
                child_a.set(tt.OP, "value")
                child_a.cost = map_op_node.cost + 1
                child_a.node_type = nt.ZNODE
                child_a.set(tt.CONTEXT, map_op_node.get(tt.CONTEXT))
                frank.context.flush(child_a, [tt.TIME])
                # G.link(op_node, child_a, 'value')
                successors.append(child_a)

                child_b = alist.copy()
                child_b.set(tt.TIME, str(parent_year.year - i))
                child_b.set(tt.OP, "value")
                child_b.cost = map_op_node.cost + 1
                child_b.set(tt.CONTEXT, map_op_node.get(tt.CONTEXT))
                frank.context.flush(child_b, [tt.TIME])
                child_b.node_type = nt.ZNODE
                # G.link(op_node, child_b, 'value')
                successors.append(child_b)
                count = count + 2
        elif parent_year.year >= current_year:
            for i in range(1, math.ceil(branch_factor)):
                child_a = alist.copy()
                child_a.set(tt.TIME, str(current_year - i))
                child_a.set(tt.OP, "value")
                child_a.cost = map_op_node.cost + 1
                child_a.node_type = nt.ZNODE
                child_a.set(tt.CONTEXT, map_op_node.get(tt.CONTEXT))
                frank.context.flush(child_a, [tt.TIME])
                # G.link(op_node, child_a, 'value')
                successors.append(child_a)
                count = count + 1

        for i in range(1, (branch_factor - count)):
            child_a = alist.copy()
            child_a.set(tt.TIME, str(parent_year.year - (count + i)))
            child_a.set(tt.OP, "value")
            child_a.cost = map_op_node.cost + 1
            child_a.node_type = nt.ZNODE
            child_a.set(tt.CONTEXT, map_op_node.get(tt.CONTEXT))
            frank.context.flush(child_a, [tt.TIME])
            # G.link(op_node, child_a, 'value')
            successors.append(child_a)

        # return (map_op_node, [reduce_op_node, reduce_op_node2], successors)
        return (map_op_node, [reduce_op_node], successors)
