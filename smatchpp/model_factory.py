from smatchpp import preprocess
logger = logging.getLogger("__main__")

class StandardizerFactory:

    @classmethod
    def get_standardizer(string):
        if not string:
            graph_standardizer = preprocess.DoNothingStandardizer()
        if string == "amr":
            graph_standardizer = preprocess.AMRStandardizer(
                                    syntactic_standardization=args.syntactic_standardization,
                                    remove_duplicates=True)
        if string == "generic":
            graph_standardizer = preprocess.GenericStandardizer()

        else:
            raise NotImplementedError("Preprocessor for string {} not implemented".format(string))

        return graph_standardizer
        

class SubgraphExtractorFactory:

    @classmethod
    def get_standardizer(string):
        if string == "amr":
            subgraph_extractor = subgraph_extraction.AMRSubGraphExtractor(add_instance=True)
        else:
            raise NotImplementedError("Subgraph extraction for graph type {} not implemented".format(string))
        return graph_standardizer
