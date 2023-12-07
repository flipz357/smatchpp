import logging
from smatchpp import util
from smatchpp import interfaces

logger = logging.getLogger("__main__")


def remove_duplicates(triples):
    triples = list(set(triples))
    return triples


def lower_all_labels(triples):
    triples = [(s.lower(), r.lower(), t.lower()) for (s, r, t) in triples]
    logging.debug("I lower-cased all strings in the graph: {}".format(triples)) 
    return triples


def remove_quotes_from_triples(triples):

    f = lambda x: x.replace("\"", "").replace("'", "")
    
    newtriples = []
    for triple in triples:
        triple = (f(triple[0]), f(triple[1]), f(triple[2]))
        newtriples.append(triple)
    
    logging.debug("I removed quotes: {}".format(newtriples))
    return newtriples


def relabel_vars(triples):
    """standardize variable names"""
    
    v2c = util.get_var_concept_dict(triples)
    constants = util.get_constant_set(triples)

    # standardize and make variable names simpler "(xyds / cat)" -> "(c / cat)"
    # just for optics and better alignment interpretation
    v2v = {}
    vnew_idx = {}
    for v in v2c:
        concept = v2c[v]
        vnew = concept[0]
        if vnew not in vnew_idx:
            v2v[v] = vnew
            vnew_idx[vnew] = 1
        else:
            v2v[v] = vnew + str(vnew_idx[vnew])
            vnew_idx[vnew] += 1
    
    # take care that there are no variable names that are same as concepts
    # some parsers and the reference does this, can lead to bugs
    # so we will change "(i / i)" -> "(ix / i)"
    for v in v2v:
        vnew = v2v[v]
        while vnew in constants:
            vnew += "x"
        v2v[v] = vnew

    # now we can map to new variables
    for i in range(len(triples)):
        src = triples[i][0]
        rel = triples[i][1]
        tgt = triples[i][2]
        if src in v2v:
            src = v2v[src]
        if tgt in v2v:
            if rel != ":instance":
                tgt = v2v[tgt]
        triples[i] = (src, triples[i][1], tgt)
    
    logging.debug("I ensured that no variable name / node index equals concept / node label: {}".format(triples)) 
    return None
     

def deinvert_e(triples):
    """ Deinvert edges (s, r-of, t) --> (t, r, s)

    Args:
        triples: triples

    Returns:
        None
        
    """
    
    for i in range(len(triples)):
        s, relation, t = triples[i]
        iters = 0
        while relation.endswith("-of"):
            relation = relation[:-3]
            iters += 1
        if iters % 2 != 0:
            triples[i] = (t, relation, s)
        else:
            triples[i] = (s, relation, t)
    logging.debug("I deinverted edges: {}".format(triples))  
    return None
 

def domain2mod(triples):
    for i, triple in enumerate(triples):
        s, r, t = triple
        if r == ":domain":
            triples[i] = (s, ":mod-of", t)
        if r == ":domain-of":
            triples[i] = (s, ":mod", t)
    return None


def concept_as_root(triples):
    """the root of a graph is usually (ROOT_OF_GRAPH, :root, x), however, 
    AMR focus style is to use (x, :root, concept) where concept is 
    from (x, :instance, concept)

    This better reflects the AMR guidelines who view "the root concept" as the focus
    of a text"
    """
    vc = util.get_var_concept_dict(triples)
    for i, tr in enumerate(triples):
        if tr[1] == ":root":
            newtriple = (tr[2], ":root", vc[tr[2]])
            triples[i] = newtriple
            logging.debug("""I set the root triple from ('{}', '{}', '{}') to {}
                   to better reflect AMR guidelines where the root
                   concept is seen as "focus" """.format(tr[0], tr[1], tr[2], newtriple))
            break
    return None


def norm_logical_ops(triples):
    """Norm logical operators for "commutative" operators "and" and "or"
       
       E.g. (x, :instance, and), (x, :op1, y), (x, :op2, z)
            ---> (x, :instance, and), (x, :op, y), (x, :op, z)
    """

    rel_from_op = []
    for i in range(len(triples)):
        s, r, t = triples[i]
        if ":op" in r:
            for j in range(len(triples)):
                sx, rx, tx = triples[j]
                if sx == s and rx == ":instance" and tx in ["or", "and"]:
                    rel_from_op.append(i)
    for i in range(len(triples)):
        if i in rel_from_op:
            s, r, t = triples[i]
            r = ":op"
            triples[i] = (s, r, t)
    return None


def reify_n(triples):
    """Reify constant nodes.
        
       constant nodes are targets with no outgoing edge (leaves) 
       that don't have an incoming :instance edge.

       E.g., (x, :polarity, -) ---> (x, :polarity, y), (y, :instance, -)
    """
    
    triples = list(triples)
    collect_ids = set()
    for i, tr in enumerate(triples):
        target = tr[2]
        incoming_instance = False
        for tr2 in triples:
            if tr2[1] == ":instance" and tr2[0] == target:
                incoming_instance = True
            if tr2[1] == ":instance" and tr2[2] == target:
                incoming_instance = True
        if not incoming_instance:
            collect_ids.add(i)
    newvarkey = "rfattribute_"
    idx = 0
    for cid in collect_ids:
        varname = newvarkey + str(idx)
        triples.append((triples[cid][0], triples[cid][1], varname))
        triples.append((varname, ":instance", triples[cid][2]))
        idx += 1
    for i in reversed(sorted(list(collect_ids))):
        del triples[i]
    
    logging.debug("I reified nodes: {}".format(triples)) 
    return triples
         

