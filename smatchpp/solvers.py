import time
import logging
from random import shuffle
logger = logging.getLogger("__main__")
import numpy as np
import sys
from collections import Counter
import interfaces
import util

def get_solver(identifier_string):

    if identifier_string == "hillclimber":
        return HillClimber()

    if identifier_string == "ilp":
        return ILP()

    if identifier_string == "dummy":
        return DummySolver()
    
    if identifier_string == "rilp":
        return RILPHC()
    
 
    raise NotImplementedError(
            "please implement the solver you spcified: \"{}\"".format(identifier_string))


class DummySolver(interfaces.Solver):

    def __init__(self):
        return None

    def _solve(self, unarymatch_dict, binarymatch_dict, V):

        mat = np.zeros(V)
        for i in range(mat.shape[0]):
            mat[i] = i

        return mat, 10000000, 0.0


class HillClimber(interfaces.Solver):
    """Class that solves alignment problems with hill-climbing

        Attributes:
            rand_inits (int): how many random restarts? More restarts
                              make better optima more likely
    """

    def __init__(self, rand_inits=4):
        self.rand_inits = rand_inits
        return None
 
    def _score(self, alignmat, unarymatch_dict, binarymatch_dict):
        """Score an alignment candidate

            Args:
                alignmat (2d array): alignments from V to V'
                unarymatch_dict (dict): scores of unary alignments 
                binarymatch_dict (dict->dict): scores of binary alignments

            Returns:
                score (float)
        """
        
        sc = 0.0 
         
        V = range(alignmat.shape[0])
        
        for i in V:
            j = alignmat[i]
            sc += unarymatch_dict[(i, j)]
        
        
        for i in V:
            j = alignmat[i]
            if not binarymatch_dict[(i, j)]:
                continue
            for k in V:
                l = alignmat[k]
                sc += binarymatch_dict[(i, j)][(k, l)]
        return sc
    
    def _gain_of_switch(self, amaxs, unarymatch_dict, binarymatch_dict, i, j, k, l):
        """Compute gain of a switch candidate

            Args:
                amaxs (array): alignment from V to V'
                unarymatch_dict (dict): scores of unary alignments 
                binarymatch_dict (dict->dict): scores of binary alignments
                i, j, k, l (int, int, int, int): switches (i->j --> i->l); (k->l --> k->j)

            Returns:
                gain of switch (may be negative)
        """
        
        # construct new candidate
        amaxs_new = amaxs.copy()
        amaxs_new[[i, k]] = amaxs[[k, i]]

        # subtract unary malus from old alignment 
        malus = -unarymatch_dict[(i, j)]
        malus -= unarymatch_dict[(k, l)] 

        # add unary bonus from new alignment
        bonus = unarymatch_dict[(i, l)]
        bonus += unarymatch_dict[(k, j)]
        
        
        # add binary match bonus from new alignment
        if (i, l) in binarymatch_dict:
            for key in binarymatch_dict[(i, l)]:
                if amaxs_new[key[0]] == key[1]:
                    bonus += binarymatch_dict[(i, l)][key] * 2

        if (k, j) in binarymatch_dict:
            for key in binarymatch_dict[(k, j)]:
                if amaxs_new[key[0]] == key[1]:
                    bonus += binarymatch_dict[(k, j)][key] * 2

        # subtract binary match malus from old alignment
        if (i, j) in binarymatch_dict:
            for key in binarymatch_dict[(i, j)]:
                if amaxs[key[0]] == key[1]:
                    malus -= binarymatch_dict[(i, j)][key] * 2

        if (k, l) in binarymatch_dict:
            for key in binarymatch_dict[(k, l)]:
                if amaxs[key[0]] == key[1]:
                    malus -= binarymatch_dict[(k, l)][key] * 2
               
        """ 
        if (i, l) in binarymatch_dict:
            bonus += sum([binarymatch_dict[(i, l)][key] for key in binarymatch_dict[(i, l)] if key[1] == amaxs_new[key[0]]]) * 2
        if (k, j) in binarymatch_dict:
            bonus += sum([binarymatch_dict[(k, j)][key] for key in binarymatch_dict[(k, j)] if key[1] == amaxs_new[key[0]]]) * 2
        if (i, j) in binarymatch_dict:
            malus -= sum([binarymatch_dict[(i, j)][key] for key in binarymatch_dict[(i, j)] if key[1] == amaxs[key[0]]]) * 2
        if (k, l) in binarymatch_dict:
            malus -= sum([binarymatch_dict[(k, l)][key] for key in binarymatch_dict[(k, l)] if key[1] == amaxs[key[0]]]) * 2
        """
        #print(bonus, malus)
        
        # cumulative gain 
        gain = bonus + malus

        return gain


    def _get_best_switch(self, alignmat, unarymatch_dict, binarymatch_dict, nogains={}):
        """This tries out candidates and selects the one with best possible gain

            Args:
                alignmat (2d array): alignment from V to V'
                unarymatch_dict (dict): scores of unary alignments 
                binarymatch_dict (dict->dict): scores of binary alignments

            Returns:
                alignmat (2d array)
                gain (float)
                found_better (Bool), this is true if the returned alignmat differs
        """
       
        # intialize
        best_gain = 0.0
        best_candidate = None
        V = range(alignmat.shape[0])

        pos_gains = []
         
        # iterate over i->j alignments
        for i, j in enumerate(alignmat):
            j = alignmat[i]

            # iterate over k->l alignments
            for k  in V:
                
                # no neeed to check twice
                if k >= i:
                    break
                
                l = alignmat[k] 
                
                
                if (i, j, k, l) in nogains:
                    continue
                # if we can't get any improvement at all by swap, no need to do anything
                if (i, l) not in unarymatch_dict and (k, j) not in unarymatch_dict and binarymatch_dict[(i, l)] == 0 and  binarymatch_dict[(k, j)] == 0:
                    nogains[(i, j, k, l)] = True
                    nogains[(k, l, i, j)] = True
                    continue
                
                # compute gain of switch, i.e. i->j --> i -> l and k-> l --> k->j
                switch = (i, j, k, l)
                tmp_gain = self._gain_of_switch(alignmat, unarymatch_dict, binarymatch_dict, *switch)
                if tmp_gain > 0.0:
                    pos_gains.append((i, k, tmp_gain))

                # if gain better than best gain found, save
                if tmp_gain > best_gain:
                    best_gain = tmp_gain
                    best_candidate = (i, k)

        found_better = bool(best_candidate)
        #print(pos_gains)
        # we're at a peak
        if not found_better:
            return alignmat, best_gain, False, nogains
        #print(len(nogains))
        # a better alignment was found

        pos_gains = sorted(pos_gains, key=lambda x:x[2], reverse=True)
        #print([(i, j) for i, j, _ in pos_gains])
        switches = []
        for idx, (i, k, _) in enumerate(pos_gains):
            if idx == 0:
                i, k = best_candidate 
                switches.append((i, k))
                #alignmat[[i, k]] = alignmat[[k, i]]
            else:
                #break
                #i, k = next_best
                j, l = alignmat[i], alignmat[k]
                conflict = False
                for tup in switches:
                    i2, k2 = tup[0], tup[1]
                    j2, l2 = alignmat[i2], alignmat[k2]

                    if [i for i in tup if i in pos_gains[idx]]:
                        conflict = True
                        break
                    if binarymatch_dict[(i2, l2)] and binarymatch_dict[(i2, l2)][(i, j)] > 0.0:
                        conflict = True
                    if binarymatch_dict[(k2, j2)] and binarymatch_dict[(k2, j2)][(i, j)] > 0.0:
                        conflict = True
                    if binarymatch_dict[(i2, l2)] and binarymatch_dict[(i2, l2)][(k, l)] > 0.0:
                        conflict = True
                    if binarymatch_dict[(k2, j2)] and binarymatch_dict[(k2, j2)][(k, l)] > 0.0:
                        conflict = True
                    
                    if binarymatch_dict[(i2, k2)] and binarymatch_dict[(i2, k2)][(i, j)] > 0.0:
                        conflict = True
                    if binarymatch_dict[(k2, l2)] and binarymatch_dict[(k2, l2)][(i, j)] > 0.0:
                        conflict = True
                    if binarymatch_dict[(i2, k2)] and binarymatch_dict[(i2, k2)][(k, l)] > 0.0:
                        conflict = True
                    if binarymatch_dict[(k2, l2)] and binarymatch_dict[(k2, l2)][(k, l)] > 0.0:
                        conflict = True
                
                if not conflict:
                    switches.append((i, k))
                #print(conflict)
        #print(switches)#, pos_gains)
        for i, k in switches:
            alignmat[[i, k]] = alignmat[[k, i]]

        """
        i, k = best_candidate 
        alignmat[[i, k]] = alignmat[[k, i]]
        """
        return alignmat, best_gain, found_better, nogains

    
    def _solve(self, unarymatch_dict, binarymatch_dict, V):
        """This tries out candidates and selects the one with best possible gain

            Args:
                alignmat (2d array): alignment from V to V'
                unarymatch_dict (dict): scores of unary alignments 
                V (int): max(nodes V, nodes V')

            Returns:
                alignmat (2d array): best alignmat found
        """
        
        max_score = 0.0
        alignmat_best = None
        
        # little pre-processing
        wd = Counter()
        tx = time.time()
        for a, b, c, d in binarymatch_dict:
            if (a, b) not in wd:
                wd[(a, b)] = Counter()
            wd[(a, b)][(c, d)] = binarymatch_dict[(a, b, c, d)]
        
        binarymatch_dict = wd
        
        #alignment_collects = []
        #alignment_scores = []
        
        # iterate over random inits
        for init in range(self.rand_inits):
            
            #init random alignmat
            alignmat = np.zeros(V, dtype=int)
            aligned = set()
            for i in range(alignmat.shape[0]):
                idxs = [x for x in list(range(V)) if x not in aligned]
                if not idxs:
                    continue
                shuffle(idxs)
                j = idxs[0]
                alignmat[i] = j
                aligned.add(j)

            # init best alignmat found
            if init == 0:
                alignmat_best = alignmat
                max_score = self._score(alignmat, unarymatch_dict, binarymatch_dict)
            
            logger.debug("initialized alignment matrix:\n{}".format(alignmat))
            logger.debug("initial score: {}... starting climbing".format(max_score))
 
            alignmat, score, _ = self._climb(unarymatch_dict, binarymatch_dict, V, alignmat)
            
            #alignment_collects.append(str(alignmat))
            #alignment_scores.append(str(score))
            
            # if solution from this init better than last inits, save
            if score > max_score:
                logger.debug("new high score over candidates and inits: {}...".format(score))
                max_score = score
                alignmat_best = alignmat
        #print(str(len(set(alignment_collects))/len(alignment_collects)) + "\t" + str(len(set(alignment_scores))/len(alignment_scores)) + "\t" + str(len(alignmat_best)))
        
        # lower bound
        max_score = self._score(alignmat_best, unarymatch_dict, binarymatch_dict)
        
        # return solution, lowe bound, upp bound
        return alignmat_best, max_score, 10000000

    def _climb(self, unarymatch_dict, binarymatch_dict, V, alignmat):
        """This tries out candidates and selects the one with best possible gain

            Args:
                alignmat (2d array): alignment from V to V'
                unarymatch_dict (dict): scores of unary alignments 
                V (int): max(nodes V, nodes V')

            Returns:
                alignmat (2d array): best alignmat found
        """ 

        # init best alignmat found
        logger.debug("initialized alignment matrix:\n{}".format(alignmat))
        score = self._score(alignmat, unarymatch_dict, binarymatch_dict)
        logger.debug("initial score: {}... starting climbing".format(score))

        iters = 0    
        
        # hill-climbing
        nogains = {}
        while True:

            # search best switch
            result = self._get_best_switch(alignmat, unarymatch_dict, binarymatch_dict, nogains)
            
            new_mat, new_gain, found_better, nogains = result
            
            if found_better == False:
                # We're at a (local) optimum
                break
            # save current
            logger.debug("new gain for candidate: {}...".format(new_gain))
            alignmat = new_mat
            score += new_gain 
            iters += 1
            #print(iters, score)
            if iters > 1000:
                logger.warning("hillclimber stopped after 1000 iterations. \
                                This may be due to a bug or very large graph")
                break


        # lower bound
        score = self._score(alignmat, unarymatch_dict, binarymatch_dict)
        
        return alignmat, score, 10000000


