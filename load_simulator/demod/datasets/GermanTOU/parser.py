"""This file contains the parser for the German data
"""

import os
import warnings
import datetime
import pandas as pd
import numpy as np
from ...utils.sim_types import Subgroup
from ...utils.sparse import SparseTPM
from ...utils.parse_helpers import (
    convert_states,
    get_initial_durations_pdfs,
    states_to_tpms,
    states_to_tpms_with_durations,
    states_to_transitions,
    replace_with_dict,
)

MAX_PEOPLE_HOUSEHOLD = 6 + 1  # always need to get one above the real max pple

dir_name = os.path.dirname(os.path.realpath(__file__))
file_path = os.path.join(dir_name, 'raw_data', 'zve13_puf_')
try:
    df_hh = pd.read_csv(file_path+'hh.csv', sep=';')
    df_akt = pd.read_csv(file_path+'takt.csv', sep=';')
    df_pers = pd.read_csv(file_path+'pers.csv', sep=';')
except FileNotFoundError:
    msg = ''.join(('Impossible to find the database files for Germany,',
        'if you have access to them, you must put them in ',
        '"{}****.csv"')).format(file_path)
    raise Exception(msg)


# missing data, fehl_tag means there is one day not in the records
#df_akt['fehl_tag'] > 0


# read the states from file
primary_states      = df_akt[['tb1_' + str(i) for i in range(1,145)]].to_numpy()
# get the secondary states
secondary_states    = df_akt[['tb2_' + str(i) for i in range(1,145)]].to_numpy()
# transportation mean
transportation_mean = df_akt[['tb3_' + str(i) for i in range(1,145)]].to_numpy()
# transportation mean
transportation_was_alone_filled = ~np.array(df_akt[['tb4_' + str(i) for i in range(1,145)]].to_numpy(), dtype= bool) # 1 means not filled so we change sign
transportation_was_alone = np.array(df_akt[['tb5_' + str(i) for i in range(1,145)]].to_numpy(), dtype= bool)
# if the person was travelling that day
travelling          = np.array(df_akt['tc5'])
# wheter the participant started at home
initial_location    = np.array(df_akt['tc7'])
final_location      = np.array(df_akt['tc8'])
# 'trifft nicht zu' = -2 and means that the start location of the next day should be used
final_location[final_location==-2] = np.roll(initial_location, 1)[final_location==-2]

# get a link between df_akt and df_pers
df_akt_index_person = np.array([np.where(df_pers['id_persx'] == i)[0][0] for i in df_akt['id_persx']])
df_hh_max_recorded_persons = np.array([np.max(df_akt['persx'][df_akt['id_hhx']==i]) for i in df_hh['id_hhx']])

df_hh_mean_age = np.array([np.average(df_pers['alterx'][df_pers['id_hhx']==i]) for i in df_hh['id_hhx']])


# axis that starts at 4
ten_minutes_axis = np.array([i for i in range(144)])/6 + 4


def get_mask_subgroup(
    only_fully_recorded_household=True, remove_missing_days=True,
    only_household_identical_days=True,
    quarter=None, weekday=None,
    n_residents=None, household_type=None,
    salary = None, hh_revenue=None,
    hh_work_type = None,
    family_situation=None,
    life_situation=None, hh_mean_age=None, age=None, geburtsland=None,
    gender=None, household_position=None,
    is_travelling=None):
    """From the german TOU, get a subgroup of diaries satifying the multiple possible kwargs arg as input
    Merges the conditionality of different parameters. Such that all the diaries indexes given as the output
    satisfy the requested inputs.

    Args:
        only_fully_recorded_household (bool, optional): return housholds where all participants have filled the survey. Defaults to True.
        remove_missing_days (bool, optional): If a participant did not record one of the diaries, remove the uncompleted day for the whole household. Defaults to True.
        only_household_identical_days (bool, optional): Returns only the households where all diaries have been recorded on the same day. Defaults to True.
        quarter (int, optional): The quarter of the year to use (1=Jan-March, 2=Apr-Jun, 3=Jul-Sep, 4=Sep-Dec). Defaults to None.
        weekday (int or list, optional): The day of the week to use (1=Mon, 2=Tue, ...), if list take all the days in list. Defaults to None.
        n_residents (int, optional): The number of residents in the household. Defaults to None.
        household_type (int, optional): The type of the household (
            1 = Einpersonenhaushalt,
            2 = Paare ohne Kinder,
            3 = Alleinerziehende mit mindestens einem Kind unter18 Jahren und ledigen Kindern unter 27 Jahren,
            4= Paare mit mindestens einem Kind unter 18 Jahren und ledigen Kindernledigen Kindern unter 27 Jahren, 
            5 = Sonstige Haushalte). Defaults to None.
        hh_work_type (str):

        life_situation (int, optional): (
            1 = Selbstständiger,Freiberufler, Landwirt,mithelfender Familienangehöriger,
            2 = Angestellter, Arbeiter, Beamter,Richter, Zeit-/Berufs-soldat, Freiwilligsoziales/ökologisches/kulturelles Jahr,freiwilliger Wehrdienst, Bundesfreiwilligendienst
            3 = Auszubildender (auch Praktikant,Volontär)
            4 = In Altersteilzeit (Arbeits-und Freistellungsphase)
            5 = In Elternzeit (mit ungekündigtem Arbeitsvertrag)
            6 = Schüler, Student
            7 = Arbeitslos
            8 = Im Ruhestand oder Vorruhestand
            9 = Dauerhaft erwerbsunfähig
            10 = Hausfrau/Hausmann
            11 = Ausanderen Gründen nicht erwerbstätig.) Defaults to None.
        age (int or tuple, optional): The age of the participants, if tuple returns all inside interval. Defaults to None.
        geburtsland (int, optional): 1 = Deutschland2 = Übrige Europäische Union, sonstiges Land. Defaults to None.
        gender (int, optional): 1 = man, 2 = woman. Defaults to None.
        household_position (int, optional): The role of that person in the household (1 =Haupteinkommensbezieher, 2 =Ehe-, Lebenspartner/-in, 3 =Kind, 4 =Bruder/Schwester, 5=Enkelkind, 6=Vater/Mutter, 7 = Großvater/Großmutter, 8=Anders verwandt/verschwägert , 9=Nicht verwandt/verschwägert). Defaults to None.
        is_travelling (bool, optional): Not impoelmented yet. Defaults to None.

    Returns:
        ndarray(bool): Mask of the diaries
    """

    _mask = np.ones(len(df_akt), dtype=bool)

    if only_fully_recorded_household:
        # check if the diary is in the list of household that have the number of records=number of people living their
        _mask &= np.isin(df_akt['id_hhx'],df_hh['id_hhx'][df_hh['ha1x']-df_hh_max_recorded_persons == 0])

    if remove_missing_days:
        hh_with_missing_day = np.array(df_akt['id_hhx'][df_akt['fehl_tag']!=0])[::2] # work-around trick as there are three days in general and only two if there is a missing day
        missing_day = np.array(df_akt['fehl_tag'][df_akt['fehl_tag']!=0])[::2]
        # remove households where there is a survey missing on a particular day
        _mask &= ~np.logical_or.reduce([ (df_akt['id_hhx'] == hh) & (df_akt['tagnr'] == day) for hh, day in zip(hh_with_missing_day,missing_day)])

    if only_household_identical_days:
        # only keep if the diary has been recorded on the same day for all occupants
        _mask &= (np.array(df_akt['selbtag']) == 1) | (np.array(df_hh['ha1x'][df_akt['id_hhx']-1]) == 1)

    if quarter:
        assert quarter <= 4 and quarter > 0, 'quarter value must be 1,2,3 or 4'
        _mask &= np.array(df_akt['quartal']) == quarter

    if weekday:
        if isinstance(weekday, list):
            _mask &= np.logical_or.reduce([get_mask_subgroup(weekday=i) for i in weekday])
        else:
            assert weekday <= 7 and weekday > 0, 'weekday value must be 1,2,3,4,5,6 or 7'
            _mask &= np.array(df_akt['wtagfei']) == weekday

    if n_residents:
        if isinstance(n_residents, list):
            _mask &= np.logical_or.reduce([get_mask_subgroup(n_residents=i) for i in n_residents])
        else:
            assert n_residents <= 6 and n_residents > 0, 'n_residents value must be 1,2,3,4,5 or 6'
            _mask &= np.array(df_hh['ha1x'][df_akt['id_hhx']-1]) == n_residents

    if hh_work_type:
        if hh_work_type == '1_fulltime':
            _mask &= np.array(df_hh['anz_erw'][df_akt['id_hhx']-1]) == 2
        elif hh_work_type == '1_halftime':
            _mask &= np.array(df_hh['anz_erw'][df_akt['id_hhx']-1]) == 3
        elif hh_work_type == '2_fulltime':
            _mask &= np.array(df_hh['anz_erw'][df_akt['id_hhx']-1]) == 4
        elif hh_work_type == '1_fulltime_1_halftime':
            _mask &= np.array(df_hh['anz_erw'][df_akt['id_hhx']-1]) == 5
        elif hh_work_type == '3_fulltime':
            _mask &= np.array(df_hh['anz_erw'][df_akt['id_hhx']-1]) == 6
        elif hh_work_type == 'other':
            _mask &= np.array(df_hh['anz_erw'][df_akt['id_hhx']-1]) == 7
        elif hh_work_type == '1_retired':
            _mask &= get_mask_subgroup(n_residents=1, life_situation=8)
        elif hh_work_type == '2_retired':
            # get the households where there are 2 retired
            hh_2res = df_hh['id_hhx'][df_hh['ha1x'] == 2]
            # gets the lebensituation of the 2 pple hhs
            jobs = [
                df_pers['pb3'][df_pers['id_hhx'] == hh_id].to_numpy()
                for hh_id in hh_2res]
            # Check the lebensituation of the 2 pple hhs is
            # Im Ruhestand oder Vorruhestand
            hh_2ret = [
                hh_id for hh_id, job in zip(hh_2res, jobs)
                if job[0] == 8 and job[1] == 8]

            _mask &= np.isin(df_akt['id_hhx'], hh_2ret)

        else:
            raise ValueError("Unkown key for subgroup['hh_work_type'] : "
                "{}".format(hh_work_type))

    if household_type:
        assert household_type <= 5 and household_type > 0, 'household_type value must be 1,2,3,4,5'
        _mask &= np.array(df_hh['hhtyp'][df_akt['id_hhx']-1]) == household_type

    if life_situation:
        if isinstance(life_situation, list):
            _mask &= np.logical_or.reduce([get_mask_subgroup(life_situation=i) for i in life_situation])
        elif isinstance(life_situation, dict):
            # individual life situation for all households memebers
            # get households with the corresponding life situations
            raise NotImplementedError()

        else:
            assert life_situation <= 11 and life_situation > 0, 'life_situation value must be 1 to 11'
            _mask &= np.array(df_pers['pb3'][df_akt_index_person]) == life_situation

    if salary:
        assert salary <= 5 and salary > 0, 'life_situation value must be 1 to 5'
        _mask &= np.array(df_pers['pe23x'][df_akt_index_person]) == salary

    if hh_revenue:
        assert hh_revenue <= 5 and hh_revenue > 0, 'hh_revenue value must be 1 to 5'
        revenue = np.array(df_hh['hd15x'][df_akt['id_hhx']-1])
        _mask &= revenue == hh_revenue

    if household_position:
        assert household_position <= 9 and household_position > 0, 'household_position value must be 1,2,3,4,5,6,7,8 or 9'
        _mask &= np.array(df_pers['ha6x'][df_akt_index_person]) == household_position

    if age:

        assert isinstance(age, tuple), 'age arg must be a tuple'
        assert age[0] <= age[1], 'age first value must be less or equal than the second'
        ages = np.array(df_pers['alterx'][df_akt_index_person])
        _mask &= (ages >= age[0]) & (ages < age[1])

    if hh_mean_age:

        assert isinstance(hh_mean_age, tuple), 'hh_mean_age arg must be a tuple'
        assert hh_mean_age[0] <= hh_mean_age[1], 'hh_mean_age first value must be less or equal than the second'
        ages = np.array(df_hh_mean_age[df_akt['id_hhx']-1])
        _mask &= (ages >= hh_mean_age[0]) & (ages < hh_mean_age[1])

    if geburtsland:
        assert geburtsland <= 2 and geburtsland > 0, 'geburtsland value must be 1 or 2'
        _mask &= np.array(df_pers['ha8x'][df_akt_index_person]) == geburtsland

    if gender:
        assert gender <= 2 and gender > 0, 'gender value must be 1 or 2'
        _mask &= np.array(df_pers['ha3'][df_akt_index_person]) == gender


    # check not empty
    if np.sum(_mask) == 0:
        warnings.warn('Empty subgroup : detected in select subgroups.', RuntimeWarning)

    return  _mask




