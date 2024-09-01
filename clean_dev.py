import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','mdr.settings')
import django
django.setup()

import numpy as np
import pandas as pd
import codecs

from problems.models import Manufacturer, Device, MDR, PatientProblem, DeviceProblem

#device
with codecs.open('data/DEVICE.txt', 'r', encoding='utf-8', errors='ignore') as f:
    dev = pd.read_csv(f, delimiter='|')
print('Device file loaded')

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
print('Manufacturer names harmonized')

#if there are multiple brand names under a product number, take the most common
dev['n'] = 1
name_frequencies = dev[~(dev.MODEL_NUMBER == 'nan')].groupby(['MODEL_NUMBER', 'BRAND_NAME'], as_index=False).count()
n_distinct = name_frequencies.groupby('MODEL_NUMBER').agg(lambda x: len(np.unique(x)))
mns_with_multiple = n_distinct[n_distinct['BRAND_NAME']>1]
mn_bn_map = name_frequencies.sort_values(by='n', ascending=False).groupby('MODEL_NUMBER').first()['BRAND_NAME'][mns_with_multiple.index].to_dict()
dev['BRAND_NAME'] = [mn_bn_map[x.MODEL_NUMBER] if x.MODEL_NUMBER in mn_bn_map.keys() else x.BRAND_NAME for i, x in dev.iterrows()]
print('Brand names harmonized')
n_brand_names = dev.groupby(['MODEL_NUMBER','BRAND_NAME'], as_index=False).count().groupby('MODEL_NUMBER').count()['BRAND_NAME']

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

dev.to_csv('data/device_cleaned.csv')