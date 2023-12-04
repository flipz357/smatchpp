from copy import deepcopy
from collections import defaultdict
import logging
from smatchpp import util
from smatchpp import interfaces
from smatchpp import graph_transforms

logger = logging.getLogger("__main__")

class DoNothingStandardizer(interfaces.GraphStandardizer):
    
    @staticmethod
    def _standardize(triples):
        return triples

class GenericStandardizer(interfaces.GraphStandardizer):
    """Class for generic graph standardization

       We apply the following steps
       
       1. Lower Casing
       ------------
       We lower case everything, e.g. (x, op1, "Obama") -> (x, op1, "obama"). 
       We presume that lower-uppercasing doesn't change the meaning.
       
       2. Remove Quotes
       -------------
       We remove quotes e.g. (x, op1, "Obama") -> (x, op1, Obama). This often makes sense since some graphs
       have quotes with ' and other with ", and we presume it makes no difference
       
       3. Reindex nodes
       -------------
       We relabel variable names / node indeces. It is a useful standardization for all graphs. It prevents
       that there are node labels that are the same as node indexes.

       4. Deinvert edges
       --------------
       We deinvert edges, e.g. (x, a-of, y) -> (y, a, x). Makes sense as a standardization, Penman uses inversion 
       only to facilitate string serialization, so relations should be deinverted.
       So this makes sense for penman graphs in general.
    """

    def __init__(): 
        return None
    
    def _standardize(self, triples):
        """Triple standardization according to parameters specified in init"""

        triples = deepcopy(triples)
        logging.debug("standardizing triples") 
        logging.debug("This is the input graph: {}".format(triples)) 
        
        triples = graph_transforms.lower_all_labels(triples) 
        triples = graph_transforms.remove_quotes_from_triples(triples)
        graph_transforms.relabel_vars(triples)
        graph_transforms.deinvert_e(triples)
        
        return triples
     
class AMRStandardizer(interfaces.GraphStandardizer):
    """Class for default AMR graph standardization.

       We apply the following steps:

        1. Lower Casing
       ----------------
       see GenericStandardizer
       
       2. Remove Quotes
       ----------------
       see GenericStandardizer
       
       3. Reindex nodes
       ----------------
       see GenericStandardizer
       
       4. Domain2Mod
       -------------
       Specific AMR inversion to handle that AMR views :domain = mod-of. 
       Makes sense as a standardization, since AMR guidelines 
       explicitly define :domain as the inverse of :mod-of.

       5. Deinvert edges
       -----------------
       see GenericStandardizer

       6. Use Concept as Root
       ----------------------
       This is justified by [AMR guidelines](https://github.com/amrisi/amr-guidelines/blob/master/amr.md) 
       who specifically speak about a *root concept*, so the root should express the focus and be non-anonymous
       With this, the two AMRs (c / car) and (d / dog) will get a score of 0.0. 
       On the other hand two AMRs would get a score of 0.5, since the root would anonymous (which may be less desired).

       7. Dereify edges
       ----------------
       It induces some standardzation and forces parsed amrs, if possible, 
       in the same format as assumed by the AMR Sembank, which derifies per default, 
       see [AMR guidelines](https://github.com/amrisi/amr-guidelines/blob/master/amr.md)

       8. Remove Duplicates
       --------------------
       The meaning of duplicate triples in AMR is not clear, therefore we remove them.
    """

    def __init__(self): 
        
        self.dereifier = graph_transforms.RuleBasedSyntacticAMRTransformer(mode="dereify")

        return None

    def _standardize(self, triples):
        """Triple standardization according to parameters specified in init"""

        triples = deepcopy(triples)
        logging.debug("standardizing triples") 
        logging.debug("1. input: {}".format(triples)) 
        
        triples = graph_transforms.lower_all_labels(triples) 
        triples = graph_transforms.remove_quotes_from_triples(triples)
        graph_transforms.relabel_vars(triples)
        graph_transforms.domain2mod(triples)
        graph_transforms.deinvert_e(triples)
        graph_transforms.concept_as_root(triples)
        triples = self.dereifier.transform(triples)
        triples = graph_transforms.remove_duplicates(triples)
        return triples


