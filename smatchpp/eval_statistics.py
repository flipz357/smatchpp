import numpy as np
from scipy.stats import bootstrap
import logging
import json
import math

logger = logging.getLogger("__main__")


def precision(match_statistic, sumzerothenone=True):
    """Calculates precision given match statistic

    Args:
        match_statistic: [a, b, c, d]
                 a is number of match_statistic from 1st graph in 2nd
                 b is number of match_statistic from 2nd graph in 1nd
                 c is size of 1st graph
                 d is size of 2nd graph
                 Note that usually a == b
                
        sumzerothenone: if both graphs are of size 0 (can happen for fine-grained score)
                        then we return a score of 1.00

    Returns:
        Precision score: a / c
    """

    if sumzerothenone and sum(match_statistic) == 0.0:
        return 1.0
    num = match_statistic[0]
    denom = match_statistic[2]
    if denom < 0.00000001:
        return 0.0
    return num / denom


def recall(match_statistic, sumzerothenone=True):
    """Calculates recall given match statistic

    Args:
        match_statistic: [a, b, c, d]
                 a is number of match_statistic from 1st graph in 2nd
                 b is number of match_statistic from 2nd graph in 1nd
                 c is size of 1st graph
                 d is size of 2nd graph
                 Note that usually a == b
                
        sumzerothenone: if both graphs are of size 0 (can happen for fine-grained score)
                        then we return a score of 1.00

    Returns:
        Recall score: b / d
    """

    if sumzerothenone and sum(match_statistic) == 0.0:
        return 1.0
    num = match_statistic[1]
    denom = match_statistic[3]
    if denom < 0.00000001:
        return 0.0
    return num / denom


def f1_score(match_statistic, sumzerothenone=True):
    """Calculates F1 given match statistic

    Args:
        match_statistic: [a, b, c, d]
                 a is number of match_statistic from 1st graph in 2nd
                 b is number of match_statistic from 2nd graph in 1nd
                 c is size of 1st graph
                 d is size of 2nd graph
                 Note that usually a == b
                
        sumzerothenone: if both graphs are of size 0 (can happen for fine-grained score)
                        then we return a score of 1.00

    Returns:
        F1 score: 2PR / (P+R)
    """

    if sumzerothenone and sum(match_statistic) == 0.0:
        return 1.0
    p = precision(match_statistic)
    r = recall(match_statistic)
    denom = p + r
    if denom < 0.00000001:
        return 0.0
    num = 2 * p * r
    return num / denom
    
def get_fpr(match_statistic):
    """Returns F1 score, precision and recall in a list"""
    return np.array([f1_score(match_statistic), precision(match_statistic), recall(match_statistic)])