class RuleBasedSemanticAMRTransformer(interfaces.GraphTransformer, interfaces.GraphStandardizer):

    def __init__(self):

        self._load_rules()
    
    def _load_rules(self):
        """Semantic standardization happens according to rules 
            and heuristic defined in resources/amr_aspects.json 
            and resources/propbank_amr_frames_args_descr.txt

            This parses the two files into applicable rules
        """
        self.amr_aspects = util.read_amr_aspects()
        frame_table = util.read_frame_table()
        self.inverted_frame_table = util.invert_frame_table(frame_table, self.amr_aspects)
        return None

    def _transform(self, triples):
        logger.debug("Semantic AMR transformer, INPUT: {}".format(triples))
        vc = util.get_var_concept_dict(triples)
        news = {}
        for name in self.amr_aspects:
            map_to = self.amr_aspects[name].get("map_to")
            if not map_to:
                continue
            associated_frame_rels = self.inverted_frame_table[name]
            for (frame, rel) in associated_frame_rels:
                for i in range(len(triples)):
                    s, r, t = triples[i]
                    if r == rel and (s == frame or vc.get(s) == frame):
                        news[i] = (s, map_to, t)
        out = []
        for i in range(len(triples)):
            if i in news:
                out.append(news[i])
            else:
                out.append(triples[i])
        logger.debug("Semantic AMR transformer, OUTPUT: {}".format(triples))
        return out

    def _standardize(self, triples):
        return self._transform(triples)

class RuleBasedSyntacticAMRTransformer(interfaces.GraphTransformer, interfaces.GraphStandardizer):
    """Class for edge de- or reification, which is defined for AMR in dictionaries
       
       Attributes:
            mode (string):                Use either:
                                          None: Nothing will be done
                                          dereify: (z, instance, locatedAt), (z, a1, x), (z, a2, y) -> (x, location, y)
                                          reify: (x, location, y) -> (z, instance, locatedAt), (z, a1, x), (z, a2, y)
    """ 

    def __init__(self, mode="dereify", lower=True):
        
        assert mode in [None, "dereify", "reify"]

        self.mode = mode
        self.lower = lower
        self._load_rules()
    
    def _load_rules(self):
        self.reify_rules, self.reify_rules_inverse = util.read_reify_table(lower=self.lower)
        return None

    def _transform(self, triples):
        logger.debug("Syntactic AMR transformer with mode={}, INPUT: {}".format(self.mode, triples))
        if not self.mode:
            return triples
        triples = list(triples)
        if self.mode == "dereify":
            self._dereify_graph(triples)
        elif self.mode == "reify":
            self._reify_graph(triples)
        logger.debug("Syntactic AMR transformer with mode={}, OUTPUT: {}".format(self.mode, triples))
        return triples

    def _reify_graph(self, triples):
        """ Reifiy a graph in place """
        new = []
        delis = []
        for i, tr in enumerate(triples):
            rel = tr[1]
            if rel in self.reify_rules:
                new.append(("ric" + str(i), ":instance", self.reify_rules[rel][0]))
                new.append(("ric" + str(i), self.reify_rules[rel][1], tr[0]))
                new.append(("ric" + str(i), self.reify_rules[rel][2], tr[2]))
                delis.append(i)
        for index in sorted(delis, reverse=True):
            del triples[index]    
        triples += new
        return None
        
    def _maybe_get_dereification(self, variable, triples):
        """Checks if variable allows a dereification 

        Args:
            variable: a variable
            triples: triples

        Returns:
            An applicable reification rule if any is found
            else Nothing

        """
        
        concept = None
        
        # get index of the instance tripile of the variable
        for i, tr in enumerate(triples):
            if tr[0] == variable and tr[1] == ":instance":
                concept = tr[2]
                ci = i
                break
        
        # continue only if the instance is a concept that can trigger a dereification
        if concept not in self.reify_rules_inverse:
            return False
        
        # if there is an incoming edge into the variable, dereification cannot happen
        for tr in triples:
            if tr[2] == variable:
                return False
        
        # now we search for outgoing relations that match the description
        foundx = 0
        foundxv = None
        foundxi = None
        foundy = 0
        foundyv = None
        foundyi = None
        foundother = 0
        for i, tr in enumerate(triples):
            if tr[0] == variable and tr[1] != ":instance":
                if tr[1] == self.reify_rules_inverse[concept][1]:
                    foundx += 1
                    foundxv = tr[2]
                    foundxi = i
                elif tr[1] == self.reify_rules_inverse[concept][2]:
                    foundy += 1
                    foundyv = tr[2] 
                    foundyi = i
                else:
                    foundother += 1
        
        # we can dereify if there are two outgoing relations that meet the description, but not more
        if foundx == foundy == 1 and foundother == 0:
            return (foundxv, foundyv, foundxi, foundyi, ci, self.reify_rules_inverse[concept][0])
        
        # we cannot dereify
        return False

    
    def _dereify_graph(self, triples):
        """Dereify a graph in place"""
        
        new = []
        delis = []
        done = []
        
        for tr in triples:
            var = tr[0]
            if var in done or util.isroot(var, triples):
                continue
            done.append(var)

            # check if a dereification can be applied 
            # e.g.     x instance be-located-91;    x :arg1 y;    x :arg2 z ----> y :location z
            rule = self._maybe_get_dereification(var, triples)
            if not rule:
                continue
            
            # yes we can apply a rule
            # e.g., src is x; tgt is z, rel is :location
            # del_i are indices of triples that can be removed 
            # i.e., the non-dereified structure
            src, tgt, deli1, deli2, deli3, rel = rule

            # remember non-dereified structure
            delis.append(deli1)
            delis.append(deli2)
            delis.append(deli3)

            # add dereified structure
            new.append((src, rel, tgt))
        
        # remove non-dereified structures
        for index in sorted(delis, reverse=True):
            del triples[index] 
        
        triples += new
        return None
    
    def _standardize(self, triples):
        return self._transform(triples)
