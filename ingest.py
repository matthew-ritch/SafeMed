import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','mdr.settings')
import django
django.setup()

import numpy as np
import pandas as pd
import codecs

from problems.models import Manufacturer, Device, MDR, PatientProblem, DeviceProblem

if True:
    with codecs.open('data/device/device_cleaned.csv', 'r', encoding='utf-8', errors='ignore') as f:
        dev = pd.read_csv(f)
    print('Device file loaded')

    # mdrfoi
    with codecs.open('data/mdr/mdrfoi.txt', 'r', encoding='utf-8', errors='ignore') as f:
        mdr1 = pd.read_csv(f, delimiter='|', on_bad_lines='skip')
    with codecs.open('data/mdr/mdrfoiThru2023.txt', 'r', encoding='utf-8', errors='ignore') as f:
        mdr2 = pd.read_csv(f, delimiter='|', on_bad_lines='skip')
    mdr = pd.concat([mdr1, mdr2])

    print('MDR and DEVICES Loaded')

if True:
    with codecs.open('data/problemCodes/patientproblemcode.txt', 'r', encoding='utf-8', errors='ignore') as f:
            pp = pd.read_csv(f, delimiter='|')
    with codecs.open('data/problemCodes/patientproblemcodes.csv', 'r', encoding='utf-8', errors='ignore') as f:
        ppc = pd.read_csv(f, delimiter=',', header=None)
    with codecs.open('data/problemCodes/foidevproblem.txt', 'r', encoding='utf-8', errors='ignore') as f:
            dp = pd.read_csv(f, delimiter='|', header=None)
    with codecs.open('data/problemCodes/deviceproblemcodes.csv', 'r', encoding='utf-8', errors='ignore') as f:
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
    mdr.loc[pd.isna(mdr.DATE_REPORT), 'DATE_REPORT'] = mdr.loc[pd.isna(mdr.DATE_REPORT), 'DATE_RECEIVED']
    mdr.loc[pd.isna(mdr.DATE_OF_EVENT), 'DATE_OF_EVENT'] = mdr.loc[pd.isna(mdr.DATE_OF_EVENT), 'DATE_REPORT']
    joined = dev.merge(mdr, how='inner', on='MDR_REPORT_KEY', )
    joined = joined[~pd.isna(joined['DATE_OF_EVENT'])]
    MDR.objects.all().delete()
    devices = np.array(Device.objects.all().values_list('model_number', flat=True))
    dev_to_add = joined[np.isin(joined.MODEL_NUMBER, devices)].reset_index(drop=True) #so we can skip the filter step
    devices = Device.objects.all()
    #mdrs
    # datefields joined[['DATE_RECEIVED', 'DATE_REPORT', 'DATE_OF_EVENT']]
    event_type_map = {'D':'Death','IN':'Injury','N':'Injury','IL':'Injury','IJ':'Injury','M':'Malfunction','O':'Other'}
    rs = []
    s = dev_to_add.shape[0]
    for i, x in dev_to_add.iterrows():
        print(f"\r{int(100*i/s)}%", end="")
        rs.append(MDR(mdr_report_key = x.MDR_REPORT_KEY, device = devices.get(model_number = x.MODEL_NUMBER), event_type = event_type_map[x.EVENT_TYPE], event_date = pd.to_datetime(x.DATE_OF_EVENT, utc=True) ))
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

    s = dp.shape[0]
    tos = []

    for i, x in dp.iterrows():
        print(f"\r{int(100*i/s)}%", end="")
        tos.append(MDR.device_problem.through(
            mdr_id=x[0],
            deviceproblem_id=x[1],
        ))

    MDR.device_problem.through.objects.bulk_create(tos)
    print('\rDevice Problems linked')