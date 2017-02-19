from __future__ import division
from scipy.stats import multivariate_normal
import numpy as np
from numpy.linalg import inv
import random
from sets import ImmutableSet
from munkres import Munkres

import math

#if we have prior of 0, return PRIOR_EPSILON
PRIOR_EPSILON = .000000001

class Parameters:
    def __init__(self, det_names, target_groupEmission_priors, clutter_grpCountByFrame_priors,\
                 clutter_group_priors, birth_count_priors, posOnly_covariance_blocks, \
                 meas_noise_mean, posAndSize_inv_covariance_blocks, R_default, H,\
                 USE_PYTHON_GAUSSIAN, USE_CONSTANT_R, score_intervals,\
                 p_birth_likelihood, p_clutter_likelihood, CHECK_K_NEAREST_TARGETS,
                 K_NEAREST_TARGETS, scale_prior_by_meas_orderings):
        '''
        Inputs:
        - det_names: list of detection source names
        -  score_intervals: list of lists, where score_intervals[i] is a list
            specifying the score intervals for measurement source i.  
            score_intervals[i][j] specifies the lower bound for the jth score
            interval corresponding to measurement source i (0 indexed).
        - CHECK_K_NEAREST_TARGETS: If true only possibly associate each measurement with
            one of its K_NEAREST_TARGETS.  If false measurements may be associated
            with any target.
        '''
        self.det_names = det_names

        #dictionary where target_groupEmission_priors[det_set] is the prior probability
        #that a ground truth object will emit the set of measurements specified by the immutable set det_set.
        self.target_groupEmission_priors = target_groupEmission_priors 
        self.clutter_grpCountByFrame_priors = clutter_grpCountByFrame_priors
        self.clutter_group_priors = clutter_group_priors
        self.birth_count_priors = birth_count_priors #dictionary, where birth_count_priors[n] is the prior probability of observing n births in a frame.

        self.posOnly_covariance_blocks = posOnly_covariance_blocks #posOnly_covariance_blocks[(det_name1, det_name2)] = posOnly_cov_block_12

        self.meas_noise_mean = meas_noise_mean
        self.posAndSize_inv_covariance_blocks = posAndSize_inv_covariance_blocks

        self.R_default = R_default
        self.H = H

        self.USE_PYTHON_GAUSSIAN = USE_PYTHON_GAUSSIAN
        self.USE_CONSTANT_R = USE_CONSTANT_R

        self.score_intervals = score_intervals

        self.p_birth_likelihood = p_birth_likelihood 
        self.p_clutter_likelihood = p_clutter_likelihood

        self.CHECK_K_NEAREST_TARGETS = CHECK_K_NEAREST_TARGETS
        self.K_NEAREST_TARGETS = K_NEAREST_TARGETS

        self.scale_prior_by_meas_orderings = scale_prior_by_meas_orderings

        print "posOnly_covariance_blocks"
        print posOnly_covariance_blocks
        #sleep(5)

        #print "target_groupEmission_priors: ", self.target_groupEmission_priors
        #print "clutter_grpCountByFrame_priors: ", self.clutter_grpCountByFrame_priors
        #print "clutter_group_priors: ", self.clutter_group_priors
        #print "birth_count_priors: ", self.birth_count_priors
        #print "posOnly_covariance_blocks: ", self.posOnly_covariance_blocks
        #print "meas_noise_mean: ", self.meas_noise_mean
        #print "posAndSize_inv_covariance_blocks: ", self.posAndSize_inv_covariance_blocks

    def birth_groupCount_prior(self, group_count):
        if group_count in self.birth_count_priors:
            return self.birth_count_priors[group_count]
        else:
            return PRIOR_EPSILON
    def birth_group_prior(self, det_group):
        if det_group in self.target_groupEmission_priors:
            #probability of any target emitting this detection group, given that the target emits some detection
            returnVal = self.target_groupEmission_priors[det_group]/(1.0 - self.target_groupEmission_priors[ImmutableSet([])]) 
            assert (returnVal>0), (self.target_groupEmission_priors, det_group, self.target_groupEmission_priors[det_group], self.target_groupEmission_priors[ImmutableSet([])])
            return self.target_groupEmission_priors[det_group]/(1.0 - self.target_groupEmission_priors[ImmutableSet([])]) 
        else:
            return PRIOR_EPSILON


    def clutter_groupCount_prior(self, group_count):
        if group_count in self.clutter_grpCountByFrame_priors:
            return self.clutter_grpCountByFrame_priors[group_count]
        else:
            return PRIOR_EPSILON

    def clutter_group_prior(self, det_group):
        if det_group in self.clutter_group_priors:
            return self.clutter_group_priors[det_group]
        else:
            return PRIOR_EPSILON

    def find_clutter_priors_by_det():
        #Compute marginal_det_priors where marginal_det_priors[det_name][n] is the prior probability

        #Marginalize over self.clutter_group_priors to find marginal priors for each detection source

        #dictionary, key=det_name value=priors for det_name
        marginal_priors = {}



