from collections import Counter

class GraphStandardizer:
    
    def standardize(self, triples):
        self._check_args(triples)
        triples = self._standardize(triples)
        self._check_result(triples)
        return triples
    
    @staticmethod
    def _check_args(triples):
        if not isinstance(triples, list):
            raise ValueError("invalid input, must be a list")

    @staticmethod
    def _check_result(triples):
        if not isinstance(triples, list):
            raise ValueError("invalid output, must return list")

class GraphTransformer:
    
    def transform(self, triples):
        self._check_args(triples)
        triples = self._transform(triples)
        self._check_result(triples)
        return triples
    
    @staticmethod
    def _check_args(triples):
        if not isinstance(triples, list):
            raise ValueError("invalid input, must be a list")

    @staticmethod
    def _check_result(triples):
        if not isinstance(triples, list):
            raise ValueError("invalid output, must return list")

class GraphPairPreparer:
    

    def prepare_get_vars(self, triples1, triples2):
        self._check_args(triples1, triples2)
        triples1, triples2, v1, v2 = self._prepare_get_vars(triples1, triples2)
        self._check_result(triples1, triples2, v1, v2)
        return triples1, triples2, v1, v2

    @staticmethod
    def _check_args(triples1, triples2):
        if not isinstance(triples1, list):
            raise ValueError("invalid input, must be a list")
        if not isinstance(triples2, list):
            raise ValueError("invalid input, must be a list")

    @staticmethod
    def _check_result(triples1, triples2, v1, v2):
        if not isinstance(triples1, list):
            raise ValueError("invalid output, must return list")
        if not isinstance(triples2, list):
            raise ValueError("invalid output, must return list")
        if not isinstance(v1, set):
            raise ValueError("invalid output, must return set")
        if not isinstance(v2, set):
            raise ValueError("invalid output, must return set")

class TripleMatcher:
    
    def triplematch(self, triple1, triple2):
        return self._triplematch(triple1, triple2)


class SubGraphExtractor:

    def all_subgraphs_by_name(self, triples):
        # should return a dictionary that maps strings onto sets with triples, i.e., subgraphs
        name_subgraph_dict = self._all_subgraphs_by_name(triples)
        return name_subgraph_dict


class GraphReader:

    def string2graph(self, string):
        triples = self._string2graph(string)
        return triples

class GraphWriter:

    def graph2string(self, triples):
        self._check_args(triples)
        string = self._graph2string(triples)
        self._check_result(string)
        return string

    @staticmethod
    def _check_args(triples):
        if not isinstance(triples, list):
            raise ValueError("invalid input, must be a list")

    @staticmethod
    def _check_result(string):
        if not isinstance(string, str):
            raise ValueError("invalid output, must return string")    


class Solver:

    def solve(self, unarymatch_dict, binarymatch_dict, V):
        self._check_args(unarymatch_dict, binarymatch_dict, V)
        alignment, lowerbound, upperbound = self._solve(unarymatch_dict, binarymatch_dict, V)
        self._check_result(alignment, upperbound, lowerbound, V)
        return alignment, lowerbound, upperbound

    @staticmethod
    def _check_args(unarymatch_dict, binarymatch_dict, V):
        if not isinstance(unarymatch_dict, Counter):
            raise ValueError("invalid unary match dict")
        if not isinstance(binarymatch_dict, Counter):
            raise ValueError("invalid binary match dict")
        if not isinstance(V, int):
            raise ValueError("V must be an int")

    @staticmethod
    def _check_result(alignmat, upperbound, lowerbound, V):
        s = alignmat.shape
        if s != (V,):
            raise ValueError("invalid alignment matrix, must be of shape ({}, ), received {}".format(V, alignmat))

class Scorer:

    def score(self, triples1, triples2, alignmat, varindex):
        self._check_args(triples1, triples2, alignmat, varindex)
        score = self._score(triples1, triples2, alignmat, varindex)
        return score

    @staticmethod
    def _check_args(triples1, triples2, alignmat, varindex):
        return None
