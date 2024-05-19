import logging
from smatchpp import interfaces
from smatchpp import util

logger = logging.getLogger("__main__")


def read_graphstrings_from_file(filepath):

    with open(filepath, "r") as f:
        stringgraphs_meta = f.read().split("\n\n")

    stringgraphs = ["\n".join([l for l in sg.split("\n") if not l.startswith("# ::")]) for sg in stringgraphs_meta]
    if not stringgraphs[-1]:
        logger.debug("removing last line which is empty")
        stringgraphs = stringgraphs[:-1]
    return stringgraphs


class PenmanReader(interfaces.GraphReader):

    def __init__(self, explicate_root=True):
        self.explicate_root = explicate_root 
        return None

    def _string2graph(self, string):
        """Parses a Penman string to triples. 

            Tries to correctly extract as many triples as possible, 
            possibly also allowing some theoretically invalid/incomplete 
            graphs such as "(a / b :x (y / z)" which misses a final closing 
            bracket but would get parsed same as "(a / b :x (y / z))".
            
            Args:
                string (str): the string in Penman format

            Returns:
                a list with triples (src, rel, tgt)
        """
        logging.debug("parsing {}".format(string))
        string = self.__protect_brackets_inside_quotes(string)
        logging.debug("Protect brackets inside quotes {}".format(string))
        string = string.replace(")", " )")
        string = string.replace("(", "( ")
        logging.debug("1. brackets replaced {}".format(string))
        tokens = string.split()
        logging.debug("2. split {}".format(tokens))
        
        # prepare
        nested_level = 0
        i = 0
        tmpsrc = {0: "ROOT_OF_GRAPH"}
        tmprel = {0: ":root"}
        triples = []
        error_state = 0
        
        # collect tokens
        while True:
            
            if i == len(tokens):
                break
            
            try:
                # get current token
                tmp_token = tokens[i]
                
                if tmp_token[0] in ["\"", "\'"]:
                    
                    # start of a string constant -> collect string, increment i    
                    if tokens[i + 1] == "/":
                        # new var + instance 
                        #-> get var, get instance, get incoming relation, append triple

                        var = tokens[i]
                        concept = tokens[i + 2]
                        
                        tmpsrc[nested_level] = var
                        
                        triple = (var, ":instance", concept) 
                        triples.append(triple)
                        
                        triple = (tmpsrc[nested_level - 1], tmprel[nested_level - 1], var) 
                        triples.append(triple)

                        i += 3
                    
                    else:
                        # start of a string constant -> collect string, increment i
                        stringtok, incr = self.__collect_string(tokens, i, stringsign=tmp_token[0])
                        triple = (tmpsrc[nested_level], tmprel[nested_level], stringtok)
                        triples.append(triple)
                        i = incr + 1

                elif tokens[i] == "(":
                    # increase depth, nothing to collect
                    nested_level += 1
                    i += 1
                
                elif tokens[i] == ")":
                    # decrease depth, nothing to collect
                    nested_level -= 1
                    i += 1

                elif tokens[i].startswith(":"):
                    # relation -> update relation dict
                    tmprel[nested_level] = tokens[i]
                    i += 1

                elif tokens[i + 1] == "/":
                    # new var + instance 
                    #-> get var, get instance, get incoming relation, append triple

                    var = tokens[i]
                    concept = tokens[i + 2]
                     
                    if concept[0] in ["\"", "\'"]:
                        concept, newincr = self.__collect_string(tokens, i + 2, stringsign=concept[0])
                        i = newincr + 1
                    else:
                        i += 3

                    tmpsrc[nested_level] = var
                    
                    triple = (var, ":instance", concept) 
                    triples.append(triple)
                    
                    triple = (tmpsrc[nested_level - 1], tmprel[nested_level - 1], var) 
                    triples.append(triple)
                else:
                    # variable token without instance
                    #-> get var, get incoming relation, append triple
                    tgt = tokens[i]
                    
                    #adapt better to possibly redundant brackets
                    tmp_nested_level = nested_level
                    j = i - 1
                    while tokens[j] == "(":
                        tmp_nested_level -= 1
                        j -= 1

                    triple = (tmpsrc[tmp_nested_level], tmprel[tmp_nested_level], tgt) 
                    triples.append(triple)
                    i += 1
            except KeyError:
                error_state  = 1
                break

        # issue a warning if graph couldn't be read properly
        if error_state > 0:
            logger.warning("""This graph string seems broken, and I tried fixing it, 
                            extracting as much triples as possible, but larger graphs 
                            of the parts may be lost. No need to worry much now, but 
                            this exception should occur veeeeery rarely. \n\n 
                            Here's the graph that caused this problem: {} \n\n 
                            And here are the triples that I managed to extract: {}""".format(string, triples))

        # hypothetically it could be that a graph uses a relation ":root", 
        # but ":root" is preseverd as a special relation, so in the hypothetical
        # case we inform the user with a warning
        if len([t for t in triples if t[1] == ":root"]) > 1:
            first_root = True
            for i, triple in enumerate(triples):
                if triple[1] == ":root":
                    if first_root:
                        first_root = False
                    else:
                        triples[i] = (triple[0], triple[1] + "_but_not_the_graph_root", triple[2])

            logger.warning("""The graph contains an explicit relation \":root\", 
                            which is normally a special implicit relation. 
                            I have renamed all explicit \":root\" relations 
                            to \":root_but_not_the_graph_root\". Here's the graph 
                            that caused the problem {}""".format(string))
        if self.explicate_root == False:
            triples = [triple for triple in triples if triple[1] != ":root"]

        triples = self.__unprotect_brackets_inside_quotes(triples)
        logging.debug("3. result after triple extraction: {}".format(triples))
        return triples
    
    @staticmethod
    def __collect_string(tokens, start, stringsign="\""):
        
        attr = tokens[start]
        if attr[-1] == stringsign and len(attr) > 1:
            return attr, start
        
        if attr == stringsign and tokens[start+1] == ")":
            return attr, start
        
        for i, token in enumerate(tokens[start+1:]):
            attr += " " + token
            if token[-1] == stringsign:
                newi = start + i + 1
                return attr, newi
         
        return tokens[start], start
    
    @staticmethod
    def __protect_brackets_inside_quotes(string):
        newstring = []
        in_double_quote = False
        in_single_quote = False
        for i, char in enumerate(string):
            if char == "\"":
                if not in_double_quote and string[i:].count("\"") == 1:
                    newstring.append(char)
                    continue
                in_double_quote = not in_double_quote
                newstring.append(char)
                continue
            if char == "\'":
                if not in_double_quote and string[i:].count("\'") == 1:
                    newstring.append(char)
                    continue
                if not in_double_quote:
                    in_single_quote = not in_single_quote
                newstring.append(char)
                continue
            if in_double_quote == in_single_quote == False:
                newstring.append(char)
                continue
            if char == "(":
                newstring.append("<ENCLOSED_LBR>")
                continue
            if char == ")":
                newstring.append("<ENCLOSED_RBR>")
                continue
            newstring.append(char)
        return "".join(newstring)
    
    @staticmethod
    def __unprotect_brackets_inside_quotes(triples):
        newtriples = []
        def f(s):
            s = s.replace("<ENCLOSED_LBR>", "(").replace("<ENCLOSED_RBR>", ")")
            return s
        newtriples = [(f(src), rel, f(tgt)) for src, rel, tgt in triples]
        return newtriples



