
'''
File: inference_graph.py
Description: InferenceGraph for FRANK

'''

import networkx as nx
import random
import plotly.graph_objects as go
from graph.alist import Alist
from graph.alist import States as st
from graph.alist import NodeTypes as nt
from graph.alist import Attributes as tt
from graph.alist import Branching as br

class InferenceGraph(nx.DiGraph):
    def __init__(self):
        nx.DiGraph.__init__(self)

    def add_alist(self, alist: Alist, create_complement=False):
        '''Add a alist to the graph'''
        if len(self.nodes) == 0:
            alist.set(tt.ID, '0')
        self.add_nodes_from([(alist.id, alist.attributes)])
        if create_complement:
            alist_ = alist.copy()
            alist_.set(tt.ID, alist.id + '_')
            alist_.is_map = 0
            alist_.check_variables()
            self.link(alist, alist_, new_child_id=False, frontier=True, complement=True)

    def add_alists_from(self, alists: list):
        '''Add a list of alists to the graph'''
        node_list = [(a.id, a.attributes) for a in list(alists)]
        self.add_nodes_from(node_list)

    def parent_alists(self, alist_id, exclude_self_complement=True):
        '''Get the parent alists of a node'''
        pred = self.predecessors(alist_id)
        pred_arr = [Alist(**self.nodes[x]) for x in pred 
                     if exclude_self_complement == False 
                        or exclude_self_complement and self[x][alist_id]['complement'] == False]
                        # alist_id.replace('_','') != x.replace('_','')]
        
        return pred_arr

    def child_alists(self, alist_id, exclude_self_complement=True):
        '''Get the child alists of a node'''
        succ = self.successors(alist_id)
        succ_arr = [Alist(**self.nodes[x]) for x in succ
                     if exclude_self_complement == False 
                        or exclude_self_complement and  self[alist_id][x]['complement'] == False]
                        #or exclude_self_complement and alist_id.replace('_','') != x.replace('_','')]
        return succ_arr

    def sibling_alists(self, alist_id):
        '''Get the sibling alists of a node'''
        is_map = False if alist_id[-1] == '_' else True
        siblings = []
        if is_map:
            parent = self.parent_alists(alist_id)
            for n in parent:
                sibs = self.child_alists(n.id)
                siblings = [x for x in sibs if x.id != alist_id and x.id[-1] != '_']
        else:
            children = self.child_alists(alist_id)
            for n in children:
                sibs = self.parent_alists(n.id)
                siblings = [x for x in sibs if x.id != alist_id and x.id[-1] == '_']
        return siblings

    def parent_ids(self, alist_id, exclude_self_complement=True):
        '''Get the parent alist ids of a node'''
        pred = self.predecessors(alist_id)
        pred_arr = [x for x in pred
                    if exclude_self_complement == False 
                        or (exclude_self_complement and  self[x][alist_id]['complement'] == False)]
                        #exclude_self_complement and alist_id.replace('_','') != x.replace('_','')]
        return pred_arr

    def child_ids(self, alist_id, exclude_self_complement=True):
        '''Get the child alist ids of a node'''
        succ = self.successors(alist_id)
        succ_arr = [x for x in succ 
                     if exclude_self_complement == False 
                        or (exclude_self_complement and self[alist_id][x]['complement'] == False)]
                        #exclude_self_complement and alist_id.replace('_','') != x.replace('_','')]
        return succ_arr

    def sibling_ids(self, alist_id):
        '''Get the sibling alists ids of a node'''
        is_map = False if alist_id[-1] == '_' else True
        siblings = []
        if is_map:
            parent = self.parent_ids(alist_id)
            for n in parent:
                sibs = self.child_ids(n)
                siblings = [x for x in sibs if x != alist_id and x[-1] != '_']
        else:
            children = self.child_ids(alist_id)
            for n in children:
                sibs = self.parent_ids(n)
                siblings = [x for x in sibs if x != alist_id and x[-1] == '_']
        return siblings

    def alist(self, alist_id):
        '''Get the alist object for a given alist id'''
        try:
            alist = Alist(**self.nodes[alist_id])
            return alist
        except:
            return None

    def alists(self):
        '''Get all alists in inference graph'''
        alists = [Alist(**self.nodes[x]) for x in list(self.nodes())]
        return alists

    def alists_and_edges(self, show_hidden_edges=True):
        '''Get a list of nodes and edges between them'''
        nodes_and_edges = [{'source': x[0], 'target': x[1], 'label':self[x[0]][x[1]]['label'],
            'edge': self[x[0]][x[1]]} 
                for x in self.edges() 
                    if show_hidden_edges==True or 
                        (show_hidden_edges==False and self[x[0]][x[1]]["hidden"]==False)]
        return nodes_and_edges

    def ui_graph(self, show_hidden_edges=True):
        '''Get list of nodes and list of edges between nodes in graph. 
        This is used for serializing the inference graph to be plotted in other UI tools.'''
        nodes = [dict(x.attributes) for x in list(self.alists())]
        nodes_arr = []
        for n in nodes:
            n.update(n['meta'])
            n.pop('meta', None)
            nodes_arr.append(n)
        return {'nodes': nodes, 'edges': self.alists_and_edges(show_hidden_edges)}

    def cytoscape_ui_graph(self):
        '''Get the inference graph in a Cytoscape compatible format.'''
        g = self.ui_graph(show_hidden_edges=False)
        nodes = [{"data": y} for y in g['nodes']]
        edges = [{"data": y} for y in g['edges']]
        return {'nodes': nodes, 'edges': edges}
        
    def link(self, parent:Alist, child:Alist, edge_label='', new_child_id=True, hidden=False, frontier=False, complement=False):
        '''Create an edge between two nodes in the graph. Can also be used to link new nodes to existing ones'''
        if parent:
            if new_child_id:
                succ = [x for x in self.successors(parent.id) if self[parent.id][x]['complement'] == False]# != parent.id + '_'] # non complement successors
                succ_nodes = [self.nodes[x] for x in succ]            
                child.depth = parent.depth + 1
                cid = f"{parent.depth + 1}{parent.id}{len(succ_nodes) + 1}"
                ctr = 1
                while cid in succ:
                    cid = f"{parent.depth + 1}{parent.id}{len(succ_nodes) + 1 + ctr}"
                    ctr += 1
                child.id = cid
                
            self.add_alist(child)
            self.add_edge(parent.id, child.id, 
                **{'label': edge_label, 'frontier': frontier, 'hidden': hidden, 'complement': complement})
        else:
            self.add_alist(child)
        return (parent.id, child.id)

    def remove_link(self, parent_id, child_id):
        '''Remove edge between two nodes in the graph.'''
        if parent_id in self and child_id in self[parent_id]:
            self.remove_edge(parent_id, child_id)

    def find_complement(self, alist_id:str, node_type='any'): ## node_type: any, map, reduce
        ''' Returns a list complement node ids'''
        complements = []
        if node_type in ['any', 'map'] and '_' not in alist_id:
            complements.extend([x for x in self[alist_id] if self[alist_id][x]['complement']==True])
        if node_type in ['any', 'reduce']:
            complements.extend([x for x in self.parent_ids(alist_id, exclude_self_complement=False) if self[x][alist_id]['complement']==True])
        return complements

    def find_complement_node(self, alist:Alist, node_type='any'): # node_type: any, map, reduce
        ''' Returns a list complement nodes'''
        complements = []
        if node_type in ['any', 'map'] and '_' not in alist.id:
            complements.extend([self.alist(x) for x in self[alist.id] if self[alist.id][x]['complement']==True])
        if node_type in ['any', 'reduce']:
            complements.extend([self.alist(x) for x in self.parent_ids(alist.id, exclude_self_complement=False) if self[x][alist.id]['complement']==True])
        return complements

    def leaf_nodes(self, sort=False, sort_key=None):
        '''Get all leaf nodes in the graph'''
        nodes = [x for x in self.nodes() if self.out_degree(x) == 0]
        return nodes

    def leaf_alists(self, sort=False, sort_key=None):
        '''Get all leaf nodes as alist objects'''
        nodes = [Alist(**self.nodes[x])
                 for x in self.nodes() if self.out_degree(x) == 0]

        if sort and sort_key:
            nodes.sort(key=sort_key)
        elif sort and not sort_key:
            nodes.sort(key=lambda x: x.attributes['meta']['cost'])

        return nodes

    def prune(self, alist_id):
        '''Remove an alist from the inference graph'''
        succ = nx.bfs_successors(self, alist_id)
        # complements = self.find_complement(alist_id)
        source = alist_id if alist_id[-1] != '_' else alist_id[0:-1]    
        parents = self.parent_ids(source)   
        compl = self.find_complement(alist_id)        
        nodes_between_set = set()
        for t in compl: 
            # target = alist_id if alist_id[-1] == '_' else alist_id + '_'
        
            paths_between_generator =  nx.all_simple_paths(self, source, t)
            nodes_between_set = nodes_between_set.union({node for path in paths_between_generator for node in path})
        
        self.remove_nodes_from(nodes_between_set)
        
    def frontier(self, size=1, state=st.UNEXPLORED, update_state=False, new_state = st.EXPLORING):
        ''' Get reduce subgraph frontier nodes that are not resolved '''
        frontier_edges = self.edges()
        frontier_map_nodes = []
        frontier_reduce_nodes = []
        for (u,v) in frontier_edges:
            if self[u][v]['frontier'] == True:
                u = self.alist(u)
                v = self.alist(v)
                if u.state == state or u.state == None:
                    if update_state:
                        u.state = new_state
                    frontier_map_nodes.append(u)
                if v.state == state or v.state == None:
                    if update_state:
                        v.state = new_state
                    frontier_reduce_nodes.append(v)
        frontier_map_nodes.sort(key=lambda x: x.attributes['meta']['cost'])
        frontier_reduce_nodes.sort(key=lambda x: x.attributes['meta']['cost'])

        return (frontier_map_nodes, frontier_reduce_nodes)

    def blanket_subgraph(self, alist_id, ancestor_length=1, descendant_length=1):
        '''Get a subgraph of the inference grah using the blanket size'''
        ancestors = nx.single_target_shortest_path(
            self, alist_id, cutoff=ancestor_length)
        descendants = nx.single_source_shortest_path(
            self, alist_id, cutoff=descendant_length)
        nodes = set(list(ancestors.keys()) + list(descendants.keys()))
        blanket = self.subgraph(nodes)
        return blanket
    
    def subdivide(self, source_alist_id, target_alist_id, map_op_node:Alist, reduce_op_nodes:list, 
                    map_op_successors:list, successor_same_states=False, successor_no_reduce=False):
        '''Subdivide an edge between two nodes to insert new alists
            Use successor_same_states=True if successor reduce nodes should 
            use same states as successor map nodes
        
        '''
        # check if edge exists
        if self.has_edge(source_alist_id,target_alist_id):
            # hide edge
            self[source_alist_id][target_alist_id]['hidden'] = True
        elif target_alist_id not in self[source_alist_id] or self[source_alist_id][target_alist_id]['complement'] == False:
            return None       
        
        # add map/reduce nodes        
        u:Alist = Alist(**self.nodes[source_alist_id])
        u.is_frontier = 0
        decomp = map_op_node
        edge = self.link(u, decomp)

        v:Alist = Alist(**self.nodes[target_alist_id])
        v.is_frontier = 0
        
        reduce_s = []
        ctr = 1
        for reduce_op_node in reduce_op_nodes:
            reduce_ = reduce_op_node
            reduce_.set(tt.ID, edge[1] + '_' + str(ctr) + '_')
            reduce_.is_map = 0
            reduce_.node_type = nt.HNODE
            reduce_s.append(reduce_)
            self.add_alist(reduce_)

            self.link(decomp, reduce_,new_child_id=False, hidden=True, complement=True)
            self.link(reduce_, v, new_child_id=False)
            ctr += 1
            
        # add value nodes and complements
        for n in map_op_successors:
            n.is_frontier = 1
            edge = self.link(decomp, n)

            if successor_no_reduce == False:
                # complement
                n_ = n.copy()
                if successor_same_states:
                    n_.state = n.state
                n_.set(tt.ID, edge[1] + '_')
                n_.check_variables()
                n_.is_map = 0
                n_.is_frontier = 1
                self.link(n, n_, new_child_id=False, frontier=True, complement=True)
                for reduce_ in reduce_s:
                    self.link(n_, reduce_, new_child_id=False)
            else:
                for reduce_ in reduce_s:
                    self.link(n, reduce_, new_child_id=False)
            
        
    def decompose(self, alist: Alist, map_op=(None, None), max_depth=10):
        """ Apply a decomposition rule to create successors of an alist

        Args
        ----
        alist : Alist to decompose

        map_op :
            (function, name) tuple of the map operation to apply to the alist

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
        if alist.depth + 1 > max_depth:
            print('max depth reached!\n')
            alist.state = st.IGNORE
            return alist

        alist.branchType = br.OR
        map_op_node = None
        try:
            map_op_node, reduce_op_nodes, map_op_successors = map_op[0](alist)
        except:
            pass
        if map_op_node is not None:
            self.subdivide(alist.id, alist.id + '_', map_op_node, reduce_op_nodes, map_op_successors)
            return (map_op_node, reduce_op_nodes, map_op_successors)
        else:
            return (None, None, None)

    def plot_plotly(self, question='', answer='',  label_exclusion_list=[], show_hidden_edges=False):
        '''Plot inference graph using Plotly'''
        G = self
        pos = self.hierarchy_layout(self,'0')    
        edge_x = []
        edge_y = []
        edge_hidden_x = []
        edge_hidden_y = []
        
        for edge in G.edges():
            x0, y0 = pos[edge[0]][0], pos[edge[0]][1]
            x1, y1 = pos[edge[1]][0], pos[edge[1]][1]
            if G[edge[0]][edge[1]]['hidden']==False:                
                edge_x.append(x0)
                edge_x.append(x1)
                edge_x.append(None)
                edge_y.append(y0)
                edge_y.append(y1)
                edge_y.append(None)
            elif G[edge[0]][edge[1]]['hidden']==False or show_hidden_edges==True:
                edge_hidden_x.append(x0)
                edge_hidden_x.append(x1)
                edge_hidden_x.append(None)
                edge_hidden_y.append(y0)
                edge_hidden_y.append(y1)
                edge_hidden_y.append(None)

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines')
        edge_hidden_trace = go.Scatter(
            x=edge_hidden_x, y=edge_hidden_y,
            line=dict(width=0.5, color='#EE8E3B', dash="dot"),
            hoverinfo='none',
            mode='lines')

        node_x = []
        node_y = []
        node_alist = []
        node_alist_text = []
        annotations = []
        for node in list(G.nodes()):
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            alist = self.alist(node)
            node_alist.append(alist)
            text = str(alist)
            text = text.replace(': {', ': <br>{')
            node_alist_text.append(text)
            op = alist.get(tt.OP)
            annotations.append(
                dict(   
                        x=x,
                        y=y,
                        xref='x',
                        yref='y',
                        text=str.upper(alist.get(tt.OP)) if (op not in label_exclusion_list or alist.id in ['0','0_']) else '',
                        showarrow=False,
                        xshift=0,
                        yshift=15
                        ))

        node_adjacencies = []
        node_text = []
        colors = []
        sizes = []
        marker_symbols = []
        
        pallette = {'grey': '#A5A5A5', 'orange': '#F28C02',
                    'cyan': '#0BE1DD', 'black': '#000000',
                    'red': '#CC0000', 'blue': '#4C4CFF', 
                    'green-teal': '#009922'  }
        for node, adjacencies in enumerate(G.adjacency()):
            node_adjacencies.append(len(adjacencies[1]))
            node_text.append(node_alist_text[node])
            alist = node_alist[node]

            if alist.id == '0':
                colors.append(pallette['red'])
            elif alist.node_type == nt.FACT:
                colors.append(pallette['black'])
            elif alist.state == st.REDUCED or alist.state == st.REDUCIBLE:
                colors.append(pallette['green-teal'])
            elif alist.is_map == 1:
                colors.append(pallette['black'])
            else:
                colors.append(pallette['orange'])


            if alist.node_type == nt.FACT:
                sizes.append(8)
                marker_symbols.append('circle-dot')
            elif alist.node_type == nt.ZNODE:
                sizes.append(8)
                marker_symbols.append('circle')
            elif alist.node_type == nt.HNODE:
                sizes.append(10)
                marker_symbols.append('square')

        node_trace = go.Scatter(
            x=node_x, 
            y=node_y,
            mode='markers',
            hoverinfo='text',
            text=node_text,
            textposition='bottom center',
            marker=dict(
                symbol=marker_symbols,
                colorscale='YlGnBu',
                reversescale=True,
                color=colors,
                size=sizes,
                opacity=0.9
            )
        )

        answer_formatted = f'<b>A:</b> {answer}' if answer else ''

        fig = go.Figure(data=[edge_trace, edge_hidden_trace, node_trace],
                        layout=go.Layout(
                            title=f'Inference Graph <br><span style="font-size:12px; margin-top:-5px"><b>Q:</b> {question} {answer_formatted} </span>',
                            titlefont_size=12,
                            font_size=10,
                            showlegend=False,
                            hovermode='closest',
                            margin=dict(b=20, l=5, r=5, t=40),
                            annotations= annotations,
                            xaxis=dict(showgrid=False, zeroline=False,
                                    showticklabels=False),
                            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            paper_bgcolor='rgb(255,255,255)',
                            plot_bgcolor='rgb(255,255,255)'
                            )
                            
                        )
        fig.show()

    def hierarchy_layout(self, G, root, levels=None, width=1., height=1.):
        '''If there is a cycle that is reachable from root, then this will see infinite recursion.
           Based on code from https://stackoverflow.com/a/29597209 and https://stackoverflow.com/a/42723250
            G: the graph
            root: the root node
            levels: a dictionary
                    key: level number (starting from 0)
                    value: number of nodes in this level
            width: horizontal space allocated for drawing
            height: vertical space allocated for drawing'''
        TOTAL = "total"
        CURRENT = "current"
        def make_levels(levels, node=root, currentLevel=0, parent=None):
            """Compute the number of nodes for each level
            """
            if not currentLevel in levels:
                levels[currentLevel] = {TOTAL : 0, CURRENT : 0}
            levels[currentLevel][TOTAL] += 1
            neighbors = list(G.neighbors(node))
            for neighbor in neighbors:
                if not neighbor == parent:
                    levels =  make_levels(levels, neighbor, currentLevel + 1, node)
            return levels

        def make_pos(pos, node=root, currentLevel=0, parent=None, width=1., xcenter=0.5, vert_loc=0,
                sibling_len = 1, idx_in_siblings=0):
            neighbors = [ x for x in list(G.neighbors(node)) if G[node][x]['hidden'] == False]

            if '_' not in node and node not in pos:                            
                pos[node] = (xcenter, vert_loc)
                levels[currentLevel][CURRENT] += 1     
            else:
                if node not in pos: # don't overwrite previous node pos          
                    node_ = node[:-1]
                    # keep x axis same as its parent complement
                    try:
                        pos[node] = (xcenter, vert_loc)  
                    except: pass
                    levels[currentLevel][CURRENT] += 1
                else:     
                    old_pos = pos[node]          
                    parents = G.parent_ids(node)   
                    if '_' in node and len(parents) == 1:
                        parent_pos = pos[parents[0]]
                        pos[node] = (parent_pos[0], min(old_pos[1],vert_loc))
                    elif '_' in node:
                        if sibling_len == 1:
                            complemt_pos = pos[self.find_complement(node)[0]]
                            pos[node] = (complemt_pos[0], min(old_pos[1],vert_loc)) # use the deepest vertical location
                        else:
                            delta = 0
                            complemt_pos = pos[self.find_complement(node)[0]]
                            sib_width = width * sibling_len
                            first_sib_pos = complemt_pos[0] - (sib_width/2)
                            pos[node] = (first_sib_pos + (sib_width * idx_in_siblings), min(old_pos[1],vert_loc)) # use the deepest vertical location
                    else:
                        pos[node] = (xcenter, min(old_pos[1],vert_loc)) # use the deepest vertical location
            
            if neighbors:
                dx = width/len(neighbors)
                nextx = xcenter - width/2 - dx/2
                idx = 0
                vert_loc = vert_loc - vert_gap - (
                    0.02 * min(max(1, len(self.child_ids(self.parent_ids(neighbors[0], exclude_self_complement=False)[0]))), 5))
                for neighbor in neighbors:
                    nextx += dx 
                    delta = 0
                    if (idx + 1) % 2 == 0:
                        delta = 0.02                  
                    if neighbor != parent:
                        pos = make_pos(pos, neighbor, currentLevel + 1, node, width=dx, xcenter=nextx, vert_loc=vert_loc-delta,
                         sibling_len=len(neighbors), idx_in_siblings=idx)
                    idx += 1
            return pos
        if levels is None:
            levels = make_levels({})
        else:
            levels = {l:{TOTAL: levels[l], CURRENT:0} for l in levels}
        vert_gap = 0.08 # height / (max([l for l in levels])+1)
        return make_pos({})

    def ui_flow_layout(self, label_exclusion_list=[], show_hidden_edges=False):
        '''Return flow layout with node positions'''
        G = self
        pos = self.hierarchy_layout(self,'0')    
        ui_graph = self.ui_graph(show_hidden_edges=False)

        default_style= {
            'background': '#fefefe', 'width': 60,
            'border': 'thin solid #70D798',
            'padding':0, 'border-radius':'5px'
            }
        reduced_style={
            'background': '#e3ffee', 'width': 60,
            'border': 'thin solid #37c36e', 'padding':0, 'border-radius':'5px'
        }
        map_style={
            'background': '#fffbef', 'width': 60,
            'border': 'thin solid #e5d298', 'padding':0, 'border-radius':'5px'
        }
        fact_style={
            'background': '#f0f2f1', 'width': 60, 
            'border': 'thin solid #DDDDDD', 'padding':0, 'border-radius':'5px'
        }

        elements = []
        reduced_nodes = set()
        for n in ui_graph['nodes']:
            try:
                element = {
                    'id':n[tt.ID],                
                    'data': {'label': f'{n[tt.OP]}', 'id': n[tt.ID], 'op':n[tt.OP]},
                    'position': {
                        'x': (pos[n[tt.ID]][0] * 1500) + 200,
                        'y': (pos[n[tt.ID]][1] * -800) + 50 + random.random()/1000 
                    }
                }
                element['type'] = 'alist'
                if n[tt.ID] == '0':
                    element['type'] = 'input'
                    element['data'] = {'label': 'Query', 'id': n[tt.ID], 'op':n[tt.OP]}
                elif n[tt.ID] == '0_':
                    element['type'] = 'output'
                    element['data'] = {'label': 'Answer', 'id': n[tt.ID], 'op':n[tt.OP]}
                elements.append(element)
                element['style'] = default_style
                if n['state'] == st.REDUCED or n['is_map'] == 1 :
                    element['style'] = reduced_style
                    reduced_nodes.add(n[tt.ID])
                if n['is_map'] == 1 :
                    element['style'] = map_style
                    reduced_nodes.add(n[tt.ID])
                if n['node_type'] == nt.FACT:
                    element['style'] = fact_style
            except:
                print(f"!!! Error generating UI graph at node {n[tt.ID]}")

        for e in ui_graph['edges']:
            try:
                element = { 
                    'id': 'e' + e['source'] + e['target'], 
                    'source': e['source'], 
                    'target': e['target'], 
                    'arrowHeadType': 'arrowclosed',
                    'animated': e['source'] not in reduced_nodes or e['target'] not in reduced_nodes }
                elements.append(element)
            except:
                print(f"Error generating UI graph at edge {e['source']}->{e['target']}")

        return elements
        


        