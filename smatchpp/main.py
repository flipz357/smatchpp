import argparse
import numpy as np
import time
from scipy.stats import pearsonr

def build_arg_parser():

    parser = argparse.ArgumentParser(
            description='amr')

    parser.add_argument('-a'
            , type=str
            , required=True
            , help='file path to first SemBank')

    parser.add_argument('-b'
            , type=str
            , required=True
            , help='file path to second SemBank')

    parser.add_argument('-log_level'
            , type=int
            , nargs='?'
            , default=40
            , choices=list(range(0, 60, 10))
            , help='logging level (int), see\
                    https://docs.python.org/3/library/logging.html#logging-levels')
      
    parser.add_argument('-score_type'
            , type=str
            , default="pairwise"
            , nargs='?'
            , choices=["micro", "macro", "pairwise", "micromacro"]
            , help='score type')
    
    parser.add_argument('-input_format'
            , type=str
            , default="pemman"
            , nargs='?'
            , choices=["tsv, penman"]
            , help='score type')
    
    parser.add_argument('-score_dimension'
            , type=str
            , default="main"
            , nargs='?'
            , choices=["main", "all-multialign", "all-onealign"]
            , help='main: returns Smatch Precision, F1, and Recall.\
                    all-multialign: returns Smatch scores for \
                                    multiple dimensions as captured by MR subgraphs \
                    all-onealign: same as "all-multialign" but uses one alignment as \
                            found by matching full MRs')
    
    parser.add_argument('-solver'
            , type=str
            , default="ilp"
            , nargs='?'
            , choices=["ilp", "hillclimber", "dummy", "rilp"]
            , help='alignment solver type: \
                        ilp: integer linear program \
                        hillclimber: hillclimber \
                        dummy: dummy alignment \
                        rilp: relaxed integer linear program (experimental)')
     
    parser.add_argument('--bootstrap'
            , action='store_true'
            , help='obtain confidence intervals, only possible if -score_type not pairwise')
    
    parser.add_argument('--lossless_graph_compression'
            , action='store_true'
            , help='shrinks alignment search space by removing  \
                    variables that are identified by a concept')
    
    parser.add_argument('--remove_duplicates'
            , action='store_true'
            , help='enable for removing duplicate triples, which makes sense for most cases')
     
    parser.add_argument('-edges'
            , default=None
            , nargs='?'
            , choices=["reify", "dereify"]
            , help='edge standardization: None, reification, or dereification \
                    E.g.: location(x, y) <-> instance(z, location) and arg1(z, x) and arg2(z,y)\
                    Here, <- is derieification, and -> reification')
    
    parser.add_argument('-output_format'
            , default='text'
            , nargs='?'
            , choices=["json", "text"]
            , help='output format \
                    json or text')

    return parser

def process_corpus(smatchppobject, amrs, amrs2):
    
    status = []
    match_dict = {}
    seconds = time.time() 
    for i, a in enumerate(amrs):
        match, tmpstatus, alx = smatchppobject.process_pair(a, amrs2[i])
        status.append(tmpstatus)
        util.append_dict(match_dict, match)
        if (i + 1) % 100 == 0:
            logger.info("graph pairs processed: {}; time for last 100 pairs: {}".format(i + 1, time.time() - seconds))
            seconds = time.time()
    return match_dict, status

class Smatchpp():

    def __init__(self, graph_reader=None, graph_standardizer=None, graph_pair_preparer=None,
                    triplematcher=None, alignmentsolver=None, graph_aligner=None, graph_scorer=None,
                    subgraph_extractor=None, printer=None, score_dimension=None):

        self.graph_reader = graph_reader
        if not self.graph_reader:
            import data_helpers
            self.graph_reader = data_helpers.PenmanReader()
        
        self.graph_standardizer = graph_standardizer
        if not self.graph_standardizer:
            import preprocess
            self.graph_standardizer = preprocess.AMRGraphStandardizer()

        self.graph_pair_preparer = graph_pair_preparer
        if not self.graph_pair_preparer:
            import preprocess
            self.graph_pair_preparer = preprocess.AMRGraphPreparer()
        
        self.triplematcher = triplematcher
        if not self.triplematcher:
            import score
            self.triplematcher = score.IDTripleMatcher()
        
        self.alignmentsolver = alignmentsolver
        if not self.alignmentsolver:
            import solvers
            self.alignmentsolver = solvers.get_solver("hillclimber")
        
        self.graph_aligner = graph_aligner
        if not self.graph_aligner:
            import align
            self.graph_aligner = align.Graphaligner(self.triplematcher, self.alignmentsolver)
        
        self.graph_scorer = graph_scorer
        if not self.graph_scorer:
            import score
            self.graph_scorer = score.AMRScorer(triplematcher=self.triplematcher)
        
        self.subgraph_extractor = subgraph_extractor
        
        self.printer = printer
        if not self.printer:
            import eval_statistics
            self.printer = eval_statistics.ResultPrinter(score_type="micro", do_boostrap=False, output_format="json")
        
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
            name_subgraph1 = subgraph_extractor.all_subgraphs_by_name(g1)
            name_subgraph2 = subgraph_extractor.all_subgraphs_by_name(g2)
            match = {}
            for name in name_subgraph1:
                g1 = name_subgraph1[name]
                g2 = name_subgraph2[name]
                g1, g2, v1, v2 = graph_pair_preparer.prepare_get_vars(g1, g2)
                logger.debug("graph pair fully prepared,\n\nG1: {}\n\nG2: {}\n\nVar G1: {}\n\nVar G2: {}".format(g1, g2, v1, v2))
                alignment, varindex, status = graph_aligner.align(g1, g2, v1, v2)
                logger.debug("alignment computed: {}; varindex: {}".format(alignment, varindex))
                match[name] = graph_scorer.main_scores(g1, g2, alignment, varindex)["main"]
                alignments[name] = alignment 
            alignment = alignments
        logger.debug("match computed: {}".format(match))
        return match, status, alignment

    def score_corpus(self, amrs, amrs2):
        
        match_dict, status = process_corpus(self, amrs, amrs2)
        
        final_result = None

        if self.printer.score_type == "pairwise":
            final_result = []
            for i in range(len(amrs)):
                match_dict_tmp = {k:[match_dict[k][i]] for k in match_dict.keys()}
                result = printer.get_result(match_dict_tmp, print_result=print_result)
                final_result.append(result)
        
        if self.printer.score_type == "macro":
            if self.score_type != "main":
                logger.warning("Cannot comply with current score type argument. Currently only main Smatch score available for macro statistics.")
            final_result = printer.get_final_result(match_dict, print_result=print_result)
        
        if self.printer.score_type == "micro":
            final_result = printer.get_final_result(match_dict, print_result=print_result)
        
        return final_result, status



