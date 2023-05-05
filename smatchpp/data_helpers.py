import logging
import interfaces

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
        tmpsrc = {0: "ROOT"}
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
    

