import logging
import os
import json
from collections import defaultdict

logger = logging.getLogger("__main__")

def remove_quotes_from_triple(triple):

    f = lambda x: x.replace("\"", "").replace("'", "")

    triple = (f(triple[0]), f(triple[1]), f(triple[2]))

    return triple


def read_reify_table(p="/resource/reify_table.txt", lower=False):
    """load reification rules"""
    
    path = os.path.dirname(__file__)

    with open(path + p, "r") as f:
        lines = [l for l in f.read().split("\n") if l if not l.startswith("#")]

    rel_rule = {}
    rel_rule_inverse = {}

    for line in lines:
        if lower:
            line = line.lower()
        spl = line.split("|")
        spl = [x.strip() for x in spl]

        for elm in spl[0].split(","):
            elm = elm.strip()
            for elm2 in spl[1].split(","):
                elm2 = elm2.strip()
                rel_rule[elm] = [elm2, spl[2], spl[3]]
                rel_rule_inverse[elm2] = [elm, spl[2], spl[3]]
    
    return rel_rule, rel_rule_inverse

def read_amr_aspects(p="/resource/amr_aspects.json"):
    """load reification rules"""
    
    path = os.path.dirname(__file__)
    
    with open(path + p, "r") as f:
        data = json.load(f)

    return data

def read_concept_groups(p="/resource/concept_groups.json"):
    """load reification rules"""
    
    path = os.path.dirname(__file__)
    
    with open(path + p, "r") as f:
        data = json.load(f)

    return data

def read_frame_table(p="/resource/propbank-amr-frames-arg-descr.txt", lower=True):
    """load frame-argument rules"""
    
    path = os.path.dirname(__file__)

    with open(path + p, "r") as f:
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
    aspects_pred_role = defaultdict(list)    
    for aspect in aspects:
        strings = aspects[aspect]["search_in_frame_descr"]
        for pred in frame_table:
            for role in frame_table[pred]:
                if any(string in frame_table[pred][role] for string in strings):
                    aspects_pred_role[aspect].append((pred, role))
    return aspects_pred_role

def xor(a, b):
    if a and b:
        return False
    if a or b:
        return True
    return False


def get_var_concept_dict(triples):
    """get mapping from variables to concepts """
    vc = {}
    for tr in triples:
        if tr[1] == ":instance":
            vc[tr[0]] = tr[2]
    return vc

def get_constant_set(triples):
    # this includes all leaves that are leaves and the root node, 
    # i.e., all tokens that are not variables
    vc = get_var_concept_dict(triples)
    constants = set()
    for tr in triples:
        src = tr[0]
        rel = tr[1]
        tgt = tr[2]
        if rel == ":instance":
            continue
        if src not in vc:
            constants.add(src)
        if tgt not in vc:
            constants.add(tgt)
    return constants.union(vc.values())

def isroot(var, triples):
    """ check if triple is root """
    trs = [tr for tr in triples if tr[2] == var]
    if not trs:
        return False
    for tr in trs:
        if tr[1] == ":root":
            return True
    return False

def add_dict(todic, fromdic):
    for key in fromdic:
        if key not in todic:
            todic[key] = fromdic[key]
        else:
            todic[key] += fromdic[key]
    return None

def append_dict(todic, fromdic):
    for key in fromdic:
        if key not in todic:
            todic[key] = [fromdic[key]]
        else:
            todic[key].append(fromdic[key])
    return None


def score(alignmat, unarymatch_dict, binarymatch_dict):
    """Score an alignment candidate

        Args:
            alignmat (2d array): alignments from V to V'
            unarymatch_dict (dict): scores of unary alignments
            binarymatch_dict (dict): scores of binary alignments

        Returns:
            score (float)
    """

    # init
    sc = 0.0
    V = range(alignmat.shape[0])

    # iterate over nodes in V
    for i in V:
        # get an alignment i -> j
        j = alignmat[i]
        #add unary triple matches
        sc += unarymatch_dict[(i, j)]
        # iterate over more nodes in V
        for k in V:
            # alignment now i-> j AND k -> l
            l = alignmat[k]
            # add score for binary triple matches
            sc += binarymatch_dict[(i, j, k, l)]
    return sc

def alignmat_compressed(alignmat):
    alignmatargmax = alignmat.argmax(axis=1)
    alignmatargmax[alignmat.sum(axis=1) == 0] = -1
    alignmat = alignmatargmax
    return alignmat


def _get_childs(triples, node):
    childs = []
    for tr in triples:
        if tr[0] == node:
            childs.append(tr)
    return childs


def _get_possible_childs(triples, node):
    childs = []
    for tr in triples:
        if tr[2] == node:
            childs.append(tr)
    return childs


def _n_incoming(triples, node):
    n = 0
    for tr in triples:
        if tr[2] == node:
            n += 1
    return n


def _n_outgoing(triples, node):
    n = 0
    for tr in triples:
        if tr[0] == node:
            n += 1
    return n