#  various functions for transforming the data
# convert states to indices using a rule
# -2 is sure not home, 2 is sure home, 1,-1 are probably and 0 is unsure
dic_home = {
    0 : 0,
    110 : 1,
    120 : 1,
    131 : 1,
    132 : 1,
    139 : 2,
    210 : -1,
    220 : -1,
    230 : -1,
    241 : -1,
    242 : 0,
    243 : -1,
    244 : -1,
    245 : -1,
    249 : -1,
    311 : -2,
    312 : -2,
    313 : -2,
    314 : -2,
    315 : -2,
    317 : -2,
    319 : -2,
    321 : -2,
    329 : -2,
    330 : -2,
    341 : -2,
    349 : -2,
    353 : 1,
    354 : 1,
    361 : 1,
    362 : -2,
    363 : -2,
    364 : -2,
    369 : 0,
    411 : 2,
    413 : 2,
    412 : 2,
    414 : 2,
    419 : 2,
    421 : 2,
    422 : 2,
    423 : 2,
    429 : 2,
    431 : 2,
    432 : 2,
    433 : 2,
    434 : 2,
    439 : 2,
    441 : 2,
    442 : 2,
    443 : 2,
    444 : 2,
    445 : 2,
    446 : 2,
    449 : 2,
    451 : 2,
    452 : 2,
    453 : 2,
    454 : 2,
    455 : 2,
    459 : 2,
    461 : -2,
    464 : -1,
    465 : -1,
    466 : -1,
    469 : -1,
    471 : 2,
    472 : 2,
    473 : 2,
    474 : 2,
    475 : 2,
    476 : 2,
    479 : 2,
    480 : 0,
    491 : 1,
    492 : 1,
    499 : 1,
    510 : -1,
    520 : -1,
    531 : -2,
    532 : -1,
    539 : -1,
    611 : 0,
    612 : 0,
    621 : -2,
    622 : -2,
    623 : -2,
    624 : -2,
    625 : -2,
    626 : -2,
    627 : -2,
    629 : 0,
    630 : 0,
    641 : 0,
    642 : 0,
    649 : 0,
    711 : -2,
    712 : -2,
    713 : -2,
    715 : -2,
    716 : -2,
    717 : -2,
    719 : -2,
    730 : 0,
    740 : 1,
    752 : 0,
    759 : 0,
    761 : 0,
    762 : 0,
    763 : 1,
    769 : 0,
    790 : -1,
    811 : 0,
    812 : 0,
    813 : 1,
    814 : 1,
    815 : 1,
    819 : 1,
    820 : 2,
    830 : 1,
    841 : 1,
    842 : 1,
    843 : 1,
    844 : 1,
    849 : 1,
    921 : -2,
    922 : -2,
    923 : -2,
    929 : -2,
    931 : -2,
    934 : -2,
    939 : -2,
    941 : -2,
    945 : -2,
    946 : -2,
    947 : -2,
    948 : -2,
    949 : -2,
    951 : -2,
    952 : -2,
    953 : -2,
    959 : -2,
    961 : -2,
    962 : -2,
    969 : -2,
    970 : -2,
    980 : -2,
    991 : -2,
    992 : -2,
    997 : 1,
    998 : 0,
    999 : 0
}


# convert to activity names
GTOU_label_to_activity = {
    0 : 'only main activity',
    110 : 'sleeping',
    120 : 'eating',
    131 : 'self_washing',
    132 : 'sleeping',
    139 : 'personal',
    210 : 'job',
    220 : 'job',
    230 : 'job',
    241 : 'job',
    242 : 'job',
    243 : 'job',
    244 : 'job',
    245 : 'job',
    249 : 'job',
    311 : 'school',
    312 : 'school',
    313 : 'school',
    314 : 'school',
    315 : 'school',
    317 : 'school',
    319 : 'school',
    321 : 'school',
    329 : 'school',
    330 : 'school',
    341 : 'school',
    349 : 'school',
    353 : 'school homework',
    354 : 'school homework',
    361 : 'school',
    362 : 'school',
    363 : 'school',
    364 : 'school',
    369 : 'school',
    411 : 'cooking',
    413 : 'cooking',
    412 : 'cooking',
    414 : 'cooking',
    419 : 'cooking',
    421 : 'cleaning',
    422 : 'cleaning',
    423 : 'cleaning',
    429 : 'cleaning',
    431 : 'laundry',
    432 : 'laundry',
    433 : 'laundry',
    434 : 'laundry',
    439 : 'laundry',
    441 : 'house work',
    442 : 'house work',
    443 : 'house work',
    444 : 'house work',
    445 : 'house work',
    446 : 'house work',
    449 : 'house work',
    451 : 'house work',
    452 : 'house work',
    453 : 'house work',
    454 : 'house work',
    455 : 'house work',
    459 : 'house work',
    461 : 'shopping',
    464 : 'shopping',
    465 : 'shopping',
    466 : 'shopping',
    469 : 'shopping',
    471 : 'family care',
    472 : 'family care',
    473 : 'family care',
    474 : 'family care',
    475 : 'family care',
    476 : 'family care',
    479 : 'family care',
    480 : 'family care',
    491 : 'family care',
    492 : 'family care',
    499 : 'family care',
    510 : 'socio-political',
    520 : 'socio-political',
    531 : 'socio-political',
    532 : 'socio-political',
    539 : 'socio-political',
    611 : 'leisure',
    612 : 'telphone',
    621 : 'leisure',
    622 : 'leisure',
    623 : 'leisure',
    624 : 'leisure',
    625 : 'leisure',
    626 : 'leisure',
    627 : 'leisure',
    629 : 'leisure',
    630 : 'leisure',
    641 : 'leisure',
    642 : 'leisure',
    649 : 'leisure',
    711 : 'leisure',
    712 : 'leisure',
    713 : 'leisure',
    715 : 'leisure',
    716 : 'leisure',
    717 : 'leisure',
    719 : 'leisure',
    730 : 'leisure',
    740 : 'leisure',
    752 : 'leisure',
    759 : 'leisure',
    761 : 'leisure',
    762 : 'leisure',
    763 : 'computer',
    769 : 'leisure',
    790 : 'leisure',
    811 : 'leisure',
    812 : 'leisure',
    813 : 'leisure',
    814 : 'leisure',
    815 : 'leisure',
    819 : 'leisure',
    820 : 'watching_tv',
    830 : 'music',
    841 : 'computer/smartphone',
    842 : 'computer/smartphone',
    843 : 'computer/smartphone',
    844 : 'computer/smartphone',
    849 : 'computer/smartphone',
    921 : 'transportation',
    922 : 'transportation',
    923 : 'transportation',
    929 : 'transportation',
    931 : 'transportation',
    934 : 'transportation',
    939 : 'transportation',
    941 : 'transportation',
    945 : 'transportation',
    946 : 'transportation',
    947 : 'transportation',
    948 : 'transportation',
    949 : 'transportation',
    951 : 'transportation',
    952 : 'transportation',
    953 : 'transportation',
    959 : 'transportation',
    961 : 'transportation',
    962 : 'transportation',
    969 : 'transportation',
    970 : 'transportation',
    980 : 'transportation',
    991 : 'transportation',
    992 : 'transportation',
    997 : 'transportation',
    998 : 'transportation',
    999 : 'transportation'
}

