import re
import logging
logger = logging.getLogger("__main__")
from smatchpp import util
from smatchpp import interfaces


def subgraph_instance(triples):
    triples = [t for t in triples if t[1] == ":instance"]
    return triples


def subgraph_lexicalized(triples):
    triples = subgraph_instance(triples)
    # "lexicalized" here means that a predicate x is sense disambiguated, 
    # usually (e.g., AMR) denoted as e.g., x-1, or x-99, etc.
    triples = [t for t in triples if re.match(r".*-[0-9]+", t[2].lower())]
    return triples


def unlabel_edges(triples):
    """Remove edge labels

    Args:
        triples: input triples, e.g., [(x, :arg0, y), (y, :arg2, z)]

    Returns:
        graph/triples where every edge label is the same, e.g.
        output triples, e.g., [(x, :rel, y), (y, :rel, z)]
    """
    out = []
    for t in triples:
        if t[1] != ":instance":
            out.append((t[0], ":rel", t[2]))
        else:
            out.append(t)
    return out
    

def unlabel_nodes(triples):
    """Unlabels nodes

    Args:
        triples: input triples with node labels, 
                 e.g. [(x, :instance, car), (y, :instance, person)]

    Returns:
        graph/triples where node labels are the same, 
        e.g. [(x, :instance, concept), (y :instance, concept)]
    """
    out = []
    for t in triples:
        if t[1] == ":instance":
            out.append((t[0], ":instance", "concept"))
        else:
            out.append(t)
    return out
 

def subgraph_reentrancies(triples):
    """Returns all triples where the target has more than one incoming edge

    Args:
        triples: input graph

    Returns:
        all triples where the target has more than one incoming edge
    """
    out = []
    var_concept_dict = util.get_var_concept_dict(triples)
    for (s, r, t) in [ t for t in triples if t[1] != ":instance"]:
        if t in var_concept_dict and util.n_incoming(triples, t) > 1:
            out.append((s, r, t))
    return out


def get_additional_instances(triples, triples_all):
    """Given a graph, if there is a node without a node label (in the subgraph), 
       try to find the node label (in the supergraph) and add it.

    Args:
        triples: subgraph
        triples_all: supergraph

    Returns:
        possibly extended subgraphs with node labels added
    """
    additional_instance = []
    var_concept_dict_sup = util.get_var_concept_dict(triples_all)
    sg_vars = []
    for (s, _, t) in triples:
        if s in var_concept_dict_sup:
            sg_vars.append(s)
        if t in var_concept_dict_sup:
            sg_vars.append(t)
    for sv in sg_vars:
        itriple = (sv, ":instance", var_concept_dict_sup[sv])
        if itriple not in triples:
            additional_instance.append(itriple)
    return additional_instance


def get_all_preds_of_a_node(triples, node):
    """Get predicates of a node n. A predicate is a node that has 0 
       incoming edges and only one outgoing edge (into n)

    Args:
        triples: input graph
        node: node 

    Returns:
        input graph possibly extended with predicates
    """
    triples = [t for t in triples if t[1] != ":instance"]
    preds = []
    for tr in triples:
        if node != tr[2]:
            continue
        if tr[1] == ":root":
            continue
        inode = tr[0]
        inc = util.n_incoming(triples, inode)
        outg = util.n_outgoing(triples, inode)
        if inc == 0 and outg == 1:
            preds.append(tr)
    return preds