if __name__ == "__main__":

    import log_helper

    args = build_arg_parser().parse_args()
    logger = log_helper.set_get_logger("smatchpp-logger", args.log_level)
    logger.info("loading amrs from files {} and {}".format(
        args.a, args.b))
    
    import data_helpers
    import solvers
    import preprocess
    import align
    import subgraph_extraction
    import score
    import eval_statistics
    import util
  
    amrs = data_helpers.read_amr_strings_from_file(args.a)
    amrs2 = data_helpers.read_amr_strings_from_file(args.b)
    
    assert len(amrs) == len(amrs2)

    logger.info("loading processing modules ...")
    graph_reader = data_helpers.get_reader(args.input_format)
    logger.info("1. Penman reader loaded")
    graph_standardizer = preprocess.AMRGraphStandardizer(edges=args.edges, remove_duplicates=args.remove_duplicates)
    logger.info("2. triple standardizer loaded")
    graph_pair_preparer = preprocess.AMRGraphPairPreparer(lossless_graph_compression=args.lossless_graph_compression)
    logger.info("3. graph pair processor loaded")
    triplematcher = score.IDTripleMatcher()
    logger.info("4a. triple matcher loaded")
    alignmentsolver = solvers.get_solver(args.solver)
    logger.info("4b. alignment solver loaded")
    graph_aligner = align.GraphAligner(triplematcher, alignmentsolver) 
    logger.info("4c. graph aligner loaded")

    if "all" in args.score_dimension:
        subgraph_extractor = subgraph_extraction.SubGraphExtractor(add_instance=True)
        logger.info("4c. sub graph extractor")
    
    
    graph_scorer = score.AMRScorer(triplematcher=triplematcher)
    logger.info("5. scorer loaded")
    logger.info("starting score calculations")
    
    printer = eval_statistics.ResultPrinter()
    seconds = time.time()

    SMATCHPP = Smatchpp(graph_reader=graph_reader, graph_standardizer=graph_standardizer, 
                        graph_pair_preparer=graph_pair_preparer, triplematcher=triplematcher,
                        alignmentsolver=alignmentsolver, graph_aligner=graph_aligner, 
                        graph_scorer=graph_scorer, printer=printer, score_dimension=args.score_dimension)

    if args.score_type == "micromacro":
        match_dict, status = process_corpus(SMATCHPP, amrs, amrs2)
        print("-------------------------------")
        print("-------------------------------")
        print("---------Micro scores----------")
        print("-------------------------------")
        print("-------------------------------")
        printer = eval_statistics.ResultPrinter(score_type="micro", do_bootstrap=args.bootstrap, output_format=args.output_format)
        printer.print_all(match_dict)
        print("-------------------------------")
        print("-------------------------------")
        print("---------Macro scores----------")
        print("-------------------------------")
        print("-------------------------------")
        if args.score_type != "main":
            logger.warning("Cannot comply with current score type argument. Currently only main Smatch score available for macro statistics.")
        match_dict = {"main": match_dict["main"]}
        printer = eval_statistics.ResultPrinter(score_type="macro", do_bootstrap=args.bootstrap, output_format=args.output_format)
        printer.print_all(match_dict)

    else:
        final_result_dic, status = SMATCHPP.score_corpus(amrs, amrs2)
        SMATCHPP.printer.print_all(final_result_dic)
    

    status_sum = [0.0, 0.0]
    non_optimal = 0
    for stat in status:
        status_sum[0] += stat[0]
        status_sum[1] += stat[1]
        if stat[1] - stat[0] > 1:
            non_optimal += 1

    logger.info("Finished.\
        Optimal status, lower & upper bound: {}\
        Pairs that do not have ensured optimal solution: {}".format(status_sum, non_optimal))
    