GTOU_label_to_energy_activity = {
    0 : '-',
    110 : 'not active',
    120 : 'eat',
    131 : 'wash self',
    132 : 'not active',
    139 : 'leisure',
    210 : 'work activity',
    220 : 'work activity',
    230 : 'work activity',
    241 : 'work activity',
    242 : 'work activity',
    243 : 'work activity',
    244 : 'work activity',
    245 : 'work activity',
    249 : 'work activity',
    311 : 'work activity',
    312 : 'work activity',
    313 : 'work activity',
    314 : 'work activity',
    315 : 'work activity',
    317 : 'work activity',
    319 : 'work activity',
    321 : 'work activity',
    329 : 'work activity',
    330 : 'work activity',
    341 : 'work activity',
    349 : 'work activity',
    353 : 'work activity',
    354 : 'work activity',
    361 : 'work activity',
    362 : 'work activity',
    363 : 'work activity',
    364 : 'work activity',
    369 : 'work activity',
    411 : 'cook',
    413 : 'cook',
    412 : 'cook',
    414 : 'cook',
    419 : 'cook',
    421 : 'house maintenance',
    422 : 'house maintenance',
    423 : 'house maintenance',
    429 : 'house maintenance',
    431 : 'laundry',
    432 : 'laundry',
    433 : 'laundry',
    434 : 'laundry',
    439 : 'laundry',
    441 : 'house maintenance',
    442 : 'house maintenance',
    443 : 'house maintenance',
    444 : 'house maintenance',
    445 : 'house maintenance',
    446 : 'house maintenance',
    449 : 'house maintenance',
    451 : 'house maintenance',
    452 : 'house maintenance',
    453 : 'house maintenance',
    454 : 'house maintenance',
    455 : 'house maintenance',
    459 : 'house maintenance',
    461 : 'house maintenance',
    464 : 'house maintenance',
    465 : 'house maintenance',
    466 : 'house maintenance',
    469 : 'house maintenance',
    471 : 'family care',
    472 : 'family care',
    473 : 'family care',
    474 : 'family care',
    475 : 'family care',
    476 : 'family care',
    479 : 'family care',
    480 : 'family care',
    491 : 'family care',
    492 : 'family care',
    499 : 'family care',
    510 : 'leisure',
    520 : 'leisure',
    531 : 'leisure',
    532 : 'leisure',
    539 : 'leisure',
    611 : 'leisure',
    612 : 'computer/smartphone',
    621 : 'leisure',
    622 : 'leisure',
    623 : 'leisure',
    624 : 'leisure',
    625 : 'leisure',
    626 : 'leisure',
    627 : 'leisure',
    629 : 'leisure',
    630 : 'leisure',
    641 : 'leisure',
    642 : 'leisure',
    649 : 'leisure',
    711 : 'leisure',
    712 : 'leisure',
    713 : 'leisure',
    715 : 'leisure',
    716 : 'leisure',
    717 : 'leisure',
    719 : 'leisure',
    730 : 'leisure',
    740 : 'leisure',
    752 : 'leisure',
    759 : 'leisure',
    761 : 'leisure',
    762 : 'leisure',
    763 : 'computer/smartphone',
    769 : 'leisure',
    790 : 'leisure',
    811 : 'leisure',
    812 : 'leisure',
    813 : 'leisure',
    814 : 'leisure',
    815 : 'leisure',
    819 : 'leisure',
    820 : 'TV',
    830 : 'music',
    841 : 'computer/smartphone',
    842 : 'computer/smartphone',
    843 : 'computer/smartphone',
    844 : 'computer/smartphone',
    849 : 'computer/smartphone',
    921 : 'transportation',
    922 : 'transportation',
    923 : 'transportation',
    929 : 'transportation',
    931 : 'transportation',
    934 : 'transportation',
    939 : 'transportation',
    941 : 'transportation',
    945 : 'transportation',
    946 : 'transportation',
    947 : 'transportation',
    948 : 'transportation',
    949 : 'transportation',
    951 : 'transportation',
    952 : 'transportation',
    953 : 'transportation',
    959 : 'transportation',
    961 : 'transportation',
    962 : 'transportation',
    969 : 'transportation',
    970 : 'transportation',
    980 : 'transportation',
    991 : 'transportation',
    992 : 'transportation',
    997 : 'leisure',
    998 : 'leisure',
    999 : 'leisure'
}

# convert to activity names to this paper https://ieeexplore.ieee.org/document/8573766
GTOU_label_to_Bottaccioli_act = {
    0 : 'other',
    110 : 'sleeping',
    120 : 'other',
    131 : 'self_washing',
    132 : 'other',
    139 : 'other',
    210 : 'other',
    220 : 'other',
    230 : 'other',
    241 : 'other',
    242 : 'other',
    243 : 'other',
    244 : 'other',
    245 : 'other',
    249 : 'other',
    311 : 'other',
    312 : 'other',
    313 : 'other',
    314 : 'other',
    315 : 'other',
    317 : 'other',
    319 : 'other',
    321 : 'other',
    329 : 'other',
    330 : 'other',
    341 : 'other',
    349 : 'other',
    353 : 'other',
    354 : 'other',
    361 : 'other',
    362 : 'other',
    363 : 'other',
    364 : 'other',
    369 : 'other',
    411 : 'cooking',
    413 : 'dishwashing',
    412 : 'cooking',
    414 : 'cooking',
    419 : 'cooking',
    421 : 'cleaning',
    422 : 'cleaning',
    423 : 'other',
    429 : 'other',
    431 : 'laundry',
    432 : 'ironing',
    433 : 'other',
    434 : 'other',
    439 : 'other',
    441 : 'other',
    442 : 'other',
    443 : 'other',
    444 : 'other',
    445 : 'other',
    446 : 'other',
    449 : 'other',
    451 : 'other',
    452 : 'other',
    453 : 'other',
    454 : 'other',
    455 : 'other',
    459 : 'other',
    461 : 'other',
    464 : 'other',
    465 : 'other',
    466 : 'other',
    469 : 'other',
    471 : 'other',
    472 : 'other',
    473 : 'other',
    474 : 'other',
    475 : 'other',
    476 : 'other',
    479 : 'other',
    480 : 'other',
    491 : 'other',
    492 : 'other',
    499 : 'other',
    510 : 'other',
    520 : 'other',
    531 : 'other',
    532 : 'other',
    539 : 'other',
    611 : 'other',
    612 : 'other',
    621 : 'other',
    622 : 'other',
    623 : 'other',
    624 : 'other',
    625 : 'other',
    626 : 'other',
    627 : 'other',
    629 : 'other',
    630 : 'other',
    641 : 'other',
    642 : 'other',
    649 : 'other',
    711 : 'other',
    712 : 'other',
    713 : 'other',
    715 : 'other',
    716 : 'other',
    717 : 'other',
    719 : 'other',
    730 : 'other',
    740 : 'other',
    752 : 'other',
    759 : 'other',
    761 : 'other',
    762 : 'other',
    763 : 'electronics',
    769 : 'other',
    790 : 'other',
    811 : 'other',
    812 : 'other',
    813 : 'other',
    814 : 'other',
    815 : 'other',
    819 : 'other',
    820 : 'watching_tv',
    830 : 'other',
    841 : 'electronics',
    842 : 'electronics',
    843 : 'electronics',
    844 : 'electronics',
    849 : 'electronics',
    921 : 'other',
    922 : 'other',
    923 : 'other',
    929 : 'other',
    931 : 'other',
    934 : 'other',
    939 : 'other',
    941 : 'other',
    945 : 'other',
    946 : 'other',
    947 : 'other',
    948 : 'other',
    949 : 'other',
    951 : 'other',
    952 : 'other',
    953 : 'other',
    959 : 'other',
    961 : 'other',
    962 : 'other',
    969 : 'other',
    970 : 'other',
    980 : 'other',
    991 : 'other',
    992 : 'other',
    997 : 'other',
    998 : 'other',
    999 : 'other'
}


