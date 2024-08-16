'''
File: normalize.py
Description: Normalization decomposition of A
'''

# import _context
from graph.alist import Alist
from graph.alist import Attributes as tt
from graph.alist import VarPrefix as vx
from graph.alist import Branching as br
from graph.alist import States as states
from graph.alist import NodeTypes as nt
from frank.kb import rdf
from .map import Map
from graph.inference_graph import InferenceGraph
import frank.context


class Normalize(Map):
    def __init__(self):
        pass

    def decompose(self, alist: Alist, G: InferenceGraph=None):
        map_op = 'normalize'
        reduce_op = 'comp'
        nest_vars = alist.uninstantiated_nesting_variables()
        used_nest_vars = {}
        for nk,nv in nest_vars.items():
            for k,v in alist.attributes.items():
                if isinstance(v, str) and v== nk:
                    used_nest_vars[nk] = nv
                    break
                elif isinstance(v, list) and nk in v:
                    used_nest_vars[nk] = nv
                    break

        successors = []
        for nest_attr, v in used_nest_vars.items():
            if NormalizeFn.FILTER in v:
                map_op_node = alist.copy()
                map_op_node.set(tt.OP, map_op)
                map_op_node.set(tt.OPVAR, nest_attr)
                del map_op_node.attributes[nest_attr]
                map_op_node.cost = alist.cost + 1
                map_op_node.branch_type = br.AND
                map_op_node.state = states.EXPLORED
                map_op_node.parent_decomposition = map_op
                map_op_node.node_type = nt.HNODE
                map_op_node.check_variables()

                reduce_op_node = map_op_node.copy()
                reduce_op_node.set(tt.OP, reduce_op)
                reduce_op_node.check_variables()

                # check for filters that heuristics apply to
                # e.g type==country and location==Europs
                filter_patterns = {}
                geo_class = ''
                for x in v[NormalizeFn.FILTER]:
                    prop = str(x['p'])
                    obj = str(x['o'])
                    if prop == 'type' and (obj == 'country' or obj == 'continent'):
                        filter_patterns['geopolitical'] = obj
                    elif prop == 'location':
                        filter_patterns['location'] = obj

                if {'geopolitical', 'location'} <= set(filter_patterns):
                    # use heuristics to create a single alist containing the
                    # conjunction to find the X located in Y
                    child = Alist(**{})
                    child.set(tt.OP, 'list')
                    child.set(tt.OPVAR, nest_attr)
                    child.set(tt.SUBJECT, nest_attr)
                    child.set(tt.PROPERTY, '__geopolitical:' +
                              filter_patterns['geopolitical'])
                    child.set(tt.OBJECT, filter_patterns['location'])
                    child.cost = map_op_node.cost + 1
                    child.state = states.UNEXPLORED
                    child.node_type = nt.ZNODE
                    child.set(tt.CONTEXT, map_op_node.get(tt.CONTEXT))
                    child = frank.context.inject_query_context(child)
                    child.check_variables()
                    successors.append(child)
                    return (map_op_node, [reduce_op_node], successors)
                else:
                    for x in v[NormalizeFn.FILTER]:
                        child = Alist(**{})
                        child.set(tt.OP, 'list')
                        child.set(tt.OPVAR, nest_attr)
                        child.set(tt.SUBJECT, nest_attr)
                        for attr, attrval in x.items():
                            child.set(attr, attrval)
                        child.cost = map_op_node.cost + 1
                        child.state = states.UNEXPLORED
                        child.node_type = nt.ZNODE
                        child.set(tt.CONTEXT, map_op_node.get(tt.CONTEXT))
                        child = frank.context.inject_query_context(child)
                        child.check_variables()
                        successors.append(child)
                    return (map_op_node, [reduce_op_node], successors)

            elif NormalizeFn.IN in v:
                map_op_node = alist.copy()
                map_op_node.set(tt.OPVAR, nest_attr)
                map_op_node.set(tt.OP, map_op)
                del map_op_node.attributes[nest_attr]
                map_op_node.cost = alist.cost + 1
                map_op_node.state = states.EXPLORED
                map_op_node.parent_decomposition = 'normalize'
                map_op_node.node_type = nt.HNODE
                map_op_node.check_variables()

                reduce_op_node = map_op_node.copy()
                reduce_op_node.set(tt.OP, reduce_op)
                reduce_op_node.check_variables()

                listed_items = []
                if isinstance(v[NormalizeFn.IN], list):
                    for x in v[NormalizeFn.IN]:
                        listed_items.append(str(x))
                elif isinstance(v[NormalizeFn.IN], str):
                    for x in str(v[NormalizeFn.IN]).split(';'):
                        listed_items.append(str(x).strip())
                for x in listed_items:
                    child = Alist(**{})
                    child.set(tt.OP, 'value')
                    if nest_attr[0] in [vx.AUXILLIARY, vx.PROJECTION, vx.NESTING]:
                        child.set(tt.OPVAR, nest_attr)
                        child.set(nest_attr, x)
                    else:
                        new_var = vx.PROJECTION + '_x' + \
                            str(len(map_op_node.attributes))
                        child.set(tt.OPVAR, new_var)
                        child.set(nest_attr, new_var)
                        child.set(new_var, x)
                    child.state = states.UNEXPLORED
                    child.node_type = nt.ZNODE
                    child.cost = map_op_node.cost + 1
                    child.set(tt.CONTEXT, map_op_node.get(tt.CONTEXT))
                    child.check_variables()
                    child = frank.context.inject_query_context(child)
                    #G.link(map_op_node, child, map_op_node.parent_decomposition)
                    successors.append(child)
                return (map_op_node, [reduce_op_node], successors)

            elif NormalizeFn.IS in v:                
                map_op_node = Alist(**{})
                map_op_node.set(tt.OP, map_op)
                new_var = vx.PROJECTION + '_x' + str(len(map_op_node.attributes))
                map_op_node.set(tt.OPVAR, new_var)
                map_op_node.set(new_var, v[NormalizeFn.IS])
                map_op_node.state = states.REDUCIBLE
                map_op_node.cost = map_op_node.cost + 1
                map_op_node.node_type = nt.ZNODE
                map_op_node.set(tt.CONTEXT, map_op_node.get(tt.CONTEXT))
                map_op_node.check_variables()
                # map_op_node = frank.context.inject_query_context(child)
                
                reduce_op = 'value'
                reduce_op_node = alist.copy()
                reduce_op_node.set(tt.OP, reduce_op)
                reduce_op_node.check_variables()

                if v[NormalizeFn.IS].startswith((vx.AUXILLIARY, vx.NESTING, vx.PROJECTION)) == False:
                    # this is an instantiation, so a pseudo leaf node should be created
                    child = Alist(**{})
                    child.set(tt.OP, 'value')
                    new_var = vx.PROJECTION + '_x' + \
                        str(len(map_op_node.attributes))
                    child.set(tt.OPVAR, new_var)
                    child.set(new_var, v[NormalizeFn.IS])
                    child.state = states.REDUCIBLE
                    child.cost = map_op_node.cost + 1
                    child.node_type = nt.ZNODE
                    child.set(tt.CONTEXT, map_op_node.get(tt.CONTEXT))
                    child = frank.context.inject_query_context(child)
                    child.check_variables()
                    successors.append(child)
                return (map_op_node, [reduce_op_node], successors)

            elif tt.OP in v:
                map_op_node = alist.copy()
                map_op_node.set(tt.OPVAR, nest_attr)
                map_op_node.set(tt.OP, map_op)
                map_op_node.set(nest_attr, '')
                map_op_node.cost = alist.cost + 1
                map_op_node.parent_decomposition = 'normalize'
                map_op_node.node_type = nt.HNODE
                map_op_node.check_variables()

                reduce_op_node = map_op_node.copy()
                reduce_op_node.set(tt.OP, reduce_op)
                reduce_op_node.check_variables()

                var_ctr = 200
                child = Alist(**v)
                # for ak, av in v.items():
                #     if isinstance(av, str):
                #         child.set(ak, av.strip())
                #     elif ak == tt.CONTEXT:
                #         child.set(ak, av)
                #     else:
                #         new_var = vx.NESTING + str(var_ctr)
                #         child.set(ak, new_var)
                #         child.set(new_var, av)
                #         var_ctr = var_ctr + 1
                child.cost = map_op_node.cost + 1
                child.node_type = nt.ZNODE
                child.set(tt.CONTEXT, map_op_node.get(tt.CONTEXT))
                child = frank.context.inject_query_context(child)
                child.check_variables()
                successors.append(child)
                return (map_op_node, [reduce_op_node], successors)
        return None

    # def decompose(self, alist: Alist, G: InferenceGraph=None):
    #     map_op = 'normalize'
    #     reduce_op = 'comp'
    #     nest_vars = alist.uninstantiated_nesting_variables()
    #     used_nest_vars = {}
    #     for nk,nv in nest_vars.items():
    #         for k,v in alist.attributes.items():
    #             if isinstance(v, str) and v== nk:
    #                 used_nest_vars[nk] = nv
    #                 break
    #             elif isinstance(v, list) and nk in v:
    #                 used_nest_vars[nk] = nv
    #                 break
        
        
    #     successors = []
    #     map_red_succ = []

    #     for nest_attr, v in used_nest_vars.items():
    #         if NormalizeFn.FILTER in v:
    #             map_op_node = alist.copy()
    #             map_op_node.set(tt.OP, map_op)
    #             map_op_node.set(tt.OPVAR, nest_attr)
    #             del map_op_node.attributes[nest_attr]
    #             map_op_node.cost = alist.cost + 1
    #             map_op_node.branch_type = br.AND
    #             map_op_node.state = states.EXPLORED
    #             map_op_node.parent_decomposition = map_op
    #             map_op_node.node_type = nt.HNODE
    #             map_op_node.check_variables()

    #             reduce_op_node = map_op_node.copy()
    #             reduce_op_node.set(tt.OP, reduce_op)
    #             reduce_op_node.check_variables()

    #             # check for filters that heuristics apply to
    #             # e.g type==country and location==Europs
    #             filter_patterns = {}
    #             geo_class = ''
    #             for x in v[NormalizeFn.FILTER]:
    #                 prop = str(x['p'])
    #                 obj = str(x['o'])
    #                 if prop == 'type' and (obj == 'country' or obj == 'continent'):
    #                     filter_patterns['geopolitical'] = obj
    #                 elif prop == 'location':
    #                     filter_patterns['location'] = obj

    #             if {'geopolitical', 'location'} <= set(filter_patterns):
    #                 # use heuristics to create a single alist containing the
    #                 # conjunction to find the X located in Y
    #                 child = Alist(**{})
    #                 child.set(tt.OP, 'list')
    #                 child.set(tt.OPVAR, nest_attr)
    #                 child.set(tt.SUBJECT, nest_attr)
    #                 child.set(tt.PROPERTY, '__geopolitical:' +
    #                           filter_patterns['geopolitical'])
    #                 child.set(tt.OBJECT, filter_patterns['location'])
    #                 child.cost = map_op_node.cost + 1
    #                 child.state = states.UNEXPLORED
    #                 child.node_type = nt.ZNODE
    #                 child.set(tt.CONTEXT, map_op_node.get(tt.CONTEXT))
    #                 child = frank.context.inject_query_context(child)
    #                 child.check_variables()
    #                 successors.append(child)
    #                 return (map_op_node, [reduce_op_node], successors)
    #             else:
    #                 for x in v[NormalizeFn.FILTER]:
    #                     child = Alist(**{})
    #                     child.set(tt.OP, 'list')
    #                     child.set(tt.OPVAR, nest_attr)
    #                     child.set(tt.SUBJECT, nest_attr)
    #                     for attr, attrval in x.items():
    #                         child.set(attr, attrval)
    #                     child.cost = map_op_node.cost + 1
    #                     child.state = states.UNEXPLORED
    #                     child.node_type = nt.ZNODE
    #                     child.set(tt.CONTEXT, map_op_node.get(tt.CONTEXT))
    #                     child = frank.context.inject_query_context(child)
    #                     child.check_variables()
    #                     successors.append(child)
    #                 return (map_op_node, [reduce_op_node], successors)

    #         elif tt.OP in v:
    #             map_op_node = alist.copy()
    #             map_op_node.set(tt.OPVAR, nest_attr)
    #             map_op_node.set(tt.OP, map_op)
    #             map_op_node.set(nest_attr, '')
    #             map_op_node.cost = alist.cost + 1
    #             map_op_node.parent_decomposition = 'normalize'
    #             map_op_node.node_type = nt.HNODE
    #             map_op_node.check_variables()

    #             reduce_op_node = map_op_node.copy()
    #             reduce_op_node.set(tt.OP, reduce_op)
    #             reduce_op_node.check_variables()

    #             var_ctr = 200
    #             child = Alist(**{})
    #             for ak, av in v.items():
    #                 if isinstance(av, str):
    #                     child.set(ak, av.strip())
    #                 elif ak == tt.CONTEXT:
    #                     child.set(ak, av)
    #                 else:
    #                     new_var = vx.NESTING + str(var_ctr)
    #                     child.set(ak, new_var)
    #                     child.set(new_var, av)
    #                     var_ctr = var_ctr + 1
    #             child.cost = map_op_node.cost + 1
    #             child.node_type = nt.ZNODE
    #             child.set(tt.CONTEXT, map_op_node.get(tt.CONTEXT))
    #             child = frank.context.inject_query_context(child)
    #             child.check_variables()
    #             successors.append(child)
    #             map_red_succ.append((map_op_node, reduce_op_node, successors))

    #     if map_red_succ:
    #         pmap_op_node = alist.copy()
    #         pmap_op_node.set(tt.OPVAR, list(used_nest_vars.keys()))
    #         pmap_op_node.set(tt.OP, map_op)
    #         for k in used_nest_vars.keys():
    #             pmap_op_node.set(k, '')
    #         pmap_op_node.cost = alist.cost + 1
    #         pmap_op_node.parent_decomposition = 'normalize'
    #         pmap_op_node.node_type = nt.HNODE
    #         pmap_op_node.check_variables()

    #         preduce_op_node = pmap_op_node.copy()
    #         preduce_op_node.set(tt.OP, reduce_op)
    #         preduce_op_node.check_variables()

    #         return (pmap_op_node, [preduce_op_node], successors)

    #         # G.subdivide(alist.id, alist.id + '_', pmap_op_node, [preduce_op_node], successors, successor_same_states=True)
    #         # for m,r,s in map_red_succ:
    #         #     G.subdivide(pmap_op_node.id, preduce_op_node.id + '_', m, [r], s, successor_same_states=True)

    #         # alist.state = states.EXPLORED
    #         # return (None, None, None)




    #     return None
 


class NormalizeFn:
    IN = '$in'
    IS = '$is'
    FILTER = '$filter'
