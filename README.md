# SMATCH++

Handy processing of graphs including graph alignment and graph matching. There is a special focus on standardized evaluation of graph parsing, but SMATCH++ allows easy extension for custom purposes and graph processing tasks. A short overview of some features:

- Simple graph reading, graph processing, graph matching
- Different graph alignment options including optimal ILP solver
- Evaluation scoring with bootstrap confidence intervals, micro and macro averages
- Standardization and best-practice for different graph types
- Fine-grained evaluation, graph compression for fast ILP
- Easy to extend

#### Table of contents

- [Requirements](#requirements)
- [**Command line examples**](#command-line)
    - [Best practice for graph evaluation](#basic-eval)
    - [Best practice for specific graph types](#amr-eval)
    - [More command line examples](#more-command-line-examples)
- [**Python package**](#python-package)
    - [Pip install](#pip-install)
    - [*14 examples* for graph processing](#python-usage)
- [FAQ](#faq)
- [Citation](#citation)

## Requirements<a id="requirements"></a>

For comprehensive usage, SMATCH++ requires `numpy>=1.20.1`, `scipy>=1.10.1`, `mip>=1.13.0`. 

These packages will be automatically installed when installing SMATCH++ via pip:

```
pip install smatchpp
```

## Command line examples<a id="command-line"></a>

Evaluation of any type of graph parsing may include ILP optimal alignment, bootstrap confidence and micro and macro averaging. Scroll down for command line examples.

### Best practice for semantic parsing evaluation<a id="basic-eval"></a>

This evaluation setup has optimal ILP alignmnent, calculates micro and macro corpus metrics and confidence intervals.

**Simply call**: 

```
./score.sh <graphs1> <graphs2>
``` 

or more explicitly call:

```
python -m smatchpp      -a <graphs1> \
                        -b <graphs2> \
                        -solver ilp_backed \
                        -graph_type generic \
                        -score_dimension main \
                        -score_type micromacro \
                        --bootstrap
```

Here, the `graph_type generic` flag means that we perform minimal graph standardization (e.g., lower-casing of node labels). 

The variables `<graphs1>` and `<graphs2>` are the paths to the files with graphs. Format is assumed to be in "penman":

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
x y :instance
w z :instance
x w :rel

# second graph
...
```

Here, `:instance` is equivalent to `/` in Penman and holds the label of a node (e.g., the label of the node `x` is `y`). Note that a difference between the formats is that Penman assumes a root node (`x` in the example). To ensure the exact same graphs in tsv *and* Penman, a triple of `root x :root` would have to be added to the tsv graph. In fact, to have full control over the graph and process graphs "as-is" (also without any standardizing), please use `-input_format tsv` and remove the `graph_type` argument.

### Evaluating specific graph types (e.g., AMR)<a id="amr-eval"></a>

Specific formalisms can be simply set with the `-graph_type` flag. E.g., for evaluating AMR graphs (Abstract Meaning Representation), please use `-graph_type amr` to perform some additional structural standardization according to AMR guidelines (i.a., dereification). 

### Other options<a id="more-command-line-examples"></a>

All options can be viewed with:

```
python -m smatchpp --help
``` 

Here are some interesting examples:

#### Using hill-climber (⚠️)

For using a hill-climber as solver, use `-solver hillclimber`. ⚠️**Warning**⚠️: Using a hill-climber is not advisable and will yield Smatch scores that are not verifiable and are likely false.

#### Fast ILP alignment with graph compression

For using a graph compression to make evaluation much faster, use `--lossless_graph_compression` (and `-solver ilp`, or `ilp_backed`).

#### Fine-grained aspect scoring

Measures similarity on different types of subgraphs (e.g., NER, cause, etc.). To apply, use `-score_dimension all-multialign` or `score_dimension all-onealign`. Multi align re-calculates alignments for each pair of sub-graph, one-align calculates one alignment for a pair of graphs which is then re-used for the sub-graph pairs. Currently only available when `-graph_type amr`.

## Python package<a id="python-package"></a>

### Pip installation<a id="pip-install"></a>

To install SMATCH++ as a python package, simply run 

`pip install smatchpp`

A main interface is a smatchpp.Smatchpp object. With this, most kinds of operations can be performed on graphs and pairs of graphs. For other and more custom operations, specific modules can be loaded. Some examples are in the following

## Python usage examples<a id="python-usage"></a>

### Basic processing and matching of graphs: 14 Examples

An overview of the examples:

- [I](#ex-basicdefault): Heuristic graph match
- [II](#ex-basicdefault-ilp): Optimal graph match
- [III](#ex-basicdefault-generic): Optimal and standardized graph match
- [IV](#ex-parser-eval): Optimal and standardized evaluation and corpus scoring
- [V](#ex-standardizer): Build custom graph standardizer
- [VI](#ex-feed-direct): Feed graph directly
- [VII](#ex-gc): Graph-compression for fast matching
- [VIII](#ex-align): Get alignment
- [IX](#ex-subgraphtest): Subgraph isomorphism test (is a in b?)
- [X](#ex-read): Read Penman string

A handful of examples for processing a specific graph formalism (here: AMR graphs):

- [XI](#ex-basicdefault-amr): Standardized AMR graph pair matching
- [XII](#ex-best-practice-amr-corpus): Standardized AMR corpus matching / evaluation
- [XIII](#ex-extract-subgraphs-amr): Extract aspectual subgraphs from an AMR graph.
- [XIV](#ex-reify-amr): read, write an reifiy an AMR graph (reify is a operation defined on AMRs)

#### Example I: SMATCH++ matching with basic default<a id="ex-basicdefault"></a>

This uses a hill-climber and does not standardize the graphs in any way.

```python
from smatchpp import Smatchpp
measure = Smatchpp()
match, optimization_status, alignment = measure.process_pair("(t / test)", "(t / test)")
print(match) # {'main': array([2., 2., 2., 2.])}, 2 left->right, 2 in right->left, 2 length of left, 2 length of right
```
Note: Here it's two triples matching since there is an implicit root, that will be parsed into an additional triple. To ignore the root, consider writing a custom standardizer ([Example V](#ex-standardizer)), or feeding the triples directly ([Example VI](#ex-feed-direct)).

For greater convience, we can also directly get an F1 / Precision / Recall score:

```python
from smatchpp import Smatchpp
measure = Smatchpp()
score = measure.score_pair("(t / test)", "(t / test)")
print(score) # prints a json dict with convenient scores: {'main': {'F1': 100.0, 'Precision': 100.0, 'Recall': 100.0}}
```

#### Example II: Optimal SMATCH++ with ILP<a id="ex-basicdefault-ilp"></a>

In this example, we use ILP for optimal alignment, which is highly recommended, since only ILP provides guaranteed true Smatch scores.

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

#### Example III: Best-practice for matching a pair of basic graphs<a id="ex-basicdefault-generic"></a>

We read a `Penman'-string, perform generic standardization of the graph (e.g., lower-casing node labels), and run ILP optimal alignment, counting the matching triples.

```python
from smatchpp import Smatchpp, solvers
from smatchpp.formalism.generic import tools as generictools
graph_standardizer = generictools.GenericStandardizer()
ilp = solvers.ILP()
measure = Smatchpp(alignmentsolver=ilp, graph_standardizer=graph_standardizer)
score = measure.score_pair("(m / man :accompanier (c / cat))", "(m / man :arg1-of (a / accompany-01 :arg0 (c / cat)))") 
print(score) # prints a json dict with convenient scores: {'main': {'F1': 60.0, 'Precision': 75.0, 'Recall': 50.0}}
```

Note that the Penman-format entails a specific "root" node (here: `m`), that will be parsed into an additional triple. For full control over the matching, consider directly feeding the triples, as shown in [Example XI](#ex-feed-direct).

#### Example IV: Best practice for evaluating a parser or corpus<a id="ex-parser-eval"></a> 

According to best practice, here we want to compute "micro Smatch" for a parser output and a reference with bootstrap 95% confidence intervals. 

```python
from smatchpp import Smatchpp, solvers, preprocess, eval_statistics
from smatchpp.formalism.generic import tools as generictools
graph_standardizer = generictools.GenericStandardizer()
printer = eval_statistics.ResultPrinter(score_type="micro", do_bootstrap=True, output_format="json")
ilp = solvers.ILP()
measure = Smatchpp(alignmentsolver=ilp, graph_standardizer=graph_standardizer, printer=printer)
corpus1 = ["(t / test)", "(d / duck)"] * 100 # we extend the lists because bootstrap doesn't work with tiny corpora
corpus2 = ["(t / test)", "(a / ant)"] * 100 # we extend the lists because bootstrap doesn't work with tiny corpora
score, optimization_status = measure.score_corpus(corpus1, corpus2)
print(score) # {'main': {'F1': {'result': 75.0, 'ci': (71.5, 78.5)}, 'Precision': {'result': 75.0, 'ci': (71.5, 78.5)}, 'Recall': {'result': 75.0, 'ci': (71.5, 78.5)}}}
```

If you want to get access to the *full bootstrap distribution* you can add `also_return_bootstrap_distribution=True` when creating the `printer`. Beware that in this case the `score` result will be very large. Note also that for this we require scipy version of at least 1.10.0.

Note that for best evaluating a specific formalism, like AMR, more specialised pre-processing can be applied. Please visit [this example](#best-practice-amr-corpus).

#### Example V: Plug in custom standardizer in the matching<a id="ex-standardizer"></a>

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

#### Example VI: Feeding graph directly without string reading<a id="ex-feed-direct"></a>

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

#### Example VII: Lossless pairwise graph compression<a id="ex-gc"></a>

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

If we want to use the compression in the matching, simply set the argument `graph_pair_preparer=pair_preparer_compressor`, while initializing a `Smatchpp` object (an example can be seen in [IX](#ex-subgraphtest)).

#### Example VIII: get an alignment<a id="ex-align"></a>

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

#### Example IX: Sub-graph isomorphism test<a id="ex-subgraphtest"></a>

We want to know: is g1 a *subgraph* of g2? We note: this is a i) binary value ii) using lossless `graph_compression` does not change the result, we iii) should ignore the `:root` relation that is implicit in Penman. So:

```python
from smatchpp import Smatchpp, preprocess, data_helpers
from smatchpp.formalism.generic import tools as generictools

reader = data_helpers.PenmanReader(explicate_root=False) # ignore root
standardizer = generictools.GenericStandardizer() # generic standardizer
pair_preparer_compressor = preprocess.BasicGraphPairPreparer(lossless_graph_compression=True)

# now we can construct our measure and classifier, and run a few examples
measure = Smatchpp(graph_reader=reader, graph_standardizer=standardizer, graph_pair_preparer=pair_preparer_compressor)
classifier = lambda x, y: measure.score_pair(x,y)["main"]["Precision"] == 100 # criterion for subgraph isomorphism
print(classifier("(t / test :rel (d / dog))", "(t / test :rel (d / dog))")) # True
print(classifier("(d / dog)", "(t / test :rel (d / dog)")) # True
print(classifier("(t / dog :rel (d / test))", "(d / test :rel (t / dog))")) # False
print(classifier("(t / dog :rel-of (d / test))", "(d / test :rel (t / dog))")) # True
```

#### Example X: Read a Penman graph<a id="ex-read"></a>

In this simple example, we read a Penman string into a graph.

```python
from smatchpp import data_helpers
graph_reader = data_helpers.PenmanReader()
s = "(t / train :mod (f / fast))"
g = graph_reader.string2graph(s)
print(g) # [('t', ':instance', 'train'), ('ROOT_OF_GRAPH', ':root', 't'), ('f', ':instance', 'fast'), ('t', ':mod', 'f')]
```

### Formalism-tailored processing (here: AMR graphs, Abstract Meaning Representation)

#### Example XI: Best-Practice for matching a pair of AMR graphs<a id="ex-basicdefault-amr"></a>

AMR is simply a special type of graph, where best-practice is implemented in `formalism/amr/tools.py`. Beyond basic defaults, we perform AMR-focused graph standardization. 

```python
from smatchpp import Smatchpp, solvers
from smatchpp.formalism.amr import tools as amrtools
graph_standardizer = amrtools.AMRStandardizer()
ilp = solvers.ILP()
measure = Smatchpp(alignmentsolver=ilp, graph_standardizer=graph_standardizer)
score = measure.score_pair("(m / man :accompanier (c / cat))", "(m / man :arg1-of (a / accompany-01 :arg0 (c / cat)))") # equivalent AMR graphs 
print(score) # prints a json dict with convenient scores: {'main': {'F1': 100.0, 'Precision': 100.0, 'Recall': 100.0}}
```

Note that the measure returns a score of 100 even though the input graphs are structurally different. This is due to advanced standardization tailored to AMR, called de/reification rules that translate between different graph structures, ensuring equivalency. Please find more information in the [SMATCH++ paper](https://arxiv.org/abs/2305.06993) or the [AMR guidelines](https://github.com/amrisi/amr-guidelines/blob/master/amr.md). Note that although de/reified structures apparently can be quite different, in practice a parser evaluation score is not much different (with/without dereification), since gold AMRs are dereified by default (sometimes, parsers forget to dereify). The score without dereification, can be seen in [Example III](#ex-basicdefault-generic).

#### Example XII: Best practice for AMR parser evaluation<a id="ex-best-practice-amr-corpus"></a>

According to best practice, here we want to compute "micro Smatch" for a parser output and a reference with bootstrap 95% confidence intervals. 

```python
from smatchpp import Smatchpp, solvers, preprocess, eval_statistics
from smatchpp.formalism.amr import tools as amrtools
graph_standardizer = amrtools.AMRStandardizer()
printer = eval_statistics.ResultPrinter(score_type="micro", do_bootstrap=True, output_format="json")
ilp = solvers.ILP()
measure = Smatchpp(alignmentsolver=ilp, graph_standardizer=graph_standardizer, printer=printer)
corpus1 = ["(t / test)", "(d / duck)"] * 100 # we extend the lists because bootstrap doesn't work with tiny corpora
corpus2 = ["(t / test)", "(a / ant)"] * 100 # we extend the lists because bootstrap doesn't work with tiny corpora
score, optimization_status = measure.score_corpus(corpus1, corpus2)
print(score) # {'main': {'F1': {'result': 50.0, 'ci': (43.0, 57.0)}, 'Precision': {'result': 50.0, 'ci': (43.0, 57.0)}, 'Recall': {'result': 50.0, 'ci': (43.0, 57.0)}}}
```

#### Example XIII: Standardize and extract subgraphs<a id="ex-extract-subgraphs-amr"></a>

For specific formalisms, we can extract subgraphs, if we have defined some tools. Currently, this is allowed for AMR, where we can extract aspectual subgraphs as follows:

```python
from smatchpp import preprocess, subgraph_extraction, data_helpers
from smatchpp.formalism.amr import tools as amrtools
standardizer = amrtools.AMRStandardizer()
reader = data_helpers.PenmanReader()
subgraph_extractor = amrtools.AMRSubgraphExtractor()
string_graph = "(c / control-01 :arg1 (c2 / computer) :arg2 (m / mouse))"
g = reader.string2graph(string_graph)
g = standardizer.standardize(g)
name_subgraph_dict = subgraph_extractor.all_subgraphs_by_name(g)

# get subgraph for "instrument"
print(name_subgraph_dict["INSTRUMENT"]) # [(c, instance, control-01), (m, instance, mouse), (c, instrument, m)]
```

#### Example XIV: Read, reify and write graph<a id="ex-reify-amr"></a>

In this example, we read a basic graph from a string, apply reification, and write the reified graph to a string. Reification are equivalency-preserving graph transformations based on rules. Currently rules are only implemnted for AMR graphs, so we will import from `formalism/amr`

```python
from smatchpp import data_helpers, graph_transforms
from smatchpp.formalism.amr import tools as amrtools
graph_reader = data_helpers.PenmanReader()
graph_writer = data_helpers.PenmanWriter()
reify_rules = amrtools.read_amr_reify_table()
reifier = graph_transforms.SyntacticReificationGraphTransformer(reify_rules, mode="reify")
s = "(t / test :mod (s / small :mod (v / very)) :quant 2 :op v)"
g = graph_reader.string2graph(s)
g = reifier.transform(g)
string = graph_writer.graph2string(g)
print(string) # (t / test :op (v / very :arg2-of (ric5 / have-mod-91 :arg1 (s / small :arg2-of (ric3 / have-mod-91 :arg1 t)))) :arg1-of (ric6 / have-quant-91 :arg2 2))
```

## FAQ<a id="faq"></a>

- *I want to process my custom graph type*: Consider implementing your custom graph standardizer that can then simply be used as shown in [Example V](#ex-standardizer). You can also extend SMATCH++ with a custom graph type that can then be called from command line. For ortientation, please consult the already implemented processing of `generic` and `amr` graph types.

- *I have very large graphs and optimal ILP doesn't terminate*: This is because optimal alignment is an NP hard problem. Mitigation options: 1. use heuristics: Either HillClimber heuristic (unfortunately the climber will get worse for large graphs because of many local optima where it gets stuck) or linear program (LP), which at least has a valid upper-bound. 2. Use `--lossless_graph_compression` (for python see [Example VII](#ex-gc)). This makes evaluation fast and gives an optimal score satisfying graph isomorphism (the score tends to be slightly harsher/lower). 3. Play with the `max_seconds` argument in the ILP solver (see `ILP` in `smatchpp/solvers.py`) and reduce it to get an intermediate solution (it can still be better than hill-climbing and it has an upper-bound). Perhaps, 2. may be the best option due to optimality.

- *I want to use other triple matching functions*: Sometimes, e.g., in evaluation of cross-lingual graphs, we want to have that a triple `(x, instance, cat)` be similar to `(x, instance, kitten)` and allow more graded matching. SMATCH++ allows easy customization of this, and you can extend to implement your own class.

- What's the difference between `-solver ilp` and `-solver ilp_backed`. Both are essentially the same solver (optimal, integer linear program). The difference is that the backed version applies some additional heuristics for the case where the maximum seconds timeount for solution is reached (it includes a backup for the ILP solver using heuristic solvers).

## Citation<a id="citation"></a>

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