GTOU_label_to_v1_act = {
    0 : 'other',
    110 : 'sleeping',
    120 : 'other',
    131 : 'self_washing',
    132 : 'other',
    139 : 'other',
    210 : 'other',
    220 : 'other',
    230 : 'other',
    241 : 'other',
    242 : 'other',
    243 : 'other',
    244 : 'other',
    245 : 'other',
    249 : 'other',
    311 : 'other',
    312 : 'other',
    313 : 'other',
    314 : 'other',
    315 : 'other',
    317 : 'other',
    319 : 'other',
    321 : 'other',
    329 : 'other',
    330 : 'other',
    341 : 'other',
    349 : 'other',
    353 : 'other',
    354 : 'other',
    361 : 'other',
    362 : 'other',
    363 : 'other',
    364 : 'other',
    369 : 'other',
    411 : 'cooking',
    413 : 'other',
    412 : 'cooking',
    414 : 'cooking',
    419 : 'cooking',
    421 : 'cleaning',
    422 : 'cleaning',
    423 : 'other',
    429 : 'other',
    431 : 'other',
    432 : 'ironing',
    433 : 'other',
    434 : 'other',
    439 : 'other',
    441 : 'other',
    442 : 'other',
    443 : 'other',
    444 : 'other',
    445 : 'other',
    446 : 'other',
    449 : 'other',
    451 : 'other',
    452 : 'other',
    453 : 'other',
    454 : 'other',
    455 : 'other',
    459 : 'other',
    461 : 'other',
    464 : 'other',
    465 : 'other',
    466 : 'other',
    469 : 'other',
    471 : 'other',
    472 : 'other',
    473 : 'other',
    474 : 'other',
    475 : 'other',
    476 : 'other',
    479 : 'other',
    480 : 'other',
    491 : 'other',
    492 : 'other',
    499 : 'other',
    510 : 'other',
    520 : 'other',
    531 : 'other',
    532 : 'other',
    539 : 'other',
    611 : 'other',
    612 : 'other',
    621 : 'other',
    622 : 'other',
    623 : 'other',
    624 : 'other',
    625 : 'other',
    626 : 'other',
    627 : 'other',
    629 : 'other',
    630 : 'other',
    641 : 'other',
    642 : 'other',
    649 : 'other',
    711 : 'other',
    712 : 'other',
    713 : 'other',
    715 : 'other',
    716 : 'other',
    717 : 'other',
    719 : 'other',
    730 : 'other',
    740 : 'other',
    752 : 'other',
    759 : 'other',
    761 : 'other',
    762 : 'other',
    763 : 'electronics',
    769 : 'other',
    790 : 'other',
    811 : 'other',
    812 : 'other',
    813 : 'other',
    814 : 'other',
    815 : 'other',
    819 : 'other',
    820 : 'watching_tv',
    830 : 'other',
    841 : 'electronics',
    842 : 'electronics',
    843 : 'electronics',
    844 : 'electronics',
    849 : 'electronics',
    921 : 'other',
    922 : 'other',
    923 : 'other',
    929 : 'other',
    931 : 'other',
    934 : 'other',
    939 : 'other',
    941 : 'other',
    945 : 'other',
    946 : 'other',
    947 : 'other',
    948 : 'other',
    949 : 'other',
    951 : 'other',
    952 : 'other',
    953 : 'other',
    959 : 'other',
    961 : 'other',
    962 : 'other',
    969 : 'other',
    970 : 'other',
    980 : 'other',
    991 : 'other',
    992 : 'other',
    997 : 'other',
    998 : 'other',
    999 : 'other'
}

# convert to activity names to the CREST consuming activities
GTOU_label_to_CREST_act = {
    0 : '-',
    110 : '-',
    120 : '-',
    131 : 'Act_WashDress',
    132 : '-',
    139 : '-',
    210 : '-',
    220 : '-',
    230 : '-',
    241 : '-',
    242 : '-',
    243 : '-',
    244 : '-',
    245 : '-',
    249 : '-',
    311 : '-',
    312 : '-',
    313 : '-',
    314 : '-',
    315 : '-',
    317 : '-',
    319 : '-',
    321 : '-',
    329 : '-',
    330 : '-',
    341 : '-',
    349 : '-',
    353 : '-',
    354 : '-',
    361 : '-',
    362 : '-',
    363 : '-',
    364 : '-',
    369 : '-',
    411 : 'Act_Cooking',
    413 : 'Act_Cooking',
    412 : 'Act_Cooking',
    414 : 'Act_Cooking',
    419 : 'Act_Cooking',
    421 : 'Act_HouseClean',
    422 : 'Act_HouseClean',
    423 : '-',
    429 : '-',
    431 : 'Act_Laundry',
    432 : 'Act_Iron',
    433 : '-',
    434 : '-',
    439 : '-',
    441 : '-',
    442 : '-',
    443 : '-',
    444 : '-',
    445 : '-',
    446 : '-',
    449 : '-',
    451 : '-',
    452 : '-',
    453 : '-',
    454 : '-',
    455 : '-',
    459 : '-',
    461 : 'shopping',
    464 : 'shopping',
    465 : 'shopping',
    466 : 'shopping',
    469 : 'shopping',
    471 : 'family care',
    472 : 'family care',
    473 : 'family care',
    474 : 'family care',
    475 : 'family care',
    476 : 'family care',
    479 : 'family care',
    480 : 'family care',
    491 : 'family care',
    492 : 'family care',
    499 : 'family care',
    510 : 'socio-political',
    520 : 'socio-political',
    531 : 'socio-political',
    532 : 'socio-political',
    539 : 'socio-political',
    611 : 'leisure',
    612 : 'telphone',
    621 : 'leisure',
    622 : 'leisure',
    623 : 'leisure',
    624 : 'leisure',
    625 : 'leisure',
    626 : 'leisure',
    627 : 'leisure',
    629 : 'leisure',
    630 : 'leisure',
    641 : 'leisure',
    642 : 'leisure',
    649 : 'leisure',
    711 : 'leisure',
    712 : 'leisure',
    713 : 'leisure',
    715 : 'leisure',
    716 : 'leisure',
    717 : 'leisure',
    719 : 'leisure',
    730 : 'leisure',
    740 : 'leisure',
    752 : 'leisure',
    759 : 'leisure',
    761 : 'leisure',
    762 : 'leisure',
    763 : 'computer',
    769 : 'leisure',
    790 : 'leisure',
    811 : 'leisure',
    812 : 'leisure',
    813 : 'leisure',
    814 : 'leisure',
    815 : 'leisure',
    819 : 'leisure',
    820 : 'Act_TV',
    830 : 'music',
    841 : 'computer/smartphone',
    842 : 'computer/smartphone',
    843 : 'computer/smartphone',
    844 : 'computer/smartphone',
    849 : 'computer/smartphone',
    921 : 'transportation',
    922 : 'transportation',
    923 : 'transportation',
    929 : 'transportation',
    931 : 'transportation',
    934 : 'transportation',
    939 : 'transportation',
    941 : 'transportation',
    945 : 'transportation',
    946 : 'transportation',
    947 : 'transportation',
    948 : 'transportation',
    949 : 'transportation',
    951 : 'transportation',
    952 : 'transportation',
    953 : 'transportation',
    959 : 'transportation',
    961 : 'transportation',
    962 : 'transportation',
    969 : 'transportation',
    970 : 'transportation',
    980 : 'transportation',
    991 : 'transportation',
    992 : 'transportation',
    997 : 'transportation',
    998 : 'transportation',
    999 : 'transportation'
}

# a second version adding the ELEC and DISHWASHER activites
GTOU_label_to_CREST_act_v2 = {
    0 : '-',
    110 : '-',
    120 : '-',
    131 : 'Act_WashDress',
    132 : '-',
    139 : '-',
    210 : '-',
    220 : '-',
    230 : '-',
    241 : '-',
    242 : '-',
    243 : '-',
    244 : '-',
    245 : '-',
    249 : '-',
    311 : '-',
    312 : '-',
    313 : '-',
    314 : '-',
    315 : '-',
    317 : '-',
    319 : '-',
    321 : '-',
    329 : '-',
    330 : '-',
    341 : '-',
    349 : '-',
    353 : '-',
    354 : '-',
    361 : '-',
    362 : '-',
    363 : '-',
    364 : '-',
    369 : '-',
    411 : 'Act_Cooking',
    413 : 'Act_Dishwashing',
    412 : 'Act_Cooking',
    414 : 'Act_Cooking',
    419 : 'Act_Cooking',
    421 : 'Act_HouseClean',
    422 : 'Act_HouseClean',
    423 : '-',
    429 : '-',
    431 : 'Act_Laundry',
    432 : 'Act_Iron',
    433 : '-',
    434 : '-',
    439 : '-',
    441 : '-',
    442 : '-',
    443 : '-',
    444 : '-',
    445 : '-',
    446 : '-',
    449 : '-',
    451 : '-',
    452 : '-',
    453 : '-',
    454 : '-',
    455 : '-',
    459 : '-',
    461 : 'shopping',
    464 : 'shopping',
    465 : 'shopping',
    466 : 'shopping',
    469 : 'shopping',
    471 : 'family care',
    472 : 'family care',
    473 : 'family care',
    474 : 'family care',
    475 : 'family care',
    476 : 'family care',
    479 : 'family care',
    480 : 'family care',
    491 : 'family care',
    492 : 'family care',
    499 : 'family care',
    510 : 'socio-political',
    520 : 'socio-political',
    531 : 'socio-political',
    532 : 'socio-political',
    539 : 'socio-political',
    611 : 'leisure',
    612 : 'telphone',
    621 : 'leisure',
    622 : 'leisure',
    623 : 'leisure',
    624 : 'leisure',
    625 : 'leisure',
    626 : 'leisure',
    627 : 'leisure',
    629 : 'leisure',
    630 : 'leisure',
    641 : 'leisure',
    642 : 'leisure',
    649 : 'leisure',
    711 : 'leisure',
    712 : 'leisure',
    713 : 'leisure',
    715 : 'leisure',
    716 : 'leisure',
    717 : 'leisure',
    719 : 'leisure',
    730 : 'leisure',
    740 : 'leisure',
    752 : 'leisure',
    759 : 'leisure',
    761 : 'leisure',
    762 : 'leisure',
    763 : 'computer',
    769 : 'leisure',
    790 : 'leisure',
    811 : 'leisure',
    812 : 'leisure',
    813 : 'leisure',
    814 : 'leisure',
    815 : 'leisure',
    819 : 'leisure',
    820 : 'Act_TV',
    830 : 'music',
    841 : 'Act_Elec',
    842 : 'Act_Elec',
    843 : 'Act_Elec',
    844 : 'Act_Elec',
    849 : 'Act_Elec',
    921 : '-',
    922 : '-',
    923 : '-',
    929 : '-',
    931 : '-',
    934 : '-',
    939 : '-',
    941 : '-',
    945 : '-',
    946 : '-',
    947 : '-',
    948 : '-',
    949 : '-',
    951 : '-',
    952 : '-',
    953 : '-',
    959 : '-',
    961 : '-',
    962 : '-',
    969 : '-',
    970 : '-',
    980 : '-',
    991 : '-',
    992 : '-',
    997 : '-',
    998 : '-',
    999 : '-'
}