def boxoverlap(a,b,criterion="union"):
    """
        boxoverlap computes intersection over union for bbox a and b in KITTI format.
        If the criterion is 'union', overlap = (a inter b) / a union b).
        If the criterion is 'a', overlap = (a inter b) / a, where b should be a dontcare area.
        Inputs:
        - a: numpy array, [x_center, y_center, width, height] for detection a
        - b: numpy array, [x_center, y_center, width, height] for detection b
    """
    a_x1 = a[0]-a[2]/2
    a_x2 = a[0]+a[2]/2
    a_y1 = a[1]-a[3]/2
    a_y2 = a[1]+a[3]/2

    b_x1 = b[0]-b[2]/2
    b_x2 = b[0]+b[2]/2
    b_y1 = b[1]-b[3]/2
    b_y2 = b[1]+b[3]/2

    x1 = max(a_x1, b_x1)
    y1 = max(a_y1, b_y1)
    x2 = min(a_x2, b_x2)
    y2 = min(a_y2, b_y2)
    
    w = x2-x1
    h = y2-y1

    if w<=0. or h<=0.:
        return 0.
    inter = w*h
    aarea = (a_x2-a_x1) * (a_y2-a_y1)
    barea = (b_x2-b_x1) * (b_y2-b_y1)
    # intersection over union overlap
    if criterion.lower()=="union":
        o = inter / float(aarea+barea-inter)
    elif criterion.lower()=="a":
        o = float(inter) / float(aarea)
    else:
        raise TypeError("Unkown type for criterion")
    return o


def group_detections(meas_groups, det_name, detection_locations, det_widths, det_heights):
    """
    Take a list of detections and try to associate them with detection groups from other measurement sources
    Inputs:
    - meas_groups: a list of detection groups, where each detection group is a dictionary of detections 
        in the group, key='det_name', value=detection
    - det_name: name of the detection source we are currently associating with current detection groups
    - detections: a list of detections from a specific measurement source, sequence, and frame
    - seq_idx: the sequence index
    - frame_idx: the frame index (in the specified sequence)

    Outputs:
    None, but meas_groups will be modified, with the new detections added (passed by reference)
    """

    hm = Munkres()
    max_cost = 1e9

    # use hungarian method to associate, using boxoverlap 0..1 as cost
    # build cost matrix
    cost_matrix = []
    this_ids = [[],[]]

    assert(len(detection_locations) == len(det_widths) and len(det_widths) == len(det_heights))
    #combine into 4d detections
    detections = []
    for det_idx, det_loc in enumerate(detection_locations):
        detections.append(np.array([det_loc[0], det_loc[1], det_widths[det_idx], det_heights[det_idx]]))

    for cur_detection in detections:
        cost_row = []
        for cur_detection_group in meas_groups:
            min_cost = max_cost
            for det_name, grouped_detection in cur_detection_group.iteritems():
                # overlap == 1 is cost ==0
                c = 1-boxoverlap(cur_detection, grouped_detection)
                if c < min_cost:
                    min_cost = c
            # gating for boxoverlap
            if min_cost<=.5:
                cost_row.append(min_cost)
            else:
                cost_row.append(max_cost)
        cost_matrix.append(cost_row)
    
    if len(detections) is 0:
        cost_matrix=[[]]
    # associate
    association_matrix = hm.compute(cost_matrix)

    associated_detection_indices = []
    check_det_count = 0
    for row,col in association_matrix:
        # apply gating on boxoverlap
        c = cost_matrix[row][col]
        if c < max_cost:
            associated_detection = detections[row]
            associated_detection_indices.append(row)
            associated_detection_group = meas_groups[col]

            #double check
            check_det_count += 1
            min_cost = max_cost
            for det_name, grouped_detection in associated_detection_group.iteritems():
                # overlap == 1 is cost ==0
                check_c = 1-boxoverlap(associated_detection, grouped_detection)
                if check_c < min_cost:
                    min_cost = check_c
            assert(min_cost == c), (min_cost, c)
            #done double check                

            associated_detection_group[det_name] = associated_detection                


    for det_idx in range(len(detections)):
        if not(det_idx in associated_detection_indices):
            meas_groups.append({det_name: detections[det_idx]})
            check_det_count += 1
    assert(check_det_count == len(detections))



