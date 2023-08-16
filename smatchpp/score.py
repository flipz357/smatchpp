from copy import deepcopy
import numpy as np
import logging
from smatchpp import util
from smatchpp import interfaces
from smatchpp.subgraph_extraction import SubGraphExtractor

logger = logging.getLogger("__main__")
                 

class IDTripleMatcher(interfaces.TripleMatcher):
    
    @staticmethod
    def _triplematch(t1, t2): 
        string1 = str(t1)
        string2 = str(t2)
        return int(string1 == string2)

class ConceptFocusMatcher(interfaces.TripleMatcher): 
    
    @staticmethod
    def _triplematch(t1, t2): 
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
        self.sg_extractor = SubGraphExtractor()
        return None
    
    @staticmethod
    def _safe_get_align(alignmat, src):
        target = alignmat[src]
        return target

    def _map_triples(self, triples, alignmat, varindex, identifier="bb_"):
        """This function overwrites variables in one graph with variables 
            from another graph given an alignment. The goal is then that the graphs
            can be matched in a transparent and controlled way. 

        Args:
            triples (list with tuples): a graph
            alignmat (an arry): an alignment mapping, e.g. [4, 0, 1] which would mean node
                                0 of first graph aligns with node 4 of second graph
                                node 1 of first graph aligns with node 0 of second graph, and so on
            varindex (dict): a mapping from indeces to variable names
            identifier (string): to identify the variables in varindex that we can map to

        Returns:
            None; it is in-place mapping of the graph
        """
         
        var_newvar = {}
        
        # build mapping from alignment index to variable names that we can map to
        index_var = {v: k for k, v in varindex.items() if identifier in k}
        
        # iterate over triples
        for k, tr in enumerate(triples):
            
            s, r, t = tr
            news = s
            newt = t
            
            # look if the source is variable and maybe get its alignment index
            i = varindex.get(s)
            if i != None:
                
                # maybe get its partner from the alignmnet
                j = alignmat[i]
                maybe_s = index_var.get(j)
                # if there is a partner, set the old variable name to the variable name of the partner
                if maybe_s:
                    news = maybe_s
            
            # same as above, but for the target of the triple
            i = varindex.get(t)
            if i != None:
                j = alignmat[i]
                maybe_t = index_var.get(j)
                if maybe_t:
                    newt = maybe_t
            
            # set mapping of nodes
            var_newvar[s] = news
            var_newvar[t] = newt
        
        # map nodes
        for k, tr in enumerate(triples):
            s, r, t = tr
            s = var_newvar[s]
            t = var_newvar[t]
            triples[k] = (s, r, t)

        return None

    def _score_given_alignment(self, triples1, triples2, alignmat, varindex):
        
        triples1_aligned = list(triples1)
        self._map_triples(triples1_aligned, alignmat, varindex)

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
    
    def _score(self, triples1, triples2, alignmat, varindex):
        
        match = self._score_given_alignment(triples1, triples2, alignmat, varindex)
        return {"main": match}
    