GTOU_label_to_COVID_leisure = {
    0 : '-',
    110 : '-',
    120 : '-',
    131 : '-',
    132 : '-',
    139 : '-',
    210 : '-',
    220 : '-',
    230 : '-',
    241 : '-',
    242 : '-',
    243 : '-',
    244 : '-',
    245 : '-',
    249 : '-',
    311 : '-',
    312 : '-',
    313 : '-',
    314 : '-',
    315 : '-',
    317 : '-',
    319 : '-',
    321 : '-',
    329 : '-',
    330 : '-',
    341 : '-',
    349 : '-',
    353 : '-',
    354 : '-',
    361 : '-',
    362 : '-',
    363 : '-',
    364 : '-',
    369 : '-',
    411 : '-',
    413 : '-',
    412 : '-',
    414 : '-',
    419 : '-',
    421 : '-',
    422 : '-',
    423 : '-',
    429 : '-',
    431 : '-',
    432 : '-',
    433 : '-',
    434 : '-',
    439 : '-',
    441 : '-',
    442 : '-',
    443 : '-',
    444 : '-',
    445 : '-',
    446 : '-',
    449 : '-',
    451 : '-',
    452 : '-',
    453 : '-',
    454 : '-',
    455 : '-',
    459 : '-',
    461 : 'shopping',
    464 : 'shopping',
    465 : 'shopping',
    466 : 'shopping',
    469 : 'shopping',
    471 : '-',
    472 : '-',
    473 : '-',
    474 : '-',
    475 : '-',
    476 : '-',
    479 : '-',
    480 : '-',
    491 : '-',
    492 : '-',
    499 : '-',
    510 : 'canceled',
    520 : 'canceled',
    531 : 'canceled',
    532 : 'canceled',
    539 : 'canceled',
    611 : '-',
    612 : '-',
    621 : 'canceled',
    622 : 'canceled',
    623 : 'canceled',
    624 : 'canceled',
    625 : 'canceled',
    626 : 'canceled',
    627 : 'canceled',
    629 : 'canceled',
    630 : '-',
    641 : 'family-friends',
    642 : 'family-friends',
    649 : 'family-friends',
    711 : '-',
    712 : '-',
    713 : '-',
    715 : 'canceled',
    716 : 'canceled',
    717 : 'canceled',
    719 : '-',
    730 : '-',
    740 : '-',
    752 : '-',
    759 : '-',
    761 : '-',
    762 : '-',
    763 : '-',
    769 : '-',
    790 : '-',
    811 : '-',
    812 : '-',
    813 : '-',
    814 : '-',
    815 : '-',
    819 : '-',
    820 : '-',
    830 : '-',
    841 : '-',
    842 : '-',
    843 : '-',
    844 : '-',
    849 : '-',
    921 : '-',
    922 : '-',
    923 : '-',
    929 : '-',
    931 : '-',
    934 : '-',
    939 : '-',
    941 : '-',
    945 : '-',
    946 : 'shopping',
    947 : 'familiy-friends',
    948 : 'familiy-friends',
    949 : '-',
    951 : 'canceled',
    952 : 'canceled',
    953 : 'canceled',
    959 : 'canceled',
    961 : 'familiy-friends',
    962 : 'canceled',
    969 : 'familiy-friends',
    970 : 'canceled',
    980 : '-',
    991 : 'travelling',
    992 : '-',
    997 : '-',
    998 : '-',
    999 : '-'
}


# Labels for activity simulation where away for work and other are included
# Adapted from Bottaccioli
GTOU_label_to_away_binaryactivity = {
    0 : 'away_other',
    110 : 'away_other',
    120 : 'away_other',
    131 : 'away_other',
    132 : 'away_other',
    139 : 'away_other',
    210 : 'away_work_edu',
    220 : 'away_work_edu',
    230 : 'away_work_edu',
    241 : 'away_work_edu',
    242 : 'away_work_edu',
    243 : 'away_work_edu',
    244 : 'away_work_edu',
    245 : 'away_work_edu',
    249 : 'away_work_edu',
    311 : 'away_work_edu',
    312 : 'away_work_edu',
    313 : 'away_work_edu',
    314 : 'away_work_edu',
    315 : 'away_work_edu',
    317 : 'away_work_edu',
    319 : 'away_work_edu',
    321 : 'away_work_edu',
    329 : 'away_work_edu',
    330 : 'away_work_edu',
    341 : 'away_work_edu',
    349 : 'away_work_edu',
    353 : 'away_work_edu',
    354 : 'away_work_edu',
    361 : 'away_work_edu',
    362 : 'away_work_edu',
    363 : 'away_work_edu',
    364 : 'away_work_edu',
    369 : 'away_work_edu',
    411 : 'away_other',
    413 : 'away_other',
    412 : 'away_other',
    414 : 'away_other',
    419 : 'away_other',
    421 : 'away_other',
    422 : 'away_other',
    423 : 'away_other',
    429 : 'away_other',
    431 : 'away_other',
    432 : 'away_other',
    433 : 'away_other',
    434 : 'away_other',
    439 : 'away_other',
    441 : 'away_other',
    442 : 'away_other',
    443 : 'away_other',
    444 : 'away_other',
    445 : 'away_other',
    446 : 'away_other',
    449 : 'away_other',
    451 : 'away_other',
    452 : 'away_other',
    453 : 'away_other',
    454 : 'away_other',
    455 : 'away_other',
    459 : 'away_other',
    461 : 'away_other',
    464 : 'away_other',
    465 : 'away_other',
    466 : 'away_other',
    469 : 'away_other',
    471 : 'away_other',
    472 : 'away_other',
    473 : 'away_other',
    474 : 'away_other',
    475 : 'away_other',
    476 : 'away_other',
    479 : 'away_other',
    480 : 'away_other',
    491 : 'away_other',
    492 : 'away_other',
    499 : 'away_other',
    510 : 'away_other',
    520 : 'away_other',
    531 : 'away_other',
    532 : 'away_other',
    539 : 'away_other',
    611 : 'away_other',
    612 : 'away_other',
    621 : 'away_other',
    622 : 'away_other',
    623 : 'away_other',
    624 : 'away_other',
    625 : 'away_other',
    626 : 'away_other',
    627 : 'away_other',
    629 : 'away_other',
    630 : 'away_other',
    641 : 'away_other',
    642 : 'away_other',
    649 : 'away_other',
    711 : 'away_other',
    712 : 'away_other',
    713 : 'away_other',
    715 : 'away_other',
    716 : 'away_other',
    717 : 'away_other',
    719 : 'away_other',
    730 : 'away_other',
    740 : 'away_other',
    752 : 'away_other',
    759 : 'away_other',
    761 : 'away_other',
    762 : 'away_other',
    763 : 'away_other',
    769 : 'away_other',
    790 : 'away_other',
    811 : 'away_other',
    812 : 'away_other',
    813 : 'away_other',
    814 : 'away_other',
    815 : 'away_other',
    819 : 'away_other',
    820 : 'away_other',
    830 : 'away_other',
    841 : 'away_other',
    842 : 'away_other',
    843 : 'away_other',
    844 : 'away_other',
    849 : 'away_other',
    921 : 'travel_work_edu',
    922 : 'travel_work_edu',
    923 : 'travel_work_edu',
    929 : 'travel_work_edu',
    931 : 'travel_work_edu',
    934 : 'travel_work_edu',
    939 : 'travel_work_edu',
    941 : 'travel_other',
    945 : 'travel_other',
    946 : 'travel_other',
    947 : 'travel_other',
    948 : 'travel_other',
    949 : 'travel_other',
    951 : 'travel_other',
    952 : 'travel_other',
    953 : 'travel_other',
    959 : 'travel_other',
    961 : 'travel_other',
    962 : 'travel_other',
    969 : 'travel_other',
    970 : 'travel_other',
    980 : 'travel_other',
    991 : 'travel_other',
    992 : 'travel_other',
    997 : 'away_other',
    998 : 'away_other',
    999 : 'away_other'
}