def sample_and_reweight(particle, measurement_lists, widths, heights, det_names, \
    cur_time, measurement_scores, params):
    """
    Input:
    - particle: type Particle, we will perform sampling and importance reweighting on this particle
    - measurement_lists: a list where measurement_lists[i] is a list of all measurements from the current
        time instance from the ith measurement source (i.e. different object detection algorithms
        or different sensors)
    - det_names: a list of names of measurement sources, where det_names[i] corresponds to measurement_lists[i]
    - measurement_scores: a list where measurement_scores[i] is a list containing scores for every measurement in
        measurement_list[i]
    - params: type Parameters, gives prior probabilities and other parameters we are using

    Output:
    - measurement_associations: A list where measurement_associations[i] is a list of association values
        for each measurements in measurement_lists[i].  Association values correspond to:
        measurement_associations[i][j] = -1 -> measurement is clutter
        measurement_associations[i][j] = particle.targets.living_count -> measurement is a new target
        measurement_associations[i][j] in range [0, particle.targets.living_count-1] -> measurement is of
            particle.targets.living_targets[measurement_associations[i][j]]

    - imprt_re_weight: After processing this measurement the particle's
        importance weight will be:
        new_importance_weight = old_importance_weight * imprt_re_weight
    - targets_to_kill: a list containing the indices of targets that should be killed, beginning
        with the smallest index in increasing order, e.g. [0, 4, 6, 33]
    """

    #get death probabilities for each target in a numpy array
    num_targs = particle.targets.living_count
    p_target_deaths = []
    for target in particle.targets.living_targets:
        p_target_deaths.append(target.death_prob)
        assert(p_target_deaths[len(p_target_deaths) - 1] >= 0 and p_target_deaths[len(p_target_deaths) - 1] <= 1)


    meas_groups = []
    for det_idx, det_name in enumerate(det_names):
        group_detections(meas_groups, det_name, measurement_lists[det_idx], widths[det_idx], heights[det_idx])

    (targets_to_kill, meas_grp_associations, meas_grp_means, meas_grp_covs, proposal_probability, 
        unassociated_target_death_probs) =  sample_grouped_meas_assoc_and_death(particle, 
        meas_groups, particle.targets.living_count, p_target_deaths, cur_time, measurement_scores, params)



    living_target_indices = []
    for i in range(particle.targets.living_count):
        if(not i in targets_to_kill):
            living_target_indices.append(i)

    exact_probability = 1.0
    likelihood = get_likelihood(particle, meas_groups, particle.targets.living_count,
                                   meas_grp_associations, params)
    assoc_prior = get_assoc_prior(particle.targets.living_count, meas_groups, meas_grp_associations, params)
    exact_probability *= likelihood * assoc_prior


    death_prior = calc_death_prior(living_target_indices, p_target_deaths)
    exact_probability *= death_prior

    assert(num_targs == particle.targets.living_count)
    #double check targets_to_kill is sorted
    assert(all([targets_to_kill[i] <= targets_to_kill[i+1] for i in xrange(len(targets_to_kill)-1)]))

    imprt_re_weight = exact_probability/proposal_probability

    assert(imprt_re_weight != 0.0), (exact_probability, proposal_probability, death_prior)

    particle.likelihood_DOUBLE_CHECK_ME = exact_probability

    print "imprt_re_weight:", imprt_re_weight

    return (meas_grp_associations, meas_grp_means, meas_grp_covs, targets_to_kill, imprt_re_weight)

def sample_grouped_meas_assoc_and_death(particle, meas_groups, total_target_count, 
                           p_target_deaths, cur_time, measurement_scores, params):
    """
    Try sampling associations with each measurement sequentially
    Input:
    - particle: type Particle, we will perform sampling and importance reweighting on this particle
    - meas_groups: a list of detection groups, where each detection group is a dictionary of detections 
        in the group, key='det_name', value=detection
    - measurement_scores: type list, measurement_scores[i] is a list containing scores for every measurement in
        measurement_list[i]
    - total_target_count: the number of living targets on the previous time instace
    - p_target_deaths: a list of length len(total_target_count) where 
        p_target_deaths[i] = the probability that target i has died between the last
        time instance and the current time instance
    - params: type Parameters, gives prior probabilities and other parameters we are using

    Output:
    - targets_to_kill: a list of targets that have been sampled to die (not killed yet)
    - meas_grp_associations: type list, meas_grp_associations[i] the association for the ith
        measurement group
    - meas_grp_means: list, each element is the combined measurment mean (np array)
    - meas_grp_covs: list, each element is the combined measurment covariance (np array)
    - proposal_probability: proposal probability of the sampled deaths and associations
        
    """
#    assert(len(measurement_lists) == len(measurement_scores))
#    measurement_associations = []
#    proposal_probability = 1.0
#    for meas_source_index in range(len(measurement_lists)):
#        (cur_associations, cur_proposal_prob) = associate_measurements_sequentially\
#            (particle, meas_source_index, measurement_lists[meas_source_index], \
#             total_target_count, p_target_deaths, measurement_scores[meas_source_index],\
#             params)
#        measurement_associations.append(cur_associations)
#        proposal_probability *= cur_proposal_prob
#
#    assert(len(measurement_associations) == len(measurement_lists))
#
#    FIXME measurement_associations, proposal_probability
############################################################################################################
    #New implementation
    
    (meas_grp_associations, meas_grp_means, meas_grp_covs, proposal_probability) = associate_measurements_sequentially\
            (particle, meas_groups, \
             total_target_count, p_target_deaths,\
             params)





############################################################################################################

############################################################################################################
    #sample target deaths from unassociated targets
    unassociated_targets = []
    unassociated_target_death_probs = []

    for i in range(total_target_count):
        target_unassociated = True
        if i in meas_grp_associations:
            target_unassociated = False
        else:
            target_unassociated = True            
        if target_unassociated:
            unassociated_targets.append(i)
            unassociated_target_death_probs.append(p_target_deaths[i])
        else:
            unassociated_target_death_probs.append(0.0)

    (targets_to_kill, death_probability) =  \
        sample_target_deaths(particle, unassociated_targets, cur_time)

    #probability of sampling all associations
    proposal_probability *= death_probability
    assert(proposal_probability != 0.0)

    #debug
    for i in range(total_target_count):
        assert(meas_grp_associations.count(i) == 0 or \
               meas_grp_associations.count(i) == 1), (meas_grp_associations,  measurement_list, total_target_count, p_target_deaths)
    #done debug

    return (targets_to_kill, meas_grp_associations, meas_grp_means, meas_grp_covs, proposal_probability, unassociated_target_death_probs)

