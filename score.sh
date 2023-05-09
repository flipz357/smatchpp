#!/usr/bin/env bash

python smatchpp/main.py -a $1 \
			-b $2 \
			-solver ilp \
			-edges dereify \
			-score_dimension main \
			-score_type micromacro \
			-log_level 20 \
			--bootstrap \
			--remove_duplicates
