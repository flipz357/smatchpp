from smatchpp import data_helpers
import logging

logger = logging.getLogger("__main__")

class StandardizerFactory:

    @classmethod
    def get_standardizer(cls, uri):
        """Get an object than can standardize a graph according to a specific graph type

        Args:
            uri (string): uri/name for the graph type (e.g., amr)

        Returns:
            an object with a *standardize* function that maps a set of triples (graph) to
            another set of triples (graph)

        Raises:
            NotImplementedError: if the standardizer extractor type has not been implemented yet
        """
        
        if not uri:
            from smatchpp.formalism.generic import tools as generictools
            return generictools.DoNothingStandardizer()
        if uri == "amr":
            from smatchpp.formalism.amr import tools as amrtools
            return amrtools.AMRStandardizer()
        if uri == "generic":
            from smatchpp.formalism.generic import tools as generictools
            return generictools.GenericStandardizer()
        
        raise NotImplementedError("Preprocessor for uri {} not implemented".format(uri))

        
class SubgraphExtractorFactory:

    @classmethod
    def get_extractor(cls, uri):
        """Get an object than can extract subgraphs from a graph

        Args:
            uri (string): uri/name for the graph type (e.g., amr)

        Returns:
            an object with a *all_subgraphs_by_name* function that maps a set of triples (graph)
            to a dictionary where keys are subgraph types and values are sets of triples (subgraphs)

        Raises:
            NotImplementedError: if the subgraph extractor type has not been implemented yet
        """

        if uri == "amr":
            from smatchpp.formalism.amr import tools as amrtools
            return amrtools.AMRSubgraphExtractor()
        
        raise NotImplementedError("Subgraph extraction for graph type {} not implemented".format(uri))


class GraphReaderFactory:

    @classmethod
    def get_reader(cls, uri):
        """Get an object that can read a graph that is serialized as a string in a specific format

        Args:
            reader_name (string): uri/name for the reader

        Returns:
            a reader object that has a *string2graph* function

        Raises:
            NameError: if a reader has not been implemented yet
        """

        if uri == "penman":
            return data_helpers.PenmanReader()

        if uri == "tsv":
            return data_helpers.TSVReader()

        raise NotImplementedError("reader of name {} is not known, available: penman, tsv".format(uri))


class GraphWriterFactory:

    @classmethod
    def get_writer(cls, uri):
        """Get an object that can write a graph into a specific format

        Args:
            writer_name (string): uri/name for the writer

        Returns:
            a writer object that has a *graph2string* function

        Raises:
            NameError: if a writer has not been implemented yet
        """

        if uri == "penman":
            return data_helpers.PenmanReader()

        raise NotImplementedError("writer of name {} is not known, available: penman".format(uri))
