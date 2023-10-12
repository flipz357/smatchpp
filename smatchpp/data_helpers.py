import logging
from smatchpp import interfaces
from smatchpp import util

logger = logging.getLogger("__main__")


def read_amr_strings_from_file(filepath):

    with open(filepath, "r") as f:
        amrs_meta = f.read().split("\n\n")

    amrs = ["\n".join([l for l in am.split("\n") if not l.startswith("# ::")]) for am in amrs_meta]
    if not amrs[-1]:
        logger.debug("removing last line which is empty")
        amrs = amrs[:-1]
    return amrs


class PenmanReader(interfaces.GraphReader):

    def __init__(self):
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
        
        # collect tokens
        while True:
            
            if i == len(tokens):
                break
            
            # get current token
            tmp_token = tokens[i]
            if tmp_token[0] in ["\"","\'"]:
                
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
                    stringtok, incr = self._collect_string(tokens, i, stringsign=tmp_token[0])
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
                concept = tokens[i+2]
                 
                if concept[0] in ["\"", "\'"]:
                    concept, newincr = self._collect_string(tokens, i + 2, stringsign=concept[0])
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
        
        logging.debug("3. result after triple extract: {}".format(triples))
        return triples
    
    @staticmethod
    def _collect_string(tokens, start, stringsign="\""):
        
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


class TSVReader(interfaces.GraphReader):
    
    @staticmethod
    def _string2graph(string):

        triples = string.split("\n")
        triples = [tuple(triple.split()) for triple in triples]
        triples = [(triple[0], triple[2], triple[1]) for triple in triples]

        return triples
    

def get_reader(reader_name):

    if reader_name == "penman":
        return PenmanReader()

    if reader_name == "tsv":
        return TSVReader()
    
    raise NameError("reader name not known, available: penman, tsv")


class PenmanWriter(interfaces.GraphWriter):

    def __init__(self, hide_root=True, root_relation=":root"):
        self.hide_root = hide_root
        self.root_relation = root_relation

    def _graph2string(self, triples):
        
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
        triples = [t for t in triples if t[1] != ":instance"]
        triples = list(sorted(triples, key=lambda t:t[1]))
        return triples

    def _gather(self, triples, node, v2c, printed_triples):
        
        # get outgoing nodes and relations
        childs = util._get_childs(triples, node)
        childs = self._rel_sort(childs)

        #get incoming nodes and relations (that can be inverted with -of) 
        possible_childs = util._get_possible_childs(triples, node)
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
            if util._n_outgoing(triples, triple[2]) == 0:
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