def associate_measurements_sequentially(particle, meas_groups, total_target_count, p_target_deaths, params):

    """
    Try sampling associations with each measurement sequentially
    Input:
    - particle: type Particle, we will perform sampling and importance reweighting on this particle     
    - meas_groups: a list of detection groups, where each detection group is a dictionary of detections 
        in the group, key='det_name', value=detection
    - total_target_count: the number of living targets on the previous time instace
    - p_target_deaths: a list of length len(total_target_count) where 
        p_target_deaths[i] = the probability that target i has died between the last
        time instance and the current time instance
    - params: type Parameters, gives prior probabilities and other parameters we are using

    Output:
    - list_of_measurement_associations: list of associations for each measurement group
    - proposal_probability: proposal probability of the sampled deaths and associations
        
    """
    list_of_measurement_associations = []
    proposal_probability = 1.0

    #sample measurement associations
    birth_count = 0
    clutter_count = 0
    remaining_meas_count = len(meas_groups)

    #list of detection group centers, meas_grp_means[i] is a 2-d numpy array
    #of the position of meas_groups[i]
    meas_grp_covs = []   
    meas_grp_means2D = []
    meas_grp_means4D = []
    for (index, detection_group) in enumerate(meas_groups):
        (combined_meas_mean, combined_covariance) = combine_arbitrary_number_measurements_4d(params.posAndSize_inv_covariance_blocks, 
                            params.meas_noise_mean, detection_group)
        combined_meas_pos = combined_meas_mean[0:2]
        meas_grp_means2D.append(combined_meas_pos)
        meas_grp_means4D.append(combined_meas_mean)
        meas_grp_covs.append(combined_covariance)


    def get_k_nearest_targets(measurement, k):
        """
        Inputs:
        - measurement: the measurement
        - k: integer, number of nearest targets to return

        Output:
        - k_nearest_target_indices: list of indices of the k nearest (L2 distance between 
            bounding box centers) targets in the living target list
        """

        k_nearest_target_indices = []
        k_nearest_target_dists = []
        for target_index in range(total_target_count):
            target = particle.targets.living_targets[target_index]            
            target_location = np.squeeze(np.dot(params.H, target.x))
            distance = (measurement[0] - target_location[0])**2 + (measurement[1] - target_location[1])**2
            if len(k_nearest_target_indices) < k: #add target
                k_nearest_target_indices.append(target_index)
                k_nearest_target_dists.append(distance)
            elif distance < max(k_nearest_target_dists):
                target_idx_to_replace = k_nearest_target_dists.index(max(k_nearest_target_dists))
                k_nearest_target_indices[target_idx_to_replace] = target_index
                k_nearest_target_dists[target_idx_to_replace] = distance

        return k_nearest_target_indices


    for (index, detection_group) in enumerate(meas_groups):
        #create proposal distribution for the current measurement
        #compute target association proposal probabilities
        proposal_distribution_list = []

        #create set of the names of detection sources preset in this detection group
        group_det_names = []
        for det_name, det in detection_group.iteritems():
            group_det_names.append(det_name)
        det_names_set = ImmutableSet(group_det_names)

        if params.CHECK_K_NEAREST_TARGETS:
            targets_to_check = get_k_nearest_targets(meas_grp_means2D[index], params.K_NEAREST_TARGETS)
        else:
            targets_to_check = [i for i in range(total_target_count)]

#        for target_index in range(total_target_count):
        for target_index in targets_to_check:
            cur_target_likelihood = memoized_assoc_likelihood(particle, detection_group, target_index, params)
            targ_likelihoods_summed_over_meas = 0.0

            debug_idx = 0
            for meas_index2, detection_group2 in enumerate(meas_groups):
                targ_likelihoods_summed_over_meas += memoized_assoc_likelihood(particle, detection_group2, target_index, params)
                debug_idx += 1

            if((targ_likelihoods_summed_over_meas != 0.0) and (not target_index in list_of_measurement_associations)\
                and p_target_deaths[target_index] < 1.0):
                cur_target_prior = params.target_groupEmission_priors[det_names_set]*cur_target_likelihood \
                                  /targ_likelihoods_summed_over_meas
            else:
                cur_target_prior = 0.0

#            print "debug_idx", debug_idx
#            print "len(meas_groups)", len(meas_groups)
#            print "cur_target_prior", cur_target_prior
#            print "targ_likelihoods_summed_over_meas", targ_likelihoods_summed_over_meas
#            print "target_index in list_of_measurement_associations", (target_index in list_of_measurement_associations)
#            print " p_target_deaths[target_index] < 1.0", ( p_target_deaths[target_index] < 1.0)
#            print "p_target_deaths:", p_target_deaths
#            sleep(5)
            proposal_distribution_list.append(cur_target_likelihood*cur_target_prior)


        cur_birth_prior = PRIOR_EPSILON
        for bc, prior in params.birth_count_priors.iteritems():
            additional_births = max(0.0, min(bc - birth_count, remaining_meas_count))
            if additional_births <= remaining_meas_count:
                cur_birth_prior += prior*additional_births/remaining_meas_count 
        cur_birth_prior *= params.birth_group_prior(det_names_set)
        assert(cur_birth_prior*params.p_birth_likelihood**len(detection_group) > 0), (cur_birth_prior,params.p_birth_likelihood,len(detection_group))



        cur_clutter_prior = PRIOR_EPSILON
        for cc, prior in params.clutter_grpCountByFrame_priors.iteritems():
            additional_clutter = max(0.0, min(cc - clutter_count, remaining_meas_count))
            if additional_clutter <= remaining_meas_count:            
                cur_clutter_prior += prior*additional_clutter/remaining_meas_count 
        cur_clutter_prior *= params.clutter_group_prior(det_names_set)
        assert(cur_clutter_prior*params.p_clutter_likelihood**len(detection_group) > 0), (cur_clutter_prior, params.p_clutter_likelihood, len(detection_group))




