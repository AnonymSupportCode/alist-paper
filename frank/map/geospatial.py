'''
File: geospatial.py
Description: Geospatial decomposition of Alist


'''

# import _context
import datetime
import math
from frank import config
from graph.alist import Alist as A
from graph.alist import Attributes as tt
from graph.alist import VarPrefix as vx
from graph.alist import Branching as br
from graph.alist import States as states
from graph.alist import Contexts as ctx
from graph.alist import NodeTypes as nt
from graph.inference_graph import InferenceGraph
from .map import Map
from frank.kb import rdf
from graph.inference_graph import InferenceGraph


class Geospatial(Map):

    def decompose(self, alist: A, G: InferenceGraph):
        # check if subject is empty or is a variable
        if not alist.get(tt.SUBJECT) \
                or alist.get(tt.SUBJECT).startswith(vx.PROJECTION) \
                or alist.get(tt.SUBJECT).startswith(vx.AUXILLIARY):
            return None

        # get the sub locations of the subject
        # TODO: perform geospatial decomp on OBJECT attribute

        sub_items = rdf.find_sub_location(
            alist.get(tt.SUBJECT).strip())
        if not sub_items:
            return None
        alist.data_sources.add('geonames')
        op_alist = alist.copy()
        op_alist.set(tt.OP, 'sum')
        # higher cost makes this decomposition more expensive
        op_alist.cost = alist.cost + 4
        op_alist.branch_type = br.AND
        op_alist.parent_decomposition = 'geospatial'
        op_alist.node_type = nt.HNODE
        # alist.link_child(op_alist)
        G.link(alist, op_alist, op_alist.parent_decomposition)

        for s in sub_items:
            child = alist.copy()
            child.set(tt.SUBJECT, s)
            child.set(tt.OP, 'value')
            child.cost = op_alist.cost + 1
            child.node_type = nt.ZNODE
            child.set(tt.CONTEXT, op_alist.get(tt.CONTEXT))
            # op_alist.link_child(child)
            G.link(op_alist, child, op_alist.parent_decomposition)

        return op_alist