class ResultPrinter:
    """Class for printing matching statistics in a reasonable format like corpus precision, recall and F1
    
       Attributes:
            score_type (string): either 'micro' or 'macro', or 'pairwise'
            do_bootstrap (bool): calculate confidence intervals
            output_format (string): either 'text' or 'json'
    """

    def __init__(self, score_type="micro", do_bootstrap=False, 
                    also_return_bootstrap_distribution=False, output_format="text"):
        
        assert score_type in ["micro", "macro", None]
        assert output_format in ["text", "json"] 
        self.score_type = score_type
        self.do_bootstrap = do_bootstrap
        self.output_format = output_format
        self.also_return_bootstrap_distribution = also_return_bootstrap_distribution
        if not self.do_bootstrap and self.also_return_bootstrap_distribution:
            raise ValueError("contradictory arguments, if you want to have bootstrap \
                                distribution do not forget to enable boostrap")
        return None
    
    def _aggr_wrapper(self, match_data, axis=0):
        """ needed for vectorized bootstrapping 

            From scipy docs: Statistic for which the confidence interval is to be calculated. 
                             statistic must be a callable that accepts len(data) samples as separate arguments 
                             and returns the resulting statistic. If vectorized is set True, 
                             statistic must also accept a keyword argument axis and 
                             be vectorized to compute the statistic along the provided axis.
        """
        
        stat = None
        
        if self.score_type == "micro":   
            # raw match statistics as input, we calculate micro scores
            dat = np.sum(match_data, axis=axis)
            p = dat[0]/dat[2]
            r = dat[1]/dat[3]
            f1 =  (2 * p * r) / (p + r)
            stat = np.array([f1, p, r])
        
        if self.score_type == "macro":
            # f1, precision, recall already calculated, we need only take the mean for macro scores
            stat = np.mean(match_data, axis=axis)

        return stat
              
    def print_all(self, final_result_dic, jsonindent=4):
        if self.output_format == "json":
            string = self._nice_format(final_result_dic, jsonindent)
        if self.output_format == "text":
            string = self._nice_format2(final_result_dic)
        print(string)
    
    def get_final_result(self, result_dic):
        # for each score dimension we have a list with pair-wise match statistics
        final_result_dic = {k:np.array(v) for k, v in result_dic.items()}

        # we iterate over each score dimension
        for score_dim in result_dic:
            match_data = result_dic[score_dim]

            # when fine-grained sub-graphs are inspected it can happen 
            # that two graphs in a pair are both empty, in that case
            # we only need the pairs where either both or one graph is not an empty graph
            if score_dim != "main":
                #match_data = [m for m in match_data if sum(m) > 0.0]
                # except if result printer is called over a single pairs we do not need to do anything
                # print(score_dim, match_data)
                if not len(match_data) == 1:
                    match_data = [m for m in match_data if sum(m) > 0.0]
                # print(match_data, score_dim) 
            # if score type micro or pair
            if self.score_type in ["micro", None]:
                match_data_reduced = np.sum(match_data, axis=0)
                res = get_fpr(match_data_reduced)

            if self.score_type == "macro":
                match_data = np.array([get_fpr(m) for m in match_data])
                res = np.mean(match_data, axis=0)
            
            low = None
            high = None
            distribution = None
            if self.do_bootstrap:
                try:
                    bs = bootstrap((match_data,), self._aggr_wrapper, vectorized=True, axis=0)
                    low = bs.confidence_interval.low
                    high = bs.confidence_interval.high
                    if self.also_return_bootstrap_distribution:
                        distribution = bs.bootstrap_distribution
                except ValueError: # ValueError:
                    logger.warning("can't do bootstrap, too many zeros in result.\
                            setting confidence interval to [0,100]")
                    low = [0.0, 0.0]
                    high = [100.0, 100.0]
                if any(math.isnan(x) for x in np.concatenate((low, high))):
                    low = [0.0, 0.0]
                    high = [100.0, 100.0]
            
            final_result_dic[score_dim] = self._get_partial_result_dict(res, low, high, distribution)
        
        return final_result_dic
    
    @staticmethod
    def _nice_format(dic, jsonindent):
        if jsonindent == 0:
            return json.dumps(dic)
        return json.dumps(dic, indent=jsonindent)
    
    def _get_partial_result_dict(self, fpr, low, high, distribution, multiplier=100, rounder=2):
        fpr *= multiplier
        fpr = np.round(fpr, rounder)
        if low is not None:
            low *= multiplier
            low = np.round(low, rounder)
        else:
            low = (None, None, None)
        if high is not None:
            high *= multiplier
            high = np.round(high, rounder)
        else:
            high = (None, None, None)
        dic = {}
        dic["F1"] = {"result": fpr[0], "ci": (low[0], high[0])}
        dic["Precision"] = {"result": fpr[1], "ci": (low[1], high[1])}
        dic["Recall"] = {"result": fpr[2], "ci": (low[2], high[2])}

        if self.also_return_bootstrap_distribution:
            dic["F1"]["bootstrap_distribution"] = distribution[0]
            dic["Precision"]["bootstrap_distribution"] = distribution[1]
            dic["Recall"]["bootstrap_distribution"] = distribution[2]

        return dic
    
    @staticmethod
    def _nice_format2(dic):
        strings = []
        dic["===> MAIN (\"Smatch\") <==="] = dic.pop("main")
        for score_dim in dic:
            fpr = np.array([dic[score_dim]["F1"]["result"], dic[score_dim]["Precision"]["result"], dic[score_dim]["Recall"]["result"]])
            fpr = [score_dim + " " * (max(len(st) for st in dic) - len(score_dim))] + list(fpr)
            string = "{} ---->   F1: {}    Precision: {}    Recall: {}".format(*fpr)
            strings.append(string)
        strings.append("----------------------------")
        strings.append("--95-confidence intervals:--")
        strings.append("----------------------------")
        for score_dim in dic:
            fpr = np.array([dic[score_dim]["F1"]["ci"][0], dic[score_dim]["F1"]["ci"][1], 
                dic[score_dim]["Precision"]["ci"][0], dic[score_dim]["Precision"]["ci"][1],
                dic[score_dim]["Recall"]["ci"][0], dic[score_dim]["Recall"]["ci"][1]])
            fpr = [score_dim + " " * (max(len(st) for st in dic) - len(score_dim))] + list(fpr)
            string = "{} ---->   F1: [{},{}]    Precision: [{},{}]    Recall: [{},{}]".format(*fpr)
            strings.append(string)
        return "\n".join(strings)