#        cur_birth_prior = cur_clutter_prior

        proposal_distribution_list.append(cur_birth_prior*params.p_birth_likelihood**len(detection_group)) #Quick test, make nicer!!


        proposal_distribution_list.append(cur_clutter_prior*params.p_clutter_likelihood**len(detection_group)) #Quick test, make nicer!!




        #normalize the proposal distribution
        proposal_distribution = np.asarray(proposal_distribution_list)
        assert(np.sum(proposal_distribution) != 0.0), (index, remaining_meas_count, len(proposal_distribution), proposal_distribution, birth_count, clutter_count, len(measurement_list), total_target_count)
        proposal_distribution /= float(np.sum(proposal_distribution))
        if params.CHECK_K_NEAREST_TARGETS:
            proposal_length = min(params.K_NEAREST_TARGETS+2, total_target_count+2)
            assert(len(proposal_distribution) == proposal_length), (proposal_length, len(proposal_distribution))

        else:
            assert(len(proposal_distribution) == total_target_count+2), len(proposal_distribution)

 #       if particle.max_importance_weight:
 #           print proposal_distribution

        sampled_assoc_idx = np.random.choice(len(proposal_distribution),
                                                p=proposal_distribution)

        if params.CHECK_K_NEAREST_TARGETS:
            possible_target_assoc_count = min(params.K_NEAREST_TARGETS, total_target_count)
            if(sampled_assoc_idx <= possible_target_assoc_count): #target or birth association
                if(sampled_assoc_idx == possible_target_assoc_count): #birth
                    birth_count += 1
                    list_of_measurement_associations.append(total_target_count)
                else: #target
                    list_of_measurement_associations.append(targets_to_check[sampled_assoc_idx])

            else: #clutter association
                assert(sampled_assoc_idx == possible_target_assoc_count+1)
                list_of_measurement_associations.append(-1)
                clutter_count += 1

        else: #we considered association with all targets
            if(sampled_assoc_idx <= total_target_count): #target or birth association
                list_of_measurement_associations.append(sampled_assoc_idx)
                if(sampled_assoc_idx == total_target_count):
                    birth_count += 1
            else: #clutter association
                assert(sampled_assoc_idx == total_target_count+1)
                list_of_measurement_associations.append(-1)
                clutter_count += 1

        proposal_probability *= proposal_distribution[sampled_assoc_idx]

        remaining_meas_count -= 1


    assert(remaining_meas_count == 0)
    return(list_of_measurement_associations, meas_grp_means4D, meas_grp_covs, proposal_probability)


def sample_target_deaths(particle, unassociated_targets, cur_time):
    """
    Sample target deaths, given they have not been associated with a measurement, using probabilities
    learned from data.
    Also kill all targets that are offscreen.

    Inputs:
    - particle: type Particle, we will perform sampling and importance reweighting on this particle     
    - unassociated_targets: a list of target indices that have not been associated with a measurement

    Output:
    - targets_to_kill: a list of targets that have been sampled to die (not killed yet)
    - probability_of_deaths: the probability of the sampled deaths
    """
    targets_to_kill = []
    probability_of_deaths = 1.0

    for target_idx in range(len(particle.targets.living_targets)):
        #kill offscreen targets with probability 1.0
        if(particle.targets.living_targets[target_idx].offscreen == True):
            targets_to_kill.append(target_idx)
        elif(target_idx in unassociated_targets):
            cur_death_prob = particle.targets.living_targets[target_idx].death_prob
            if(random.random() < cur_death_prob):
                targets_to_kill.append(target_idx)
                probability_of_deaths *= cur_death_prob
            else:
                probability_of_deaths *= (1 - cur_death_prob)
    return (targets_to_kill, probability_of_deaths)

def calc_death_prior(living_target_indices, p_target_deaths):
    death_prior = 1.0
    for (cur_target_index, cur_target_death_prob) in enumerate(p_target_deaths):
        if cur_target_index in living_target_indices:
            death_prior *= (1.0 - cur_target_death_prob)
            assert((1.0 - cur_target_death_prob) != 0.0), cur_target_death_prob
        else:
            death_prior *= cur_target_death_prob
            assert((cur_target_death_prob) != 0.0), cur_target_death_prob

    return death_prior

def nCr(n,r):
    return math.factorial(n) / math.factorial(r) / math.factorial(n-r)

