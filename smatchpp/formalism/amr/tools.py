import logging
import os
import json
from collections import defaultdict
from smatchpp import interfaces
from smatchpp import graph_transforms
from smatchpp import subgraph_extraction

logger = logging.getLogger("__main__")

def read_amr_reify_table(p="/resource/reify_table.txt", lower=False):
    """load reification rules"""
    
    path = os.path.dirname(__file__)
    with open(path + p, "r") as f:
        lines = [l for l in f.read().split("\n") if l if not l.startswith("#")]

    rel_rule = {}

    for line in lines:
        if lower:
            line = line.lower()
        line = line.replace("`", "").replace("'", "") 
        spl = line.split("|")
        spl = [x.strip() for x in spl]

        for elm in spl[0].split(","):
            elm = elm.strip()
            for elm2 in spl[1].split(","):
                elm2 = elm2.strip()
                if elm not in rel_rule:
                    rel_rule[elm] = [elm2, spl[2], spl[3]]
    return rel_rule


def read_amr_aspects(p="/resource/graph_aspects.json"):
    """load reification rules"""
    
    path = os.path.dirname(__file__)
    
    with open(path + p, "r") as f:
        data = json.load(f)

    return data


def read_amr_concept_groups(p="/resource/concept_groups.json"):
    """load reification rules"""
    
    path = os.path.dirname(__file__)
    
    with open(path + p, "r") as f:
        data = json.load(f)

    return data


def maybe_download_amr_frame_file(targetpath="/resource/propbank-amr-frames-arg-descr.txt",
        url="https://amr.isi.edu/doc/propbank-amr-frames-arg-descr.txt"):
    path = os.path.dirname(__file__)
    fullpath = path + targetpath
    error_state = 0
    if os.path.isfile(fullpath):
        return error_state
    
    logger.info("PropBank frame file not found under resource/, I'll try to download it\
                from {}".format(url))
    try:
        import requests
        predfile = requests.get(url).text
        with open(fullpath, "w") as out_file:
            out_file.write(predfile)
        logger.info("suffessfully downloaded the predicate frame file and placed it under {}".format(fullpath))
        error_state = 0
    except:
        logger.warning("Something went wrong when trying to download the predicate frame file.\
                        You can fix this problem manually by downloading the file from: {}\
                        and placing it as {}".format(url, fullpath))
        error_state = 1
    
    return error_state


def read_frame_table(p="/resource/propbank-amr-frames-arg-descr.txt", lower=True):
    """load frame-argument rules"""
    
    error = maybe_download_amr_frame_file()
    if error:
        logger.warning("Couldn't load the predicate file which is used to enhance fine-grained\
                        semantic scoring. I'll use an empty dictionary instead.")
        return {}

    path = os.path.dirname(__file__)
    fullpath = path + p
   
    with open(fullpath, "r") as f:
        lines = [l for l in f.read().split("\n") if l]

    frame_table = {}

    for line in lines:
        if lower:
            line = line.lower()
        spl = line.split("  arg")
        pred = spl[0]
        frame_table[pred] = {}
        for elm in spl[1:]:
            elm = elm.replace(", ", " ")
            elm = elm.replace(". ", " ")
            role_descr = elm.split(": ")
            frame_table[pred][":arg" + role_descr[0]] = " " + " ".join(role_descr[1].split()) + " "
    return frame_table


def invert_frame_table(frame_table, aspects):
    pred_role_map = defaultdict(dict)
    for aspect in aspects:
        strings = aspects[aspect]["search_in_frame_descr"].keys()
        for pred in frame_table:
            for role in frame_table[pred]:
                for string in strings:
                    if string in frame_table[pred][role]:
                        pred_role_map[pred][role] = aspects[aspect]["search_in_frame_descr"][string]
    return pred_role_map


class AMRStandardizer(interfaces.GraphStandardizer):
    """Class for default AMR graph standardization.

       We apply the following steps:

        1. Lower Casing
       ----------------
       see GenericStandardizer in preprocess.py

       2. Remove Quotes
       ----------------
       see GenericStandardizer in preprocess.py

       3. Reindex nodes
       ----------------
       see GenericStandardizer in preprocess.py

       4. Domain2Mod
       -------------
       Specific AMR inversion to handle that AMR views :domain = mod-of.
       Makes sense as a standardization, since AMR guidelines
       explicitly define :domain as the inverse of :mod.

       5. Deinvert edges
       -----------------
       see GenericStandardizer in preprocess.py

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

        reify_rules = read_amr_reify_table(lower=True)
        self.dereifier = graph_transforms.SyntacticReificationGraphTransformer(reify_rules, mode="dereify")

        return None

    def _standardize(self, triples):
        """Triple standardization according to parameters specified in init"""

        triples = list(triples)
        logging.debug("standardizing triples")
        logging.debug("1. input: {}".format(triples))
        triples = graph_transforms.lower_all_labels(triples)
        triples = graph_transforms.remove_quotes_from_triples(triples)
        triples = graph_transforms.relabel_vars(triples)
        triples = graph_transforms.domain2mod(triples)
        triples = graph_transforms.deinvert_e(triples)
        graph_transforms.concept_as_root(triples)
        triples = self.dereifier.transform(triples)
        triples = graph_transforms.remove_duplicates(triples)
        return triples

class AMRSubgraphExtractor(interfaces.SubgraphExtractor):

    def __init__(self):
        
        # we read the amr aspects, e.g., CAUSE, LOCATION, etc.
        graph_aspects = read_amr_aspects()
        
        # we read the concept groups that are associated with particular aspects
        concept_groups = read_amr_concept_groups()

        # we read propbank frames and role specifications
        propbank_frames = read_frame_table()

        # we intialize a semantic standardizer that uses PropBank frames to translate
        # core roles to explicit non-core roles, e.g., for INSTRUMENT 
        # (control-01 :arg2 -> control-01 :instrument), since arg2 is the instrument
        semantic_rules = invert_frame_table(propbank_frames, graph_aspects)
        self.semantic_standardizer = graph_transforms.SyntacticEdgeRelabelingTransformer(semantic_rules)

        # we create a generic extractor based on our rules from aspects and concept groups
        self.extractor = subgraph_extraction.BasicSubgraphExtractor(add_instance=True,
                                                          graph_aspects=graph_aspects,
                                                          concept_groups=concept_groups)
 
    def _all_subgraphs_by_name(self, triples):
        
        # we semantically standardize the graph with ropbank frames (see above) 
        triples = self.semantic_standardizer.standardize(triples)

        # we return the aspectual subgraphs
        return self.extractor.all_subgraphs_by_name(triples)

