'''
File: frank_api.py
Description: Command line interface FRANK


'''

import json
import uuid
import argparse
import matplotlib.pyplot as plt
from frank.launcher import Launcher
from frank.config import config
from graph.alist import Alist
from graph.alist import Attributes as tt
from graph.inference_graph import InferenceGraph
from frank.processLog import pcolors as pcol


inference_graphs = {}
argparser =  argparse.ArgumentParser(
        prog="FRANK CLI", 
        description="Command line interface for FRANK")
argparser.add_argument("-q", "--query", type=str, 
    default="", help="a query to be answered; alist query")
argparser.add_argument("-c", "--context", type=str,
    default={}, help="context for the query; (default = {})")
argparser.add_argument("-f", "--file", type=str,
    help="batch file; used when evaluating multiple questions in a file")
argparser.add_argument("-o", "--output", type=str,
    default="output.json", help="file to output batch query results to; (default = output.json)")
argparser.add_argument("-d", "--debug", type=int,
    default=0, help="plot inference graph during decompositions")


def cli(query, context={}, debug=0):
    session_id = uuid.uuid4().hex
    interactive = False
    answer = None
    if query:
        query_json = None
    else:
        print(f"\n{pcol.CYAN}FRANK CLI{pcol.RESETALL}")
        query = input(f"Enter question or alist query: \n {pcol.CYAN}>{pcol.RESETALL} ")
        context = input(f"Enter context: \n {pcol.CYAN}>{pcol.RESETALL} ")
        query_json = None
        interactive = True
    
    # check if input is question or alist
    if type(query) == str and '{' in query and '"' in query:
        query_json = json.loads(query)
    elif type(query) == dict:
        query_json = query
    else:
        print("Enter an alist query")

    if query_json:        
        alist = Alist(**query_json)
        if context:
            context_json = json.loads(context) if type(context) == str else context
            alist.set(tt.CONTEXT, context_json)
        print(f"{pcol.YELLOW} ├── query alist:{json.dumps(alist.attributes)} {pcol.RESETALL}")
        print(f"{pcol.YELLOW} └── session id:{session_id} {pcol.RESETALL}\n")
        launch = Launcher()
        launch.start(query, alist, session_id, inference_graphs, debug, is_cli=True)

        if session_id in inference_graphs:
            answer = inference_graphs[session_id]['answer']['answer']
            graph = inference_graphs[session_id]['graph']
            # graph.plot_plotly(query, answer)
        if interactive:
            input("\npress any key to exit")
    else:
        print("\nCould not parse question. Please try again.")
    return answer

def batch(batch_file, output, debug=0):
    results = []
    with open(batch_file) as json_file:
        queries = json.load(json_file)
        for q in queries:
            answer = cli(q['question'], q['context'], debug)
            results.append({'id': q['id'], 'answer': answer})
            with open(output, 'w') as out_file:
                json.dump(results, out_file)
    
    
    
    print('Done! \nResults in ' + output)


if __name__ == '__main__':
    args = argparser.parse_args()
    if args.file and args.query:
        print("\nThe --query option cannot be used with the --file option.")
    if args.file and args.context:
        print("\nCannot use --context together with the --file flag.")  

    if args.file:
        batch(args.file, args.output, args.debug)
    else:
        cli(args.query, args.context, args.debug)
 