def count_meas_orderings(M, T, b, c):
    """
    We define target observation priors in terms of whether each target was observed and it
    is irrelevant which measurement the target is associated with.  Likewise, birth count priors
    and clutter count priors are defined in terms of total counts, not which specific measurements
    are associated with clutter and births.  This function counts the number of possible 
    measurement-association assignments given we have already chosen which targets are observed, 
    how many births occur, and how many clutter measurements are present.  

    If the prior probability of observing T specific targets, b births, and c clutter observations 
    given M measurements is divided by the count_meas_orderings(M, T, b, c), the prior probability 
    is split between all possible associations.  This ensures that our prior is a proper probability
    distribution that sums to one over the entire state space.  

    Calculates the ordered vector of associations by equally prior probability of unordered set of
    associations between all orderings.  This is the most straightforward idea, but it seems problematic.
    As the number of targets increases, the number of possible measurment target associations blows
    up and prior must be spilt between all.  It may make more sense to simply calculate the prior
    of an unordered measurement set and then calculate likelihood based on the unordered set of observations.

####### 
#######   However, we our calculating the prior:

#######   p(c_k, #y_k | e_1:k-1, c_1:k-1, y_1:k-1, #y_1:k-1)
#######   
#######   Note we are given all past measurements, associations, and the state of all living targets at the
#######   last time instance.  


    [
    *OLD EXPLANATION BELOW*:
    We view the the ordering of measurements on any time instance as arbitrary.  This
    function counts the number of possible measurement orderings given we have already
    chosen which targets are observed, how many births occur, and how many clutter 
    measurements are present.
    ]
    
    Inputs:
    - M: the number of measurements
    - T: the number of observed targets
    - b: the number of birth associations
    - c: the number of clutter associations

    This must be true: M = T+b+c

    Output:
    - combinations: the number of measurement orderings as a float. The value is:
        combinations = nCr(M, T)*math.factorial(T)*nCr(M-T, b)

    """
    assert(M == T + b + c)
    combinations = nCr(M, T)*math.factorial(T)*nCr(M-T, b)
    return float(combinations)


def combine_arbitrary_number_measurements_4d(blocked_cov_inv, meas_noise_mean, detection_group):
    """
    
    Inputs:
    - blocked_cov_inv: dictionary containing the inverse of the measurement noise covariance matrix, between
    all measurement source

    [sigma_11    sigma_1j     sigma_1n]
    [.       .                        ]
    [.          .                     ]
    [.             .                  ]
    [sigma_i1    sigma_ij     sigma_in]
    [.                 .              ]
    [.                    .           ]
    [.                       .        ]
    [sigma_n1    sigma_nj     sigma_nn]
    
    Where there are n measurement sources and sigma_ij represents the block of the INVERSE of the noise covariance
    corresponding to the ith blocked row and the jth blocked column.  To access sigma_ij, call 
    blocked_cov_inv[('meas_namei','meas_namej')] where 'meas_namei' is the string representation of the name of
    measurement source i.

    -meas_noise_mean: a dictionary where meas_noise_mean['meas_namei'] = the mean measurement noise for measurement
    source with name 'meas_namei'

    -detection_group: dictionary of detections to combine, key='det_name', value=detection

    """
    meas_count = len(detection_group) #number of associated measurements

    #dictionary containing all measurements in appropriately formatted numpy arrays
    reformatted_zs = {}
    for det_name, det in detection_group.iteritems():
        cur_z = np.array([det[0] - meas_noise_mean[det_name][0], 
                          det[1] - meas_noise_mean[det_name][1],
                          det[2] - meas_noise_mean[det_name][2],
                          det[3] - meas_noise_mean[det_name][3]])
        reformatted_zs[det_name] = cur_z
    A = 0
    b = 0
    for det_name1, det in reformatted_zs.iteritems():
        for det_name2, ignore_me_det in detection_group.iteritems():
            A += blocked_cov_inv[(det_name1, det_name2)]
            b += np.dot(det, blocked_cov_inv[(det_name1, det_name2)])
    combined_meas_mean = np.dot(inv(A), b.transpose())
    combined_covariance = inv(A)
    assert(combined_meas_mean.shape == (4,)), (meas_count, detection_group)
    return (combined_meas_mean.flatten(), combined_covariance)




def get_assoc_prior(living_target_count, meas_groups, meas_grp_associations, params):
    """
    Inputs:
    - living_target_count: number of living counts, measurement associations that correspond to association
        with a target will be in the range [0, living_target_count)
    """
    #get list of detection names present in our detection group

    #count the number of unique target associations
    unique_assoc = set(meas_grp_associations)
    if(living_target_count in unique_assoc):
        unique_assoc.remove(living_target_count)
    if((-1) in unique_assoc):
        unique_assoc.remove((-1))

    #the number of targets we observed on this time instance
    observed_target_count = len(unique_assoc)
    #the number of targets we don't observe on this time instance
    #but are still alive on this time instance
    unobserved_target_count = living_target_count - observed_target_count

    prior = params.target_groupEmission_priors[ImmutableSet([])]**unobserved_target_count
    for meas_grp_idx, meas_grp_assoc in enumerate(meas_grp_associations):
        #get the names of detection sources in this group
        group_det_names = []
        for det_name, det in meas_groups[meas_grp_idx].iteritems():
            group_det_names.append(det_name)
        det_names_set = ImmutableSet(group_det_names)          
  
        if meas_grp_assoc>=0 and meas_grp_assoc < living_target_count: #target association
            prior *= params.target_groupEmission_priors[det_names_set]
        elif meas_grp_assoc == -1:
            prior *= params.clutter_group_prior(det_names_set)
        else:
            assert(meas_grp_assoc == living_target_count), (meas_grp_assoc, living_target_count)
            prior *= params.birth_group_prior(det_names_set)

    birth_count = meas_grp_associations.count(living_target_count)
    prior *= params.birth_groupCount_prior(birth_count)

    clutter_count = meas_grp_associations.count(-1)
    prior *= params.clutter_groupCount_prior(clutter_count)

    return prior