class ILP(interfaces.Solver):
    """Class that solves alignment problem with ILP

        Attributes:
            max_seconds (int): time limit
            backup_solver (solver object): if no optimal aligmment is found in time
                                            use this solver as backup (default=None)
    """

    def __init__(self, max_seconds=240, backup_solver=None):
        
        self.max_seconds = max_seconds
        self.backup_solver = backup_solver
        
        try:
            import mip
            self.mip = mip
        except ModuleNotFoundError:
            raise ModuleNotFoundError("Module mip not found, please install mip \
                                       we used version 1.13.0")
        return None

    def _solve(self, unarymatch_dict, binarymatch_dict, V):
        
        # init model
        model = self.mip.Model()
        model.verbose = 0
        model.preprocess = -1
        model.max_seconds = self.max_seconds
        
        # some short cuts 
        ux = unarymatch_dict
        bx = binarymatch_dict
        Vr = range(V)
        
        # init binary alignment vars
        x = [[model.add_var(var_type=self.mip.BINARY) for i in Vr] for j in Vr]
        
        # init binary match vars for binary structural matches
        y = {}
        for (i, j, k, l) in bx:
            y[(i, j, k, l)] = model.add_var(var_type=self.mip.BINARY)
        
        # set model objective
        model.objective = self.mip.maximize(
                self.mip.xsum(ux[(i, j)] * x[i][j] for i in Vr for j in Vr) 
                + self.mip.xsum(bx[(i, j, k, l)]*y[(i, j, k, l)] for (i, j, k, l) in bx))
        

        # constraints: every var must be aligned only to one other var (or remain unaligned)
        for i in Vr:
            model += self.mip.xsum(x[i][j] for j in Vr) <= 1

        for i in Vr:
            model += self.mip.xsum(x[j][i] for j in Vr) <= 1

        # binary structural match constraint, i.e., if two vars are not aligned, all involved
        # struct matches must be zero
        for (i, j, k, l) in bx.keys():
            model += y[(i, j, k, l)] <= x[i][j]
            model += y[(i, j, k, l)] <= x[k][l]
    
        # optimizing
        status = model.optimize(max_seconds=self.max_seconds, relax=False)
        
        # checking if a solution was found, and return result
        if model.num_solutions:
            logger.debug("alignment with value {} found".format(model.objective_value))
            alignmat = np.array([x[i][j].x for i in Vr for j in Vr]).reshape((V, V))
            alignmat = util.alignmat_compressed(alignmat)
            return alignmat, model.objective_value, model.objective_bound
        
        logger.warning("not one good alignment found in reasonbable time ({} secs), falling back on backup \
                solver, consider increasing alignment time or ignore".format(self.max_seconds))
        
        # if no solution was found and no backup solver stated, use relaxed program
        if self.backup_solver is None: 
            logger.warning("no optimal alignment found, falling back on default relaxed LP")
            status = model.optimize(max_seconds=5, relax=True)
            if model.num_solutions:
                logger.debug("alignment with value {} found".format(model.objective_value))
                alignmat = np.array([x[i][j].x for i in Vr for j in Vr]).reshape((V, V))
                alignmat = util.alignmat_compressed(alignmat)
                return alignmat, model.objective_value, model.objective_bound
     
        logger.warning("no optimal alignment found, using backup solver")
        # no solution was found return solution from backupsolver
        return self.backup_solver.solve(unarymatch_dict, binarymatch_dict, V)
        



