import numpy as np
from scipy.stats import bootstrap
import logging
import json
import math

logger = logging.getLogger("__main__")

def precision(matches, sumzerothenone=True):
    if sumzerothenone and sum(matches) == 0.0:
        return 1.0
    num = matches[0]
    denom = matches[2]
    if denom < 0.00000001:
        return 0.0
    return num / denom

def recall(matches, sumzerothenone=True):
    if sumzerothenone and sum(matches) == 0.0:
        return 1.0
    num = matches[1]
    denom = matches[3]
    if denom < 0.00000001:
        return 0.0
    return num / denom

def f1_score(matches, sumzerothenone=True):
    if sumzerothenone and sum(matches) == 0.0:
        return 1.0
    p = precision(matches)
    r = recall(matches)
    denom = p + r
    if denom < 0.00000001:
        return 0.0
    num = 2 * (p * r)
    return num / denom


class ResultPrinter:

    def __init__(self, score_type="micro", do_bootstrap=False, output_format="text"):
        self.score_type = score_type
        self.do_bootstrap = do_bootstrap
        self.output_format = output_format
        return None

    def get_fpr(self, match_data_reduced):
        return np.array([f1_score(match_data_reduced), precision(match_data_reduced), recall(match_data_reduced)])

    def _aggr_wrapper(self, match_data, axis=0):
        result = None

        if self.score_type == "micro":        
            dat = np.sum(match_data, axis=axis)
            p = dat[0]/dat[2]
            r = dat[1]/dat[3]
            stat =  2 * (p * r) / (p + r)
            result = np.array([stat, p, r])
        
        if self.score_type == "macro":        
            result = np.mean(match_data, axis=axis)

        return result
              
    def print_all(self, final_result_dic):
        if self.output_format == "json":
            string = self._nice_format(final_result_dic)
        if self.output_format == "text":
            string = self._nice_format2(final_result_dic)
        print(string)
    
    def get_final_result(self, result_dic):
        final_result_dic = {k:np.array(v) for k, v in result_dic.items()}
        for score_dim in result_dic:
            match_data = result_dic[score_dim]
            if score_dim != "main" and self.score_type != "pairwise":
                match_data = [m for m in match_data if sum(m) > 0.0]
            low = None
            high = None
            if self.score_type in ["micro", "pairwise"]:
                match_data_reduced = np.sum(match_data, axis=0)
                res = self.get_fpr(match_data_reduced)
            if self.score_type == "macro":
                match_data = np.array([self.get_fpr(m) for m in match_data])
                res = np.mean(match_data, axis=0)
            if self.do_bootstrap:
                try:
                    bs = bootstrap((match_data,), self._aggr_wrapper, vectorized=True, axis=0)
                    low = bs.confidence_interval.low
                    high = bs.confidence_interval.high
                except ValueError: # ValueError:
                    logger.warning("can't do bootstrap, too many zeros in result.\
                            setting confidence interval to [0,100]")
                    low = [0.0, 0.0]
                    high = [100.0, 100.0]
                if any(math.isnan(x) for x in np.concatenate((low, high))):
                    low = [0.0, 0.0]
                    high = [100.0, 100.0]

            final_result_dic[score_dim] = self._get_partial_result_dict(res, low, high)
        return final_result_dic

    def _nice_format(self, dic):
        if self.score_type == "pairwise":
            return json.dumps(dic)
        return json.dumps(dic, indent=4)

    def _get_partial_result_dict(self, fpr, low, high, multiplier=100, rounder=2):
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
        return dic

    def _nice_format2(self, dic):
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

