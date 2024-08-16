'''
File: inference.py
Description: Core functions to the FRANK algorithm


'''

import datetime
import random
import threading
import time

import frank.cache.logger as clogger
import frank.map.map_wrapper
import frank.processLog as plog
from frank.processLog import pcolors as pcol
import frank.reduce.comp
import frank.reduce.eq
import frank.reduce.neq
import frank.reduce.gt
import frank.reduce.gte
import frank.reduce.lt
import frank.reduce.lte
import frank.reduce.max
import frank.reduce.mean
import frank.reduce.median
import frank.reduce.min
import frank.reduce.mode
import frank.reduce.rank
import frank.reduce.nnpredict
import frank.reduce.product
import frank.reduce.regress
import frank.reduce.sum
import frank.reduce.value
import frank.reduce.count
import frank.reduce.list
import frank.reduce.startswith
from frank.util import utils
from graph.alist import Alist
from graph.alist import Attributes as tt
from graph.alist import Branching as br
from graph.alist import NodeTypes as nt
from graph.alist import States as states
from frank import config
from frank.kb import rdf, wikidata, worldbank, musicbrainz, jsonld
from frank import processLog
from frank.uncertainty.sourcePrior import SourcePrior as sourcePrior
import frank.context
from graph.alist import Contexts as ctx
from graph.inference_graph import InferenceGraph