def states_to_activity(states):
    """Convert the states to activity states (1= active, 0 = not active)

    Args:
        states (ndarray): The raw states from the german TOU

    Returns:
        ndarray: The activity states
    """

    dic = {
        110 : 0,
        120 : 1,
        131 : 1,
        132 : 0,
        139 : 1,
        210 : 1,
        220 : 1,
        230 : 1,
        241 : 1,
        242 : 1,
        243 : 1,
        244 : 1,
        245 : 1,
        249 : 1,
        311 : 1,
        312 : 1,
        313 : 1,
        314 : 1,
        315 : 1,
        317 : 1,
        319 : 1,
        321 : 1,
        329 : 1,
        330 : 1,
        341 : 1,
        349 : 1,
        353 : 1,
        354 : 1,
        361 : 1,
        362 : 1,
        363 : 1,
        364 : 1,
        369 : 1,
        411 : 1,
        412 : 1,
        413 : 1,
        414 : 1,
        419 : 1,
        421 : 1,
        422 : 1,
        423 : 1,
        429 : 1,
        431 : 1,
        432 : 1,
        433 : 1,
        434 : 1,
        439 : 1,
        441 : 1,
        442 : 1,
        443 : 1,
        444 : 1,
        445 : 1,
        446 : 1,
        449 : 1,
        451 : 1,
        452 : 1,
        453 : 1,
        454 : 1,
        455 : 1,
        459 : 1,
        461 : 1,
        464 : 1,
        465 : 1,
        466 : 1,
        469 : 1,
        471 : 1,
        472 : 1,
        473 : 1,
        474 : 1,
        475 : 1,
        476 : 1,
        479 : 1,
        480 : 1,
        491 : 1,
        492 : 1,
        499 : 1,
        510 : 1,
        520 : 1,
        531 : 1,
        532 : 1,
        539 : 1,
        611 : 1,
        612 : 1,
        621 : 1,
        622 : 1,
        623 : 1,
        624 : 1,
        625 : 1,
        626 : 1,
        627 : 1,
        629 : 1,
        630 : 1,
        641 : 1,
        642 : 1,
        649 : 1,
        711 : 1,
        712 : 1,
        713 : 1,
        715 : 1,
        716 : 1,
        717 : 1,
        719 : 1,
        730 : 1,
        740 : 1,
        752 : 1,
        759 : 1,
        761 : 1,
        762 : 1,
        763 : 1,
        769 : 1,
        790 : 1,
        811 : 1,
        812 : 1,
        813 : 1,
        814 : 1,
        815 : 1,
        819 : 1,
        820 : 1,
        830 : 1,
        841 : 1,
        842 : 1,
        843 : 1,
        844 : 1,
        849 : 1,
        921 : 1,
        922 : 1,
        923 : 1,
        929 : 1,
        931 : 1,
        934 : 1,
        939 : 1,
        941 : 1,
        945 : 1,
        946 : 1,
        947 : 1,
        948 : 1,
        949 : 1,
        951 : 1,
        952 : 1,
        953 : 1,
        959 : 1,
        961 : 1,
        962 : 1,
        969 : 1,
        970 : 1,
        980 : 1,
        991 : 1,
        992 : 1,
        997 : 1,
        998 : 1,
        999 : 1
    }
    s,l = convert_states(states, dic)
    return l[s]

def is_transportation(states):
    """Define if a state correspond to a transportation activity

    Args:
        states (ndarray): The raw states form the GTOU

    Returns:
        ndarray(bool): The mask of transportation activities
    """
    #return states >=900  # naive and wrong implementation
    return (states >=900) & (states!= 997) & (states!= 999) & (states!= 998)


def is_for_work_or_school(states):
    """Define if a state was performed for a school or work activity

    Args:
        states (ndarray): The raw states form the GTOU

    Returns:
        ndarray(bool): The mask of the school or work activities
    """
    return ((states>=200) & (states<400)) | ((states>=900) &(states<=940))


def states_to_occupancy(primary_states, secondary_states, initial_occupancy, final_occupancy, dic_home):
    """Convert the states form the German TOU to occupancy. As the occupancy is not given in the german TOU,
    this uses an algorithm that estimates the occupancy.

    Args:
        primary_states (ndarray): The raw states form the GTOU
        secondary_states (ndarray): The raw secondary states form the GTOU
        initial_occupancy (ndarray): The initial occupancy form the GTOU
        final_occupancy (ndarray): The final occupancy form the GTOU
        dic_home (dict): a dictionary with a factor stating the suceptibility of being home doing that activity

    Returns:
        ndarray: The occupancy states

    Note:
        There is no guarantee on the validity of this, but results seems ok
    """
    # convert the states to their home indice rating
    main_rating, _         = convert_states(primary_states, dic_home)
    secondary_rating, _    = convert_states(secondary_states, dic_home)
    home_ratings = main_rating + secondary_rating

    #initialize the occupancy
    current_occupancy= np.zeros_like(initial_occupancy, dtype=bool)
    # assign occupants at home
    current_occupancy[initial_occupancy == 1] = True
    # missing must check the current states
    current_occupancy[initial_occupancy == -1] = home_ratings[:, 0][initial_occupancy == -1] >= 0  # favor being home with the =0, as we start at 4:00
    # current_occupancy[initial_occupancy == 2] = False # from inital vector

    # find out where the last travel occurs so that the state can easily be determined
    # (take the last index where ther was a transportation (>=900) or -42(unreachable later) if there was no travel)
    last_travel_indexes = np.array([-42 if len(inds := np.where(is_transportation(ps) | is_transportation(ss))[0]) == 0 else inds[-1] for ps, ss in zip(primary_states, secondary_states)], dtype=int)


    occupancies = []
    mask_was_travelling = np.zeros_like(current_occupancy)
    mask_at_home_before_last_travel = np.zeros_like(current_occupancy)

    for i, (prim_state, sec_state, home_rating) in enumerate(zip(primary_states.T, secondary_states.T, home_ratings.T)):

        # only update the new states after a travel has been done
        mask_travelling = is_transportation(prim_state) | is_transportation(sec_state) # travelling is occurring

        # people who leave are not there anymore
        mask_leave = ~mask_was_travelling & mask_travelling
        mask_at_home_before_last_travel[mask_leave] = current_occupancy[mask_leave] # save state of before last travel
        current_occupancy[mask_leave] = False

        # people who finish a travel can be at home or not
        mask_finish_travel = mask_was_travelling & ~mask_travelling
        # check if activity can be perform at home,  also take into account the previous occupancy and imagine it should change
        previous_occ_bias = -2 * mask_at_home_before_last_travel[mask_finish_travel] + 1 # true->-1, false->1
        current_occupancy[mask_finish_travel] = (home_rating[mask_finish_travel] + previous_occ_bias)>= 0
        # if it is the last travel, set to the last occupancy
        mask_after_last_travel = last_travel_indexes == i-1 # check if the end of the travel
        current_occupancy[mask_after_last_travel & (final_occupancy == 1)] = True
        current_occupancy[mask_after_last_travel & (final_occupancy == 2)] = False
        # keine angabe gets the last value probability
        current_occupancy[mask_after_last_travel & (final_occupancy == -1)] =  home_ratings.T[-1][mask_after_last_travel & (final_occupancy == -1)]

        #
        mask_travelling = np.array(mask_was_travelling)
        occupancies.append(np.array(current_occupancy))

    return np.asarray(occupancies).T

def states_to_out_for_what_model(occupancy, primary_states, secondary_states):
    """Return the states of weather the person is out for work(HWH) or others(HOH).
    This is inspired from the paper by Yamaguchi et al.(2020)

    Args:
        occupancy (ndarray): The array of the occupancy states
        primary_states (ndarray): The raw states from GTOU
        secondary_states (ndarray): The raw secondary states form GTOU

    Returns:
        tuple : 1. the states , 2. the labels of the states
    """
    out = np.array(primary_states)
    mask_HWH = is_for_work_or_school(primary_states) | is_for_work_or_school(secondary_states)
    out[occupancy] = 0
    out[(~occupancy) & mask_HWH] = 1
    out[(~occupancy) & (~mask_HWH)] = 2
    return out, np.array(['In-house', 'HWH', 'HOH'])



def states_to_sparse_tpm(states, first_matrix_strategy='last'):
    """Convert the states to a sparse TPM.

    Args:
        states (ndarray): The array of states to be converted to sparse TPM
        first_matrix_strategy (str, optional): Describes how to handle the first matrix, last replaces it by last, 'nothing' keeps it same. Defaults to 'last'.

    Raises:
        TypeError: If the first matrix startegy is not understood.

    Returns:
        SparseTPM: transition probability matrix for the given states
    """
    # get the shape of the input matrix
    n_persons, n_times = states.shape
    # define an array of the time corresponding to the states
    times = np.broadcast_to(np.arange(n_times), (n_persons, n_times))

    # initialize the next state
    new_states = np.roll(states, -1, axis=-1)

    # get the transitions in an array of shape (n_transistion * [times, states, new_states])
    transitions = np.swapaxes(np.array([times, states, new_states]), 0, 2).reshape((-1,3))
    # counts the unique transitions
    unique_transitions, index_transitions, counts_transitions = np.unique(transitions, axis=0, return_counts=True, return_index=True)
    # count the transitions occuring at the same time and from the same old state (positions stored in inv)
    _, inv, old_states_sum = np.unique(transitions[:,0:2], axis=0, return_inverse=True, return_counts=True)
    # compute the tranistion probabilites
    probs = counts_transitions / old_states_sum[inv][index_transitions]
    # flatten the arrayes
    # find out the values to store in the sparse TPM
    tpms = SparseTPM(
        times       =unique_transitions[:,0],
        inds_from   =unique_transitions[:,1],
        inds_to     =unique_transitions[:,2],
        values      =probs)

    # define what we should do with the first matrix that has false transitions
    if first_matrix_strategy == 'last':
        tpms[0] = np.array(tpms[-1])
    elif first_matrix_strategy == 'nothing':
        pass
    else:
        raise TypeError('Unknown first matrix stragtegy kwarg')



    return tpms

