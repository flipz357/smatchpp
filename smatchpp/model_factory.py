from smatchpp import preprocess
from smatchpp import subgraph_extraction
import logging
logger = logging.getLogger("__main__")

class StandardizerFactory:

    @classmethod
    def get_standardizer(cls, string):
        
        if not string:
            graph_standardizer = preprocess.DoNothingStandardizer()
        elif string == "amr":
            graph_standardizer = preprocess.AMRStandardizer()
        elif string == "generic":
            graph_standardizer = preprocess.GenericStandardizer()
        else:
            raise NotImplementedError("Preprocessor for string {} not implemented".format(string))

        return graph_standardizer
        

class SubgraphExtractorFactory:

    @classmethod
    def get_extractor(cls, string):
        if string == "amr":
            subgraph_extractor = subgraph_extraction.AMRSubGraphExtractor(add_instance=True)
        else:
            raise NotImplementedError("Subgraph extraction for graph type {} not implemented".format(string))
        return subgraph_extractor
