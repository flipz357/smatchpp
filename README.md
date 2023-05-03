# SMATCH++

Contains standardized and optimal Smatch solving. *Code coming on 5/4*. 

## Example configurations

### ILP alignment, corpus metrics and confidence intervals

Efficiency: + 
Optimality: +++
Graph standardization: + 

./score.sh examples/ex1.txt examples/ex2.txt

### Hill-climber alignment, corpus metrics and confidence intervals

Efficiency: ++ 
Optimality: +
Graph standardization: + 

./score\_hillclimb.sh examples/ex1.txt examples/ex2.txt

### Fast ILP with graph compression, corpus metrics and confidence intervals

Efficiency: ++ 
Optimality: +++
Graph standardization: + 

./score\_compressed.sh

### ILP with reification, corpus metrics and confidence intervals

Efficiency: -
Optimality: +++
Graph standardization: +++

./score\_fully\_standardized.sh

### ILP alignment, corpus sub-aspect metrics and confidence intervals

Efficiency: + 
Optimality: +++
Graph standardization: + 

./sub\_score.sh examples/ex1.txt examples/ex2.txt

## Pip install

coming.
