import numpy as np
import pandas as pd
import codecs
import glob

#device
devfiles = glob.glob('data/device/DEVICE*.txt')
devs = []
for dfile in devfiles:
    with codecs.open(dfile, 'r', encoding='utf-8', errors='ignore') as f:
        devs.append(pd.read_csv(f, delimiter='|', on_bad_lines='skip'))
dev = pd.concat(devs)

# with codecs.open('data/device/DEVICE.txt', 'r', encoding='utf-8', errors='ignore') as f:
#         dev = pd.read_csv(f, delimiter='|', on_bad_lines='skip')

print('Device file loaded')

dev['MANUFACTURER_D_NAME'] = dev['MANUFACTURER_D_NAME'].str.replace('[.,]|INC|LLC|LTD(?!O)','', regex=True).str.strip()
dev['BRAND_NAME'] = dev['BRAND_NAME'].str.replace('UNK_|UNKNOWN|UNKNOWN_','', regex=True).str.strip(' ,._-/')
dev = dev[~(dev.BRAND_NAME == '')]

#manufacturer groupings (manually defined in this csv)
mg = pd.read_csv('data/device/manufacturers.csv')
maps = mg[~pd.isna(mg['Group'])]
maps['Group'] = maps['Group'].str.lower()
for gr, dfg in maps.groupby('Group'):
    m = np.isin(dev['MANUFACTURER_D_NAME'], dfg.MANUFACTURER)
    if not any(m): continue
    t = dev[m]
    values, counts = np.unique(t['MANUFACTURER_D_NAME'], return_counts=True)
    dev.loc[m, 'MANUFACTURER_D_NAME'] = values[np.argmax(counts)]
print('Manufacturer names harmonized')

#for nan manufacturers, take 1) mfr from most common use of MODEL_NUMBER or if no other mn use then 2) mfr of most common product with same brand name
#1
dev['n'] = 1
name_frequencies = dev[~(pd.isna(dev.MANUFACTURER_D_NAME))].groupby(['MODEL_NUMBER', 'MANUFACTURER_D_NAME'], as_index=False).count()
n_distinct = name_frequencies.groupby('MODEL_NUMBER').agg(lambda x: len(np.unique(x)))
dev_w_nans = dev[pd.isna(dev.MANUFACTURER_D_NAME)]
mn_bn_map = name_frequencies.sort_values(by='n', ascending=False).groupby('MODEL_NUMBER').first()['MANUFACTURER_D_NAME'].to_dict()
m = pd.isna(dev.MANUFACTURER_D_NAME)
dev.loc[m, 'MANUFACTURER_D_NAME'] = [mn_bn_map[x.MODEL_NUMBER] if pd.isna(x.MANUFACTURER_D_NAME) and (x.MODEL_NUMBER in mn_bn_map.keys()) else x.MANUFACTURER_D_NAME for i, x in dev[m].iterrows()]
#2
dev['n'] = 1
name_frequencies = dev[~(pd.isna(dev.MANUFACTURER_D_NAME))].groupby(['BRAND_NAME', 'MANUFACTURER_D_NAME'], as_index=False).count()
n_distinct = name_frequencies.groupby('BRAND_NAME').agg(lambda x: len(np.unique(x)))
dev_w_nans = dev[pd.isna(dev.MANUFACTURER_D_NAME)]
mn_bn_map = name_frequencies.sort_values(by='n', ascending=False).groupby('BRAND_NAME').first()['MANUFACTURER_D_NAME'].to_dict()
m = pd.isna(dev.MANUFACTURER_D_NAME) 
dev.loc[m, 'MANUFACTURER_D_NAME'] = [mn_bn_map[x.BRAND_NAME] if pd.isna(x.MANUFACTURER_D_NAME) and (x.BRAND_NAME in mn_bn_map.keys()) else x.MANUFACTURER_D_NAME for i, x in dev[m].iterrows()]
print('Nan manufacturers interpolated')

#if there are multiple brand names under a product number, take the most common
dev['n'] = 1
name_frequencies = dev[~(dev.MODEL_NUMBER == 'nan')].groupby(['MODEL_NUMBER', 'BRAND_NAME'], as_index=False).count()
n_distinct = name_frequencies.groupby('MODEL_NUMBER').agg(lambda x: len(np.unique(x)))
mns_with_multiple = n_distinct[n_distinct['BRAND_NAME']>1]
mn_bn_map = name_frequencies.sort_values(by='n', ascending=False).groupby('MODEL_NUMBER').first()['BRAND_NAME'][mns_with_multiple.index].to_dict()
m = np.isin(dev.MODEL_NUMBER, list(mn_bn_map.keys()))
dev.loc[m, 'BRAND_NAME'] = dev.loc[m, 'MODEL_NUMBER'].map(mn_bn_map)
# dev['BRAND_NAME'] = [mn_bn_map[x.MODEL_NUMBER] if x.MODEL_NUMBER in mn_bn_map.keys() else x.BRAND_NAME for i, x in dev.iterrows()]

