from collections import defaultdict
import logging
from smatchpp import util
from smatchpp import interfaces
from smatchpp import graph_transforms

logger = logging.getLogger("__main__")


class DoNothingStandardizer(interfaces.GraphStandardizer):

    @staticmethod
    def _standardize(triples):
        return triples


class GenericStandardizer(interfaces.GraphStandardizer):
    """Class for generic graph standardization

       We apply the following steps
       
       1. Lower Casing
       ------------
       We lower case everything, e.g. (x, op1, "Obama") -> (x, op1, "obama"). 
       We presume that lower-uppercasing doesn't change the meaning.
       
       2. Remove Quotes
       -------------
       We remove quotes e.g. (x, op1, "Obama") -> (x, op1, Obama). This often makes sense since some graphs
       have quotes with ' and other with ", and we presume it makes no difference
       
       3. Reindex nodes
       -------------
       We relabel variable names / node indeces. It is a useful standardization for all graphs. It prevents
       that there are node labels that are the same as node indexes.

       4. Deinvert edges
       --------------
       We deinvert edges, e.g. (x, a-of, y) -> (y, a, x). Makes sense as a standardization, Penman uses inversion 
       only to facilitate string serialization, so relations should be deinverted.
       So this makes sense for penman graphs in general.
    """

    def __init__(self):
        return None

    @staticmethod
    def _standardize(triples):
        """Triple standardization according to parameters specified in init"""

        triples = list(triples)
        logging.debug("standardizing triples")
        logging.debug("This is the input graph: {}".format(triples))
        triples = graph_transforms.lower_all_labels(triples)
        triples = graph_transforms.remove_quotes_from_triples(triples)
        graph_transforms.relabel_vars(triples)
        graph_transforms.deinvert_e(triples)

        return triples