def get_assoc_prior_prev(living_target_indices, total_target_count, number_measurements, 
             measurement_associations, measurement_scores, params,\
             meas_source_index):
    """
    Calculate the prior probability of the observed number of measurements and their assigned associations
    given all past measurements, their associations, and living targets (particularly important, we are 
    given the number of targets currently alive). That is, calculate:
    p(c_k, #y_k | e_1:k-1, c_1:k-1, y_1:k-1, #y_1:k-1)




    Input: 
    - living_target_indices: a list of indices of targets from last time instance that are still alive
    - total_target_count: the number of living targets on the previous time instace
    - number_measurements: the number of measurements on this time instance
    - measurement_associations: a list of association values for each measurement. Each association has the value
        of a living target index (index from last time instance), target birth (total_target_count), 
        or clutter (-1)
    -p_target_emission: the probability that a target will emit a measurement on a 
        time instance (the same for all targets and time instances)
    -birth_count_prior: a probability distribution, specified as a list, such that
        birth_count_prior[i] = the probability of i births during any time instance
    -clutter_count_prior: a probability distribution, specified as a list, such that
        clutter_count_prior[i] = the probability of i clutter measurements during 
        any time instance
    """

    assert(len(measurement_associations) == number_measurements), (number_measurements, len(measurement_associations), measurement_associations)
    #number of targets from the last time instance that are still alive
    living_target_count = len(living_target_indices)
    #numnber of targets from the last time instance that died
    dead_target_count = total_target_count - living_target_count

    #count the number of unique target associations
    unique_assoc = set(measurement_associations)
    if(total_target_count in unique_assoc):
        unique_assoc.remove(total_target_count)
    if((-1) in unique_assoc):
        unique_assoc.remove((-1))

    #the number of targets we observed on this time instance
    observed_target_count = len(unique_assoc)

    #the number of target measurements by measurement score
    meas_counts_by_score = [0 for i in range(len(params.score_intervals[meas_source_index]))]
    for i in range(len(measurement_associations)):
        if measurement_associations[i] != -1 and measurement_associations[i] != total_target_count:
            index = params.get_score_index(measurement_scores[i], meas_source_index)
            meas_counts_by_score[index] += 1

    #the number of targets we don't observe on this time instance
    #but are still alive on this time instance
    unobserved_target_count = living_target_count - observed_target_count
    #the number of new targets born on this time instance
    birth_count = measurement_associations.count(total_target_count)
    birth_counts_by_score = [0 for i in range(len(params.score_intervals[meas_source_index]))]
    for i in range(len(measurement_associations)):
        if measurement_associations[i] == total_target_count:
            index = params.get_score_index(measurement_scores[i], meas_source_index)
            birth_counts_by_score[index] += 1
    #the number of clutter measurements on this time instance
    clutter_count = measurement_associations.count(-1)
    clutter_counts_by_score = [0 for i in range(len(params.score_intervals[meas_source_index]))]
    for i in range(len(measurement_associations)):
        if measurement_associations[i] == -1:
            index = params.get_score_index(measurement_scores[i], meas_source_index)
            clutter_counts_by_score[index] += 1

    assert(observed_target_count + birth_count + clutter_count == number_measurements),\
        (number_measurements, observed_target_count, birth_count, clutter_count, \
        total_target_count, measurement_associations)


    params.check_counts(clutter_counts_by_score, birth_counts_by_score, meas_source_index)

    #the prior probability of this number of measurements with these associations
    if params.scale_prior_by_meas_orderings == 'original':
        p_target_does_not_emit = 1.0 - sum(params.target_emission_probs[meas_source_index])
        assoc_prior = (p_target_does_not_emit)**(unobserved_target_count) \
                      /count_meas_orderings(number_measurements, observed_target_count, \
                                            birth_count, clutter_count)
        for i in range(len(params.score_intervals[meas_source_index])):
            assoc_prior *= params.target_emission_probs[meas_source_index][i]**(meas_counts_by_score[i]) \
                              *params.birth_probabilities[meas_source_index][i][birth_counts_by_score[i]] \
                              *params.clutter_probabilities[meas_source_index][i][clutter_counts_by_score[i]]
    elif params.scale_prior_by_meas_orderings == 'corrected_with_score_intervals':
        p_target_does_not_emit = 1.0 - sum(params.target_emission_probs[meas_source_index])
        assoc_prior = (p_target_does_not_emit)**(unobserved_target_count)
        for i in range(len(params.score_intervals[meas_source_index])):
            #The number of measurements in the current score interval associatd with a target
            cur_score_T = meas_counts_by_score[i]
            #The number of measurements in the current score interval associatd with a birth
            cur_score_B = birth_counts_by_score[i]
            #The number of measurements in the current score interval associatd with clutter
            cur_score_C = clutter_counts_by_score[i]
            #The total number of measurements in the current score interval
            cur_score_M = cur_score_T + cur_score_B + cur_score_C

            assoc_prior *= params.target_emission_probs[meas_source_index][i]**(cur_score_T) \
                              *params.birth_probabilities[meas_source_index][i][cur_score_B] \
                              *params.clutter_probabilities[meas_source_index][i][cur_score_C] \
                              /count_meas_orderings(cur_score_M, cur_score_T, \
                                            cur_score_B, cur_score_C)
    elif params.scale_prior_by_meas_orderings == 'ignore_meas_orderings':
        p_target_does_not_emit = 1.0 - sum(params.target_emission_probs[meas_source_index])
        assoc_prior = (p_target_does_not_emit)**(unobserved_target_count)
        for i in range(len(params.score_intervals[meas_source_index])):
            assoc_prior *= params.target_emission_probs[meas_source_index][i]**(meas_counts_by_score[i]) \
                              *params.birth_probabilities[meas_source_index][i][birth_counts_by_score[i]] \
                              *params.clutter_probabilities[meas_source_index][i][clutter_counts_by_score[i]]
    else:
        raise ValueError('Invalid params.scale_prior_by_meas_orderings value: %s' % params.scale_prior_by_meas_orderings)

    #####TESTING
    meas_orderings = count_meas_orderings(number_measurements, observed_target_count, \
                                        birth_count, clutter_count)

    for i in range(len(params.score_intervals[meas_source_index])):
        assert(params.target_emission_probs[meas_source_index][i]**(meas_counts_by_score[i])!=0), params.target_emission_probs[meas_source_index][i]**(meas_counts_by_score[i])
        assert(params.birth_probabilities[meas_source_index][i][birth_counts_by_score[i]] != 0), (birth_counts_by_score[i], i, params.birth_probabilities[meas_source_index][i])
        assert(params.clutter_probabilities[meas_source_index][i][clutter_counts_by_score[i]] != 0), (clutter_counts_by_score[i], i, params.clutter_probabilities[meas_source_index][i])

    #####DONE TESTING

    return assoc_prior


