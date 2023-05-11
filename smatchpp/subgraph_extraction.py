import re
from collections import defaultdict
import util

class SubGraphExtractor():

    def __init__(self, reify_rules=None, add_instance=True, subtree_context_depth=2, wiki_option=1):
        
        if not reify_rules:
            reify_rules = util.read_reify_table()
        
        self.reify_rules = reify_rules
        self.add_instance = add_instance
        self.subtree_context_depth = subtree_context_depth
        self.wiki_option = wiki_option
        
    def all_subgraphs_by_name(self, triples):
        
        name_subgraph = {}
        
        # full graph
        name_subgraph["main"] = triples 
        if self.wiki_option == 0:
            name_subgraph["main"] = [t for t in triples if t[1] != ":wiki"]
        name_subgraph["wiki"] = self._maybe_add_instance([t for t in triples if t[1] == ":wiki"], triples)

        if self.wiki_option == 1:
            triples = [t for t in triples if t[1] != ":wiki"]
        
        for rel in list(self.reify_rules[0].keys()) + [":arg0", ":arg1", ":arg2", ":arg3", ":arg4"]:
            x_triples = self.subgraph_rel(triples, rel)
            name_subgraph[rel.replace(":", "")] = x_triples
        name_subgraph["coreference"] = self.subgraph_reentrancies(triples)
        name_subgraph["predicate sense disambiguation (wsd)"] = self.subgraph_predicate(triples)
        name_subgraph["semantic role labeling (srl)"] = self.subgraph_srl(triples)
        name_subgraph["concepts"] = self.subgraph_instance(triples)
         
        # maybe also interesting
        #name_subgraph["edges_unlabeled"] = self.unlabel_edges(triples)
        #name_subgraph["nodes_unlabeled"] = self.unlabel_nodes(triples)
        
        name_subgraph["quantification"] = name_subgraph["quant"]
        name_subgraph["modification"] = name_subgraph["mod"]
        name_subgraph["possession"] = name_subgraph["poss"]
        
        # keep a selection
        selection = ["main", "manner", "coreference", "predicate sense disambiguation (wsd)", "semantic role labeling (srl)", 
                        "concepts", "time", "location", "cause", "modification", "wiki",
                        "quantification", "possession", "polarity"]
        
        name_subgraph = {k:name_subgraph[k] for k in selection}
        
        return name_subgraph

    def subgraph_srl(self, triples):
        out = []
        for triple in triples:
            if re.match(r":arg[0-9]+", triple[1]):
                out.append(triple)
        out = self._maybe_add_subtree(out, triples)
        out = self._maybe_add_instance(out, triples)
        return out
    
    def subgraph_rel(self, triples, rel=None):
        
        if not rel:
            raise ValuerError("relation needs to be defined for subgrah extraction")

	# if not reified this is what we want
        out = [t for t in triples if rel == t[1]]
        vars_of_reified_concept = []

	# check for reified rel nodes, collect related variabl      
        if rel in self.reify_rules[0]:
            for (s, r, t) in triples:
                if r == ":instance" and t == self.reify_rules[0][rel][0]:
                    vars_of_reified_concept.append(s)
            for (s, r, t) in triples:
                if (t in vars_of_reified_concept or s in vars_of_reified_concept) and r != ":instance":
                    out.append((s, r, t))
        out = self._maybe_add_subtree(out, triples)
        out = self._maybe_add_instance(out, triples)
        return out
    
    def subgraph_instance(self, triples):
        triples = [t for t in triples1 if t[1] == ":instance"]
        return triples

    def subgraph_predicate(self, triples):
        triples = self.subgraph_instance(triples)
        triples = [t for t in triples if re.match(r".*-[0-9]+", t[2].lower())]
        return triples

    def subgraph_instance(self, triples):
        triples = [t for t in triples if t[1] == ":instance"]
        return triples
    
    def unlabel_edges(self, triples):
        out = []
        for t in triples:
            if t[1] != ":instance":
                out.append((t[0], ":rel", t[2]))
            else:
                out.append(t)
        return out
    
    def unlabel_nodes(self, triples):
        out = []
        for t in triples:
            if t[1] == ":instance":
                out.append((t[0], ":instance", "concept"))
            else:
                out.append(t)
        return out

    def subgraph_reentrancies(self, triples):
        out = []
        inc_rels = defaultdict(int)
        var_concept_dict = util.get_var_concept_dict(triples)
        for (s, r, t) in triples:
            if t in var_concept_dict:
                inc_rels[t] += 1
        for (s, r, t) in [ t for t in triples if t[1] != ":instance"]:
            if t in var_concept_dict and inc_rels[t] > 1:
                out.append((s, r, t))
        out = self._maybe_add_subtree(out, triples)
        out = self._maybe_add_instance(out, triples)
        return out
     
    def _maybe_add_instance(self, triples, triples_all):
        out = []
        if self.add_instance:
            ai = self._get_additional_instances(triples, triples_all)
            out = triples + ai
        return out
    
    def _maybe_add_subtree(self, triples, triples_all):
        out = list(triples)
        
        if self.subtree_context_depth != 0:
            
            finished = False
            depth = 0
            while not finished:
                finished = True
                if depth == self.subtree_context_depth:
                    break
                tmp = []
                for tri in out:
                    tgt = tri[2]
                    for tri_other in triples_all:
                        if tri_other[1] == ":instance":
                            continue
                        if tri_other in out:
                            continue
                        if tgt == tri_other[0]:
                            tmp.append(tri_other)
                            finished = False
                out += tmp
                depth += 1
        out = list(set(out))
        return out
            
    def _get_additional_instances(self, triples, triples_all):
        additional_instance = []
        var_concept_dict = util.get_var_concept_dict(triples_all)
        tvars = set()
        for (s, _, t) in triples:
            if s in var_concept_dict:
                tvars.add(s)
            if t in var_concept_dict:
                tvars.add(t)
        for var in tvars:
            itriple = (var, ":instance", var_concept_dict[var])
            if itriple not in additional_instance:
                additional_instance.append(itriple)

        return additional_instance