class BasicGraphPairPreparer(interfaces.GraphPairPreparer):
    """Class for prepairing graph pairs

       Some standardization may involve a graph pair, e.g., 
       when we simplify coreference in two graphs

       Attributes:
            method (str): either "basic" or "reduced". If reduced, we apply content reduction
                          via coreference simplification
            rename_vars (bool): we rename variables in two graphs
    """

    def __init__(self, lossless_graph_compression=False, affix_vars=True):

        self.lossless_graph_compression = lossless_graph_compression
        self.affix_vars = affix_vars

    def _prepare_get_vars(self, triples1, triples2):
        
        logger.debug("preparing graph pair...")
        triples1, triples2 = list(triples1), list(triples2)
        var1 = None
        var2 = None

        # maybe do a lossless graph compression, and get the reduced sets of variables
        if self.lossless_graph_compression:    
            logger.debug("lossless content conversion input graph 1: {}".format(triples1))
            logger.debug("lossless content conversion input graph 2: {}".format(triples2))
            var1, var2 = self._lossless_reduction(triples1, triples2)
            logger.debug("lossless content conversion output graph 1: {}".format(triples1))
            logger.debug("lossless content conversion output graph 2: {}".format(triples2))
        
        # else we just get the sets of variables
        else:
            var1 = util.get_var_concept_dict(triples1)
            var2 = util.get_var_concept_dict(triples2)
            var1 = var1.keys()
            var2 = var2.keys()
         
        logger.debug("varset graph 1: {}".format(var1))
        logger.debug("varset graph 2: {}".format(var2))
        
        # it may be useful to rename the variables in two graph to indicate from which graph they are
        if self.affix_vars:
            
            logger.debug("renaming vars in graph 1...")
            
            var1 = self._affix_vars(var1, triples1, "aa_")
            logger.debug("renamed vars graph 1: {}".format(var1))
            logger.debug("new graph 1: {}".format(triples1))
            
            var2 = self._affix_vars(var2, triples2, "bb_")
            logger.debug("renamed vars graph 2: {}".format(var2))
            logger.debug("new graph 2: {}".format(triples2))
        
        return triples1, triples2, var1, var2
    
    @staticmethod
    def _affix_vars(var, triples, affix=""):
        
        # new mapping
        var_newvar = {v: affix + v for v in var}

        # iterate over triples
        for i in range(len(triples)):
            src = triples[i][0]
            tgt = triples[i][2]
            if src in var_newvar:
                src = var_newvar[src]
            if tgt in var_newvar and not triples[i][1] == ":instance":
                tgt = var_newvar[tgt]
            # overwrite variable name via mapping
            triples[i] = (src, triples[i][1], tgt)
        
        # get the new variable set and return it
        var = var_newvar.values()
        var = set(var)
        return var
    
    @staticmethod
    def _lossless_reduction_with_dict(triples, single_ref, var_concept):
        
        # remembering which triples we can delete
        delis = []
        
        # iterate over triples
        for i, tr in enumerate(triples):
            src = tr[0]
            rel = tr[1]
            tgt = tr[2]
            concept = var_concept.get(src)

            # check if there is max one mention of the concept in each graph
            if concept in single_ref:
                # yes? -> overwrite variable with concept
                src = var_concept[src]
        
            if rel not in [":instance", ":root"] and var_concept.get(tgt) in single_ref:
                # same as above but for target variable
                tgt = var_concept[tgt]
            
            # we can remove the instance-relation
            if concept in single_ref and rel == ":instance":
                delis.append(i)

            # and maybe overwrite the triple
            triples[i] = (src, rel, tgt)
        
        # remove the triples we can delete
        for index in sorted(delis, reverse=True):
            del triples[index] 

        return None

    def _lossless_reduction(self, triples1, triples2):
        
        # get var concept dict for both graphs
        var_concept1 = util.get_var_concept_dict(triples1)
        var_concept2 = util.get_var_concept_dict(triples2)

        # count concept mentions
        concept_count1 = defaultdict(int)
        concept_count2 = defaultdict(int)
        for _, c in var_concept1.items():
            concept_count1[c] += 1 
        for _, c in var_concept2.items():
            concept_count2[c] += 1 
        
        # gather concepts that are maximally mentioned once in each graph
        single_ref = set()
        for c in set(concept_count1.keys()).union(set(concept_count2.keys())):
            co1 = concept_count1[c]
            co2 = concept_count2[c]

            # either graph as only one mention of a concept
            if co1 + co2 == 1:
                single_ref.add(c)

            # both graphs have exactly one mention of the concept
            elif co1 == co2 == 1:
                single_ref.add(c)
        
        # perform graph reduction based on gathered info
        self._lossless_reduction_with_dict(triples1, single_ref, var_concept1)
        self._lossless_reduction_with_dict(triples2, single_ref, var_concept2)
        
        # get new variable dicts
        vc1 = util.get_var_concept_dict(triples1)
        vc2 = util.get_var_concept_dict(triples2)

        return vc1.keys(), vc2.keys()
