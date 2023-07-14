from collections import Counter

class GraphStandardizer:
    
    def __init__(self):
        return None

    def standardize(self, triples):
        self._check_args(triples)
        triples = self._standardize(triples)
        self._check_result(triples)
        return triples

    def _check_args(self, triples):
        if not isinstance(triples, list):
            raise ValueError("invalid input, must be a list")

    def _check_result(self, triples):
        if not isinstance(triples, list):
            raise ValueError("invalid output, must return list")

class GraphPairPreparer:
    
    def __init__(self):
        return None

    def prepare_get_vars(self, triples1, triples2):
        self._check_args(triples1, triples2)
        triples1, triples2, v1, v2 = self._prepare_get_vars(triples1, triples2)
        self._check_result(triples1, triples2, v1, v2)
        return triples1, triples2, v1, v2

    def _check_args(self, triples1, triples2):
        if not isinstance(triples1, list):
            raise ValueError("invalid input, must be a list")
        if not isinstance(triples2, list):
            raise ValueError("invalid input, must be a list")

    def _check_result(self, triples1, triples2, v1, v2):
        if not isinstance(triples1, list):
            raise ValueError("invalid output, must return list")
        if not isinstance(triples2, list):
            raise ValueError("invalid output, must return list")
        if not isinstance(v1, set):
            raise ValueError("invalid output, must return set")
        if not isinstance(v2, set):
            raise ValueError("invalid output, must return set")

class TripleMatcher:
    
    def __init__(self):
        return None

    def triplematch(self, triple1, triple2):
        return self._triplematch(triple1, triple2)


class GraphReader:

    def string2graph(self, string):
        self._check_args(string)
        triples = self._string2graph(string)
        self._check_result(triples)
        return triples

    def _check_args(self, string):
        if not isinstance(string, str):
            raise ValueError("invalid input, must be a string")

    def _check_result(self, triples):
        if not isinstance(triples, list):
            raise ValueError("invalid output, must return list")    


class GraphWriter:

    def graph2string(self, triples):
        self._check_args(triples)
        string = self._graph2string(triples)
        self._check_result(string)
        return string

    def _check_args(self, triples):
        if not isinstance(triples, list):
            raise ValueError("invalid input, must be a list")

    def _check_result(self, string):
        if not isinstance(string, str):
            raise ValueError("invalid output, must return string")    


class Solver:

    def __init__(self):
        return None

    def solve(self, unarymatch_dict, binarymatch_dict, V):
        self._check_args(unarymatch_dict, binarymatch_dict, V)
        alignment, lowerbound, upperbound = self._solve(unarymatch_dict, binarymatch_dict, V)
        self._check_result(alignment, upperbound, lowerbound, V)
        return alignment, lowerbound, upperbound

    def _check_args(self, unarymatch_dict, binarymatch_dict, V):
        if not isinstance(unarymatch_dict, Counter):
            raise ValueError("invalid unary match dict")
        if not isinstance(binarymatch_dict, Counter):
            raise ValueError("invalid binary match dict")
        if not isinstance(V, int):
            raise ValueError("V must be an int")

    def _check_result(self, alignmat, upperbound, lowerbound, V):
        s = alignmat.shape
        if s != (V,):
            raise ValueError("invalid alignment matrix, must be of shape ({}, ), received {}".format(V, alignmat))

class Scorer:

    def __init__(self):
        return None

    def score(self, triples1, triples2, alignmat, varindex):
        self._check_args(triples1, triples2, alignmat, varindex)
        score = self._score(triples1, triples2, alignmat, varindex)
        return score

    def _check_args(self, unarymatch_dict, binarymatch_dict, V):
        return None
