import re
from collections import defaultdict
from smatchpp import util

def subgraph_instance(triples):
    triples = [t for t in triples if t[1] == ":instance"]
    return triples

def subgraph_predicate(triples):
    triples = subgraph_instance(triples)
    triples = [t for t in triples if re.match(r".*-[0-9]+", t[2].lower())]
    return triples

def unlabel_edges(triples):
    out = []
    for t in triples:
        if t[1] != ":instance":
            out.append((t[0], ":rel", t[2]))
        else:
            out.append(t)
    return out
    
def unlabel_nodes(triples):
    out = []
    for t in triples:
        if t[1] == ":instance":
            out.append((t[0], ":instance", "concept"))
        else:
            out.append(t)
    return out


def get_preds(triples, node):
    triples = [t for t in triples if t[1] != ":instance"]
    preds = []
    for tr in triples:
        if node != tr[2]:
            continue
        inode = tr[0]
        inc = util._n_incoming(triples, inode)
        outg = util._n_outgoing(triples, inode)
        if inc == 0 and outg == 1:
            preds.append(tr)
    return preds
    

def subgraph_reentrancies(triples):
    out = []
    inc_rels = defaultdict(int)
    var_concept_dict = util.get_var_concept_dict(triples)
    for (s, r, t) in triples:
        if t in var_concept_dict:
            inc_rels[t] += 1
    for (s, r, t) in [ t for t in triples if t[1] != ":instance"]:
        if t in var_concept_dict and inc_rels[t] > 1:
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
        itriple = (var, ":instance", var_concept_dict[var])
        if itriple not in additional_instance:
            additional_instance.append(itriple)

    return additional_instance


class SubGraphExtractor():

    def __init__(self, add_instance=True, semantic_standardization=True, add_preds=True):
         
         
        self.add_instance = add_instance
        self.semantic_standardization = semantic_standardization
        if self.semantic_standardization:
            from smatchpp.preprocess import SemanticAMRStandardizer
        self.semantic_standardizer = SemanticAMRStandardizer()
        self.add_preds = add_preds
        self.reify_rules = util.read_reify_table()
        self.concept_groups = util.read_concept_groups()
        self.amr_aspects = util.read_amr_aspects()

    def all_subgraphs_by_name(self, triples):
        name_subgraph = {}
        
        # full graph
        name_subgraph["main"] = triples 
        name_subgraph["main without wiki"] = [t for t in triples if t[1] != ":wiki"]
        name_subgraph["wiki"] = self._maybe_add_instance([t for t in triples if t[1] == ":wiki"], triples)
        
        # remove wiki from all subgraphs that will be extracted
        tmptriples = name_subgraph["main without wiki"]
        
        if self.semantic_standardization:
            tmptriples = self.semantic_standardizer.standardize(triples)
            name_subgraph["main (semantically standardized)"] = tmptriples
        for name, subgraph in self._iter_name_subgraph(tmptriples):
            name_subgraph[name] = subgraph
        
        # more complex aspects
        name_subgraph["REENTRANCIES"] = subgraph_reentrancies(tmptriples)
        
        exclude = ["main", "main without wiki", "wiki", "main (semantically standardized)"]
        for name in name_subgraph:
            if name in exclude:
                continue
            sg = name_subgraph[name]
            sg = self.clean_extend_subgraph(sg, tmptriples, name)
            name_subgraph[name] = sg
         
        return name_subgraph

    def _iter_name_subgraph(self, triples):
        
        for name in self.amr_aspects:
            yield self._get_subgraph_by_name(name, triples)

    def _get_subgraph_by_name(self, name, triples):

        rules = self.amr_aspects[name]
        associated_rels = rules["associated_rel"]
        sgtriples = [t for t in triples if t[1] in associated_rels]
        
        if rules["associated_concept"] and rules["associated_concept"][0] in self.concept_groups:
            concept_group = self.concept_groups[rules["associated_concept"][0]]["aliases"]
            vs = [t[0] for t in triples if t[2] in concept_group] 
            sgtriples += [t for t in triples if t[0] in vs or t[2] in vs] 
        
	# check for reified rel nodes, collect related variable    
        for associated_rel in associated_rels:
            vars_of_reified_concept = []
            if associated_rel in self.reify_rules[0]:
                for (s, r, t) in triples:
                    if r == ":instance" and t == self.reify_rules[0][associated_rel][0]:
                        vars_of_reified_concept.append(s)
                for (s, r, t) in triples:
                    if (t in vars_of_reified_concept or s in vars_of_reified_concept) and r != ":instance":
                        sgtriples.append((s, r, t))
        
        return name, sgtriples 
    
    def clean_extend_subgraph(self, sgtriples, triples_all, name):
        
        sgtriples = self._maybe_add_subtree(sgtriples, triples_all, name)
        sgtriples = self._maybe_add_preds(sgtriples, triples_all)
        sgtriples = self._maybe_add_instance(sgtriples, triples_all)
        sgtriples = list(set(sgtriples))

        return sgtriples

    def _maybe_add_preds(self, triples, triples_all):
        if not self.add_preds:
            return triples
        out = []
        for tr in triples:
            out += get_preds(triples_all, tr[0]) 
            out += get_preds(triples_all, tr[2])
        out = triples + out
        return out
 
    def _maybe_add_instance(self, triples, triples_all):
        if not self.add_instance:
            return triples
        out = []
        ai = get_additional_instances(triples, triples_all)
        out = triples + ai
        return out
    
    def _maybe_add_subtree(self, triples, triples_all, name):
        
        out = list(triples)
        if name not in self.amr_aspects:
            return out
        subtree_context_depth = self.amr_aspects[name].get("subgraph_extraction_range")
        subtree_context_depth = int(subtree_context_depth)
        
        if subtree_context_depth != 0:    
            finished = False
            depth = 0
            while not finished:
                finished = True
                if depth == subtree_context_depth:
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
