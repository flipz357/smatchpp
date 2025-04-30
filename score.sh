#!/usr/bin/env bash

python -m smatchpp      -a $1 \
			-b $2 \
			-solver ilp_backed \
			-graph_type generic \
			-score_dimension main \
			-score_type micromacro \
			--bootstrap 
