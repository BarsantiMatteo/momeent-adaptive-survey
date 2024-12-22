import numpy as np

# Number of households
n_households = 500

# Usage patterns for appliances
usage_patterns = {
    'target_cycles': {
        'DISH_WASHER': 251,
        'WASHING_MACHINE': 100
    },
    'day_prob_profiles': {
        'DISH_WASHER': np.ones((n_households, 24)).tolist(),  # Probability profiles (uniform by default)
        'WASHING_MACHINE': np.ones((n_households, 24)).tolist()
    },
    'energy_cycle': {
        'DISH_WASHER': 1,  # Energy consumption per cycle (kWh)
        'WASHING_MACHINE': 1
    }
}

# Electricity prices by time of day (in EUR/kWh) for Germany
price_dict_DE = {
    'morning': 0.467,
    'midday': 0.334,
    'afternoon': 0.346,
    'evening': 0.512,
    'night': 0.375
}

# Electricity prices by time of day (in CHF/kWh) for Switzerland
price_dict_CH = {
    'morning': 0.310,
    'midday': 0.222,
    'afternoon': 0.229,
    'evening': 0.340,
    'night': 0.249
}

# Renewable energy supply (RES) percentages by time of day
RES_dict = {
    'morning': 47.8,
    'midday': 69.9,
    'afternoon': 33.3,
    'evening': 0.0,
    'night': 0.0
}