########################################################################
########################################################################
# What follows are experimental relaxed iterative ILP solvers.         #
# They should provide optimal result in polynomial time or can provide #
# intermediate solution with upper-bound                               ä
########################################################################
########################################################################

class RILP(interfaces.Solver):

    def __init__(self, max_seconds=15):
        
        try:
            import sparse
            self.sparse = sparse
        except ModuleNotFoundError:
            logger.critical("please install sparse (e.g., 0.13.0) \
                    for using this class... exiting...")
            sys.exit(1)

        try:
            from scipy import optimize
            self._optimize = optimize
        except ModuleNotFoundError:
            logger.critical("please install scipy (e.g., 1.7.3) \
                    for using this class... exiting...")
            sys.exit(1)

        self.max_seconds = max_seconds

    def _eval_problem(self, candidate_map, ys, unarymatch_dict, binarymatch_dict, lmps=None):
         
        su = 0.0
        sb = 0.0
        amaxs = np.argmax(candidate_map, axis=1)
        
        for i in range(amaxs.shape[0]):
            j = amaxs[i]
            su += unarymatch_dict[i, j]     
        
        if lmps is not None:
            sb += (binarymatch_dict * ys + lmps * ys).sum()
        else:
            sb += (binarymatch_dict * ys).sum()
        s = su + sb
        return s 
        

    def _dim_reduce_weight(self, i, j, n, binarydata, lmps):
            
        keyx = dict()
        keyy = dict()
        x = 0
        y = 0
        weight_k_l = np.zeros((n,n))
        for k, l in binarydata[(i, j)].keys():
            weight_k_l[k, l] = binarydata[(i, j)][(k, l)] + lmps[(i, j, k, l)]
            
            if k not in keyx:
                keyx[k] = x
                x += 1
                
            if l not in keyy:
                keyy[l] = y
                y += 1
            
        dim = max(x, y)  
        reduced_weight = np.zeros((dim, dim))
        for k, l in binarydata[(i, j)].keys():
            x = keyx[k]
            y = keyy[l]
            val = weight_k_l[k, l]
            reduced_weight[x, y] = val

        return reduced_weight, dim
    
    def _solve_relaxed_with_max_match(self, n, unarydata, binarydata, lmps):
         
        profit_i_j = np.zeros((n, n))
        lmps = Counter(lmps.asformat("dok").data)
        
        co = 0
        
        for i, j in binarydata.keys():
             
            reduced_weight, dim = self._dim_reduce_weight(i, j, n, binarydata, lmps)
            matchingx = self._optimize.linear_sum_assignment(reduced_weight, maximize=True)
            _, sum_weightx = self._get_candidate_map_from_matching(matchingx, reduced_weight, dim)
            profit_i_j[i, j] = sum_weightx        
            profit_i_j[i, j] += unarydata[(i, j)]       
            co += 1
        
        for i, j in unarydata.keys() - binarydata.keys():
            profit_i_j[i, j] += unarydata[(i, j)] 
        
        matching = self._optimize.linear_sum_assignment(profit_i_j, maximize=True)
        cm, sum_weight = self._get_candidate_map_from_matching(matching, profit_i_j, n)
     
        candidate_map = cm
        
        return candidate_map


    def _complete_struct(self, cm, unarymatch_dict, binarymatch_dict, lmps=None):
        n = unarymatch_dict.shape[0]
        
        ys = self.sparse.DOK((n, n, n, n)).to_coo()
        if lmps is not None:
            w = binarymatch_dict + lmps #*lmps
        else:
            w = binarymatch_dict.copy()
        
        marker = w > 0
        
        ys = self.sparse.where(marker, 1, ys) 
        
        if lmps is not None:
            ys = ys.transpose((2, 3, 0, 1)) * cm 
            ys = ys.transpose((2, 3, 0, 1)) 
        
        if lmps is None:
            ys = ys.transpose((2, 3, 0, 1)) * cm 
            ys = ys.transpose((2, 3, 0, 1)) 
            ys *= cm
        
        return ys
    
    def _get_candidate_map_from_matching(self, matching, weight_mat, n):
        sum_weight = 0.0
        candidate_map = np.zeros((n, n))
        for n1, n2 in zip(*matching):
            weight = weight_mat[n1, n2]
            sum_weight += weight
            candidate_map[n1, n2] = 1
        return candidate_map, sum_weight

    def _adapt_lmps(self, lmps, ys, stepsize):
        grad = ys - ys.transpose((2, 3, 0, 1))
        
        gnom = (grad * grad).sum()
        
        if gnom > 0.000001:
            stepsize /= gnom
        
        newlmps = lmps -  stepsize * grad 
        
        return newlmps

    def _preprocess(self, unarydata, binarydata, V):
        
        unarymatch_dict = self.sparse.DOK((V, V), data=unarydata)
        binarymatch_dict = self.sparse.DOK((V, V, V, V), data=binarydata)
        
        wd = Counter()
    
        for a, b, c, d in binarydata:
            if (a,b) not in wd:
                wd[(a, b)] = Counter()
            wd[(a, b)][(c, d)] = binarydata[(a, b, c, d)] 
            

        binarydata = wd
        
        return unarymatch_dict.to_coo(), binarymatch_dict.to_coo(), binarydata

    def _solve(self, unarydata, binarydata, V):
        
        # some preprocessing
        unarymatch_dict, binarymatch_dict, binarydata = self._preprocess(unarydata, binarydata, V)
        
        alignmat = None

        # intial slack variables
        lmps = self.sparse.DOK(shape=binarymatch_dict.shape).to_coo()
        
        # set lower and upper bounds
        lower_bound = 0
        simple_lower_bound = 0
        upper_bound = 10000000
        
        # initialize some running numbers
        iters = 0
        tx = time.time()
        improvement = -1
        MU = 1
        last_upper_bound_reduce = -1
        improved_ub = False

        # start iterating
        while True:
            logger.debug("upper bound: {}".format(upper_bound))
            logger.debug("lower bound: {}".format(lower_bound))
            
            # solve relaxed problem, which gives us an upperbound
            candidate_map = self._solve_relaxed_with_max_match(V, unarydata, binarydata, lmps=lmps)
            ysrelax = self._complete_struct(candidate_map, unarymatch_dict, binarymatch_dict, lmps)
            rv = self._eval_problem(candidate_map, ysrelax, unarymatch_dict, binarymatch_dict, lmps=lmps)
            
            if rv < upper_bound:
                # tighten upper-bound
                upper_bound = rv
                last_upper_bound_reduce = iters
                improved_ub = True
            else:
                improved_ub = False

            # if no improvement, reduce MU
            if iters - last_upper_bound_reduce > 50:
                MU /= 1.8
                last_upper_bound_reduce = iters
            
            # decrease stepsize
            stepsize = max(MU * (upper_bound - lower_bound), 0.0005)

            # adapt slack variables
            lmps = self._adapt_lmps(lmps, ysrelax, stepsize)
            
            # find a valid solution
            ysstrict = self._complete_struct(candidate_map, unarymatch_dict, binarymatch_dict, lmps=None)
            sv = self._eval_problem(candidate_map, ysstrict, unarymatch_dict, binarymatch_dict)

            # check if valid solution is better than last
            
            if sv > lower_bound:
                lower_bound = sv
                alignmat = candidate_map
                improvement = iters

            iters += 1
            if iters == 250:
                alignmat = util.alignmat_compressed(alignmat)
                return alignmat, lower_bound, upper_bound
            if upper_bound - lower_bound < 1.0:
                alignmat = util.alignmat_compressed(alignmat)
                return alignmat, lower_bound, upper_bound
            if time.time() - tx > self.max_seconds:
                alignmat = util.alignmat_compressed(alignmat)
                return alignmat, lower_bound, upper_bound

        alignmat = util.alignmat_compress(alignmat)
        return alignmat, None, None


