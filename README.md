# SMATCH++

The package targets standardized evaluation of graph parsers with Smatch (structural matching of graphs). While it is oriented at standardized (A)MR evaluation it also allows processing of other kinds of graph structures and operations such as sub-graph extraction or graph compression for faster metric computation. A short overview:

- Graph reading, graph writing, different graph standardization options  
- Different alignment solvers including optimal ILP alignment
- Evaluation scoring with bootstrap confidence intervals, micro and macro averages
- AMR-targeted subgraph extraction and extended scoring for spatial, temporal, causal, and more meaning aspects

Jump directly to [easy and standardized parser evaluation](#basic-eval) or (new) [pip install](#pip-install) to use smatch++ and its options simply from within your python program. The following text also gives an overview over some options of Smatch++.

## Requirements

For the most basic version, there shouldn't be a need to install additional modules. However, when using ilp optimal solving and bootstrapping, we require

```
mip (tested: 1.13.0)
scipy (tested: 1.7.3)
numpy (tested: 1.20.1)
```

The packages can all be installed with `pip ...`

## Example configurations

### Recommended for average case: ILP alignment, dereification, corpus metrics and confidence intervals<a id="basic-eval"></a>

- Efficiency: + 
- Optimality: +++
- Graph standardization: ++ 

**Simply call**: 

```
./score.sh <amrs1> <amrs2>
``` 

where `<amrs1>` and `<amrs2>` are the paths to the files with graphs. Format is assumed to be in "penman":

```
# first graph
(x / y
   :rel (w / z))

# second graph
(...
```

Or can set to tsv with `-input_format tsv`, where the file looks like:

```
# first graph
x y nodelabel
w z nodelabel
x w rel

# second graph
...
```

### Hill-climber alignment, dereification, corpus metrics and confidence intervals

- Efficiency: ++ 
- Optimality: +
- Graph standardization: ++

```
python -m smatchpp      -a <amrs1> \
			-b <amrs2> \
			-solver hillclimber \
			-edges dereify \
			-score_dimension main \
			-score_type micromacro \
			-log_level 20 \
			--bootstrap \
			--remove_duplicates
```


### Fast ILP with graph compression, corpus metrics and confidence intervals

- Efficiency: ++ 
- Optimality: +++
- Graph standardization: + 

```
python -m smatchpp      -a <amrs1> \
			-b <amrs2> \
			-solver ilp \
			-edges dereify \
			-score_dimension main \
			-score_type micromacro \
			-log_level 20 \
			--bootstrap \
			--remove_duplicates \
			--lossless_graph_compression
```

### ILP with reification, corpus metrics and confidence intervals

- Efficiency: -
- Optimality: +++
- Graph standardization: +++

```
python -m smatchpp      -a <amrs1> \
			-b <amrs2> \
			-solver ilp \
			-edges reify \
			-score_dimension main \
			-score_type micromacro \
			-log_level 20 \
			--bootstrap \
			--remove_duplicates \
```

### ILP alignment, corpus sub-aspect metrics and confidence intervals

- Efficiency: + 
- Optimality: +++
- Graph standardization: ++ 

```
python -m smatchpp      -a <amrs1> \
			-b <amrs2> \
			-solver ilp \
			-edges dereify \
			-score_dimension all-multialign \
			-score_type micromacro \
			-log_level 20 \
			--bootstrap \
			--remove_duplicates \
```

### Other configurations

See

```
python -m smatchpp --help
```

## Additional functionality

### Custom triple matching

Can be implemented in `score.py`

### Changing subgraph metrics

See `subgraph_extraction.py` 

## Pip install<a id="pip-install"></a>

### Pip installation

Simply run 

`pip install smatchpp`

The main interface is a smatchpp.Smatchpp object. With this, most kinds of operations can be performed on graphs and pairs of graphs. Some examples are in the following,

### Example I: Smatch++ matching with some basic default

```python
import smatchpp
measure = smatchpp.Smatchpp()
match, optimization_status, alignment = measure.process_pair("(t / test)", "(t / test)")
print(match) # [2, 2, 2, 2], 2 left->right, 2 in right->left, 2 length of left, 2 length of right 
```

Note: Here it's two triples matching since there is an implicit root.

### Example II: Standardize and extract subgraphs

```python
import smatchpp
measure = smatchpp.Smatchpp()
string_graph = "(c / control-01 :arg1 (c2 / computer) :arg2 (m / mouse))"
g = measure.graph_reader.string2graph(string_graph)
g = measure.graph_standardizer.standardize(g)
name_subgraph_dict = measure.subgraph_extractor.all_subgraphs_by_name(g)

# get subgraph for "instrument"
print(name_subgraph_dict["INSTRUMENT"]) # [(c, instance, control-01), (m, instance, mouse), (c, instrument, m)]
```

Note that the result is the same as when we mention the `instrument` edge explicitly, i.e., `string_graph = "(c / control-01 :arg1 (c2 / computer) :instrument (m / mouse))"`. 
Such a semantic standarization can also be performed on a full graph by loading an explicit standardizer (here without subgraph extraction):

```python
from smatchpp import data_helpers, preprocess
graph_reader = data_helpers.PenmanReader()
graph_writer = data_helpers.PenmanWriter()
graph_standardizer = preprocess.AMRGraphStandardizer(semantic_standardization=True)
string_graph = "(c / control-01 :arg1 (c2 / computer) :arg2 (m / mouse))"
g = graph_reader.string2graph(string_graph)
g = graph_standardizer.standardize(g)
print(g) # [(c, instance, control-01), (m, instance, mouse), (c, instrument, m), (c, arg1, c2), (c2, instance, computer)]
```

### Example III: Smatch++ matching same as default but with ILP

In this example, we use ILP for optimal alignment.

```python
import smatchpp, smatchpp.solvers
ilp = smatchpp.solvers.ILP()
measure = smatchpp.Smatchpp(alignmentsolver=ilp)
match, optimization_status, alignment = measure.process_pair("(t / test)", "(t / test)")
print(match) # in this case same result as Example I
```

### Example IV: get an alignment

In this example, we retrieve an alignment between graph nodes.

```python
import smatchpp
measure = smatchpp.Smatchpp()
measure.graph_standardizer.relabel_vars = False
s1 = "(x / test)"
s2 = "(y / test)"
g1 = measure.graph_reader.string2graph(s1)
g1 = measure.graph_standardizer.standardize(g1)
g2 = measure.graph_reader.string2graph(s2)
g2 = measure.graph_standardizer.standardize(g2)
g1, g2, v1, v2 = measure.graph_pair_preparer.prepare_get_vars(g1, g2)
alignment, var_index, _ = measure.graph_aligner.align(g1, g2, v1, v2)
var_map = measure.graph_aligner._get_var_map(alignment, var_index)
interpretable_mapping = measure.graph_aligner._interpretable_mapping(var_map, g1, g2)
print(interpretable_mapping) # prints [[('aa_x_test', 'bb_y_test')]], where aa/bb indicates 1st/2nd graph
```

Note that the alignment is a by-product of the matching and can be also retrieved in simpler ways (here we show the process from scratch).

### Example V: Read, standardize and write graph

In this example, we read a basic graph from a string, apply reification standardization, and write the reified graph to a string.
```python
from smatchpp import data_helpers, preprocess
graph_reader = data_helpers.PenmanReader()
graph_writer = data_helpers.PenmanWriter()
graph_standardizer = preprocess.AMRGraphStandardizer(edges="reify")
s = "(t / test :mod (s / small :mod (v / very)) :quant 2 :op v)"
g = graph_reader.string2graph(s)
g = graph_standardizer.standardize(g)
string = graph_writer.graph2string(g)
print(string) # (t / test :op (v / very :arg2-of (ric5 / have-mod-91 :arg1 (s / small :arg2-of (ric3 / have-mod-91 :arg1 t)))) :arg1-of (ric6 / have-quant-91 :arg2 2))
```

## Citation

If you like the project, consider citing

```
@inproceedings{opitz-2023-smatch,
    title = "{SMATCH}++: Standardized and Extended Evaluation of Semantic Graphs",
    author = "Opitz, Juri",
    booktitle = "Findings of the Association for Computational Linguistics: EACL 2023",
    month = may,
    year = "2023",
    address = "Dubrovnik, Croatia",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2023.findings-eacl.118",
    pages = "1595--1607"
}
```
