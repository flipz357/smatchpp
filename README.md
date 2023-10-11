# SMATCH++

The package allows handy processing of graphs including graph alignment and graph matching. There is a special focus on standardized evaluation of semantic AMR graphs via structural matching ('Smatch'), but in principle the package allows straightforward extension to working also with other kinds of graphs. A short overview of some features:

- Simple graph reading, graph writing, different syntactic and semantic standardization options tailored to AMR
- Alignment solvers including optimal ILP alignment, and optional graph compression
- Evaluation scoring with bootstrap confidence intervals, micro and macro averages
- AMR-targeted subgraph extraction and extended scoring for spatial, temporal, causal, and more meaning aspects

Jump directly to [parser evaluation best practices](#basic-eval) or (new) [pip install](#pip-install) to use smatch++ and its options simply from within your python program. The following text also gives an overview over some options of Smatch++. 

## Requirements

For the most basic version, there shouldn't be a need to install additional modules. However, when using ILP optimal solving and bootstrapping, we require

```
mip (tested: 1.13.0)
scipy (tested: 1.10.1)
numpy (tested: 1.20.1)
```

The packages can be installed with `pip ...`

## Example configurations for evaluation

### Best practice: ILP alignment, dereification, corpus metrics and confidence intervals<a id="basic-eval"></a>

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
- Optimality: -
- Graph standardization: ++

```
python -m smatchpp      -a <amrs1> \
			-b <amrs2> \
			-solver hillclimber \
			-syntactic_standardization dereify \
			-score_dimension main \
			-score_type micromacro \
			-log_level 20 \
			--bootstrap \
			--remove_duplicates
```


### Fast ILP alignment with graph compression, corpus metrics and confidence intervals

- Efficiency: ++ 
- Optimality: +++
- Graph standardization: + 

```
python -m smatchpp      -a <amrs1> \
			-b <amrs2> \
			-solver ilp \
			-syntactic_standardization dereify \
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
			-syntactic_standardization reify \
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
			-syntactic_standardization dereify \
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

## Pip install<a id="pip-install"></a>

### Pip installation

Simply run 

`pip install smatchpp`

The main interface is a smatchpp.Smatchpp object. With this, most kinds of operations can be performed on graphs and pairs of graphs. Some examples are in the following,

### Example I: Smatch++ matching with some basic default

This uses some basic default such as lower-casing and hill-climber.

```python
from smatchpp import Smatchpp
measure = Smatchpp()
match, optimization_status, alignment = measure.process_pair("(t / test)", "(t / test)")
print(match) # {'main': array([2., 2., 2., 2.])}, 2 left->right, 2 in right->left, 2 length of left, 2 length of right
```
Note: Here it's two triples matching since there is an implicit root.

For greater convienience, we can also directly get an F1 / Precision / Recall score:

```python
from smatchpp import Smatchpp
measure = Smatchpp()
score = measure.score_pair("(t / test)", "(t / test)")
print(score) # prints a json dict with convenient scores: {'main': {'F1': 100.0, 'Precision': 100.0, 'Recall': 100.0}}
```

### Example II: Smatch++ matching same as default but with ILP

In this example, we use ILP for optimal alignment.

```python
from smatchpp import Smatchpp, solvers
ilp = solvers.ILP()
measure = Smatchpp(alignmentsolver=ilp)
match, optimization_status, alignment = measure.process_pair("(t / test)", "(t / test)")
print(match) # in this case same result as Example I
```

As in the first example, for convenience, we can also get directly an F1/Precision/Recall score.

```python
from smatchpp import Smatchpp, solvers
ilp = solvers.ILP()
measure = Smatchpp(alignmentsolver=ilp)
score = measure.score_pair("(t / test)", "(t / test)")
print(score) # prints a json dict with convenient scores: {'main': {'F1': 100.0, 'Precision': 100.0, 'Recall': 100.0}}
```

### Example III: Best-Practice matching for a pair of AMR graphs.

Beyond basic defaults, we need an ILP solver for best alignment and dereification for graph standadization.

```python
from smatchpp import Smatchpp, solvers, preprocess
graph_standardizer = preprocess.AMRStandardizer(syntactic_standardization="dereify")
ilp = solvers.ILP()
measure = Smatchpp(alignmentsolver=ilp, graph_standardizer=graph_standardizer)
score = measure.score_pair("(m / man :accompanier (c / cat))", "(m / man :arg1-of (a / accompany-01 :arg0 (c / cat)))") # equivalent AMR graphs 
print(score) # prints a json dict with convenient scores: {'main': {'F1': 100.0, 'Precision': 100.0, 'Recall': 100.0}}
```

Note that the measure returns a score of 100 even though the input graphs are structurally different. This is due to advanced standardization tailored to AMR, called de/reification rules that translate between different graph structures, ensuring equivalency. Please find more information in the [Smatch++ paper](https://arxiv.org/abs/2305.06993) or the [AMR guidelines](https://github.com/amrisi/amr-guidelines/blob/master/amr.md). Note that although de/reified structures apparently can be quite different, in practice a parser evaluation score is not much different (with/without dereification), since gold AMRs are dereified by default (sometimes, parsers forget to dereify, and therefore by ensuring dereification as preprocessing, a more fair comparison is ensured).

### Example IV: Best practice for AMR corpus scoring

According to best practice, here we want to compute "micro Smatch" for a parser output and a reference with bootstrap 95% confidence intervals.

```python
from smatchpp import Smatchpp, solvers, preprocess, eval_statistics
graph_standardizer = preprocess.AMRStandardizer(syntactic_standardization="dereify")
printer = eval_statistics.ResultPrinter(score_type="micro", do_bootstrap=True, output_format="json")
ilp = solvers.ILP()
measure = Smatchpp(alignmentsolver=ilp, graph_standardizer=graph_standardizer, printer=printer)
corpus1 = ["(t / test)", "(d / duck)"] * 100 # we extend the lists because bootstrap doesn't work with tiny corpora
corpus2 = ["(t / test)", "(a / ant)"] * 100 # we extend the lists because bootstrap doesn't work with tiny corpora
score, optimization_status = measure.score_corpus(corpus1, corpus2)
print(score) # {'main': {'F1': {'result': 50.0, 'ci': (43.0, 57.0)}, 'Precision': {'result': 50.0, 'ci': (43.0, 57.0)}, 'Recall': {'result': 50.0, 'ci': (43.0, 57.0)}}}
```

If you want to get access to the *full bootstrap distribution* you can add `also_return_bootstrap_distribution=True` when creating the `printer`. Beware that in this case the `score` result will be very large. Note also that for this we require scipy version of at least 1.10.0.

### Example V: Standardize and extract subgraphs

```python
from smatchpp import Smatchpp
measure = Smatchpp()
string_graph = "(c / control-01 :arg1 (c2 / computer) :arg2 (m / mouse))"
g = measure.graph_reader.string2graph(string_graph)
g = measure.graph_standardizer.standardize(g)
name_subgraph_dict = measure.subgraph_extractor.all_subgraphs_by_name(g)

# get subgraph for "instrument"
print(name_subgraph_dict["INSTRUMENT"]) # [(c, instance, control-01), (m, instance, mouse), (c, instrument, m)]
```

Note that the result is the same as when we mention the `instrument` edge explicitly, i.e., `string_graph = "(c / control-01 :arg1 (c2 / computer) :instrument (m / mouse))"`. 
Such a semantic standarization can also be performed on a full graph by loading an explicit standardizer (here without subgraph extraction), which explicates core-roles, if possible:

```python
from smatchpp import data_helpers, preprocess
graph_reader = data_helpers.PenmanReader()
graph_writer = data_helpers.PenmanWriter()
graph_standardizer = preprocess.AMRStandardizer(semantic_standardization=True)
string_graph = "(c / control-01 :arg1 (c2 / computer) :arg2 (m / mouse))"
g = graph_reader.string2graph(string_graph)
g = graph_standardizer.standardize(g)
print(g) # [('c', ':instrument', 'm'), ('c', ':instance', 'control-01'), ('c1', ':instance', 'computer'), ('m', ':instance', 'mouse'), ('c', ':arg1', 'c1'), ('c', ':root', 'control-01')]
```

### Example VI: get an alignment

In this example, we retrieve an alignment between graph nodes.

```python
from smatchpp import Smatchpp
measure = Smatchpp()
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

Note that the alignment is a by-product of the matching and can be also retrieved in simpler ways (here we showed the process from scratch).

### Example VII: Read, standardize and write graph

In this example, we read a basic graph from a string, apply reification standardization, and write the reified graph to a string.

```python
from smatchpp import data_helpers, preprocess
graph_reader = data_helpers.PenmanReader()
graph_writer = data_helpers.PenmanWriter()
graph_standardizer = preprocess.AMRStandardizer(syntactic_standardization="reify")
s = "(t / test :mod (s / small :mod (v / very)) :quant 2 :op v)"
g = graph_reader.string2graph(s)
g = graph_standardizer.standardize(g)
string = graph_writer.graph2string(g)
print(string) # (t / test :op (v / very :arg2-of (ric5 / have-mod-91 :arg1 (s / small :arg2-of (ric3 / have-mod-91 :arg1 t)))) :arg1-of (ric6 / have-quant-91 :arg2 2))
```

### Example VIII: Lossless pairwise graph compression<a id="lossless-gc"></a>

Lossless graph compression means that the graph size and alignment search space shrinks, but the input graphs can be fully reconstructed. This may be ideal for very fast matching, or quicker matching of very large graphs. Note that it holds that if Smatch on two compressed graphs equals 1, it is also the case for the uncompressed graphs, and vice versa.

```python
from smatchpp import preprocess
pair_preparer_compressor = preprocess.AMRPairPreparer(lossless_graph_compression=True)
g1 = [("c", ":instance", "cat"), ("c2", ":instance", "cat"), ("d", ":instance", "dog"), ("c", ":rel", "d"), ("c2", ":otherrel", "d")]
g2 = [("c", ":instance", "cat"), ("d", ":instance", "dog"), ("c", ":rel", "d")]
print(len(g1), len(g2)) #5, 3
g1, g2, _, _ = pair_preparer_compressor.prepare_get_vars(g1, g2)
print(len(g1), len(g2)) #4, 2
```

If we want to use the compression in the matching, simply set the argument `graph_pair_preparer=pair_preparer_compressor`, while initializing a `Smatchpp` object.

## FAQ

- *I want to process other kinds of graphs*: While tailored to AMR the package allows processing of all kinds of graphs. To evaluate graphs that are different from AMR, it can be good to remove AMR-specifc arguments (like `syntactic_standardization` in `score.sh`), other than that there should be no other things to do. Of course, if you have specific graphs it can also help to write your own standardizer (see example for AMRStandardizer in `smatchpp/preprocess.py`) and possibly create another Reader (currently it is possibly to read graphs in penman form or tsv, see readers in `smatchpp/data_helpers.py').

- *I have very large graphs and optimal ILP doesn't terminate*: This is because optimal alignment is fundamentally an NP hard problem. In this case we have three options. 1. use a heuristic by setting solver as HillClimber (unfortunately the solutions by heuristic will get worse if graphs are large since there are lots of local optima where it can get stuck). 2. Use ILP with `--lossless_graph_compression` as argument from console (for python see [Example VIII](#lossless-gc)). This makes evaluation much faster and still gives an optimal score (the score tends to be slightly harsher/lower). 3. you can play with the `max_seconds` argument in the ILP solver (see `ILPSolver` in `smatchpp/solvers.py`) and reduce it to get a solution that may be not optimal (as in the hill-climber) but also has a useful upper-bound to understand solution quality. Maybe, in case of large graphs option 2. is most suitable as it can offer best solution quality.

- *I want to use other triple matching functions*: Sometimes, e.g., in evaluation of cross-lingual graphs, we want to have that a triple `(x, instance, cat)` be similar to `(x, instance, kitten)` and allow graded matching. Smatch++ allows easy customization of the triple matching function, and you can easily implement your own class. For examples, see file `smtachpp/score.py`.

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
