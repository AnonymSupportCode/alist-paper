# Supplementary data for ALIST Paper

## Setup

* Install the Python programming language (version 3.9) (https://www.python.org/downloads/)
* Install the required python packages by running the code below in the terminal:

```
python -m pip install -r requirements.txt
```

## Alist Examples from LC-QuAQ question types

List of examples are in the alist_lcquad.txt file

## Inference Using Alists
Run the `eval.py` script using the following command in the terminal.

```
python eval.py
```

Script runs a set of alist queries, and for each returns a trace of the inference process detailing the decomposition and aggregation of alists. It also returns an answer alist, together with a web page (that should open your default browsing) showing the inference graph for each query. Hover over nodes in the inference graph to view the content of alist in each node.

### Notes and Assumptions:

* Relevant code files:\
    * Code for the alsit and inference graph is located in the `\graph` directory.
    * Code for decomposition (map) and aggregation (reduce) operations are stored in the 
`\frank\map\` and `\frank\reduce\` directories. 
    * Code for interfaces to difference knowledge bases are in the `\frank\kb\` directory.

* Data that is needed to answer the quesions are not saved locally, and so an internet connection is requiured to retrieve data from knowledge sources including Wikidata, MusicBrainz and the World Bank. This is necessary to evidence the dynamic curation of data from different sources using alists.

* To speed up retrieval of data from Wikdata, we locally cache a list of property names and their corresponding Wikidata indentifiers. This reduces the number of calls we make to the Wikidata endpoint to avoid breaching their data request limits. Similarly, for the World Bank's dataset, we cache a list of countries.