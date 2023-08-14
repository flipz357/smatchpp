#!/usr/bin/env bash

python -m smatchpp      -a $1 \
			-b $2 \
			-solver ilp \
			-syntactic_standardization dereify \
			-score_dimension main \
			-score_type micromacro \
			-log_level 20 \
			--bootstrap \
			--remove_duplicates