class BasicSubgraphExtractor(interfaces.SubgraphExtractor):

    def __init__(self, add_instance=True, graph_aspects=None, concept_groups=None):
        """Sets up a subgraph extractor. 
           The idea is to extract subgraphs from a graph according to certain aspects.
           

        Args:
            add_instance: if True adds the node labels of variables/nodes contained in a subgraph,
                          which is equivalent to adding :instance triples for all variables
                          in a subgraph. E.g., if the subgraph is [(x, :polarity, -)], and in the
                          supergraph the label of x is "good": (x, :instance, good, we might
                          return the subgraph [(x, :polarity, -), (x, :instance, good)]
            graph_aspects (dict): specifies the target aspects with a dictionary
                                  E.g. {"LOCATION (spatial)":
                                        {
                                            "associated_rel": [":location", ":path", ":destination", ":direction"],
                                            "associated_concept_group": "locations",
                                            "subgraph_extraction_range": 2,
                                            "add_parent": 0,
                                            "add_predicates": 1
                                        },
            concept_groups (dict): specifies a (non-exhaustive) clustering of node labels, from graph_aspects 
                            to associated node labels 
                            e.g. {"locations": ["city", "place", "village"]},
                            "organization": ["government-organization", "company"]} means that
                            means that node labels in the graph aspect of "organization" are selected for the
                            subgraph of "organization"
        """
        self.add_instance = add_instance
        self.concept_groups = concept_groups
        self.graph_aspects = graph_aspects

    def _all_subgraphs_by_name(self, triples):
        name_subgraph = {}
        
        for name, subgraph in self._iter_name_subgraph(triples):
            name_subgraph[name] = subgraph
        
        # more complex aspects
        name_subgraph["REENTRANCIES"] = subgraph_reentrancies(triples)
        
        exclude = ["main", "main without wiki", "wiki", "main (semantically standardized)"]
        
        for name in name_subgraph:
            if name in exclude:
                continue
            sg = name_subgraph[name]
            sg = self.clean_extend_subgraph(sg, triples, name)
            name_subgraph[name] = sg
            logger.debug("subgraph of type {}:\n{}".format(name, sg))
        return name_subgraph

    def _iter_name_subgraph(self, triples):
        
        for name in self.graph_aspects:
            yield self._get_subgraph_by_name(name, triples)

    def _get_subgraph_by_name(self, name, triples):

        rules = self.graph_aspects[name]
        associated_rels = rules["associated_rel"]
        sgtriples = [t for t in triples if t[1] in associated_rels]
        
        if rules["associated_concept_group"] and rules["associated_concept_group"] in self.concept_groups:
            concept_group = self.concept_groups[rules["associated_concept_group"]]
            vs = [t[0] for t in triples if t[2] in concept_group] 
            sgtriples += [t for t in triples if t[0] in vs or t[2] in vs] 
        
        return name, sgtriples 
    
    def clean_extend_subgraph(self, sgtriples, triples_all, name):
        
        sgtriples = self._maybe_add_context(sgtriples, triples_all, name)
        sgtriples = self._maybe_add_preds(sgtriples, triples_all, name)
        sgtriples = self._maybe_add_instance(sgtriples, triples_all)
        sgtriples = list(set(sgtriples))
        logger.debug("name: {} -> sugraph: {}".format(name, sgtriples))
        return sgtriples

    def _maybe_add_preds(self, triples, triples_all, name):
        if name not in self.graph_aspects:
            return triples
        if self.graph_aspects[name]["add_predicates"] == 0:
            return triples
        out = []
        for tr in triples:
            out += get_all_preds_of_a_node(triples_all, tr[0]) 
            out += get_all_preds_of_a_node(triples_all, tr[2])
        out = triples + out
        return out
     
    def _maybe_add_instance(self, triples, triples_all):
        if not self.add_instance:
            return triples
        ai = get_additional_instances(triples, triples_all)
        out = triples + ai
        return out
    
    def _maybe_add_context(self, triples, triples_all, name):
        
        out = list(triples)
        if name not in self.graph_aspects:
            return out
        parent_additions = []
        if self.graph_aspects[name].get("add_parent") == 1:
            for (s, _, t) in triples:
                ps = [t for t in triples_all if t[2] == s]
                parent_additions += [elm for elm in ps if elm not in triples]
        subtree_context_depth = self.graph_aspects[name].get("subgraph_extraction_range")
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
        out += parent_additions
        return out
