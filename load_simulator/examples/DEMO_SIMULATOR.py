import os
import sys
import json
import numpy as np
import pandas as pd
import datetime
from datetime import timedelta

    
module_path = os.path.dirname(os.path.dirname(__file__))
if module_path not in sys.path:
    sys.path.append(module_path)

from demod.datasets.Germany.loader import GermanDataHerus
from demod.simulators.appliance_simulators import (ActivityApplianceSimulator, 
                                                   ProbabilisticActivityAppliancesSimulator, 
                                                   AvailableOccupancyApplianceSimulator)
from demod.simulators.base_simulators import SimLogger
from demod.simulators.activity_simulators import SubgroupsIndividualsActivitySimulator, SemiMarkovSimulator, MarkovChain1rstOrder


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
        use_week_ends_days=True
    )
    
    # initialization appliance simulator
    if appliance == 'WASHING_MACHINE':
        wet_appliances = np.zeros((n_hh_list[0],32), dtype=bool)
        wet_appliances[:,(-5)] = True
    elif appliance == 'DISH_WASHER':
        wet_appliances = np.zeros((n_hh_list[0],32), dtype=bool)
        wet_appliances[:,(-7)] = True
    else:
        raise ValueError('Appliance type not recognized: please pass'
                         'either washing_mahcine or dishwasher')
        
    sim_app = AvailableOccupancyApplianceSimulator(
        subgroups_list=hh_subgroups,  
        initial_active_occupancy=sim_act.get_activity_states()['other'],
        start_datetime=start_datetime,
        n_households_list=n_hh_list,
        equipped_sampling_algo="set_defined",
        equipped_set_defined=wet_appliances,
        data=data,
        usage_patterns=usage_patterns,
        logger=SimLogger('get_current_power_consumptions', aggregated=False)
    )
    
    
    # run the simulation for 1 day
    for i in range(144):

        for i in range(10):       
            # update load every 1 min
            sim_app.step(sim_act.get_activity_states()['other']+
                         sim_act.get_activity_states()['dishwashing']+
                         sim_act.get_activity_states()['laundry']
                         )
        # update activity every 10 min    
        sim_act.step()
    
    # retrieve the simulated load profile 
    # DIM0: min of the day, DIM1: households, DIM2: appliances
    loads = sim_app.logger.get('get_current_power_consumptions')
    
    # mean profile over the 1000 households simulated
    mean_load = np.mean(loads, axis=1).sum(axis=1)

    
    # weight the load based on number of cycles
    if usage_patterns:
        if 'target_cycles' in usage_patterns.keys():
            if appliance:
                weight = usage_patterns['target_cycles'][appliance][0] * usage_patterns['energy_cycle'][appliance] * 60 * 1000 / mean_load.sum()  / 365.25
                final_load = mean_load * weight
    
    return final_load


if __name__ == "__main__":
    event = {
        "n_residents": 1,
        "household_type": 1
    }
    lambda_handler(event)
    
    
