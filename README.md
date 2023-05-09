# SMATCH++

Contains standardized and optimal Smatch solving.

## Requirements

Code written for python (3). For the most basic version, there shouldn't be a need to install additional modules. However, when using ilp optimal solving and bootstrapping, we require

```
mip (tested: 1.13.0)
scipy (tested: 1.7.3)
numpy (tested: 1.20.1)
```

The packages can all be installed with `pip ...`

## Example configurations

### Recommended for average case: ILP alignment, dereification, corpus metrics and confidence intervals

- Efficiency: + 
- Optimality: +++
- Graph standardization: ++ 

**Simply call**: 

```
./score.sh <amrs1> <amrs2>
``` 

where `<amrs1>` and `<amrs>` are the paths to the files with graphs. Format is assumed to be in "penman":

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
python smatchpp/main.py -a <amrs1> \
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
python smatchpp/main.py -a <amrs1> \
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
python smatchpp/main.py -a <amrs1> \
			-b <amrs2> \
			-solver ilp \
			-edges reify \
			-score_dimension main \
			-score_type micromacro \
			-log_level 20 \
			--bootstrap \
			--remove_duplicates \
			--lossless_graph_compression
```

### ILP alignment, corpus sub-aspect metrics and confidence intervals

- Efficiency: + 
- Optimality: +++
- Graph standardization: ++ 

```
python smatchpp/main.py -a <amrs1> \
			-b <amrs2> \
			-solver ilp \
			-edges dereify \
			-score_dimension all-multialign \
			-score_type micromacro \
			-log_level 20 \
			--bootstrap \
			--remove_duplicates \
			--lossless_graph_compression
```

### Other configurations

See

```
python smatchpp/main.py --help
```

## Additional functionality

### Custom triple matching

Can be implemented in `score.py`

### Changing subgraph metrics

See `subgraph_extraction.py` 

## Pip install

coming.

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