class RILPHC(RILP):

    def __init__(self, max_seconds=15):
        RILP.__init__(self)
    
    def _solve(self, unarydata, binarydata, V):
        
        unarymatch_dict, binarymatch_dict, binarydata = self._preprocess(unarydata, binarydata, V)
        
        alignmat = None
        lmps = self.sparse.DOK(shape=binarymatch_dict.shape).to_coo()
        
        lower_bound = 0
        simple_lower_bound = 0
        upper_bound = 10000000
 
        iters = 0
        tx = time.time()
        improvement = -1
        MU = 1
        last_upper_bound_reduce = -1

        improved_ub = False
        
        while True:
            logger.debug("upper bound: {}".format(upper_bound))
            logger.debug("lower bound: {}".format(lower_bound))
            candidate_map = self._solve_relaxed_with_max_match(V, unarydata, binarydata, lmps=lmps)
            hc = HillClimber()
            ysrelax = self._complete_struct(candidate_map, unarymatch_dict, binarymatch_dict, lmps)
            rv = self._eval_problem(candidate_map, ysrelax, unarymatch_dict, binarymatch_dict, lmps=lmps)
            
            if rv < upper_bound:
                upper_bound = rv
                last_upper_bound_reduce = iters
                improved_ub = True
            else:
                improved_ub = False

             
            if iters - last_upper_bound_reduce > 50:
                MU /= 1.8
                last_upper_bound_reduce = iters
 

            stepsize = max(MU * (upper_bound - lower_bound), 0.0005)

            lmps = self._adapt_lmps(lmps, ysrelax, stepsize)

            ysstrict = self._complete_struct(candidate_map, unarymatch_dict, binarymatch_dict, lmps=None)
             
            sv = self._eval_problem(candidate_map, ysstrict, unarymatch_dict, binarymatch_dict)
            
            if sv > simple_lower_bound:
                
                simple_lower_bound = sv
                candidate_map = util.alignmat_compressed(candidate_map.copy())
                candidate_map, _ , _ = hc._climb(unarydata, binarydata, V, candidate_map)
                candidate_map = util.alignmat_decompressed(candidate_map)
                ysstrict = self._complete_struct(candidate_map, unarymatch_dict, binarymatch_dict, lmps=None)
                sv = self._eval_problem(candidate_map, ysstrict, unarymatch_dict, binarymatch_dict)
                
                if sv > lower_bound:
                    lower_bound = sv
                    alignmat = candidate_map
                    improvement = iters

            iters += 1
            
            if iters == 250:
                alignmat = util.alignmat_compressed(alignmat)
                return alignmat, lower_bound, upper_bound
            if upper_bound - lower_bound < 1.0:
                alignmat = util.alignmat_compressed(alignmat)
                return alignmat, lower_bound, upper_bound
            if time.time() - tx > self.max_seconds:
                alignmat = util.alignmat_compressed(alignmat)
                return alignmat, lower_bound, upper_bound

        alignmat = util.alignmat_compress(alignmat)
        return alignmat, None, None



