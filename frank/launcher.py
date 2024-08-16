'''
File: scheduler.py
Description: 


'''
import time
import timeit
import uuid
import json
import threading
from frank.infer import Infer

from graph.alist import Alist
from graph.alist import Attributes as tt
from graph.alist import States as states
from graph.alist import Branching as branching
from frank import config
from frank.util import utils
from graph.inference_graph import InferenceGraph
from frank.processLog import pcolors as pcol
import frank.context


class Launcher():

    def __init__(self, **kwargs):
        self.infer: Infer = None
        self.timeout = 60  # self.timeout in seconds
        self.start_time = time.time()
        self.inference_graphs = {}
        self.question = ''
        self.debug = 0
        self.is_cli = False

    def start(self, question, alist: Alist, session_id, inference_graphs, debug=0, is_cli=False):
        ''' Create new inference graph to infere answer'''
        G = InferenceGraph()
        self.infer = Infer(G)
        self.infer.session_id = session_id
        self.inference_graphs = inference_graphs
        self.question = question
        self.debug = debug
        self.is_cli = is_cli
        self.infer.debug = debug
        self.start_time = time.time()
        self.infer.last_heartbeat = time.time()
        alist = frank.context.inject_query_context(alist)
        alist.check_variables()
        self.infer.enqueue_root(alist)
        self.schedule(-1)

    def api_start(self, question, alist_obj, session_id, inference_graphs):

        alist = Alist(**alist_obj)
        t = threading.Thread(target=self.start, args=(
            question, alist, session_id, inference_graphs))
        t.start()
        return session_id

    def schedule(self, last_root_prop_depth):
        ''' Loop through the leaves of the inference graph and 
        schedule nodes to resolve.
        '''
        if time.time() - self.infer.last_heartbeat > self.timeout:
            # stop and print any answer found
            self.cache_and_print_answer(True)

        max_prop_depth_diff = 1
        stop_flag = False
        while True:
            if self.infer.session_id in self.inference_graphs:
                self.inference_graphs[self.infer.session_id]['graph'] = self.infer.G
                if self.inference_graphs[self.infer.session_id]['command'] == 'cancel':
                    print(f"\n{pcol.RED}Session Cancelled{pcol.RESETALL} \n")
                    stop_flag = True
                    break                
            else:
                self.inference_graphs[self.infer.session_id] = {
                    'graph': self.infer.G,
                    'command' : None,
                    'intermediate_answer': None,
                    'answer': None,
                }
            flag = False
            # first check if there are any leaf nodes that can be reduced
            reducible, _ = self.infer.G.frontier(state=states.REDUCIBLE, update_state=False)
            if reducible:
                propagatedToRoot = self.infer.run_frank(reducible[0])
                if propagatedToRoot:
                    self.cache_and_print_answer(False)
                    flag = True

            if not flag:
                # check if there are any unexplored leaf nodes
                unexplored, _ = self.infer.G.frontier(state=states.UNEXPLORED, update_state=False)
                # if unexplored and last_root_prop_depth > 0 and (unexplored[0].depth > last_root_prop_depth + max_prop_depth_diff):
                #     stop_flag = True
                #     break
                if unexplored:
                    propagatedToRoot = self.infer.run_frank(unexplored[0])
                    if propagatedToRoot:
                        last_root_prop_depth = unexplored[0].depth
                        self.cache_and_print_answer(False)
                        flag = True
                # else:
                #     stop_flag = True
                #     break
            if not flag:
                break

        if stop_flag:
            self.cache_and_print_answer(True)
        else:
            # if no answer has been propagated to root and
            if time.time() - self.infer.last_heartbeat <= self.timeout:
                time.sleep(3)
            unexplored, _ = self.infer.G.frontier(update_state=False)
            if unexplored:
                self.schedule(last_root_prop_depth)
            else:
                # stop and print any answer found
                self.cache_and_print_answer(True)

    def cache_and_print_answer(self, isFinal=False):
        elapsed_time = time.time() - self.start_time
        answer = 'No answer found'

        if self.infer.propagated_alists:
            latest = self.infer.propagated_alists[-1]
            latest_root = self.infer.G.find_complement_node(latest)[0]


            # get projection variables from the alist
            # only one projection variable can be used as an alist
            projVars = latest_root.projection_variables()
            if projVars:
                for pvkey, pv in projVars.items():
                    answer = latest_root.instantiation_value(pvkey)

            # if no projection variables exist, then use aggregation variable as answer
            else:
                answer = latest_root.get(tt.OPVALUE)
 
            # format error bar
            errorbar = 0.0
            try:
                errorbar = utils.get_number(latest_root.get(
                    tt.COV), 0) * utils.get_number(answer, 0)
                errorbar_sigdig = utils.sig_dig(
                    errorbar, int(config.config["errorbar_sigdig"]))
            except Exception:
                pass
            ans_obj = {"answer": f"{answer}",
                       "error_bar": f"{errorbar_sigdig}",
                       "sources": f"{','.join(list(latest_root.data_sources))}",
                       "elapsed_time": f"{round(elapsed_time)}s",
                       "alist": self.infer.propagated_alists[-1].attributes
                       }

            self.inference_graphs[self.infer.session_id]['graph'] = self.infer.G
            self.inference_graphs[self.infer.session_id]['intermediate_answer'] = ans_obj
            self.inference_graphs[self.infer.session_id]['answer'] = ans_obj if isFinal else None

            if self.debug == 1 and self.is_cli:
                self.infer.G.plot_plotly(question=self.question, answer=answer)


            if isFinal:
                print(f"\n{pcol.CYAN}Answer alist{pcol.RESETALL} \n" +
                      json.dumps(ans_obj, indent=2))
                if self.is_cli:
                    self.infer.G.plot_plotly(question=self.question, answer=answer)
                

# if __name__ == '__main__':
#     launcher = Launcher()
#     launcher.cli()
