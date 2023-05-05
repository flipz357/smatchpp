from copy import deepcopy
from collections import defaultdict
import numpy as np
import logging
import util
import re
import interfaces
from subgraph_extraction import SubGraphExtractor

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

        self.vecs = self.gensim.downloader.api.load("glove-wiki-gigaword-100")


    def _triplematch(self, t1, t2): 
        string1 = str(t1)
        string2 = str(t2)
        sc = int(string1 == string2)
        if sc:
            return sc
        if ":instance" == t1[1] == t2[1]:
            concept1 = t1[2]
            concept2 = t2[2]
            vc1 = self.vectors.get(vc1)
            vc2 = self.vectors.get(vc2)
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

    def _map_triples(self, triples, alignmat, varindex, identifier="XsecondX"):
        
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
        #print(var_newvar)
        #print("\n\n\n")
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
        #print(sorted(triples1_aligned, key=lambda x:x[0]))
        #print(sorted(triples2, key=lambda x:x[0]))
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
        #print(matchsum_x, matchsum_y, xlen, ylen)        
        match = np.array([matchsum_x, matchsum_y, xlen, ylen])
        sxtmp = len(set(triples1_aligned).intersection(triples2))
        match = [sxtmp, sxtmp, match[2], match[3]]
        #print(varindex)
        #for xtr in sxtmp:
        #    if triples1_aligned.count(xtr) != 1:
        #        print(xtr, triples1_aligned.count(xtr))
        return match
    
    def main_scores(self, triples1, triples2, alignmat, varindex):
        
        match = self._score(triples1, triples2, alignmat, varindex)
        return {"main": match}

    def subtask_scores(self, triples1, triples2, alignmat, varindex):
        
        """
        def get_sub_structure(triples, rel):
            
            # if not reified this is what we want
            out = [t for t in triples if rel == t[1]] 
            vars_of_reified_concept = []

            # check for reified rel nodes, collect related variables
            if rel in self.reify_rules[0]:
                for (s, r, t) in triples:
                    if r == ":instance" and t == self.reify_rules[0][rel][0]: 
                        vars_of_reified_concept.append(s)
                for (s, r, t) in triples:
                    if t in vars_of_reified_concept or s in vars_of_reified_concept and r != ":instance":
                        out.append((s, r, t))
            return out
        
        def get_sub_structure_reent(triples):
            out = []
            inc_rels = defaultdict(int)
            var_concept_dict = util.get_var_concept_dict(triples)
            for (s, r, t) in triples:
                if t in var_concept_dict:
                    inc_rels[t] += 1
            
            for (s, r, t) in triples:
                if s in var_concept_dict and inc_rels[s] > 1:
                    out.append((s, r, t))
                elif t in var_concept_dict and inc_rels[t] > 1:
                    out.append((s, r, t))
            return out
        
        def get_additional_instances(triples, triples_all):
            additional_instance = []
            var_concept_dict = util.get_var_concept_dict(triples_all)
            tvars = set()
            for (s, _, t) in triples:
                if s in var_concept_dict:
                    tvars.add(s)
                if t in var_concept_dict:
                    tvars.add(t)
            for var in tvars:
                additional_instance.append((var, ":instance", var_concept_dict[var]))
            
            return additional_instance

        score_dict = {}
        
        x_triples1 = [t for t in triples1 if ":instance" == t[1].lower()]
        x_triples2 = [t for t in triples2 if ":instance" == t[1].lower()]
        score_dict["instance (Concept)"] = self._score(x_triples1, x_triples2, alignmat, varindex)

        x_triples1 = [t for t in triples1 if re.match(r".*-[0-9]+",t[2].lower())]
        x_triples2 = [t for t in triples2 if re.match(r".*-[0-9]+",t[2].lower())]
        score_dict["wsd"] = self._score(x_triples1, x_triples2, alignmat, varindex)

        for rel in list(self.reify_rules[0].keys()) + [":cause"] + [":arg"]:
            x_triples1 = get_sub_structure(triples1, rel)
            x_triples1 += get_additional_instances(x_triples1, triples1)
            x_triples2 = get_sub_structure(triples2, rel)
            x_triples2 += get_additional_instances(x_triples2, triples2)
            score_dict[rel.replace(":", "")] = self._score(x_triples1, x_triples2, alignmat, varindex)
        
        x_triples1 = get_sub_structure_reent(triples1)
        x_triples1 += get_additional_instances(x_triples1, triples1)
        x_triples2 = get_sub_structure_reent(triples2)
        x_triples2 += get_additional_instances(x_triples2, triples2)
        score_dict["reent"] = self._score(x_triples1, x_triples2, alignmat, varindex)
        score_dict["main"] = self._score(triples1, triples2, alignmat, varindex)
        """
        
        sub_graphs_1 = self.sg_extractor.all_subgraphs_by_name(triples1)
        sub_graphs_2 = self.sg_extractor.all_subgraphs_by_name(triples2)

        score_dict = {}
        for name in sub_graphs_1:
            score = self._score(sub_graphs_1[name], sub_graphs_2[name], alignmat, varindex)
            score_dict[name] = score

        return score_dict