def get_likelihood(particle, meas_groups, total_target_count,
                   measurement_associations, params):
    """


    """

    likelihood = 1.0
    assert(len(measurement_associations) == len(meas_groups))
    for meas_index, meas_association in enumerate(measurement_associations):
        if(meas_association == total_target_count): #birth
            likelihood *= params.p_birth_likelihood  #FIX ME!!
        elif(meas_association == -1): #clutter
            likelihood *= params.p_clutter_likelihood  #FIX ME!!
        else:
            assert(meas_association >= 0 and meas_association < total_target_count), (meas_association, total_target_count)
            likelihood *= memoized_assoc_likelihood(particle, meas_groups[meas_index], meas_association, params)

    assert(likelihood != 0.0), (likelihood)

    return likelihood


def memoized_assoc_likelihood(particle, detection_group, target_index, params):
    """
        LSVM and regionlets produced two measurements with the same locations (centers), so using the 
        meas_source_index as part of the key is (sort of) necessary.  Currently also using the score_index, 
        could possibly be removed (not sure if this would improve speed).

        Currently saving more in the value than necessary (from debugging), can eliminate to improve
        performance (possibly noticable)

    Inputs:
    - params: type Parameters, gives prior probabilities and other parameters we are using

    """

    if((str(detection_group), target_index) in particle.assoc_likelihood_cache):
        (assoc_likelihood, cached_measurement) = particle.assoc_likelihood_cache[(str(detection_group), target_index)]
        return assoc_likelihood
    else: #likelihood not cached

        target = particle.targets.living_targets[target_index]
        target_cov = np.dot(np.dot(params.H, target.P), params.H.T)
        assert(target.x.shape == (4, 1))

        state_mean_meas_space = np.dot(params.H, target.x)
        state_mean_meas_space = np.squeeze(state_mean_meas_space)



        #get list of detection names present in our detection group
        dets_present = []
        for det_name, detection in detection_group.iteritems():
            dets_present.append(det_name)
        # create array of all detection positions in the group
        all_det_loc = np.zeros(2*len(detection_group))
        # repeat the target location to map it to the #detections * 2 dimension space
        target_loc_repeated = np.zeros(2*len(detection_group))
        for idx, det_name in enumerate(dets_present):
            all_det_loc[idx*2] = detection_group[det_name][0]
            all_det_loc[idx*2+1] = detection_group[det_name][1]

            target_loc_repeated[idx*2] = state_mean_meas_space[0]
            target_loc_repeated[idx*2+1] = state_mean_meas_space[1]


        complete_covariance = np.zeros((2*len(detection_group), 2*len(detection_group)))
        for idx1, det_name1 in enumerate(dets_present):
            for idx2, det_name2 in enumerate(dets_present):
                complete_covariance[idx1*2:(idx1+1)*2][idx2*2:(idx2+1)*2] = params.posOnly_covariance_blocks[(det_name1, det_name2)] + target_cov


        distribution = multivariate_normal(mean=target_loc_repeated, cov=complete_covariance)
        assoc_likelihood = distribution.pdf(all_det_loc)


#        if params.USE_PYTHON_GAUSSIAN:
#            distribution = multivariate_normal(mean=state_mean_meas_space, cov=S)
#            assoc_likelihood = distribution.pdf(measurement)
#        else:
#            S_det = S[0][0]*S[1][1] - S[0][1]*S[1][0] # a little faster
#            S_inv = inv(S)
#            assert(S_det > 0), S_det
#            LIKELIHOOD_DISTR_NORM = 1.0/math.sqrt((2*math.pi)**2*S_det)
#
#            offset = measurement - state_mean_meas_space
#            a = -.5*np.dot(np.dot(offset, S_inv), offset)
#            assoc_likelihood = LIKELIHOOD_DISTR_NORM*math.exp(a)
#
#        particle.assoc_likelihood_cache[(str(detection_group), target_index)] = (assoc_likelihood, measurement)
        return assoc_likelihood