print('Brand names harmonized')

#if there are multiple generic names under a product number, take the most common
dev['n'] = 1
name_frequencies = dev[~(dev.MODEL_NUMBER == 'nan')].groupby(['MODEL_NUMBER', 'GENERIC_NAME'], as_index=False).count()
n_distinct = name_frequencies.groupby('MODEL_NUMBER')['GENERIC_NAME'].agg([lambda x: len(np.unique(x)), lambda y: '<>'.join(y)])
mns_with_multiple = n_distinct[n_distinct['<lambda_0>']>1]
mn_bn_map = name_frequencies.sort_values(by='n', ascending=False).groupby('MODEL_NUMBER').first()['GENERIC_NAME'][mns_with_multiple.index].to_dict()
m = np.isin(dev.MODEL_NUMBER, list(mn_bn_map.keys()))
dev.loc[m, 'GENERIC_NAME'] = dev.loc[m, 'MODEL_NUMBER'].map(mn_bn_map)
# dev['GENERIC_NAME'] = [mn_bn_map[x.MODEL_NUMBER] if x.MODEL_NUMBER in mn_bn_map.keys() else x.GENERIC_NAME for i, x in dev.iterrows()]

print('Generic names harmonized')

#if there are multiple product numbers for one manufacturer and brand name, take the most common
dev['n'] = 1
name_frequencies = dev.groupby(['MODEL_NUMBER', 'BRAND_NAME', 'MANUFACTURER_D_NAME'], as_index=False).count()
n_distinct = name_frequencies.groupby(['BRAND_NAME', 'MANUFACTURER_D_NAME'])['MODEL_NUMBER'].agg([lambda x: len(np.unique(x)), lambda y: '<>'.join(y)])
mns_with_multiple = n_distinct[n_distinct['<lambda_0>']>1]
mn_bn_map = name_frequencies.sort_values(by='n', ascending=False).groupby(['BRAND_NAME', 'MANUFACTURER_D_NAME']).first()['MODEL_NUMBER'][mns_with_multiple.index].to_dict()
v1 = [f'{x[0]}<3967390572>{x[1]}' for x in list(zip(dev.BRAND_NAME, dev.MANUFACTURER_D_NAME))]
v2 = [f'{x[0]}<3967390572>{x[1]}' for x in list(mn_bn_map.keys())]
m = np.isin(v1, v2)
dev['v'] = list(zip(dev.BRAND_NAME, dev.MANUFACTURER_D_NAME))
dev.loc[m, 'MODEL_NUMBER'] = dev.loc[m, 'v'].map(mn_bn_map)
# dev['MODEL_NUMBER'] = [mn_bn_map[tuple(x[['BRAND_NAME', 'MANUFACTURER_D_NAME']].values)] if tuple(x[['BRAND_NAME', 'MANUFACTURER_D_NAME']].values) in mn_bn_map.keys() else x.MODEL_NUMBER for i, x in dev.iterrows()]

print('Product numbers harmonized')

#for nan model numbers, take mn from most common matching brand name from same manufacturer
dev_w_nans = dev[pd.isna(dev.MODEL_NUMBER)]
dev['n'] = 1
name_frequencies = dev.groupby(['MODEL_NUMBER', 'BRAND_NAME', 'MANUFACTURER_D_NAME'], as_index=False).count()
mn_bn_map = name_frequencies.sort_values(by='n', ascending=False).groupby(['BRAND_NAME', 'MANUFACTURER_D_NAME']).first()['MODEL_NUMBER'].to_dict()
v1 = [f'{x[0]}<3967390572>{x[1]}' for x in list(zip(dev.BRAND_NAME, dev.MANUFACTURER_D_NAME))]
v2 = [f'{x[0]}<3967390572>{x[1]}' for x in list(mn_bn_map.keys())]
m = np.isin(v1, v2) & pd.isna(dev.MODEL_NUMBER)
dev['v'] = list(zip(dev.BRAND_NAME, dev.MANUFACTURER_D_NAME))
dev.loc[m, 'MODEL_NUMBER'] = dev.loc[m, 'v'].map(mn_bn_map)
# dev['MODEL_NUMBER'] = [mn_bn_map[tuple(x[['BRAND_NAME', 'MANUFACTURER_D_NAME']].values)] if (pd.isna(x.MODEL_NUMBER)) and (tuple(x[['BRAND_NAME', 'MANUFACTURER_D_NAME']].values) in mn_bn_map.keys()) else x.MODEL_NUMBER for i, x in dev.iterrows()]