class TSVReader(interfaces.GraphReader):
    
    @staticmethod
    def _string2graph(string):

        triples = string.split("\n")
        triples = [tuple(triple.split()) for triple in triples]
        triples = [(triple[0], triple[2], triple[1]) for triple in triples]

        return triples


class GoodmamiPenmanReader(interfaces.GraphReader):
    
    def __init__(self):
        try:
            import penman as gmpm
            self.gmpm = gmpm
        except ModuleNotFoundError:
            print("please install goodmami's penman reader to use this class: https://github.com/goodmami/penman")
    
    def _string2graph(self, string):
        triples = self.__read_with_gmpm(string)
        return triples
    
    def __read_with_gmpm(self, string):
        g = self.gmpm.decode(string)
        triples = g.triples
        r = ("ROOT_OF_GRAPH", ":root", triples[0][0])
        triples = [r] + list(triples)
        return triples


class PenmanWriter(interfaces.GraphWriter):

    def __init__(self, hide_root=True, root_relation=":root"):
        self.hide_root = hide_root
        self.root_relation = root_relation

    def _graph2string(self, triples):
        """Prepeates and then calls recursive function to 
           build a string version / serialization of a DAG ("Penman")

        Args:
            triples: the graph
        Returns:
            a string that contains a graph serialization in the Penman style
        """
        
        # preparation, maybe remove explicit root triplet
        v2c = util.get_var_concept_dict(triples)
        root = [t for t in triples if t[1] == self.root_relation][0]
        if root[0] in v2c:
            root = root[0]
        elif root[2] in v2c:
            root = root[2]
        if self.hide_root:
            triples = [t for t in triples if t[1] != ":root"]
        v2c = util.get_var_concept_dict(triples)

        # build string via recursion
        string = "(" + root + " / " + v2c.pop(root) + self._gather(triples, root, v2c, printed_triples=set()) + ")"
        return string
    
    @staticmethod
    def _rel_sort(triples):
        """sort all edges alphabetically according to edge labels"""
        triples = [t for t in triples if t[1] != ":instance"]
        triples = list(sorted(triples, key=lambda t:t[1]))
        return triples

    def _gather(self, triples, node, v2c, printed_triples):
        """Recursive function to build a string version / serialization of a DAG ("Penman")

        Args:
            triples: the graph
            node: the current node
            v2c: mapping from variables to concepts
            printed_triples: the triples that have already been treated

        Returns:
            a string that contains a graph serialization in the Penman style
        """
        
        # get outgoing nodes and relations
        childs = self._get_triples_where_node_is_child(triples, node)
        childs = self._rel_sort(childs)

        #get incoming nodes and relations (that can be inverted with -of) 
        possible_childs = self._get_triples_where_node_could_be_made_child(triples, node)
        possible_childs = self._rel_sort(possible_childs)
        
        # temporary string
        tmpstring = ""

        # iteratate over outgoing
        for triple in childs:
            
            # maybe we have considered this triple already
            if triple in printed_triples:
                continue
            
            printed_triples.add(triple)
            
            tmprel = triple[1] 
            tmptarget = triple[2]
            
            # if the target node is a variable
            if tmptarget in v2c:

                # we remember that and get its concept
                concept = v2c.pop(tmptarget)

                # introduce a new subgraph
                tmpstring += " " + tmprel + " (" + tmptarget + " / " + concept + self._gather(triples, tmptarget, v2c, printed_triples) + ")"

            # if it's a variable but we've already seen it, we don't need to start a new subgraph
            elif tmptarget in util.get_var_concept_dict(triples):
                tmpstring += " " + tmprel + " " + tmptarget 
            
            # otherwise it's a constant node or string
            else:
                tmpstring += " " + tmprel + " " + tmptarget + self._gather(triples, tmptarget, v2c, printed_triples)
        
        # iteratate over incoming that can be inverted 
        for triple in possible_childs:
            
            # maybe we have considered this triple already
            if triple in printed_triples:
                continue

            # maybe it's a leaf then it makes no sense to invert
            if util.n_outgoing(triples, triple[2]) == 0:
                continue
            printed_triples.add(triple)

            # let's try an inversion
            tmprel = triple[1]
            if "-of" in tmprel:
                tmprel = tmprel.replace("-of","")
            else:
                tmprel += "-of"
            tmptarget = triple[0]

            # see above
            if tmptarget in v2c:
                concept = v2c.pop(tmptarget)
                tmpstring += " " + tmprel + " (" + tmptarget + " / " + concept + self._gather(triples, tmptarget, v2c, printed_triples) + ")"
            elif tmptarget in util.get_var_concept_dict(triples):
                tmpstring += " " + tmprel + " " + tmptarget 
            else:
                tmpstring += " " + tmprel + " " + tmptarget + self._gather(triples, tmptarget, v2c, printed_triples)
        
        return tmpstring 
    
    
    @staticmethod
    def _get_triples_where_node_is_child(triples, node):
        """Get all triples where node is the source

        Args:
            triples: the graph
            node: the node

        Returns:
            list with triples
        """
        childs = []
        for tr in triples:
            if tr[0] == node:
                childs.append(tr)
        return childs

    
    @staticmethod
    def _get_triples_where_node_could_be_made_child(triples, node):
        """Get all triples where node is the target

        These triples are incoming relations, but could be converted
        in linearization to outgoing relations, via "-of"

        Args:
            triples: the graph
            node: the node

        Returns:
            list with triples that could be inverted to make the source a child of node
        """
        childs = []
        for tr in triples:
            if tr[2] == node:
                childs.append(tr)
        return childs


class TSVWriter(interfaces.GraphWriter):
    
    @staticmethod
    def _graph2string(triples): 
        string = "\n".join(["\t".join((t[0], t[2], t[1])) for t in triples])
        return string

