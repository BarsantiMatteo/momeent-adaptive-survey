from flask import Flask, request, render_template, jsonify, session, abort
import os, sys, json
import datetime
import numpy as np
import secrets
import conf.credentials as conf
import math 
from decimal import Decimal
import pandas as pd
import matplotlib.pyplot as plt

#module_path = "/home/faten/HERUS/MoMeEnT-Project/web_interface/src/" #TODO change this
module_path1 = os.path.abspath(os.path.join('../..')) 
module_path2 = module_path1 +'/load_simulator'
module_path3 = module_path2 +'/demod'
for mpath in [module_path1, module_path2, module_path3]:
    print(mpath)
    if mpath not in sys.path:
        sys.path.append(mpath)

from load_simulator.demod_load_simulator import get_avg_load_profile

def generate_profile(values_dict):
    raw_profile = np.asarray([values_dict['night']] * 2  + \
                             [values_dict['morning']] * 4  + \
                             [values_dict['midday']] * 4  + \
                             [values_dict['afternoon']] * 4  + \
                             [values_dict['evening']] * 4  + \
                             [values_dict['night']] * 6 
                            )
    return raw_profile 

values_dict = {0: {'morning':1,
                   'midday':0,
                   'afternoon':0,
                   'evening':0,
                   'night':0
                   },
               1: {'morning':0,
                    'midday':0,
                    'afternoon':1,
                    'evening':0,
                    'night':0
                    },
               2: {'morning':0,
                    'midday':1,
                    'afternoon':0,
                    'evening':0,
                    'night':0
                    }
               
               }
               

n_households = 1000

# profile = np.ones((n_households, 24))
# arr = generate_profile(values_dict)
# profile = np.array([arr for _ in range(n_households)])
# usage_patterns = {'target_cycles':{'DISH_WASHER':251,
#                                     'WASHING_MACHINE':100},
#                   'day_prob_profiles':{'DISH_WASHER':profile.tolist(),  
#                                        'WASHING_MACHINE':profile.tolist()
#                                        },
#                     'energy_cycle': {'DISH_WASHER': 1, 'WASHING_MACHINE':1}
#                 }

n_residents = 2
household_type = 2
appliance='DISH_WASHER'

loads = {}

for i in range(3):
    
    arr = generate_profile(values_dict[i])
    profile = np.array([arr for _ in range(n_households)])
    usage_patterns = {'target_cycles':{'DISH_WASHER':251,
                                        'WASHING_MACHINE':100},
                      'day_prob_profiles':{'DISH_WASHER':profile.tolist(),  
                                           'WASHING_MACHINE':profile.tolist()
                                           },
                        'energy_cycle': {'DISH_WASHER': 1, 'WASHING_MACHINE':1}
                    }
    

    loads[i] = get_avg_load_profile(n_residents=n_residents,
                                household_type=household_type,
                                usage_patterns=usage_patterns,
                                appliance=appliance, 
                                n_households=n_households)



fig, ax = plt.subplots()

for i in range(3):
    ax.plot(loads[i])
    print(f'Total load {i}: ', sum(loads[i]))

plt.show()
