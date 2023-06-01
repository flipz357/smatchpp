import time
import logging
from smatchpp import util

logger = logging.getLogger("__main__")

class Smatchpp():

    def __init__(self, graph_reader=None, graph_standardizer=None, graph_pair_preparer=None,
                    triplematcher=None, alignmentsolver=None, graph_aligner=None, graph_scorer=None,
                    subgraph_extractor=None, printer=None, score_dimension=None):

        self.graph_reader = graph_reader
        if not self.graph_reader:
            from smatchpp import data_helpers
            self.graph_reader = data_helpers.PenmanReader()
        
        self.graph_standardizer = graph_standardizer
        if not self.graph_standardizer:
            from smatchpp import preprocess
            self.graph_standardizer = preprocess.AMRGraphStandardizer()

        self.graph_pair_preparer = graph_pair_preparer
        if not self.graph_pair_preparer:
            from smatchpp import preprocess
            self.graph_pair_preparer = preprocess.AMRGraphPairPreparer()
        
        self.triplematcher = triplematcher
        if not self.triplematcher:
            from smatchpp import score
            self.triplematcher = score.IDTripleMatcher()
        
        self.alignmentsolver = alignmentsolver
        if not self.alignmentsolver:
            from smatchpp import solvers
            self.alignmentsolver = solvers.get_solver("hillclimber")
        
        self.graph_aligner = graph_aligner
        if not self.graph_aligner:
            from smatchpp import align
            self.graph_aligner = align.GraphAligner(self.triplematcher, self.alignmentsolver)
        
        self.graph_scorer = graph_scorer
        if not self.graph_scorer:
            from smatchpp import score
            self.graph_scorer = score.AMRScorer(triplematcher=self.triplematcher)
        
        self.subgraph_extractor = subgraph_extractor
        if not self.subgraph_extractor:
            from smatchpp import subgraph_extraction
            self.subgraph_extractor = subgraph_extraction.SubGraphExtractor(add_instance=True)

        self.printer = printer
        if not self.printer:
            from smatchpp import eval_statistics
            self.printer = eval_statistics.ResultPrinter(score_type="micro", do_bootstrap=False, output_format="json")
        
        self.score_dimension = score_dimension
        if not self.score_dimension:
            self.score_dimension = "main"

        
    def process_pair(self, string_g1, string_g2):
        g1 = self.graph_reader.string2graph(string_g1)
        g2 = self.graph_reader.string2graph(string_g2)
        logger.debug("graph pair loaded,\n\nG1: {}\n\nG2: {}".format(g1, g2))
        g1 = self.graph_standardizer.standardize(g1)
        g2 = self.graph_standardizer.standardize(g2)
        logger.debug("graph pair standardized,\n\nG1: {}\n\nG2: {}".format(g1, g2))
        
        if self.score_dimension == "main":
            g1, g2, v1, v2 = self.graph_pair_preparer.prepare_get_vars(g1, g2)
            logger.debug("graph pair fully prepared,\n\nG1: {}\n\nG2: {}\n\nVar G1: {}\n\nVar G2: {}".format(g1, g2, v1, v2))
            alignment, varindex, status = self.graph_aligner.align(g1, g2, v1, v2)
            logger.debug("alignment computed: {}; varindex: {}".format(alignment, varindex))
            match = self.graph_scorer.main_scores(g1, g2, alignment, varindex)

        elif self.score_dimension == "all-onealign":
            g1, g2, v1, v2 = self.graph_pair_preparer.prepare_get_vars(g1, g2)
            logger.debug("graph pair fully prepared,\n\nG1: {}\n\nG2: {}\n\nVar G1: {}\n\nVar G2: {}".format(g1, g2, v1, v2))
            alignment, varindex, status = self.graph_aligner.align(g1, g2, v1, v2)
            logger.debug("alignment computed: {}; varindex: {}".format(alignment, varindex))
            match = self.graph_scorer.subtask_scores(g1, g2, alignment, varindex)

        elif self.score_dimension == "all-multialign":
            g1, g2, v1, v2 = self.graph_pair_preparer.prepare_get_vars(g1, g2)
            name_subgraph1 = self.subgraph_extractor.all_subgraphs_by_name(g1)
            name_subgraph2 = self.subgraph_extractor.all_subgraphs_by_name(g2)
            match = {}
            alignments = {}
            for name in name_subgraph1:
                g1t = name_subgraph1[name]
                g2t = name_subgraph2[name]
                g1t, g2t, v1t, v2t = self.graph_pair_preparer.prepare_get_vars(g1t, g2t)
                logger.debug("graph pair fully prepared,\n\nG1: {}\n\nG2: {}\n\nVar G1: {}\n\nVar G2: {}".format(g1t, g2t, v1t, v2t))
                alignment, varindex, status = self.graph_aligner.align(g1t, g2t, v1t, v2t)
                logger.debug("alignment computed: {}; varindex: {}".format(alignment, varindex))
                match[name] = self.graph_scorer.main_scores(g1, g2, alignment, varindex)["main"]
                alignments[name] = alignment 
            alignment = alignments
        logger.debug("match computed: {}".format(match))
        status = (status[0], min(len(g1), len(g2), status[1]))
        return match, status, alignment
    
    
    def process_corpus(self, amrs, amrs2):
        
        status = []
        match_dict = {}
        seconds = time.time() 
        for i, a in enumerate(amrs):
            match, tmpstatus, alx = self.process_pair(a, amrs2[i])
            status.append(tmpstatus)
            util.append_dict(match_dict, match)
            if (i + 1) % 100 == 0:
                logger.info("graph pairs processed: {}; time for last 100 pairs: {}".format(i + 1, time.time() - seconds))
                seconds = time.time()
        return match_dict, status

    
    def score_corpus(self, amrs, amrs2):
        
        match_dict, status = self.process_corpus(self, amrs, amrs2)
        
        final_result = None

        if self.printer.score_type == "pairwise":
            final_result = []
            for i in range(len(amrs)):
                match_dict_tmp = {k:[match_dict[k][i]] for k in match_dict.keys()}
                result = self.printer.get_final_result(match_dict_tmp)
                final_result.append(result)
        
        if self.printer.score_type == "macro":
            final_result = self.printer.get_final_result(match_dict)
        
        if self.printer.score_type == "micro":
            final_result = self.printer.get_final_result(match_dict)
        
        return final_result, status
