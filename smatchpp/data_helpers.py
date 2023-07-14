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
        """ Parses a Penman string to triples

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
                    concept = tokens[i+2]
                    
                    tmpsrc[nested_level] = var
                    
                    triple = (var, ":instance", concept) 
                    triples.append(triple)
                    
                    triple = (tmpsrc[nested_level-1], tmprel[nested_level-1], var) 
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
                
                tmpsrc[nested_level] = var
                
                triple = (var, ":instance", concept) 
                triples.append(triple)
                
                triple = (tmpsrc[nested_level-1], tmprel[nested_level-1], var) 
                triples.append(triple)

                i += 3

            else:
                # variable token without instance
                #-> get var, get incoming relation, append triple
                tgt = tokens[i]
                triple = (tmpsrc[nested_level], tmprel[nested_level], tgt) 
                triples.append(triple)
                i += 1

        logging.debug("3. result after triple extract: {}".format(triples))
        return triples

    def _collect_string(self, tokens, start, stringsign="\""):
        
        attr = tokens[start]
        if attr[-1] == stringsign and len(attr) > 1:
            return attr, start
        
        if attr == stringsign and tokens[start+1] == ")":
            return attr, start
        
        for i, token in enumerate(tokens[start+1:]):
            attr += token
            if token[-1] == stringsign:
                newi = start + i + 1
                return attr, newi
        
        return tokens[start], start


class TSVReader(interfaces.GraphReader):

    def _string2graph(self, string):

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
        newtriples = []
        if self.hide_root:
            triples = [t for t in triples if t[1] != ":root"]
        v2c = util.get_var_concept_dict(triples)

        # build string via recursion
        string = "(" + root + " / " + v2c.pop(root) + self._gather(triples, root, v2c, printed_triples=set()) + ")"
        return string
        
    def _rel_sort(self, triples):
        triples = [t for t in triples if t[1] != ":instance"]
        triples = list(sorted(triples, key=lambda t:t[1]))
        return triples

    def _gather(self, triples, node, v2c, printed_triples):
        
        # get outgoing nodes and relations
        childs = self._get_childs(triples, node)
        childs = self._rel_sort(childs)

        #get incoming nodes and relations (that can be inverted with -of) 
        possible_childs = self._get_possible_childs(triples, node)
        possible_childs = self._rel_sort(possible_childs)
        
        # temporary string
        tmpstring = ""

        # iteratate over outgoing
        for triple in childs:
            
            # maybe we have considered this triple already
            if triple in printed_triples:
                continue
            
            printed_triples.add(triple)
            
            tmpsrc = triple[0]
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
            if self._n_outgoing(triples, triple[2]) == 0:
                continue
            printed_triples.add(triple)

            # let's try an inversion
            tmpsrc = triple[2]
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

    def _get_childs(self, triples, node):
        childs = []
        for tr in triples:
            if tr[0] == node:
                childs.append(tr)
        return childs
    
    def _get_possible_childs(self, triples, node):
        childs = []
        for tr in triples:
            if tr[2] == node:
                childs.append(tr)
        return childs

    def _n_incoming(self, triples, node):
        n = 0
        for tr in triples:
            if tr[2] == node:
                n += 1
        return n
    
    def _n_outgoing(self, triples, node):
        n = 0
        for tr in triples:
            if tr[0] == node:
                n += 1
        return n




