from collections import Counter
import numpy as np
import logging
from smatchpp.util import xor, get_var_concept_dict

logger = logging.getLogger("__main__")


class GraphAligner:

    def __init__(self, triplematcher, solver):  
        self.triplematcher = triplematcher
        self.solver = solver
     
    def _make_binary_match_dict(self, triples1, triples2, var1, var2, var_index):
         
        data = Counter() 
        triples1 = [tr for tr in triples1 if (tr[0] in var1 and tr[2] in var1)]
        triples2 = [tr for tr in triples2 if (tr[0] in var2 and tr[2] in var2)]

        for triple in triples1:
            s, r, t  = triple
            i = var_index[s]
            j = var_index[t]
            for triple_other in triples2:
                s_other, r_other, t_other  = triple_other
                i_other = var_index[s_other]
                j_other = var_index[t_other]
                match = self.triplematcher.triplematch(("xtmp", r, "ytmp"), ("xtmp", r_other, "ytmp"))
                if match > 0.0:
                    data[(i, i_other, j, j_other)] += match / 2
                    data[(j, j_other, i, i_other)] += match / 2
        
        return data
                
    def _make_unary_match_dict(self, triples1, triples2, var1, var2, var_index):
        
        data = Counter()
        triples1 = [tr for tr in triples1 if xor(tr[0] in var1, tr[2] in var1)]
        triples2 = [tr for tr in triples2 if xor(tr[0] in var2, tr[2] in var2)]
        
        for triple in triples1:
            s, r, t  = triple
            i = var_index.get(s)
            j = var_index.get(t)
            for triple_other in triples2:
                s_other, r_other, t_other  = triple_other
                i_other = None
                j_other = None
                i_other = var_index.get(s_other)
                if i_other is not None and i is not None:
                    match = self.triplematcher.triplematch(("xtmp", r, t), ("xtmp", r_other, t_other))
                    if match > 0.0:
                        data[(i, i_other)] += match
                    continue
                
                j_other = var_index.get(t_other)
                if j_other is not None and j is not None:
                    match = self.triplematcher.triplematch((s, r, "ytmp"), (s_other, r_other, "ytmp"))
                    if match > 0.0:
                        data[(j, j_other)] += match
                    continue
        
        return data
    
    def _compute_match_dicts(self, triples1, triples2, var1, var2, var_index):
        unary = self._make_unary_match_dict(triples1, triples2, var1, var2, var_index)
        binary = self._make_binary_match_dict(triples1, triples2, var1, var2, var_index)
        return unary, binary

    def _get_var_map(self, alignment, var_index):
        index_var_1 = {i:v for v, i in var_index.items() if "first" in v} 
        index_var_2 = {i:v for v, i in var_index.items() if "second" in v} 
        mapping = []
        
        for i, j in enumerate(alignment):
            var1 = index_var_1.get(i)
            var2 = index_var_2.get(j)
            mapping.append((var1, var2))
        
        return mapping
    
    def _interpretable_mapping(self, varmapping, triples1, triples2):
        
        var_concept_map1 = get_var_concept_dict(triples1)
        var_concept_map2 = get_var_concept_dict(triples2)
        
        out = []
        for (x1, x2) in varmapping:
            
            x1bar = str(x1) + "_" + str(var_concept_map1.get(x1))
            x2bar = str(x2) + "_" + str(var_concept_map2.get(x2))
            out.append((x1bar, x2bar))
            
        return out

    def align(self, triples1, triples2, var1, var2):

        logging.debug("starting alignment")
        if not var1 or not var2:
            return np.array([]), {}, (0, 0)

        var_index = {}
        for i, v in enumerate(list(sorted(var1))):
            var_index[v] = i
        for i, v in enumerate(list(sorted(var2))):
            var_index[v] = i
        if not var_index:
            return None, []
        logging.debug("1. var index created: {}".format(var_index))
        unarymatch_dict, binarymatch_dict = self._compute_match_dicts(triples1, triples2, var1, var2, var_index)

        logging.debug("2a. unary match_dict created {}; sum {}".format(unarymatch_dict, np.sum(unarymatch_dict)))
        logging.debug("2b. binary match_dict created {}; sum {}".format(binarymatch_dict, np.sum(binarymatch_dict)))
        V = max(len(var1), len(var2))
        
        alignmat, objective_value, objective_bound = self.solver.solve(unarymatch_dict, binarymatch_dict, V)
        logging.debug("4. found alignment \n{}\n\
                objective value: {}\n\
                upper bound (if available):{}\n".format(alignmat, objective_value, objective_bound))
        
        var_map = self._get_var_map(alignmat, var_index)
        logging.debug("5. output mapping {}".format(var_map))
        logging.debug("5. output mapping interpreted {}".format(self._interpretable_mapping(var_map, triples1, triples2)))
        return alignmat, var_index, (objective_value, objective_bound)