print('Nan model numbers interpolated')

#for devices that are still na model numbers but have mfrs and brand names, make them new mns
m = pd.isna(dev['MODEL_NUMBER'])&(~pd.isna(dev['MANUFACTURER_D_NAME']))&(~pd.isna(dev['MODEL_NUMBER']))
dev.loc[m, 'MODEL_NUMBER'] = dev.loc[m, 'MANUFACTURER_D_NAME'] + ' ' + dev.loc[m, 'BRAND_NAME']
#if brand name is nan, take the generic name
dev['BRAND_NAME'][pd.isna(dev['BRAND_NAME'])] = dev['GENERIC_NAME'][pd.isna(dev['BRAND_NAME'])]

#other cleaning
dev = dev[dev.MDR_REPORT_KEY.astype(str).str.isnumeric()]
dev = dev.drop_duplicates(subset='MDR_REPORT_KEY')

#second pass - if there are multiple brand names under a product number, take the most common
dev['n'] = 1
name_frequencies = dev[~(dev.MODEL_NUMBER == 'nan')].groupby(['MODEL_NUMBER', 'BRAND_NAME'], as_index=False).count()
n_distinct = name_frequencies.groupby('MODEL_NUMBER').agg(lambda x: len(np.unique(x)))
mns_with_multiple = n_distinct[n_distinct['BRAND_NAME']>1]
mn_bn_map = name_frequencies.sort_values(by='n', ascending=False).groupby('MODEL_NUMBER').first()['BRAND_NAME'][mns_with_multiple.index].to_dict()
# dev['BRAND_NAME'] = [mn_bn_map[x.MODEL_NUMBER] if x.MODEL_NUMBER in mn_bn_map.keys() else x.BRAND_NAME for i, x in dev.iterrows()]
m = np.isin(dev.MODEL_NUMBER, list(mn_bn_map.keys()))
dev.loc[m, 'BRAND_NAME'] = dev.loc[m, 'MODEL_NUMBER'].map(mn_bn_map)

print('Brand names harmonized again')

#if there are multiple pns for same bn / mfr, take most common pn
dev['n'] = 1
name_frequencies = dev[~(dev.MODEL_NUMBER == 'nan')].groupby(['MODEL_NUMBER', 'BRAND_NAME', 'MANUFACTURER_D_NAME'], as_index=False).count()
n_distinct = name_frequencies.groupby(['BRAND_NAME', 'MANUFACTURER_D_NAME']).agg(lambda x: len(np.unique(x)))
mns_with_multiple = n_distinct[n_distinct['MODEL_NUMBER']>1]
mn_bn_map = name_frequencies.sort_values(by='n', ascending=False).groupby(['BRAND_NAME', 'MANUFACTURER_D_NAME']).first()['MODEL_NUMBER'][mns_with_multiple.index].to_dict()
v1 = [f'{x[0]}<3967390572>{x[1]}' for x in list(zip(dev.BRAND_NAME, dev.MANUFACTURER_D_NAME))]
v2 = [f'{x[0]}<3967390572>{x[1]}' for x in list(mn_bn_map.keys())]
m = np.isin(v1, v2) 
dev['v'] = list(zip(dev.BRAND_NAME, dev.MANUFACTURER_D_NAME))
dev.loc[m, 'MODEL_NUMBER'] = dev.loc[m, 'v'].map(mn_bn_map)
# dev['MODEL_NUMBER'] = [mn_bn_map[tuple(x[['BRAND_NAME', 'MANUFACTURER_D_NAME']].values)] if tuple(x[['BRAND_NAME', 'MANUFACTURER_D_NAME']].values) in mn_bn_map.keys() else x.MODEL_NUMBER for i, x in dev.iterrows()]
 
print('Repeat BN/MFR harmonized')

#check
# n_brand_names = dev.groupby(['MODEL_NUMBER', 'MANUFACTURER_D_NAME', 'BRAND_NAME'], as_index=False).count().groupby(['MODEL_NUMBER', 'MANUFACTURER_D_NAME'])['BRAND_NAME'].agg([lambda x: len(np.unique(x)), lambda y: '<>'.join(y)])
# x = n_brand_names[n_brand_names['<lambda_0>']>1]
# print(f'check: {n_brand_names['<lambda_0>'].max()} == 1')

dev.to_csv('data/device/device_cleaned.csv')