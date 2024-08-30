import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','mdr.settings')
import django
django.setup()

import numpy as np
import pandas as pd
import codecs

from problems.models import Manufacturer, Device, MDR, PatientProblem, DeviceProblem

if True:
    #device
    with codecs.open('data/DEVICE.txt', 'r', encoding='utf-8', errors='ignore') as f:
        dev = pd.read_csv(f, delimiter='|')
    dev['MANUFACTURER_D_NAME'] = dev['MANUFACTURER_D_NAME'].str.replace('[.,]|INC|LLC|LTD(?!O)','', regex=True).str.strip()
    #manufacturer groupings (manually defined in this csv)
    mg = pd.read_csv('data/manufacturers.csv')
    maps = mg[~pd.isna(mg['Group'])]
    maps['Group'] = maps['Group'].str.lower()
    for gr, dfg in maps.groupby('Group'):
        m = np.isin(dev['MANUFACTURER_D_NAME'], dfg.MANUFACTURER)
        if not any(m): continue
        t = dev[m]
        values, counts = np.unique(t['MANUFACTURER_D_NAME'], return_counts=True)
        dev.loc[m, 'MANUFACTURER_D_NAME'] = values[np.argmax(counts)]
    
    #if there are multiple brand names under a product number, take the most common
    dev['n'] = 1
    name_frequencies = dev[~(dev.MODEL_NUMBER == 'nan')].groupby(['MODEL_NUMBER', 'BRAND_NAME'], as_index=False).count()
    n_distinct = name_frequencies.groupby('MODEL_NUMBER').agg(lambda x: len(np.unique(x)))
    mns_with_multiple = n_distinct[n_distinct['BRAND_NAME']>1]
    mn_bn_map = name_frequencies.sort_values(by='n', ascending=False).groupby('MODEL_NUMBER').first()['BRAND_NAME'][mns_with_multiple.index].to_dict()
    dev['BRAND_NAME'] = [mn_bn_map[x.MODEL_NUMBER] if x.MODEL_NUMBER in mn_bn_map.keys() else x.BRAND_NAME for i, x in dev.iterrows()]
    print('Brand names harmonized')

    #if there are multiple generic names under a product number, take the most common
    dev['n'] = 1
    name_frequencies = dev[~(dev.MODEL_NUMBER == 'nan')].groupby(['MODEL_NUMBER', 'GENERIC_NAME'], as_index=False).count()
    n_distinct = name_frequencies.groupby('MODEL_NUMBER')['GENERIC_NAME'].agg([lambda x: len(np.unique(x)), lambda y: '<>'.join(y)])
    mns_with_multiple = n_distinct[n_distinct['<lambda_0>']>1]
    mn_bn_map = name_frequencies.sort_values(by='n', ascending=False).groupby('MODEL_NUMBER').first()['GENERIC_NAME'][mns_with_multiple.index].to_dict()
    dev['GENERIC_NAME'] = [mn_bn_map[x.MODEL_NUMBER] if x.MODEL_NUMBER in mn_bn_map.keys() else x.GENERIC_NAME for i, x in dev.iterrows()]
    print('Generic names harmonized')

    #if there are multiple product numbers for one manufacturer and brand name, take the most common
    dev['n'] = 1
    name_frequencies = dev.groupby(['MODEL_NUMBER', 'BRAND_NAME', 'MANUFACTURER_D_NAME'], as_index=False).count()
    n_distinct = name_frequencies.groupby(['BRAND_NAME', 'MANUFACTURER_D_NAME'])['MODEL_NUMBER'].agg([lambda x: len(np.unique(x)), lambda y: '<>'.join(y)])
    mns_with_multiple = n_distinct[n_distinct['<lambda_0>']>1]
    mn_bn_map = name_frequencies.sort_values(by='n', ascending=False).groupby(['BRAND_NAME', 'MANUFACTURER_D_NAME']).first()['MODEL_NUMBER'][mns_with_multiple.index].to_dict()
    dev['MODEL_NUMBER'] = [mn_bn_map[tuple(x[['BRAND_NAME', 'MANUFACTURER_D_NAME']].values)] if tuple(x[['BRAND_NAME', 'MANUFACTURER_D_NAME']].values) in mn_bn_map.keys() else x.MODEL_NUMBER for i, x in dev.iterrows()]
    print('Product numbers harmonized')

    #for nan model numbers, take mn from most common matching brand name from same manufacturer
    dev_w_nans = dev[pd.isna(dev.MODEL_NUMBER)]
    dev['n'] = 1
    name_frequencies = dev.groupby(['MODEL_NUMBER', 'BRAND_NAME', 'MANUFACTURER_D_NAME'], as_index=False).count()
    mn_bn_map = name_frequencies.sort_values(by='n', ascending=False).groupby(['BRAND_NAME', 'MANUFACTURER_D_NAME']).first()['MODEL_NUMBER'].to_dict()
    dev['MODEL_NUMBER'] = [mn_bn_map[tuple(x[['BRAND_NAME', 'MANUFACTURER_D_NAME']].values)] if (pd.isna(x.MODEL_NUMBER)) and (tuple(x[['BRAND_NAME', 'MANUFACTURER_D_NAME']].values) in mn_bn_map.keys()) else x.MODEL_NUMBER for i, x in dev.iterrows()]
    print('Nan model numbers interpolated')
    
    #for nan manufacturers, take 1) mfr from most common use of MODEL_NUMBER or if no other mn use then 2) mfr of most common product with same brand name
    #1
    dev['n'] = 1
    name_frequencies = dev[~(pd.isna(dev.MANUFACTURER_D_NAME))].groupby(['MODEL_NUMBER', 'MANUFACTURER_D_NAME'], as_index=False).count()
    n_distinct = name_frequencies.groupby('MODEL_NUMBER').agg(lambda x: len(np.unique(x)))
    dev_w_nans = dev[pd.isna(dev.MANUFACTURER_D_NAME)]
    mn_bn_map = name_frequencies.sort_values(by='n', ascending=False).groupby('MODEL_NUMBER').first()['MANUFACTURER_D_NAME'].to_dict()
    dev['MANUFACTURER_D_NAME'] = [mn_bn_map[x.MODEL_NUMBER] if pd.isna(x.MANUFACTURER_D_NAME) and (x.MODEL_NUMBER in mn_bn_map.keys()) else x.MANUFACTURER_D_NAME for i, x in dev.iterrows()]
    #2
    dev['n'] = 1
    name_frequencies = dev[~(pd.isna(dev.MANUFACTURER_D_NAME))].groupby(['BRAND_NAME', 'MANUFACTURER_D_NAME'], as_index=False).count()
    n_distinct = name_frequencies.groupby('BRAND_NAME').agg(lambda x: len(np.unique(x)))
    dev_w_nans = dev[pd.isna(dev.MANUFACTURER_D_NAME)]
    mn_bn_map = name_frequencies.sort_values(by='n', ascending=False).groupby('BRAND_NAME').first()['MANUFACTURER_D_NAME'].to_dict()
    dev['MANUFACTURER_D_NAME'] = [mn_bn_map[x.BRAND_NAME] if pd.isna(x.MANUFACTURER_D_NAME) and (x.BRAND_NAME in mn_bn_map.keys()) else x.MANUFACTURER_D_NAME for i, x in dev.iterrows()]
    print('Nan manufacturers interpolated')

    #for devices that are still na model numbers but have mfrs and brand names, make them new mns
    dev['MODEL_NUMBER'][pd.isna(dev['MODEL_NUMBER'])&(~pd.isna(dev['MANUFACTURER_D_NAME']))&(~pd.isna(dev['MODEL_NUMBER']))] = (dev['MANUFACTURER_D_NAME'].astype(str)+' '+dev['BRAND_NAME'].astype(str))[pd.isna(dev['MODEL_NUMBER'])]
    #if brand name is nan, take the generic name
    dev['BRAND_NAME'][pd.isna(dev['BRAND_NAME'])] = dev['GENERIC_NAME'][pd.isna(dev['BRAND_NAME'])]

    #other cleaning
    dev = dev[dev.MDR_REPORT_KEY.astype(str).str.isnumeric()]
    dev = dev.drop_duplicates(subset='MDR_REPORT_KEY')

    # mdrfoi
    with codecs.open('data/mdrfoi.txt', 'r', encoding='utf-8', errors='ignore') as f:
        mdr = pd.read_csv(f, delimiter='|')

    print('MDR and DEVICES Loaded')

