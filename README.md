# SMATCH++

Handy processing of graphs including graph alignment and graph matching. There is a special focus on standardized evaluation of graph parsing, but SMATCH++ allows easy customization. A short overview of some features:

- Simple graph reading, graph writing, graph processing
- Different alignment solvers including optimal ILP alignment, and optional graph compression
- Evaluation scoring with bootstrap confidence intervals, micro and macro averages
- Standardization for different graph types such as AMR, Fine-grained evaluation
- Easy to extend

Jump directly to [parser evaluation best practices](#basic-eval) or (new) [pip install](#pip-install) to use Smatch++ and its options simply from within your python program. The following text also gives an overview over some options of Smatch++. 

## Requirements

For the most basic version, there shouldn't be a need to install additional modules. However, when using ILP optimal solving and bootstrapping for evaluation (highly recommended!), we require

```
mip (tested: 1.13.0)
scipy (tested: 1.10.1)
numpy (tested: 1.20.1)
```

The packages can be installed with `pip ...`

## Example configurations for best-practice evaluation

### Best practice for AMR evaluation<a id="basic-eval"></a>

This evaluation setup has optimal ILP alignmnent, calculates micro and macro corpus metrics and confidence intervals. It also applies AMR graph standardization.

**Simply call**: 

```
./score.sh <graphs1> <graphs2>
``` 

where `<graphs1>` and `<graphs2>` are the paths to the files with graphs. Format is assumed to be in "penman":

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

## Other interesting configurations

### Evaluating other kinds of graphs

For evaluating other kinds of graphs, set the flag `-graph_type generic` in `score.sh`, to peform some minimal generic standardization. Or remove the flag, to perform no graph pre-processing at all.

### Using hill-climber (⚠️)

For using a hill-climber as solver, set the flag `-solver hillclimber` in `score.sh`. ⚠️**Warning**⚠️: Using a hill-climber is not advisable and will yield Smatch scores that are not verifiable and are likely false.

### Fast ILP alignment with graph compression

For using a graph compression to make evaluation much faster, add the flag `--lossless_graph_compression` in `score.sh`

### Fine-grained aspect scoring

Here we want to measure performance on differnt types of subgraphs (e.g., NER, cause, etc.). This is currently only available when `-graph_type amr`, for other graph types, you need to define your custom subgraph extraction. To do fine-grained score set the flag `-score_dimension all-multialign` or `score_dimension onealign`. Multi align re-calculates alignments for each pair of sub-graph, one-align calculates one alignment for a pair of graphs which is then re-used for the sub-graph pairs.

### Visit other options of evaluation

See

```
python -m smatchpp --help
``` 

## Python package<a id="pip-install"></a>

### Pip installation

Simply run 

`pip install smatchpp`

The main interface is a smatchpp.Smatchpp object. With this, most kinds of operations can be performed on graphs and pairs of graphs. For other and more custom operations, specific modules can be loaded. Some examples are in the following,

### Example I: Smatch++ matching with basic default<a id="ex-basicdefault"></a>

This uses a hill-climber and does not standardize the graphs in any way.

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

### Example II: Optimal Smatch++ with ILP<a id="ex-basicdefault-ilp"></a>

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

### Example III: Best-Practice matching for a pair of AMR graphs<a id="ex-basicdefault-amr"></a>

Beyond basic defaults, we need an ILP solver for best alignment and dereification for graph standadization.

```python
from smatchpp import Smatchpp, solvers, preprocess
graph_standardizer = preprocess.AMRStandardizer()
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
graph_standardizer = preprocess.AMRStandardizer()
printer = eval_statistics.ResultPrinter(score_type="micro", do_bootstrap=True, output_format="json")
ilp = solvers.ILP()
measure = Smatchpp(alignmentsolver=ilp, graph_standardizer=graph_standardizer, printer=printer)
corpus1 = ["(t / test)", "(d / duck)"] * 100 # we extend the lists because bootstrap doesn't work with tiny corpora
corpus2 = ["(t / test)", "(a / ant)"] * 100 # we extend the lists because bootstrap doesn't work with tiny corpora
score, optimization_status = measure.score_corpus(corpus1, corpus2)
print(score) # {'main': {'F1': {'result': 50.0, 'ci': (43.0, 57.0)}, 'Precision': {'result': 50.0, 'ci': (43.0, 57.0)}, 'Recall': {'result': 50.0, 'ci': (43.0, 57.0)}}}
```

If you want to get access to the *full bootstrap distribution* you can add `also_return_bootstrap_distribution=True` when creating the `printer`. Beware that in this case the `score` result will be very large. Note also that for this we require scipy version of at least 1.10.0.

### Example V: Standardize and extract subgraphs for AMR

```python
from smatchpp import preprocess, subgraph_extraction, data_helpers
reader = data_helpers.PenmanReader()
standardizer = preprocess.AMRStandardizer()
subgraph_extractor = subgraph_extraction.AMRSubGraphExtractor()
string_graph = "(c / control-01 :arg1 (c2 / computer) :arg2 (m / mouse))"
g = reader.string2graph(string_graph)
g = standardizer.standardize(g)
name_subgraph_dict = subgraph_extractor.all_subgraphs_by_name(g)

# get subgraph for "instrument"
print(name_subgraph_dict["INSTRUMENT"]) # [(c, instance, control-01), (m, instance, mouse), (c, instrument, m)]
```

Note that the result is the same as when we mention the `instrument` edge explicitly, i.e., `string_graph = "(c / control-01 :arg1 (c2 / computer) :instrument (m / mouse))"`. 
Such a semantic standarization can also be performed on a full graph by loading an explicit standardizer (here without subgraph extraction), which explicates core-roles, if possible:

```python
from smatchpp import data_helpers, graph_transforms
graph_reader = data_helpers.PenmanReader()
graph_transformer = graph_transforms.RuleBasedSemanticAMRTransformer()
string_graph = "(c / control-01 :arg1 (c2 / computer) :arg2 (m / mouse))"
g = graph_reader.string2graph(string_graph)
g = graph_transformer.transform(g)
print(g) # [('c', ':instrument', 'm'), ('c', ':instance', 'control-01'), ('c1', ':instance', 'computer'), ('m', ':instance', 'mouse'), ('c', ':arg1', 'c1'), ('c', ':root', 'control-01')]
```

### Example VI: get an alignment

In this example, we retrieve an alignment between graph nodes.

```python
from smatchpp import Smatchpp
measure = Smatchpp()
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

### Example VII: Read, reify and write graph

In this example, we read a basic graph from a string, apply reification standardization, and write the reified graph to a string.

```python
from smatchpp import data_helpers, graph_transforms
graph_reader = data_helpers.PenmanReader()
graph_writer = data_helpers.PenmanWriter()
reifier = graph_transforms.RuleBasedSyntacticAMRTransformer(mode="reify")
s = "(t / test :mod (s / small :mod (v / very)) :quant 2 :op v)"
g = graph_reader.string2graph(s)
g = reifier.transform(g)
string = graph_writer.graph2string(g)
print(string) # (t / test :op (v / very :arg2-of (ric5 / have-mod-91 :arg1 (s / small :arg2-of (ric3 / have-mod-91 :arg1 t)))) :arg1-of (ric6 / have-quant-91 :arg2 2))
```

### Example VIII: Lossless pairwise graph compression<a id="ex-lossless-gc"></a>

Lossless graph compression means that the graph size and alignment search space shrinks, but the input graphs can be fully reconstructed. This may be ideal for very fast matching, or quicker matching of very large graphs. Note that it holds that if Smatch on two compressed graphs equals 1, it is also the case for the uncompressed graphs, and vice versa.

```python
from smatchpp import preprocess
pair_preparer_compressor = preprocess.BasicGraphPairPreparer(lossless_graph_compression=True)
g1 = [("c", ":instance", "cat"), ("c2", ":instance", "cat"), ("d", ":instance", "dog"), ("c", ":rel", "d"), ("c2", ":otherrel", "d")]
g2 = [("c", ":instance", "cat"), ("d", ":instance", "dog"), ("c", ":rel", "d")]
print(len(g1), len(g2)) #5, 3
g1, g2, _, _ = pair_preparer_compressor.prepare_get_vars(g1, g2)
print(len(g1), len(g2)) #4, 2
```

If we want to use the compression in the matching, simply set the argument `graph_pair_preparer=pair_preparer_compressor`, while initializing a `Smatchpp` object.

### Example IX: Plug in custom standardizer in the matching<a id="ex-custom-standardizer"></a>

To customize SMATCH++ in any ways should be easy. Here, in this example, we want to plug in a custom graph processing to make graphs unlabeled:

```python
from smatchpp import Smatchpp
measure = Smatchpp()
s1 = "(x / y :abc (w / z))"
s2 = "(x / y :cde (w / z))"
print(measure.score_pair(s1, s2)) # {'main': {'F1': 75.0, 'Precision': 75.0, 'Recall': 75.0}}

# design a custom standardizer class (just needs to have a _standardize function)
from smatchpp import interfaces
class Unlabeler(interfaces.GraphStandardizer):
    def _standardize(self, triples):
        return [(s, ":rel", t) for s, _, t in triples]

# init object and re-score
my_standardizer = Unlabeler()
custom_measure = Smatchpp(graph_standardizer=my_standardizer)
print(custom_measure.score_pair(s1, s2)) # {'main': {'F1': 100.0, 'Precision': 100.0, 'Recall': 100.0}}
```

### Example X: Feeding graph directly without string reading

Again, there's different ways to achieve this, like building you own pipeline. However, simplest would be to implement a dummy reader:

```python
from smatchpp import Smatchpp, interfaces
test_graph1 = [("ROOT", ":root", "x"), ("x", ":instance", "test")] # string: (x / test)
test_graph2 = [("ROOT", ":root", "y"), ("y", ":instance", "test")] # string: (y / test)

class DummyReader(interfaces.GraphReader):
    def _string2graph(self, input):
        return input

dummy_reader = DummyReader()
Smatchpp(graph_reader=dummy_reader).score_pair(test_graph1, test_graph2) # {'main': {'F1': 100.0, 'Precision': 100.0, 'Recall': 100.0}}
```


## FAQ

- *I want to process other custom graph type*: Consider implementing your custom graph standardizer that can then be used as shown [Example IX](#ex-custom-standardizer).

- *I have very large graphs and optimal ILP doesn't terminate*: This is because optimal alignment is fundamentally an NP hard problem. Mitigation options: 1. use heuristic by setting solver as HillClimber (unfortunately heuristic will get worse if graphs are large since there are lots of local optima where it can get stuck). 2. Use ILP with `--lossless_graph_compression` as argument from console (for python see [Example VIII](#ex-lossless-gc)). This makes evaluation fast and still gives an optimal score (the score tends to be slightly harsher/lower). 3. You can play with the `max_seconds` argument in the ILP solver (see `ILPSolver` in `smatchpp/solvers.py`) and reduce it to get a solution that may be not optimal but also has a useful upper-bound to understand solution quality. Maybe, in case of large graphs option 2. is most suitable as it can offer best solution quality.

- *I want to use other triple matching functions*: Sometimes, e.g., in evaluation of cross-lingual graphs, we want to have that a triple `(x, instance, cat)` be similar to `(x, instance, kitten)` and allow graded matching. Smatch++ allows easy customization of the triple matching function, and you can easily implement your own class. For examples, see file `smatchpp/score.py`.

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