def group_in_household_4states(states, household_indexes=np.array(df_akt['id_hhx']), days_indexes=np.array(df_akt['tagnr'])):
    """Group the states given as single resident observation to a household occupancy. Merges the occupants
    along the given days and households as optional arguments. (will use German ATUS as default)

    Args:
        states (ndarray): the states of the single residents
        household_indexes (ndarray, optional): the indexes of the housholds. Defaults to np.array(df_akt['id_hhx']).
        days_indexes (ndarray, optional): the indexes of the days. Defaults to np.array(df_akt['tagnr']).

    Returns:
        merged_states: the household states after having merged residents together
    """
    assert (states.shape[0] == len(household_indexes)) & (states.shape[0] == len(days_indexes)), 'length must correspond to the number of diaries'
    assert np.all(np.logical_or.reduce((
        states == 0, states == 1, states == 10, states == 11)
    )), 'states given as input must correspond to the 4 state model with single resident states'
    merged_states = []
    for day_nr, household_id in zip(*np.unique([days_indexes, household_indexes], axis=1)):
        merged_states.append(np.sum(states[(household_indexes==household_id) & (days_indexes==day_nr)], axis=0))
    return np.asarray(merged_states)


def group_in_household_activity(mask_activity, household_indexes=np.array(df_akt['id_hhx']), days_indexes=np.array(df_akt['tagnr'])):
    """
    Group the activity mask given as single resident survey, to the number of occupant of the household.
    Doing this activity at that moment. Merges the occupants
    along the given days and households as optional arguments. (will use German ATUS as default)

    Args:
        mask_activity (ndarray): a mask of the states array that is true when an occupant is doing the activity at a certain time
        household_indexes (ndarray, optional): the indexes of the housholds. Defaults to np.array(df_akt['id_hhx']).
        days_indexes (ndarray, optional): the indexes of the days. Defaults to np.array(df_akt['tagnr']).

    Returns:
        merged_activities: the number of occupant doing activity at a given time after having merged residents together
    """
    assert (mask_activity.shape[0] == len(household_indexes)) & (mask_activity.shape[0] == len(days_indexes)), 'length must correspond to the number of diaries'

    merged_states = []
    for day_nr, household_id in zip(*np.unique([days_indexes, household_indexes], axis=1)):
        merged_states.append(np.sum(mask_activity[(household_indexes==household_id) & (days_indexes==day_nr)], axis=0))
    return np.asarray(merged_states)



# compute some of the states transformations for reducing load in usage

occ = states_to_occupancy(primary_states, secondary_states, initial_location, final_location, dic_home )
act = states_to_activity(primary_states)


def get_active_occupancy(subgroup_kwargs):
    mask = get_mask_subgroup(**subgroup_kwargs)



    hh_states = group_in_household_activity(
        (occ & act)[mask],
        household_indexes=np.array(df_akt['id_hhx'])[mask],
        days_indexes=np.array(df_akt['tagnr'])[mask]
    )

    return np.sum(hh_states, axis=0)

def get_tpms_activity(
    subgroup: Subgroup,
    activity_dict=GTOU_label_to_activity,
    away_dict=False,
    first_tpm_modification_algo='nothing',
    add_away_state=True,
    add_durations=False,
    use_sec_states=True,
):
    """Get the tpms of a desired activity dictionary.

    Attributes:
        add_away_state:
            Wether to replace the states by 'away' when there is
            no one.
        use_sec_states:
            Wheter to use secondary states as well, to replace
            the 'other' activity when a secondary state is not other

    Does NOT group by households.
    """
    mask_subgroup = get_mask_subgroup( **subgroup)

    raw_states = primary_states[mask_subgroup]

    if add_away_state:
        raw_states[~occ[mask_subgroup]] = 0
        activity_dict = activity_dict.copy()
        activity_dict[0] = 'away'
    else:
        # staring index for tracking away states
        index_max = max(activity_dict.keys()) + 1
        # dictionary of away states to be added to the activity dictionary 
        new_states_dict = {index_max+n : v for n,v 
                           in enumerate(set(away_dict.values()))}
        inv_new_states_dict = {v: k for k, v in new_states_dict.items()}
        # dictionary for replacing values with the away states
        away_states_replace_dict = {k: inv_new_states_dict.get(v, v) 
                                    for k, v in away_dict.items()}
        # convert and update away states in the raw dataset
        raw_states[~occ[mask_subgroup]] = replace_with_dict(
                    raw_states[~occ[mask_subgroup]], 
                    away_states_replace_dict)
        # include the away states in the activity dictionary
        activity_dict = activity_dict.copy()
        activity_dict.update(new_states_dict)

    states, states_label = convert_states(raw_states, activity_dict)

    states_label[states_label=='-'] = 'other'

    if use_sec_states:
        # Gets the secondary states
        raw_sec_states = primary_states[mask_subgroup]
        sec_states, sec_states_label = convert_states(
            raw_sec_states, activity_dict
        )
        sec_states_label[sec_states_label=='-'] = 'other'
        # Find where to replace
        mask_can_replace = (
            (states_label[states] == 'other')
            & (sec_states_label[sec_states] != 'other')
        )
        # Recontruct a states array with the secondary states
        raw_act_array = states_label[states]
        raw_act_array[mask_can_replace] = sec_states_label[sec_states][mask_can_replace]
        # Finds back in states format
        states, states_label = convert_states(raw_act_array)


    # Adds missing activities from dict to states labels
    all_activities = np.array(list(activity_dict.values()))
    missing_act = all_activities[~np.isin(all_activities, states_label)]
    states_label = np.concatenate((states_label, missing_act))

    # get the pdf of the initial distribution and save it
    initial_counts = np.bincount( states[:,0], minlength=len(states_label))
    initial_pdf = initial_counts/ np.sum(initial_counts)

    dict_legend = {}
    dict_legend['number of persons diaries'] = int(np.sum(mask_subgroup))
    dict_legend['subgroup_kwargs'] = subgroup
    dict_legend['cration date'] = str(datetime.datetime.now())
    dict_legend['first_tpm_modification_algo'] = first_tpm_modification_algo

    if add_durations:

        tpm, duration, duration_with_previous = states_to_tpms_with_durations(
            states,
            first_tpm_modification_algo=first_tpm_modification_algo,
            labels=states_label
        )
        # PDFs that should depend on the duration at start depending on
        # the first state shape = n_states, n_times
        intial_durations_pdf = get_initial_durations_pdfs(states)

        return (
            tpm, duration, states_label,
            initial_pdf, intial_durations_pdf, dict_legend
        )
    else:
        # Return the standard tpms algo
        tpm = states_to_tpms(
            states, first_tpm_modification_algo=first_tpm_modification_algo,
            labels=states_label
        )

        return tpm, states_label, initial_pdf, dict_legend



def get_data_4states(
    subgroup_kwargs,
    first_tpm_modification_algo='last',
    add_durations=False
):
    # gets the concerned households
    mask_subgroup = get_mask_subgroup( **subgroup_kwargs)

    hh_states = group_in_household_4states(
        np.array(10 * occ + 1 * act, dtype=int)[mask_subgroup],
        household_indexes=np.array(df_akt['id_hhx'])[mask_subgroup],
        days_indexes=np.array(df_akt['tagnr'])[mask_subgroup]
    )

    states, states_label = convert_states(hh_states)


    # get the pdf of the initial distribution and save it
    initial_counts = np.bincount( states[:,0], minlength=len(states_label))
    initial_pdf = initial_counts/ np.sum(initial_counts)

    dict_legend = {}
    dict_legend['number of households diaries'] = len(hh_states)
    dict_legend['number of persons diaries'] = int(np.sum(mask_subgroup))
    dict_legend['subgroup_kwargs'] = subgroup_kwargs
    dict_legend['cration date'] = str(datetime.datetime.now())
    dict_legend['first_tpm_modification_algo'] = first_tpm_modification_algo

    if add_durations:

        tpm, duration, duration_with_previous = states_to_tpms_with_durations(
            states, first_tpm_modification_algo=first_tpm_modification_algo
        )
        # PDFs that should depend on the duration at start depending on
        # the first state shape = n_states, n_times
        intial_durations_pdf = get_initial_durations_pdfs(states)

        return (
            tpm, duration,  states_label,
            initial_pdf, intial_durations_pdf, dict_legend
        )
    else:
        # Return the standard tpms algo
        tpm = states_to_tpms(
            states, first_tpm_modification_algo=first_tpm_modification_algo
        )

        return tpm, states_label, initial_pdf, dict_legend