if True:
    with codecs.open('data/patientproblemcode.txt', 'r', encoding='utf-8', errors='ignore') as f:
            pp = pd.read_csv(f, delimiter='|')
    with codecs.open('data/patientproblemcodes.csv', 'r', encoding='utf-8', errors='ignore') as f:
        ppc = pd.read_csv(f, delimiter=',', header=None)
    with codecs.open('data/foidevproblem.txt', 'r', encoding='utf-8', errors='ignore') as f:
            dp = pd.read_csv(f, delimiter='|', header=None)
    with codecs.open('data/deviceproblemcodes.csv', 'r', encoding='utf-8', errors='ignore') as f:
        dpc = pd.read_csv(f, delimiter=',', header=None)

    pp = pp.drop_duplicates(subset = ['MDR_REPORT_KEY','PROBLEM_CODE'])
    pp = pp[~pp[['MDR_REPORT_KEY','PROBLEM_CODE']].isna().any(axis=1)]
    dp = dp.drop_duplicates(subset = [0,1])
    dp = dp[~dp[[0,1]].isna().any(axis=1)]

if True:
    Manufacturer.objects.all().delete()
    Device.objects.all().delete()

    #manufacturers
    manufacturers = dev['MANUFACTURER_D_NAME'].unique()
    Manufacturer.objects.bulk_create([Manufacturer(name=m) for m in manufacturers])
    print('Manufacturers Ingested')

    #devices
    ddf = dev.drop_duplicates(subset=['MODEL_NUMBER','MANUFACTURER_D_NAME']).groupby('MODEL_NUMBER')
    s = dev.drop_duplicates(subset=['MODEL_NUMBER','MANUFACTURER_D_NAME'])['MODEL_NUMBER'].shape[0]
    ind = 0
    for mn, X in ddf:
        print(f"\r{int(100*ind/s)}%", end="")
        x = X.iloc[0]
        d = Device.objects.create(model_number = x.MODEL_NUMBER, generic_name = x.GENERIC_NAME, brand_name = x.BRAND_NAME)
        d.save()
        for i in range(X.shape[0]): 
            x = X.iloc[i]
            d.manufacturer.add(Manufacturer.objects.get(name = x.MANUFACTURER_D_NAME))
        ind += 1
    print('\rDevices Ingested')

