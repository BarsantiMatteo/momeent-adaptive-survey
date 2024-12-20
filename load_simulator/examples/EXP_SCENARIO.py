"""
DEMO FILE FOR QUALTRICS API INTEGRATION
"""

import os
import sys

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
import datetime
from datetime import timedelta
import time

module_path = os.path.abspath(os.path.join('..'))
if module_path not in sys.path:
    sys.path.append(module_path)

from demod.datasets.Germany.loader import GermanDataHerus

from EXP_SIMULATOR import load_calculator


#%% INPUTS

"""
For the time being, we can simplify the problem and consider only the type of 
household and the number of residents as input. The input dictionary is as follows:
    - 'n_residents' : int from 1 to 5
    - 'household_type' : int from 1 to 5
        1 = One person household
        2 = Couple without kid
        3 = Single Parent with at least one kid under 18 and the other under 27
        4 = Couple with at least one kid under 18 and the other under 27
        5 = Others
        
        subgroups = [{'n_residents': 1, 'household_type': 1, 'weekday':[1,2,3,4,5]},
                      {'n_residents': 2, 'household_type': 2, 'weekday':[1,2,3,4,5]},
                      {'n_residents': 2, 'household_type': 3, 'weekday':[1,2,3,4,5]},
                      {'n_residents': 3, 'household_type': 3, 'weekday':[1,2,3,4,5]},
                      {'n_residents': 3, 'household_type': 4, 'weekday':[1,2,3,4,5]},
                      {'n_residents': 4, 'household_type': 4, 'weekday':[1,2,3,4,5]},
                      {'n_residents': 5, 'household_type': 4, 'weekday':[1,2,3,4,5]}]
        hh_subgroups = [subgroups[0]]
        n_hh_list = [n_households]
        type of hh: 1 single, 2 couple without children, 3 single parent, 4 couple with childrens
"""


# From qualtrics
subgroups = [{'n_residents': 2, 'household_type': 2, 'weekday':[1,2,3,4,5]}]
n_households = 10000

# Other inputs
# From qualtrics
wm_cycles = 3
dw_cycles = 4
dict_progr = {}
dict_progr['DISH_WASHER'] = {'ECO':1,
                             'Normal':3,
                             'Intensive':2,
                             'Auto':2,
                             'Gentle':0,
                             'Quick low':1,
                             'Quick high':0,
                             }

dict_progr['WASHING_MACHINE'] = {'30°C':1,
                                 '40-45°C':3,
                                 '55-60°C':2,
                                 '90°C':6,
                                }
# From adaptive-experiment
values_dict = {'morning':0,
               'midday':1,
               'afternoon':1,
               'evening':1,
               'night':1,
               }

# Other static inputs
n_households = 10000


#%% INPUTS PREPARATION

# appliance usage pattern 
usage_patterns = {'target_cycles':{},
                  'day_prob_profiles':{},
                  'energy_cycle':{},
                  }


# number of cycles 
usage_patterns['target_cycles']['DISH_WASHER'] = int(dw_cycles * 52)
usage_patterns['target_cycles']['WASHING_MACHINE'] = int(wm_cycles * 52)


# usage profiles
def movingaverage(interval, window_size):
    window = np.ones(int(window_size))/float(window_size)
    return np.convolve(interval, window, 'same')


def generate_profile(values_dict):
    raw_profile = np.asarray([values_dict['night']] * 6 * 6  +\
                             [values_dict['morning']] * 4 * 6 + \
                             [values_dict['midday']] * 4 * 6+ \
                             [values_dict['afternoon']] * 4 * 6+ \
                             [values_dict['evening']] * 4 * 6+ \
                             [values_dict['night']] * 2 * 6                             
                            )
    # profile = movingaverage(raw_profile, 3)
    return raw_profile

usage_patterns['day_prob_profiles']['DISH_WASHER'] = generate_profile(values_dict)
usage_patterns['day_prob_profiles']['WASHING_MACHINE'] = generate_profile(values_dict)


# average energy intensity per cycle
usage_patterns['energy_cycle']['DISH_WASHER'] = (dict_progr['DISH_WASHER']['ECO'] * 0.9 + \
                                                dict_progr['DISH_WASHER']['Normal'] * 1.1 + \
                                                dict_progr['DISH_WASHER']['Intensive'] * 1.44 + \
                                                dict_progr['DISH_WASHER']['Auto'] * 0.93 + \
                                                dict_progr['DISH_WASHER']['Gentle'] * 0.65 + \
                                                dict_progr['DISH_WASHER']['Quick low'] * 0.8 + \
                                                dict_progr['DISH_WASHER']['Quick high'] * 1.3 ) / \
                                                sum(dict_progr['DISH_WASHER'].values())

avg_wm_temp = (dict_progr['WASHING_MACHINE']['30°C'] * 30 + \
               dict_progr['WASHING_MACHINE']['40-45°C'] * 42.5 + \
               dict_progr['WASHING_MACHINE']['55-60°C'] * 57.5 + \
               dict_progr['WASHING_MACHINE']['90°C'] * 90) / \
               sum(dict_progr['WASHING_MACHINE'].values())
 
usage_patterns['energy_cycle']['WASHING_MACHINE'] = 0.95 + 0.02 * (avg_wm_temp - 60)


#%% SIMULATION

start = time.time()

# TODOs
# 1. remove moving average
# 2. update generate_profile (start from 0am and remove moving average)
# 3. usage patterns --> day prob profile single array 
# 4. usage patterns --> target cycle int 

appliance = 'WASHING_MACHINE'

load = load_calculator(
        hh_subgroups = subgroups,        
        n_hh_list = [n_households],
        start_datetime = datetime.datetime(2014, 4, 1, 0, 0, 0),
        data = GermanDataHerus(version='v1.1'),
        appliance=appliance,
        usage_patterns = usage_patterns,
        )


end = time.time()
print('The simulation took {:0.1f} s'.format(end-start))



fig, ax = plt.subplots()
ax.plot(range(len(load)), load)
ax1 = ax.twinx()
esp_profile = np.repeat(usage_patterns['day_prob_profiles'][appliance], 10)
ax1.plot(range(len(esp_profile)), esp_profile)
plt.show()
print('total energy consumption {:0.2f} kWh/day'.format(sum(load)/60/1000))