def get_data_sparse9states(subgroup_kwargs):

    # transportation model
    states_out_for_what , labels_out_for_what = states_to_out_for_what_model(
        occ,
        primary_states,
        secondary_states)

    # convert states
    primary_activities, activity_labels = convert_states(primary_states, GTOU_label_to_energy_activity)
    secondary_activities, sec_activity_labels = convert_states(secondary_states, GTOU_label_to_energy_activity)
    #states = states_out_for_what
    #labels = labels_out_for_what
    active_states = (activity_labels[primary_activities] != 'not active') & (sec_activity_labels[secondary_activities] != 'not active')
    labels_9states = ['active']

    # puts it to a N-states power model
    personas_states = np.array(active_states, dtype=np.uint64)



    # replace states by the two commuting states
    activity_offset = len(labels_9states)
    labels_9states = np.append(labels_9states, labels_out_for_what[1:]) # don't override the in house activites in the labels
    personas_states = np.where(
        states_out_for_what != 0, # 0 is the 'In-house' state
        MAX_PEOPLE_HOUSEHOLD**np.array(activity_offset + states_out_for_what - 1, dtype=np.uint64),
        personas_states
    )


    # gets the concerned households
    mask_subgroup = get_mask_subgroup( **subgroup_kwargs)


    # group activities by households
    hh_states = group_in_household_activity(
        personas_states[mask_subgroup],
        household_indexes=np.array(df_akt['id_hhx'])[mask_subgroup],
        days_indexes=np.array(df_akt['tagnr'])[mask_subgroup])


    # convert states to a sparse TPM
    states, states_label = convert_states(hh_states)
    tpm = states_to_sparse_tpm(states, first_matrix_strategy='nothing')


    # get the pdf of the initial distribution and save it
    initial_counts = np.bincount( states[:,0], minlength=tpm.n_states)
    initial_pdf = initial_counts/ np.sum(initial_counts)

    dict_legend = {}
    dict_legend['number of households diaries'] = len(hh_states)
    dict_legend['number of persons diaries'] = int(np.sum(mask_subgroup))
    dict_legend['subgroup_kwargs'] = subgroup_kwargs
    dict_legend['cration date'] = str(datetime.datetime.now())


    return tpm, states_label, labels_9states, initial_pdf, dict_legend




def create_data_activity_profile(
    subgroup_kwargs,
    approach: str = 'CREST'):
    """Create the activity profiles of a day for a requested subgroup kwargs

    Args:
        subgroup_kwargs (dict): dictonary of the subgroup to generate the activity profile
        approach (str): activity profile calculation method. Now available:
            - 'CREST' activity profiles based on active occupants
            - 'avail_occupancy' activity profiles based on active occupants, 
               which are also available (not performing other explicit activities)
        compiled_data_path (string, optional): The access path where the data should be saved.
            Defaults to os.path.join(__this_dir__, 'compiled_data').
    """

    # generate the activity profiles
    mask_subgroup = get_mask_subgroup( **subgroup_kwargs)
    
    if approach == 'CREST':
        # gets the activities we want
        main_activity_states, main_activity_labels = convert_states(
            primary_states[mask_subgroup], GTOU_label_to_CREST_act_v2)
        sec_activity_states, sec_activity_labels = convert_states(
            secondary_states[mask_subgroup], GTOU_label_to_CREST_act_v2)
    
        # convert to a 4 states model, and group the 4 states to households states to get the active occupancy
        merged_states, merged_labels = convert_states(10*occ + act)
    
        household_states = group_in_household_4states(
            np.array(merged_labels[merged_states])[mask_subgroup],
            household_indexes=np.array(df_akt['id_hhx'])[mask_subgroup],
            days_indexes=np.array(df_akt['tagnr'])[mask_subgroup] )
    
        active_occ = np.minimum(household_states%10, household_states//10)
    
        # loop over the activities to be parsed
        all_activity_labels = ['Act_TV','Act_Cooking','Act_Laundry','Act_WashDress','Act_Iron','Act_HouseClean', 'Act_Dishwashing', 'Act_Elec']
        demod_act_name = ['watching_tv','cooking','laundry','self_washing','ironing','cleaning', 'dishwashing', 'electronics']
    
        out_dict = {}
        # LEvel is always on
        out_dict['level'] = np.ones((144, 6), dtype=float)
        # active occupancy is 0 for 0 active occupants
        out_dict['active_occupancy'] = np.ones((144, 6), dtype=float)
        out_dict['active_occupancy'][:, 0] = 0.
    
        for desired_act, demod_act in zip(all_activity_labels, demod_act_name):
            # A
            out_dict[demod_act] = np.zeros_like(out_dict['level'])
    
    
            # gets the indice of the activity in the states
            main_act_ind = np.where(main_activity_labels==desired_act)[0]
            sec_act_ind  = np.where(sec_activity_labels==desired_act)[0]
            # if there is no record of the desired activity, choose an impossible index
            if len(main_act_ind) == 0:
                main_act_ind = -42
            if len(sec_act_ind) == 0:
                sec_act_ind = -42
    
            # find in each household how many people are doing the activity desired
            n_occ_performing_act = group_in_household_activity(
                (main_activity_states == main_act_ind) | (sec_activity_states == sec_act_ind),
                household_indexes=np.array(df_akt['id_hhx'])[mask_subgroup],
                days_indexes=np.array(df_akt['tagnr'])[mask_subgroup]
                )
    
            for n_occ in range(1,6):
                # the probability that at least n_occ is doing an activity is the probability that
                # a houshold is doing this activity divided by the number of household with that number of
                # active occupant
                n_hh_with_n_act_occ = np.sum(active_occ == n_occ, axis=0)
    
                # probability that at least n_occ are doing the activity
                # prob_n_occ_performing_act = np.mean(n_occ_performing_act>=n_occ, axis=0)
    
                prob_at_least_one_occ_perfoming_act = np.sum(
                    (n_occ_performing_act>0) & (active_occ == n_occ), axis=0 ) / n_hh_with_n_act_occ
                # set to zero the nan values, as there was no active occupant
                prob_at_least_one_occ_perfoming_act[np.isnan(prob_at_least_one_occ_perfoming_act)] = 0.0
    
                # get the path where the data will be saved
                out_dict[demod_act][:, n_occ] = prob_at_least_one_occ_perfoming_act
    
    
    elif approach == 'avail_occupancy':
        # gets the activities we want
        main_activity_states, main_activity_labels = convert_states(
            primary_states[mask_subgroup], GTOU_label_to_Bottaccioli_act)
        sec_activity_states, sec_activity_labels = convert_states(
            secondary_states[mask_subgroup], GTOU_label_to_Bottaccioli_act)

        # convert to a 4 states model, and group the 4 states to households states to get the active occupancy
        # labels -> 00: not present inactive; 10: present inactive; 
        # 01: present inactive; 11: present active
        # merged_states, merged_labels = convert_states(10*occ + act)[mask_subgroup]

        # household_states = group_in_household_4states(
        #     np.array(merged_labels[merged_states])[mask_subgroup],
        #     household_indexes=np.array(df_akt['id_hhx'])[mask_subgroup],
        #     days_indexes=np.array(df_akt['tagnr'])[mask_subgroup] )

        # active_occ = np.minimum(household_states%10, household_states//10)
        
        # gets the indice of the activity in the states
        avail_act_states = (act & occ)[mask_subgroup]
        act_in_other = ['other','dishwashing','laundry']
        for other_act in act_in_other:
            # gets the indice of the activity in the states
            main_act_ind = np.where(main_activity_labels==other_act)[0]
            sec_act_ind  = np.where(sec_activity_labels==other_act)[0]
            avail_act_states |=  (main_activity_states == main_act_ind) #| (sec_activity_states == main_act_ind)

        avail_occ = group_in_household_activity(
            avail_act_states,
            household_indexes=np.array(df_akt['id_hhx'])[mask_subgroup],
            days_indexes=np.array(df_akt['tagnr'])[mask_subgroup]
            )
        
    
        out_dict = {}
        # LEvel is always on
        out_dict['level'] = np.ones((144, 6), dtype=float)
        # active occupancy is 0 for 0 active occupants
        out_dict['active_occupancy'] = np.ones((144, 6), dtype=float)
        out_dict['active_occupancy'][:, 0] = 0.

        for demod_act in set(GTOU_label_to_Bottaccioli_act.values()):
            # A
            out_dict[demod_act] = np.zeros_like(out_dict['level'])

            # gets the indice of the activity in the states
            main_act_ind = np.where(main_activity_labels==demod_act)[0]
            sec_act_ind  = np.where(sec_activity_labels==demod_act)[0]
            # if there is no record of the desired activity, choose an impossible index
            if len(main_act_ind) == 0:
                main_act_ind = -42
            if len(sec_act_ind) == 0:
                sec_act_ind = -42

            # find in each household how many people are doing the activity desired
            n_occ_performing_act = group_in_household_activity(
                (main_activity_states == main_act_ind) | (sec_activity_states == sec_act_ind),
                household_indexes=np.array(df_akt['id_hhx'])[mask_subgroup],
                days_indexes=np.array(df_akt['tagnr'])[mask_subgroup]
                )

            for n_avail_occ in range(1,6):
                # the probability that at least n_occ is doing an activity is the probability that
                # a houshold is doing this activity divided by the number of household with that number of
                # active occupant which are not inolved in other explicited activities
                n_hh_with_n_act_occ = np.sum(avail_occ == n_avail_occ, axis=0)

                # probability that at least n_occ are doing the activity
                # prob_n_occ_performing_act = np.mean(n_occ_performing_act>=n_occ, axis=0)

                prob_at_least_one_occ_perfoming_act = np.sum(
                    (n_occ_performing_act>0) & (avail_occ == n_avail_occ), axis=0 ) / n_hh_with_n_act_occ
                # set to zero the nan values, as there was no active occupant
                prob_at_least_one_occ_perfoming_act[np.isnan(prob_at_least_one_occ_perfoming_act)] = 0.0

                # get the path where the data will be saved
                out_dict[demod_act][:, n_avail_occ] = prob_at_least_one_occ_perfoming_act
        
    else:
        #TODO: raise error
        pass

    return out_dict