if True:
    PatientProblem.objects.all().delete()
    DeviceProblem.objects.all().delete()

    #PatientProblems
    PatientProblem.objects.bulk_create([PatientProblem(code=x[0], description=x[1]) for i, x in ppc.iterrows()])

    print('Patient Problem Codes created')

    pp['DATE_ADDED'] = pd.to_datetime(pp['DATE_ADDED'])
    pp = pp[pp['DATE_ADDED']> pd.to_datetime('01/01/2023')]

    #DeviceProblems
    DeviceProblem.objects.bulk_create([PatientProblem(code=x[0], description=x[1]) for i, x in dpc.iterrows()])
    print('Device Problem Codes created')

if True:
    MDR.objects.all().delete()
    devices = np.array(Device.objects.all().values_list('model_number', flat=True))
    dev_to_add = dev[np.isin(dev.MODEL_NUMBER, devices)].reset_index(drop=True) #so we can skip the filter step
    devices = Device.objects.all()
    #mdrs
    rs = []
    s = dev_to_add.shape[0]
    for i, x in dev_to_add.iterrows():
        print(f"\r{int(100*i/s)}%", end="")
        rs.append(MDR(mdr_report_key = x.MDR_REPORT_KEY, device = devices.get(model_number = x.MODEL_NUMBER)))
    MDR.objects.bulk_create(rs)
    print('\rMDRs created')

if True:
    MDR.patient_problem.through.objects.all().delete()
    mdrs = np.array(MDR.objects.all().values_list('mdr_report_key', flat=True))
    pp = pp[np.isin(pp.MDR_REPORT_KEY, np.array(MDR.objects.all().values_list('mdr_report_key', flat=True)))]
    pp = pp[np.isin(pp.PROBLEM_CODE, np.array(PatientProblem.objects.all().values_list('code', flat=True)))].reset_index(drop=True)

    s = pp.shape[0]
    tos = []
    for i, x in pp.iterrows():
        print(f"\r{int(100*i/s)}%", end="")
        tos.append(MDR.patient_problem.through(
                mdr_id=x.MDR_REPORT_KEY,
                patientproblem_id=x.PROBLEM_CODE,
            ))

    MDR.patient_problem.through.objects.bulk_create(tos)
    print('\rPatient Problems linked')

if True:
    MDR.device_problem.through.objects.all().delete()

    mdrs = np.array(MDR.objects.all().values_list('mdr_report_key', flat=True))
    dp = dp[np.isin(dp[0], np.array(MDR.objects.all().values_list('mdr_report_key', flat=True)))]
    dp = dp[np.isin(dp[1], np.array(DeviceProblem.objects.all().values_list('code', flat=True)))].reset_index(drop=True)

    s = len(np.unique(dp[0]))
    tos = []

    for i, x in dp.iterrows():
        print(f"\r{int(100*i/s)}%", end="")
        tos.append(MDR.device_problem.through(
            mdr_id=x[0],
            deviceproblem_id=x[1],
        ))

    MDR.device_problem.through.objects.bulk_create(tos)
    print('\rDevice Problems linked')