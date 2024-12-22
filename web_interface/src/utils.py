import numpy as np

def process_data(data):
    """
    Processes raw data into a dictionary of period values.
    Extracts the main period from "Period" and converts "Value" to integers.
    """
    return {
        d["Period"].split()[0]: int(d["Value"])
        for d in data
    }

def generate_profile(values_dict):
    """
    Generates a daily profile based on the provided values_dict.
    The profile is time-shifted to align with demod probability functions starting at 4:00 am.
    """
    return np.array(
        [values_dict['night']] * 2 +  # 12:00 AM - 2:00 AM
        [values_dict['morning']] * 4 +  # 4:00 AM - 8:00 AM
        [values_dict['midday']] * 4 +  # 8:00 AM - 12:00 PM
        [values_dict['afternoon']] * 4 +  # 12:00 PM - 4:00 PM
        [values_dict['evening']] * 4 +  # 4:00 PM - 8:00 PM
        [values_dict['night']] * 6    # 8:00 PM - 2:00 AM (next day)
    )

def min_profile_from_val_period(period_dict):
    """
    Generates a minute-level profile for a 24-hour period based on the given period_dict.
    Each period is repeated according to its duration in minutes.
    """
    return np.array(
        [period_dict['night']] * (6 * 60) +  # 12:00 AM - 6:00 AM
        [period_dict['morning']] * (4 * 60) +  # 6:00 AM - 10:00 AM
        [period_dict['midday']] * (4 * 60) +  # 10:00 AM - 2:00 PM
        [period_dict['afternoon']] * (4 * 60) +  # 2:00 PM - 6:00 PM
        [period_dict['evening']] * (4 * 60) +  # 6:00 PM - 10:00 PM
        [period_dict['night']] * (2 * 60)    # 10:00 PM - 12:00 AM
    )


