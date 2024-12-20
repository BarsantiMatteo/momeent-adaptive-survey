import os
import sys
import json
import numpy as np
import pandas as pd
import datetime
from datetime import timedelta
from typing import Dict, Optional

# Add module paths for custom imports
MODULE_PATH = os.path.dirname(os.path.dirname(__file__))
SIMULATOR_PATH = os.path.join(MODULE_PATH, 'load_simulator')
if SIMULATOR_PATH not in sys.path:
    sys.path.append(SIMULATOR_PATH)

# Importing custom modules
from demod.datasets.Germany.loader import GermanDataHerus
from demod.simulators.appliance_simulators import (
    ActivityApplianceSimulator,
    ProbabilisticActivityAppliancesSimulator,
    AvailableOccupancyApplianceSimulator
)
from demod.simulators.base_simulators import SimLogger
from demod.simulators.activity_simulators import (
    SubgroupsIndividualsActivitySimulator,
    SemiMarkovSimulator,
    MarkovChain1rstOrder
)

def get_avg_load_profile(
    n_residents: int,
    household_type: str,
    n_households: int,
    start_datetime: datetime.datetime = datetime.datetime(2014, 4, 1),
    data: object = GermanDataHerus(version='v1.1'),
    appliance: Optional[str] = None,
    usage_patterns: Optional[Dict] = None
) -> np.ndarray:
    """
    Simulates the average daily load profile for specified appliances.

    Parameters:
    - n_residents: Number of residents in each household.
    - household_type: Type of household (e.g., family, single-person).
    - n_households: Total number of households to simulate.
    - start_datetime: Start time of the simulation (default: April 1, 2014).
    - data: Data object containing household activity data (default: 'GermanDataHerus').
    - appliance: The appliance to simulate ('WASHING_MACHINE' or 'DISH_WASHER').
    - usage_patterns: Dictionary with appliance usage details (e.g., target cycles, energy per cycle).

    Returns:
    - A numpy array representing the weighted load profile for the appliance.
    """
    if appliance not in ['WASHING_MACHINE', 'DISH_WASHER']:
        raise ValueError("Appliance must be 'WASHING_MACHINE' or 'DISH_WASHER'.")

    # Define household subgroups and counts
    household_subgroups = [{'n_residents': n_residents, 'household_type': household_type}]
    household_counts = [n_households]

    # Initialize the activity simulator
    activity_simulator = SubgroupsIndividualsActivitySimulator(
        household_subgroups,
        household_counts,
        subsimulator=SemiMarkovSimulator,
        data=data,
        start_datetime=start_datetime,
        use_week_ends_days=True
    )

    # Initialize the appliance configuration
    wet_appliances = np.zeros((household_counts[0], 32), dtype=bool)
    if appliance == 'WASHING_MACHINE':
        wet_appliances[:, -5] = True
    elif appliance == 'DISH_WASHER':
        wet_appliances[:, -7] = True

    # Initialize the appliance simulator
    appliance_simulator = AvailableOccupancyApplianceSimulator(
        subgroups_list=household_subgroups,
        initial_active_occupancy=activity_simulator.get_activity_states()['other'],
        start_datetime=start_datetime,
        n_households_list=household_counts,
        equipped_sampling_algo="set_defined",
        equipped_set_defined=wet_appliances,
        data=data,
        usage_patterns=usage_patterns,
        logger=SimLogger('get_current_power_consumptions', aggregated=False)
    )

    # Simulate one day (1440 minutes)
    for minute in range(1440):
        # Update appliance load
        activity_state = (
            activity_simulator.get_activity_states()['other'] +
            activity_simulator.get_activity_states().get('dishwashing', 0) +
            activity_simulator.get_activity_states().get('laundry', 0)
        )
        appliance_simulator.step(activity_state)

        # Update activity states every 10 minutes
        if minute % 10 == 0:
            activity_simulator.step()

    # Retrieve the simulated load profile
    load_data = appliance_simulator.logger.get('get_current_power_consumptions')

    # Calculate the mean load over all households
    mean_hh_load = np.mean(load_data, axis=1).sum(axis=1)
    
    mask_running_hh_load = mean_hh_load > 3 # 3W is the stand-by consumption

    # Adjust the load based on usage patterns if provided
    if usage_patterns and appliance in usage_patterns['day_prob_profiles']:
        appliance_usage = usage_patterns['day_prob_profiles'][appliance]
        target_cycles = usage_patterns['target_cycles'][appliance] 
        energy_per_cycle = usage_patterns['energy_cycle'][appliance] 
        weight = (
            target_cycles * energy_per_cycle * 60 * 1000 /
            mean_hh_load[mask_running_hh_load].sum() / 365.25
        )
        weighted_load = mean_hh_load.copy()
        weighted_load[mask_running_hh_load] *= weight 
    else:
        weighted_load = mean_hh_load

    return weighted_load
