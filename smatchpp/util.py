import logging

logger = logging.getLogger("__main__")

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


def n_incoming(triples, node):
    """Counts incoming edges

    Args:
        triples: the graph
        node: the node

    Returns:
        number of incoming edges into node
    """
    n = 0
    for tr in triples:
        if tr[2] == node:
            n += 1
    return n


def n_outgoing(triples, node):
    """Counts outgoing edges

    Args:
        triples: the graph
        node: the node

    Returns:
        number of outgoing edges from node
    """
    n = 0
    for tr in triples:
        if tr[0] == node:
            n += 1
    return n
