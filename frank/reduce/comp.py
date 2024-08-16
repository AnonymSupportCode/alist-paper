'''
File: comp.py
Description: Set comprehension reduce operation


'''
import json
from ntpath import join
from typing import List

from graph.alist import Alist
from graph.alist import Attributes as tt
from graph.alist import VarPrefix as vx
from graph.alist import Branching as br
from graph.alist import States as states
from graph.alist import NodeTypes as nt
from frank.util import utils
from graph.inference_graph import InferenceGraph
from frank.processLog import pcolors as pcol


def reduce(alist: Alist, input_nodes: List[Alist], G: InferenceGraph):
    if not input_nodes:
        return None

    # get intersection of child values
    common_items = set()
    head, *tail = input_nodes
    # has_head_input = False
    # has_tail_inputs = False

    if head.get(tt.OP) != 'comp':
        v = head.projected_value()
        if type(v) == str and v[0] == '[' and v[-1] == ']':
            try:
                v = json.loads(v)
                common_items.update(v)
            except:
                pass
        else:
            common_items.add(v)

    if tail:
        tail_items = set()    
        for t in tail:    
            tail_items.add(v.projected_value())            
        common_items = common_items.intersection(tail_items)


    if not common_items:
        return None
    else:
        nodes_to_prune = G.child_alists(alist.id)
        # if common items not empty, prune existing successor before creating new siblings
    # else:
    #     # if common items not empty, prune existing successor before creating new siblings
    #     succ = G.child_alists(alist.id)
    #     for x in succ:
    #         if x.id != '0_':
    #             G.prune(x.id)
    #             print(f'{pcol.RED} successor pruned {x.id}{pcol.RESET} {x}{pcol.RESETALL}')

    if len(common_items) == 1:
        # check if the items are lists of singletons
        single_list = []
        try:
            single_list = json.loads(list(common_items)[0])
        except: pass
        if single_list:
            join_items = json.dumps(single_list)
        else:
            join_items = list(common_items)[0]
    else:
        join_items = json.dumps(list(common_items))

    alist.instantiate_variable(tt.OPVALUE, join_items)
    alist.instantiate_variable(alist.get(tt.OPVAR), join_items)
    # setup new sibling branch(s)
    parent = G.parent_alists(G.find_complement(alist.id)[0])[0]
    map_op_alist = parent.copy()
    map_op_alist.set(alist.get(tt.OPVAR), '')

    map_op_alist.set(tt.OP, parent.get(tt.OP))
    map_op_alist.set(tt.OPVAR, parent.get(tt.OPVAR))
    map_op_alist.state = states.EXPLORED
    map_op_alist.data_sources = alist.data_sources
    # set as an aggregation node to help with display rendering
    map_op_alist.node_type = nt.HNODE
    map_op_alist.check_variables()
    map_op_alist.instantiate_variable(alist.get(tt.OPVAR), join_items)

    parent_ = G.alist(parent.id + '_')
    reduce_op_alist = parent.copy()
    reduce_op_alist.set(tt.OP, parent_.get(tt.OP))
    reduce_op_alist.data_sources = alist.data_sources
    reduce_op_alist.node_type = nt.HNODE
    reduce_op_alist.check_variables()
    reduce_op_alist.instantiate_variable(alist.get(tt.OPVAR), join_items)

    print(f'{pcol.BLUE}set-comp >> {map_op_alist.id}{pcol.RESET} {map_op_alist}{pcol.RESETALL}')

    # create children of the new branch
    # copy to avoid using different version from another thread in loop
    op_alist_copy = map_op_alist.copy()
    successors = []
    child_opvars = op_alist_copy.get(tt.OPVAR)
    if isinstance(child_opvars, list) and len(op_alist_copy.getOpVar()) < len(child_opvars) and len(op_alist_copy.getOpVar())==1:
        # to handle cases like the RANK($x, 1) reduce fns
        child_opvars = op_alist_copy.getOpVar()[0]
    for ff in common_items:
        succ: Alist = op_alist_copy.copy()
        succ.set(tt.OP, 'value')
        succ.set(tt.OPVAR, child_opvars)
        succ.set(alist.get(tt.OPVAR), ff)
        succ.instantiate_variable(alist.get(tt.OPVAR), ff)
        for ref in succ.variable_references(alist.get(tt.OPVAR)):
            if ref not in [tt.OPVAR]:
                succ.set(ref, ff)
        succ.data_sources = alist.data_sources
        succ.node_type = nt.ZNODE
        succ.check_variables()
        successors.append(succ)
        print(
            f'{pcol.BLUE}  set-comp-child >>> {succ.id}{pcol.RESET} {succ}{pcol.RESETALL}')

    G.subdivide(parent.id, parent_.id, map_op_alist, [reduce_op_alist], successors, successor_same_states=True)
    alist.state = states.REDUCED
    
    G.add_alist(alist)
    G.link(alist, map_op_alist, 'set-comp', new_child_id=False)

        
    for x in nodes_to_prune:
        if x.id != '0_':
            G.prune(x.id)
            print(f'{pcol.RED} successor pruned {x.id}{pcol.RESET} {x}{pcol.RESETALL}')

    p_ = G.parent_ids(G.find_complement(alist.id)[0])[0] + '_'
    G.remove_link(alist.id,p_)

    return alist