class Infer:
    """ 
    Resolve alists by infer projection variables in alist

    Attributes
    ----------
    G: InferenceGraph

    session_id : str

    last_heartbeat : time
        The last time an inference activity happened to 
        determine when to time-out.

    property_refs : dict
        Reference to properties in knowledge bases that match predicate in query.

    reverse_property_ref s: dict
        Inverse references to properties in knowledge bases that match predicate in query.

    max_depth: int
        The current maximum depth in the inference graph from the root node.

    propagated_alists : list
        List of root node alists resolved after successful propagation 
        of variables from leaf nodes.

    root : Alist
        Alist in the root node of inference graph.

    """

    def __init__(self, G: InferenceGraph):
        """
        Parameters
        ----------
        G : InferenceGraph
        """
        self.G = G
        self.debug = 0
        self.session_id = '0'
        self.last_heartbeat = time.time()
        self.property_refs = {}
        self.reverse_property_refs = {}
        self.max_depth = 0
        self.propagated_alists = []
        self.root = None

    def enqueue_root(self, alist):
        """ Add alist as the root node of the inference graph"""
        self.root = alist
        self.G.add_alist(alist, create_complement=True)
        # self.G.plot_plotly()

    def run_frank(self, alist: Alist):
        """ Run the FRANK algorithm for an alist

        Args
        ----
        alist : Alist

        Return
        ------
        Return True if the instantiation of the project variable of an alist 
        is propagated to the root node.

        Notes
        -----
        For the given alist, attempt to instantiate projection 
        variable. If instantiation is successful, attempt to reduce
        Else decompose and add new children to queue
        """
        self.last_heartbeat = time.time()
        curr_propagated_alists = []
        self.max_depth = alist.depth
        if alist.state is states.PRUNED:
            self.write_trace(
                f"{pcol.RED}ignore pruned {alist.id}{pcol.RESET}-{alist}{pcol.RESETALL}")
            return self.propagated_alists

        alist.state = states.EXPLORING

        # if not a reduce node, check if its reduce complement instantiated
        alist_ = self.G.find_complement_node(alist)[0]  
        alist_.check_variables()   
        proj_instantiated = True if alist_.projected_value() else False
        opval = alist_.operation_variable_value()
        if not opval:
            opval_instantiated = False
        elif isinstance(opval, list) and None in opval:
            opval_instantiated = False
        else:
            opval_instantiated = True

        if proj_instantiated and (not opval_instantiated):
            if alist_.projection_variable_names()[0] == tt.PRJVAR or alist_.is_all_instantiated():
                alist_c = [] 
                if str(alist.id)[-1] != '_':
                    alist_c = self.G.find_complement(alist.id)
                for fc in alist_c:
                    fc_node = self.G.alist(fc)
                    fc_node.set(tt.OPVALUE, fc_node.projected_value())
                    self.G.add_alist(fc_node)
                    self.propagate(fc_node.id)
                opval_instantiated = True
        
        elif not proj_instantiated and opval_instantiated:
            if alist_.projection_variable_names()[0] == tt.PRJVAR or alist_.is_all_instantiated(): 
                alist_c = [] 
                if str(alist.id)[-1] != '_':
                    alist_c = self.G.find_complement(alist.id)
                for fc in alist_c:
                    fc_node = self.G.alist(fc)
                    fc_node.set(tt.PRJVAR, fc_node.operation_variable_value())
                    self.G.add_alist(fc_node)
                    self.propagate(fc_node.id)
                proj_instantiated = True
              

        instantiated = proj_instantiated and opval_instantiated

        # in instantiated but only root node exists,
        #  then insert a datanode same as the root node
        #  so that propagaation (aggregation) works
        if instantiated and self.G.number_of_edges() == 1:
            map_op = alist.copy()
            reduce_op = alist.copy()
            reduce_op.state = states.REDUCED
            reduce_op.check_variables()
            default_data_node  = alist.copy()
            default_data_node.state = states.REDUCED
            default_data_node.check_variables()
            self.G.subdivide('0','0_', map_op,[reduce_op],[default_data_node], True, True)

        # if projection var not instantiated, search KB
        if not instantiated:
            instantiated = self.search_kb(alist)

        if instantiated:
            is_propagated = False
            alist.state = states.EXPLORED
            self.G.add_alist(alist)
            # if all necessary variables are instantiated, 
            #  then set the node complement to REDUCIBLE
            complements = self.G.find_complement(alist.id)
            for complement in complements:
                complement_node = self.G.alist(complement)
                complement_node.state = states.REDUCIBLE
                self.G.add_alist(complement_node)

            if self.G.child_ids(alist.id):                
                children = self.G.child_ids(alist.id)
                is_propagated = False
                for child in children:
                    complements = self.G.find_complement(child)
                    for complement in complements:
                        is_propagated = is_propagated or self.propagate(complement)
            else:
                if alist.id != '0':
                    self.propagate(
                        self.G.child_ids(self.G.parent_ids(alist.id)[0])[0] + '_')
                else:
                    self.propagate('0_')


            # if complement of foot node has projection variable instantiated,
            # then change state and set intermediate answer
            root_compl_alist = self.G.alist(self.root.id + '_')
            is_propagated_to_root =  root_compl_alist.is_instantiated(root_compl_alist.projection_variable_names()[0])

            if is_propagated_to_root:
                root_compl_alist.state = states.REDUCED
                self.G.add_alist(root_compl_alist)
                self.write_trace(f"{pcol.CYAN}intermediate ans: "
                                 f"{pcol.RESET}-{root_compl_alist}{pcol.RESETALL}",
                                 loglevel=processLog.LogLevel.ANSWER)
                curr_propagated_alists.append(root_compl_alist.copy())
                self.propagated_alists.append(root_compl_alist.copy())
        else:
            alist.state = states.EXPLORED
            self.G.add_alist(alist)
            for mapOp in self.get_map_strategy(alist):
                self.decompose(alist, mapOp)
        if self.debug == 1:
            self.G.plot_plotly()
        return curr_propagated_alists

    def search_kb(self, alist: Alist):
        """ Search knowledge bases to instantiate variables in alist.

        Args
        ----
        alist: Alist

        Return
        ------
        Returns `True` if variable instantiation is successful from a KB search.

        """
        self.last_heartbeat = time.time()
        prop_refs = []
        found_facts = []
        # cannot search if alist has uninstantiated nested variables
        if alist.uninstantiated_nesting_variables():
            return found_facts

        self.write_trace(
            f"{pcol.MAGENTA}search {alist.id}{pcol.RESET} {alist}{pcol.RESETALL}")
        if alist.state == states.EXPLORED:
            new_alist = alist.copy()
            new_alist.state = states.EXPLORED
            new_alist.set(tt.OPVAR, alist.get(tt.OPVAR))
            return True

        prop_string = alist.get(tt.PROPERTY)        
        sources = {
            'wikidata': {'fn': wikidata, 'trust': 'low'}, 
            'worldbank': {'fn': worldbank, 'trust': 'high'},
            'musicbrainz': {'fn': musicbrainz, 'trust': 'high'}
            }
        context = alist.get(tt.CONTEXT)
        context_store = {}
        context_store = {**context[0], **context[1],
                         **context[2]} if context else {}
        for source_name, source in sources.items():
            # check context for trust
            if ctx.trust in context_store:
                if context_store[ctx.trust] == 'high' and source['trust'] != 'high':
                    continue
            # for source_name, source in {'worldbank':worldbank}.items():
            search_alist = alist.copy()
            # inject context into IR
            search_alist = frank.context.inject_retrieval_context(
                search_alist, source_name)

            # if the property_refs does not contain an entry for the property in this alist
            # search KB for a ref for the property
            prop_sources = []
            if prop_string in self.property_refs:
                prop_sources = [x[1] for x in self.property_refs[prop_string]]

            if (prop_string not in self.property_refs and not prop_string.startswith('__')) \
                    or (prop_string in self.property_refs and source_name not in prop_sources):

                props = source['fn'].search_properties(prop_string)

                if len(props) > 0:
                    maxScore = 0
                    for p in props:
                        if p[2] >= maxScore:
                            prop_refs.append((p, source_name))
                            self.reverse_property_refs[p[0]] = prop_string
                            maxScore = p[2]
                        else:
                            break
                self.property_refs[prop_string] = prop_refs

            search_attr = tt.SUBJECT
            uninstantiated_variables = search_alist.uninstantiated_attributes()
            if tt.SUBJECT in uninstantiated_variables:
                search_attr = tt.SUBJECT
            elif tt.OBJECT in uninstantiated_variables:
                search_attr = tt.OBJECT
            elif tt.TIME in uninstantiated_variables:
                search_attr = tt.TIME

            cache_found_flag = False
            if config.config['use_cache']:
                searchable_attr = list(filter(lambda x: x != search_attr,
                                              [tt.SUBJECT, tt.PROPERTY, tt.OBJECT, tt.TIME]))
                # search with original property name
                (cache_found_flag, results) = (False, [])
                if cache_found_flag == True:
                    found_facts.append(results[0])
                # search with source-specific property IDs

                for (propid, _source_name) in self.property_refs[prop_string]:
                    self.last_heartbeat = time.time()
                    search_alist.set(tt.PROPERTY, propid[0])
                    (cache_found_flag, results) = (False, [])
                    if cache_found_flag == True:
                        found_facts.append(results[0])
                        self.write_trace(
                            f'{pcol.MAGENTA}found: cache{pcol.RESETALL}')
            if not cache_found_flag and prop_string in self.property_refs:
                # search for data for each property reference source
                for propid_label, _source_name in self.property_refs[prop_string]:
                    self.last_heartbeat = time.time()

                    try:
                        if _source_name == source_name:
                            search_alist.set(tt.PROPERTY, propid_label[0])
                            found_facts.extend(source['fn'].find_property_values(
                                search_alist, search_attr))
                            # TODO: handle location search in less adhoc manner
                            if alist.get(tt.PROPERTY).lower() == "location":
                                if search_attr == tt.SUBJECT:
                                    found_facts.extend(
                                        wikidata.part_of_relation_subject(search_alist))
                                elif search_attr == tt.OBJECT:
                                    found_facts.extend(
                                        wikidata.part_of_relation_object(search_alist))
                            break
                    except Exception as ex:
                        self.write_trace(
                            f"{pcol.RED}Search Error{pcol.RESETALL}", processLog.LogLevel.ERROR)
                        # print(str(ex))
            if not found_facts and alist.get(tt.PROPERTY).startswith('__geopolitical:'):
                if search_attr == tt.SUBJECT:
                    found_facts.extend(
                        wikidata.part_of_geopolitical_subject(search_alist))
            # TODO: save facts found to cache if caching is enabled

        if found_facts:
            self.last_heartbeat = time.time()
            all_numeric = True
            non_numeric_data_items = []
            numeric_data_items = []

            fact_nodes = []

            for ff in found_facts:
                # self.last_heartbeat = time.time()
                ff.set(tt.OP, 'value')
                ff.set(tt.OPVAR, alist.get(tt.OPVAR))                
                ff.set(ff.get(tt.OPVAR), ff.get(search_attr))
                ff.set(tt.OPVALUE, ff.get(search_attr))
                ff.instantiate_variable(uninstantiated_variables[search_attr], ff.get(search_attr))
                sourceCov = sourcePrior().get_prior(
                    source=list(ff.data_sources)[0]).cov
                ff.set(tt.COV, sourceCov)
                # ff.state = states.REDUCIBLE
                ff.state = states.REDUCED
                ff.set(tt.EXPLAIN, '')
                ff.node_type = nt.FACT
                if ff.get(tt.PROPERTY) in self.reverse_property_refs:
                    ff.set(tt.PROPERTY,
                           self.reverse_property_refs[ff.get(tt.PROPERTY)])

                ff.check_variables()
                alist.parent_decomposition = "Lookup"
                fact_nodes.append(ff)

                # fact is considered reduced
                self.write_trace(
                    f'  {pcol.MAGENTA}found:{pcol.RESET} {str(ff)}{pcol.RESETALL}')

            map_op_node = alist.copy()
            map_op_node.set(tt.OP, "lookup")
            map_op_node.set(tt.OPVAR, alist.getOpVar())
            map_op_node.node_type = nt.HNODE
            map_op_node.check_variables()
            reduce_op_node = alist.copy()
            reduce_op_node.set(tt.OP, "list")
            reduce_op_node.node_type = nt.HNODE
            reduce_op_node.check_variables()

            self.G.subdivide(alist.id, alist.id + '_', map_op_node, [reduce_op_node], fact_nodes, 
                successor_same_states=True, successor_no_reduce=True)
            if self.debug == 1:
                self.G.plot_plotly()
        return len(found_facts) > 0

    def get_map_strategy(self, alist: Alist):
        """ Get decomposition rules to apply to an alist

        Args
        ----
        alist : Alist

        Return
        ------
        ops : A list of reduce functions for aggregating alists

        """
        # TODO: learn to predict best strategy given path of root from
        # node and attributes in alist
        self.last_heartbeat = time.time()
        # if alist.get(tt.OP).lower() in ['eq', 'lt', 'gt', 'lte', 'gte']:
        #     return [(frank.map.map_wrapper.get_mapper_fn("comparison"), "comparison")]
        # if compound frame (i.e nesting point in frame), then normalize
        if alist.uninstantiated_nesting_variables():
            return [(frank.map.map_wrapper.get_mapper_fn("normalize"), "normalize")]
        else:
            ops = []
            for allowed_op in config.config["base_decompositions"]:
                try:
                    ops.append(
                        (frank.map.map_wrapper.get_mapper_fn(allowed_op), allowed_op))
                except Exception as ex:
                    print("Error in decomposition mapper: " + str(ex))
            random.shuffle(ops)
            return ops

    def decompose(self, alist: Alist, map_op):
        """ Apply a decomposition rule to create successors of an alist

        Args
        ----
        alist : Alist to decompose

        map_op : str
            Name of the map operation to apply to the alist

        Return
        ------
        alist: Alist
            Successor h-node alist that has z-node child alists

        Notes
        -----
        z-nodes are alists that represent facts and contain variables that 
        are to be instantiated with data from knowledge bases.
        h-nodes are alists that have operations to aggregate their child z-nodes.
        Decompositions create z-node and specify the `h` operations for aggregating 
        the decomposed child nodes.

                    (alist)
                       |
                       |
                    (h-node)
                    / ... \\
                   /  ...  \\   
            (z-node1) ... (z-nodeN)

        """
        alist.check_variables()
        self.last_heartbeat = time.time()
        self.write_trace('{blue}{bold}T{thread}{reset} > {op}:{id}-{alist}{resetall}'.format(
            blue=pcol.BLUE, reset=pcol.RESET, bold=pcol.RESET, resetall=pcol.RESETALL,
            thread=threading.get_ident(),
            op=map_op[1], alist=alist, id=alist.id))

        # check for query context
        context = alist.get(tt.CONTEXT)
        map_op_node, reduce_op_node, map_op_successors = self.G.decompose(alist, map_op, max_depth=config.config['max_depth'])
        if map_op_node:
            self.write_trace(f'{pcol.BLUE}>> {map_op_node.id}{pcol.RESET}-{str(map_op_node)}{pcol.RESETALL}')                
            for succ in map_op_successors:
                self.write_trace(f'  {pcol.BLUE}>>> {succ.id}{pcol.RESET}-{str(succ)}{pcol.RESETALL}')
            self.write_trace(f'{pcol.BLUE}>> {" ; ".join([x.id for x in reduce_op_node])}{pcol.RESET}-{str(reduce_op_node[0])}{pcol.RESETALL}')

            if self.debug == 1:
                self.G.plot_plotly()
        

    def aggregate(self, alist_id):
        """ Aggregate the child nodes of an alist by applying the operation 
            specified by the *`h`* attribute of the node's alist.

        Args
        ----
        alist_id : str
            Id of alist whose child nodes should be aggregated

        Return
        --------
        Returns True if aggregation was successful.  

        Notes
        -----
        Only child alists that are in the `reduced` or `reducible` states are aggregated.
        The result of the aggregation is stored in the alist and the inference graph is updated.
        Text explaining the aggregation is also added to the `xp` attribute of the alist.
        """
        alist = self.G.alist(alist_id)
        # if alist.state == states.UNEXPLORED:
        #     return False
        self.last_heartbeat = time.time()
        self.write_trace(
            f'{pcol.YELLOW}reducing {alist.id}{pcol.RESET}-{alist}{pcol.RESETALL}')

        reduce_op = None
        try:
            reduce_op = eval('frank.reduce.' + alist.get(tt.OP).lower())
        except:
            print(f"Cannot process {alist.get(tt.OP).lower()}")

        assert(reduce_op is not None)

        predecessors = self.G.parent_alists(alist.id)
        reducibles = [x for x in predecessors
                      if (x.state == states.REDUCIBLE or x.state == states.REDUCED)
                      and x.get(tt.OP).lower() != 'comp']

        if reducibles:
            for x in reducibles:
                self.write_trace(
                    f'  {pcol.YELLOW}<<< {x.id}{pcol.RESET}-{x}{pcol.RESETALL}')

            unexplored = [
                x for x in predecessors if x.state == states.UNEXPLORED]
            if not reducibles or len(unexplored) == len(predecessors):
                return False  # there's nothing to reduce

            reduced_alists = reduce_op.reduce(alist, reducibles, self.G)

            last_heartbeat = time.time()

            if reduced_alists is not None:
                for c in predecessors:
                    alist.data_sources = list(
                        set(alist.data_sources + c.data_sources))
                for r in reducibles:
                    r.state = states.REDUCED
                    self.G.add_alist(r)
                if alist.state != states.REDUCED:
                    alist.state = states.REDUCIBLE  # check later
                    complements = self.G.find_complement(alist.id)
                    for complement in complements:
                        complement_node = self.G.alist(complement)
                        complement_node.state = states.EXPLORED
                        self.G.add_alist(complement_node)
                self.G.add_alist(alist)
                self.write_trace(
                    f"{pcol.GREEN}reduced {alist.id}{pcol.RESET}-{alist}{pcol.RESETALL}")
                return True
            else:
                self.write_trace(
                    f"{pcol.YELLOW}reduce {alist.id} failed {pcol.RESET}-{alist}{pcol.RESETALL}")
                return False
        else:
            # if no reducibles but node has an instantiated projection variable, the 
            proj_val = alist.projected_value()
            if proj_val: 
                alist.instantiate_variable(tt.OPVALUE, proj_val) #instantiate own opvalue
                alist.state = states.REDUCED 
                self.G.add_alist(alist)
                complements = self.G.find_complement(alist.id)
                for complement in complements:
                    complement_node = self.G.alist(complement)
                    complement_node.state = states.EXPLORED
                    self.G.add_alist(complement_node)
                return True
            else:
                return False

    def propagate(self, alist_id):
        self.last_heartbeat = time.time()
        curr_alist = self.G.alist(alist_id)
        self.write_trace(
            f'{pcol.GREEN}propagate {curr_alist.id}{pcol.RESET}-{curr_alist}{pcol.RESETALL}')
        
        # iter until node 0_
        while curr_alist != None:
            # get the predecessor nodes to aggregate
            if self.aggregate(curr_alist.id):
                # set the cur_alist to the next successor node
                successors = self.G.child_alists(curr_alist.id)
                if successors:
                    # curr_alist = successors[0]
                    for succ in successors:
                        node_id = succ.id
                        if '_' not in succ.id:
                            node_id = self.G.find_complement(succ.id)[0]
                        self.propagate(node_id)
                    curr_alist = None                    
                else:
                    curr_alist = None
            else:
                return False
        return True

    def write_trace(self, content, loglevel=processLog.LogLevel.INFO):
        processLog.println(content, processLog.LogLevel.INFO)
