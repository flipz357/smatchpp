from copy import deepcopy
import numpy as np
import logging
from smatchpp import util
from smatchpp import interfaces
from smatchpp.subgraph_extraction import SubGraphExtractor

logger = logging.getLogger("__main__")
                 

class IDTripleMatcher(interfaces.TripleMatcher):

    def _triplematch(self, t1, t2): 
        string1 = str(t1)
        string2 = str(t2)
        return int(string1 == string2)

class ConceptFocusMatcher(interfaces.TripleMatcher): 
    
    def _triplematch(self, t1, t2): 
        string1 = str(t1)
        string2 = str(t2)
        sc = int(string1 == string2)
        if ":instance" == t1[1] == t2[1]:
            sc *= 3.0
        return sc

class EmbeddingConceptMatcher(interfaces.TripleMatcher): 
    
    def __init__(self):

        try:
            import scipy
            self.scipy = scipy
        except ModuleNotFoundError:
            raise ModuleNotFoundError("for calling cosine distance please install scipy")
        
        try:
            import gensim
            self.gensim = gensim
        except ModuleNotFoundError:
            raise ModuleNotFoundError("gensim not found")

        self.vectors = self.gensim.downloader.api.load("glove-wiki-gigaword-100")


    def _triplematch(self, t1, t2): 
        string1 = str(t1)
        string2 = str(t2)
        sc = int(string1 == string2)
        if sc:
            return sc
        if ":instance" == t1[1] == t2[1]:
            concept1 = t1[2]
            concept2 = t2[2]
            vc1 = self.vectors.get(concept1)
            vc2 = self.vectors.get(concept2)
            return 1 - self.scipy.spatial.distance.cosine(vc1, vc2)
        return sc


class AMRScorer(interfaces.Scorer):

    def __init__(self, triplematcher=None):
        if not triplematcher:
            triplematcher = IDTripleMatcher()
        self.triplematcher = triplematcher
        self.reify_rules = util.read_reify_table()
        self.sg_extractor = SubGraphExtractor()
        return None
    
    def _safe_get_align(self, alignmat, src):
        target = alignmat[src]
        return target

    def _map_triples(self, triples, alignmat, varindex, identifier="bb_"):
        
        triples_aligned = deepcopy(triples)
        var_newvar = {}
        
        for k, tr in enumerate(triples_aligned):
            
            s, r, t = tr
            news  = s
            newt = t
            
            if s in varindex:
                i = varindex[s]
                j = self._safe_get_align(alignmat, i)
                found = None
                for v in varindex:
                    if identifier in v and varindex[v] == j:
                        found = v
                if found:
                    news = found
            
            if t in varindex:
                i = varindex[t]
                j = self._safe_get_align(alignmat, i)
                found = None
                for v in varindex:
                    if identifier in v and varindex[v] == j:
                        found = v
                if found:
                    newt = found
            
            var_newvar[s] = news
            var_newvar[t] = newt
        
        for k, tr in enumerate(triples_aligned):
            s, r, t = tr
            s = var_newvar[s]
            t = var_newvar[t]
            triples_aligned[k] = (s, r, t)

        return triples_aligned

    def _score(self, triples1, triples2, alignmat, varindex):
        
        triples1_aligned = deepcopy(triples1)
         
        triples1_aligned = self._map_triples(triples1, alignmat, varindex)
        xlen = len(triples1_aligned)
        ylen = len(triples2)
        
        matchsum_x = 0.0
        for triple in triples1_aligned:
            scores = [0.0] 
            scores += [self.triplematcher.triplematch(triple, triples2[i]) for i in range(len(triples2))]
            matchsum_x += max(scores)
        
        matchsum_y = 0.0
        for triple in triples2:
            scores = [0.0] 
            scores += [self.triplematcher.triplematch(triple, triples1_aligned[i]) for i in range(len(triples1_aligned))]
            matchsum_y += max(scores)
        
        match = np.array([matchsum_x, matchsum_y, xlen, ylen])
        #note: in basic Smatch w/o duplicates we have IDTripleMatch matchsum_x = matchsum_y = len(set(triples1_aligned).intersection(triples2))
        return match
    
    def main_scores(self, triples1, triples2, alignmat, varindex):
        
        match = self._score(triples1, triples2, alignmat, varindex)
        return {"main": match}

    def subtask_scores(self, triples1, triples2, alignmat, varindex):
         
        sub_graphs_1 = self.sg_extractor.all_subgraphs_by_name(triples1)
        sub_graphs_2 = self.sg_extractor.all_subgraphs_by_name(triples2)

        score_dict = {}
        for name in sub_graphs_1:
            score = self._score(sub_graphs_1[name], sub_graphs_2[name], alignmat, varindex)
            score_dict[name] = score

        return score_dict






