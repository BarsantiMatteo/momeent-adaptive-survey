import os
import sys
import numpy as np
import pandas as pd
import datetime
    
module_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
if module_path not in sys.path:
    sys.path.append(module_path)

from demod.datasets.Germany.loader import GermanDataHerus
from demod.simulators.base_simulators import SimLogger
from demod.simulators.activity_simulators import SubgroupsIndividualsActivitySimulator, SemiMarkovSimulator

def lambda_handler(event, context=None):
    n_residents = event['n_residents']
    household_type = event['household_type']
    n_households = event['n_households']
    appliance = event["appliance"]
    subgroups = [{'n_residents': n_residents, 'household_type': household_type, 'weekday':[1,2,3,4,5]}]
    usage_patterns = event["usage_patterns"]
    print("\nusage_patterns = ", usage_patterns)
    load = load_calculator(hh_subgroups=subgroups, usage_patterns=usage_patterns, appliance=appliance)
    print("\nLOAD CALCULATED SUCCESSFULLY\n")
    return {
        "load": load.tolist()
    }

def rejection_sampling(
        num_samples: int, x_min: float, x_max: float, profile: np.ndarray
    ):
    """ Sample from given distribution within an interval x_min-x_max
    """   
    x = np.random.randint(x_min, x_max, num_samples)
    u = np.random.uniform(np.zeros_like(x), max(profile[x_min:x_max]))
    (idx,) = np.where(u < profile[x])
    return x[idx], len(idx) / num_samples
   

def slice_profile(profile, interval):
    """ Slicing function from array, which handles consecutive and 
    non consecutive intervals    
    """
    if interval[0] < interval[1]:
        return profile[interval[0]:interval[1]]
    else:
        return np.append(profile[0:interval[1]], profile[interval[0]:]) 
    

def weighted_profile(profile, weights, intervals, n_cycles = 10000):
    """ Function to weight various intervals of a distribution differently
    """
    
    avg_weights = np.asarray([])
    avg_profile = np.asarray([])
    
    for interval in intervals:        
        val_prof_interval = slice_profile(profile, interval)      
        avg_profile = np.append(avg_profile, [np.mean(val_prof_interval)] * len(val_prof_interval))
        
        val_weight_interval = slice_profile(weights, interval)         
        avg_weights = np.append(avg_weights, [np.mean(val_weight_interval)] * len(val_weight_interval))
    
    output = np.roll(profile,-intervals[0][0]) / avg_profile   * avg_weights / sum(avg_weights) * n_cycles
    output = np.roll(output,intervals[0][0])
    
    return output



def load_calculator(
        hh_subgroups : list,        
        n_hh_list : list = [1000],
        start_datetime : datetime.datetime = datetime.datetime(2014, 4, 1, 0, 0, 0),
        data = GermanDataHerus(version='v1.1'),
        appliance : str = None,
        usage_patterns : dict = None,
        ) -> float:
    """
    Simulator of the average daily load profile for wet appliances
    washing machine and dishwasher.
    """
    
    # initialization activitity simulatore
    sim_act = SubgroupsIndividualsActivitySimulator(
        hh_subgroups,
        n_hh_list,
        subsimulator=SemiMarkovSimulator,
        data=data,
        start_datetime = start_datetime,
        use_week_ends_days=True,
        logger=SimLogger('get_activity_states', aggregated=False)
    )
    
    # run the simulation for 1 day
    for i in range(144):
        # update activity every 10 min    
        sim_act.step()
    
    # retrieve the simulated load profile 
    # DIM0: min of the day, DIM1: households, DIM2: appliances
    activities = sim_act.logger.get('get_activity_states')
    
    standard_dict = {'morning':[6*6,10*6],
                      'midday':[10*6,14*6],
                      'afternoon':[14*6,18*6],
                      'evening':[18*6,22*6],
                      'night':[22*6,6*6],
                      }
    
    dict_activities = {'DISH_WASHER':'dishwashing',
                       'WASHING_MACHINE':'laundry'}

    # weight the activity profile based on usage patterns day prob profile
    weighted_act = weighted_profile(
                    profile=activities[dict_activities[appliance]].sum(axis=1),
                    weights=usage_patterns['day_prob_profiles'][appliance],
                    intervals=list(standard_dict.values()),
                    )
    
    weighted_act = [round(x) for x in weighted_act]    
    
    # estimate the load of of the activity profile
    power_rating = {'DISH_WASHER':np.ones(6),
                    'WASHING_MACHINE':  np.mean(np.array([73] * (9-0) +\
                                                 [2056] * (30-9) +\
                                                 [73] * (82-30) +\
                                                ([73] * 11 + [250] * 2) * 4 +\
                                                 [568] * (139-133)
                                                 ).reshape(-1, 10)
                                                , axis=1)
                }
    len_cycle = len(power_rating[appliance])
    cycle = power_rating[appliance]
    load_profile0 = np.append(cycle, np.zeros(144-len(cycle)))
    load_profiles = load_profile0[:,np.newaxis]
    
    for i in range(1,144):        
        load_profiles = np.append(load_profiles, 
                                  np.roll(load_profile0,i)[:,np.newaxis], 
                                  axis=1)
    
    unweighted_load =np.sum( load_profiles * weighted_act, axis=1)
    
    # weight the mean daily load based on number of cycles
    if usage_patterns:
        if 'target_cycles' in usage_patterns.keys():
            if appliance:
                P_standby = 3 # [W]
                # Energy per cycle 
                # E cycle =  E_tot_cycle [kWh]- P_standby [W] * lenghty cycle [10 min] * 10 [10min/min]/ 60 [min/h] / 1000 [W/kW]
                E_cycle = usage_patterns['energy_cycle'][appliance] - P_standby * len_cycle * 10 / 60 / 1000 
                # Weighting factor
                # N° cycles [cycles/year] * E cycle [kWh/cycle] / n days year [days/year] * 6 [10min/h] / (E cycles simulated [no energy unit * 10min] ) 
                weight = usage_patterns['target_cycles'][appliance] * E_cycle / 365.25 * 6 / unweighted_load.sum() * 1000 # [W10min/-]
                weighted_load = unweighted_load * weight + P_standby 
    
    output = np.repeat(weighted_load,10)
    
    return output
                     
    
   
