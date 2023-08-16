import argparse
import time

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
            , default="penman"
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
     
    parser.add_argument('-syntactic_standardization'
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

if __name__ == "__main__":

    from smatchpp import log_helper

    args = build_arg_parser().parse_args()
    logger = log_helper.set_get_logger("smatchpp-logger", args.log_level)
    logger.info("loading amrs from files {} and {}".format(
        args.a, args.b))
    
    from smatchpp import data_helpers
    from smatchpp import solvers
    from smatchpp import preprocess
    from smatchpp import align
    from smatchpp import subgraph_extraction
    from smatchpp import score
    from smatchpp import eval_statistics
  
    amrs = data_helpers.read_amr_strings_from_file(args.a)
    amrs2 = data_helpers.read_amr_strings_from_file(args.b)
    
    assert len(amrs) == len(amrs2)

    logger.info("loading processing modules ...")
    graph_reader = data_helpers.get_reader(args.input_format)
    logger.info("1. Penman reader loaded")
    graph_standardizer = preprocess.AMRStandardizer(
                                        syntactic_standardization=args.syntactic_standardization, 
                                        remove_duplicates=args.remove_duplicates)
    logger.info("2. triple standardizer loaded")
    graph_pair_preparer = preprocess.AMRPairPreparer(lossless_graph_compression=args.lossless_graph_compression)
    logger.info("3. graph pair processor loaded")
    triplematcher = score.IDTripleMatcher()
    logger.info("4a. triple matcher loaded")
    alignmentsolver = solvers.get_solver(args.solver)
    logger.info("4b. alignment solver loaded")
    graph_aligner = align.GraphAligner(triplematcher, alignmentsolver) 
    logger.info("4c. graph aligner loaded")

    subgraph_extractor = None
    if "all" in args.score_dimension:
        subgraph_extractor = subgraph_extraction.SubGraphExtractor(add_instance=True)
        logger.info("4c. sub graph extractor")
    
    
    graph_scorer = score.AMRScorer(triplematcher=triplematcher)
    logger.info("5. scorer loaded")
    logger.info("starting score calculations")
    
    if args.score_type in ["micro", "macro"]:
        printer = eval_statistics.ResultPrinter(score_type=args.score_type, 
                                            do_bootstrap=args.bootstrap, 
                                            output_format=args.output_format)
    else:
        printer = eval_statistics.ResultPrinter(score_type=None, 
                                            do_bootstrap=args.bootstrap, 
                                            output_format=args.output_format)

    seconds = time.time()
    
    from smatchpp.bindings import Smatchpp

    SMATCHPP = Smatchpp(graph_reader=graph_reader, graph_standardizer=graph_standardizer, 
                        graph_pair_preparer=graph_pair_preparer, triplematcher=triplematcher,
                        alignmentsolver=alignmentsolver, graph_aligner=graph_aligner, 
                        graph_scorer=graph_scorer, printer=printer, score_dimension=args.score_dimension, 
                        subgraph_extractor=subgraph_extractor)

    if args.score_type == "micromacro":
        
        match_dict, status = SMATCHPP.process_corpus(amrs, amrs2)
        
        #get micro scores
        printer = eval_statistics.ResultPrinter(score_type="micro", do_bootstrap=args.bootstrap, output_format=args.output_format)
        final_result_dict_micro = printer.get_final_result(match_dict)
        
        #get macro scores
        printer = eval_statistics.ResultPrinter(score_type="macro", do_bootstrap=args.bootstrap, output_format=args.output_format)
        final_result_dict_macro = printer.get_final_result(match_dict)
        
        if args.output_format == "json":
            printer.print_all({"micro scores": final_result_dict_micro, "macro scores": final_result_dict_macro})
        else:
            print("-------------------------------")
            print("-------------------------------")
            print("---------Micro scores----------")
            print("-------------------------------")
            print("-------------------------------")
            printer.print_all(final_result_dict_micro)
            print("-------------------------------")
            print("-------------------------------")
            print("---------Macro scores----------")
            print("-------------------------------")
            print("-------------------------------")
            printer.print_all(final_result_dict_macro)

    elif args.score_type == "pairwise":
        final_result_list, status = SMATCHPP.score_corpus(amrs, amrs2)
        for singlepair in final_result_list:
            SMATCHPP.printer.print_all(singlepair, jsonindent=0)
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
    
