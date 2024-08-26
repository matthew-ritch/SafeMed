import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','mdr.settings')
import django
django.setup()

import numpy as np
import pandas as pd
import codecs

from problems.models import Manufacturer, Device, MDR, PatientProblem, DeviceProblem

if False:
    #device
    with codecs.open('data/DEVICE.txt', 'r', encoding='utf-8', errors='ignore') as f:
        dev = pd.read_csv(f, delimiter='|')

    #if there are multiple brand names under a product number, take the most common
    dev['n'] = 1
    name_frequencies = dev[~(dev.MODEL_NUMBER == 'nan')].groupby(['MODEL_NUMBER', 'BRAND_NAME'], as_index=False).count()
    n_distinct = name_frequencies.groupby('MODEL_NUMBER').agg(lambda x: len(np.unique(x)))
    mns_with_multiple = n_distinct[n_distinct['BRAND_NAME']>1]
    mn_bn_map = name_frequencies.sort_values(by='n', ascending=False).groupby('MODEL_NUMBER').first()['BRAND_NAME'][mns_with_multiple.index].to_dict()
    dev['BRAND_NAME'] = dev['MODEL_NUMBER'].replace(mn_bn_map)

    #if there are multiple generic names under a product number, take the most common
    dev['n'] = 1
    name_frequencies = dev[~(dev.MODEL_NUMBER == 'nan')].groupby(['MODEL_NUMBER', 'GENERIC_NAME'], as_index=False).count()
    n_distinct = name_frequencies.groupby('MODEL_NUMBER')['GENERIC_NAME'].agg([lambda x: len(np.unique(x)), lambda y: '<>'.join(y)])
    mns_with_multiple = n_distinct[n_distinct['<lambda_0>']>1]
    mn_bn_map = name_frequencies.sort_values(by='n', ascending=False).groupby('MODEL_NUMBER').first()['GENERIC_NAME'][mns_with_multiple.index].to_dict()
    dev['GENERIC_NAME'] = dev['MODEL_NUMBER'].replace(mn_bn_map)

    #other cleaning
    dev['MANUFACTURER_D_NAME'] = dev['MANUFACTURER_D_NAME'].str.replace('[.,]|INC|LTD','', regex=True).str.strip()
    dev = dev[dev.MDR_REPORT_KEY.astype(str).str.isnumeric()]
    dev = dev.drop_duplicates(subset='MDR_REPORT_KEY')

    # mdrfoi
    with codecs.open('data/mdrfoi.txt', 'r', encoding='utf-8', errors='ignore') as f:
        mdr = pd.read_csv(f, delimiter='|')

    print('MDR and DEVICES Loaded')

with codecs.open('data/patientproblemcode.txt', 'r', encoding='utf-8', errors='ignore') as f:
        pp = pd.read_csv(f, delimiter='|')
with codecs.open('data/patientproblemcodes.csv', 'r', encoding='utf-8', errors='ignore') as f:
    ppc = pd.read_csv(f, delimiter=',', header=None)
with codecs.open('data/foidevproblem.txt', 'r', encoding='utf-8', errors='ignore') as f:
        dp = pd.read_csv(f, delimiter='|', header=None)
with codecs.open('data/deviceproblemcodes.csv', 'r', encoding='utf-8', errors='ignore') as f:
    dpc = pd.read_csv(f, delimiter=',', header=None)

pp = pp.drop_duplicates(subset = ['MDR_REPORT_KEY','PROBLEM_CODE'])
dp = dp.drop_duplicates(subset = [0,1])

if False:
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

if False:
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

if False:
    MDR.objects.all().delete()

    #mdrs
    joined = dev.merge(mdr, how='left', on='MDR_REPORT_KEY', suffixes=['_dev','_mdr'])
    rs = []
    s = joined.shape[0]
    i = 0
    for i,x in joined.iterrows():
        print(f"\r{int(100*i/s)}%", end="")
        d = Device.objects.filter(model_number = x.MODEL_NUMBER)
        if d:   
            rs.append(MDR(mdr_report_key = x.MDR_REPORT_KEY, device = d[0]))
        i += 1
    MDR.objects.bulk_create(rs)
    print('\rMDRs created')

if True:
    PatientProblem.objects.all().delete()

    s = pp.shape[0]
    tos = []
    for i, x in pp.iterrows():
        print(f"\r{int(100*i/s)}%", end="")
        tos.append(MDR.patient_problem.through(
                mdr_id=x.MDR_REPORT_KEY,
                patientproblem_id=x.PROBLEM_CODE,
            ))

    MDR.patient_problem.through.objects.bulk_create(tos)

if True:
    DeviceProblem.objects.all().delete()

    s = len(np.unique(dp['0']))
    tos = []

    for i, x in dp.iterrows():
        tos.append(MDR.device_problem.through(
            mdr_id=x['0'],
            deviceproblem_id=x['1'],
        ))

    MDR.device_problem.through.objects.bulk_create(tos)