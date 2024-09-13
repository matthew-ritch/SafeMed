import numpy as np
import pandas as pd
import codecs
import glob

#device
devfiles = glob.glob('data/device/DEVICE*.txt')
devs = []
for dfile in devfiles:
    with codecs.open(dfile, 'r', encoding='utf-8', errors='ignore') as f:
        devs.append(pd.read_csv(f, delimiter='|', on_bad_lines='skip', usecols = ['MODEL_NUMBER','MANUFACTURER_D_NAME','MDR_REPORT_KEY','BRAND_NAME','GENERIC_NAME']))
dev = pd.concat(devs)

print('Device file loaded')

dev['MANUFACTURER_D_NAME'] = dev['MANUFACTURER_D_NAME'].str.replace('[.,]|INC|LLC|LTD(?!O)','', regex=True).str.strip(' ,._-/*')
dev['BRAND_NAME'] = dev['BRAND_NAME'].str.replace('UNK_|UNKNOWN|UNKNOWN_','', regex=True).str.strip(' ,._-/*[]()')
dev = dev[~(dev.BRAND_NAME == '')]
dev = dev[~(dev.BRAND_NAME == 'UNK')]
# dev = dev[~(dev.BRAND_NAME.astype(str).str.contains('|'))]
dev = dev[~(dev.MODEL_NUMBER == 'UNK')]
dev = dev[~(dev.MANUFACTURER_D_NAME == '')]
print('First cleaning done')
#manufacturer groupings (defined in this csv)
mg = pd.read_csv('data/device/mfrNameMap.csv').set_index('mfr')['mfr2'].to_dict()
dev['MANUFACTURER_D_NAME'] = dev['MANUFACTURER_D_NAME'].map(mg)
x = dev['MANUFACTURER_D_NAME'].map(mg)
dev['MANUFACTURER_D_NAME'] = np.where(x.isna(),
                                dev['MANUFACTURER_D_NAME'],
                                x)
print('Manufacturer names harmonized')
#for nan manufacturers, take 1) mfr from most common use of MODEL_NUMBER or if no other mn use then 2) mfr of most common product with same brand name
#1
dev['n'] = 1
name_frequencies = dev[~(pd.isna(dev.MANUFACTURER_D_NAME))].groupby(['MODEL_NUMBER', 'MANUFACTURER_D_NAME'], as_index=False).count()
n_distinct = name_frequencies.groupby('MODEL_NUMBER').agg(lambda x: len(np.unique(x)))
dev_w_nans = dev[pd.isna(dev.MANUFACTURER_D_NAME)]
mn_bn_map = name_frequencies.sort_values(by='n', ascending=False).groupby('MODEL_NUMBER').first()['MANUFACTURER_D_NAME'].to_dict()
m = pd.isna(dev.MANUFACTURER_D_NAME)
x = dev.loc[m, 'MODEL_NUMBER'].map(mn_bn_map)
dev.loc[m, 'MANUFACTURER_D_NAME'] = np.where(x.isna(),
                                dev.loc[m, 'MANUFACTURER_D_NAME'],
                                x)
#2
dev['n'] = 1
name_frequencies = dev[~(pd.isna(dev.MANUFACTURER_D_NAME))].groupby(['BRAND_NAME', 'MANUFACTURER_D_NAME'], as_index=False).count()
n_distinct = name_frequencies.groupby('BRAND_NAME').agg(lambda x: len(np.unique(x)))
dev_w_nans = dev[pd.isna(dev.MANUFACTURER_D_NAME)]
mn_bn_map = name_frequencies.sort_values(by='n', ascending=False).groupby('BRAND_NAME').first()['MANUFACTURER_D_NAME'].to_dict()
m = pd.isna(dev.MANUFACTURER_D_NAME) 
x = dev.loc[m, 'BRAND_NAME'].map(mn_bn_map)
dev.loc[m, 'MANUFACTURER_D_NAME'] = np.where(x.isna(),
                                dev.loc[m, 'MANUFACTURER_D_NAME'],
                                x)
print('Nan manufacturers interpolated')

#if there are multiple brand names under a product number, take the most common
dev['n'] = 1
name_frequencies = dev[~(dev.MODEL_NUMBER == 'nan')].groupby(['MODEL_NUMBER', 'BRAND_NAME'], as_index=False).count()
n_distinct = name_frequencies.groupby('MODEL_NUMBER').agg(lambda x: len(np.unique(x)))
mns_with_multiple = n_distinct[n_distinct['BRAND_NAME']>1]
mn_bn_map = name_frequencies.sort_values(by='n', ascending=False).groupby('MODEL_NUMBER').first()['BRAND_NAME'][mns_with_multiple.index].to_dict()
x = dev['MODEL_NUMBER'].map(mn_bn_map)
dev['BRAND_NAME'] = np.where(x.isna(),
                                dev['BRAND_NAME'],
                                x)
print('Brand names harmonized')

#if there are multiple generic names under a product number, take the most common
dev['n'] = 1
name_frequencies = dev[~(dev.MODEL_NUMBER == 'nan')].groupby(['MODEL_NUMBER', 'GENERIC_NAME'], as_index=False).count()
n_distinct = name_frequencies.groupby('MODEL_NUMBER')['GENERIC_NAME'].agg([lambda x: len(np.unique(x)), lambda y: '<>'.join(y)])
mns_with_multiple = n_distinct[n_distinct['<lambda_0>']>1]
mn_bn_map = name_frequencies.sort_values(by='n', ascending=False).groupby('MODEL_NUMBER').first()['GENERIC_NAME'][mns_with_multiple.index].to_dict()
x = dev['MODEL_NUMBER'].map(mn_bn_map)
dev['GENERIC_NAME'] = np.where(x.isna(),
                                dev['GENERIC_NAME'],
                                x)

print('Generic names harmonized')

#if there are multiple product numbers for one manufacturer and brand name, take the most common
dev['n'] = 1
name_frequencies = dev.groupby(['MODEL_NUMBER', 'BRAND_NAME', 'MANUFACTURER_D_NAME'], as_index=False).count()
n_distinct = name_frequencies.groupby(['BRAND_NAME', 'MANUFACTURER_D_NAME'])['MODEL_NUMBER'].agg([lambda x: len(np.unique(x)), lambda y: '<>'.join(y)])
mns_with_multiple = n_distinct[n_distinct['<lambda_0>']>1]
mn_bn_map = name_frequencies.sort_values(by='n', ascending=False).groupby(['BRAND_NAME', 'MANUFACTURER_D_NAME']).first()['MODEL_NUMBER'][mns_with_multiple.index].to_dict()
dev['v'] = list(zip(dev.BRAND_NAME, dev.MANUFACTURER_D_NAME))
x = dev['v'].map(mn_bn_map)
dev['MODEL_NUMBER'] = np.where(x.isna(),
                                dev['MODEL_NUMBER'],
                                x)

print('Product numbers harmonized')

#for nan model numbers, take mn from most common matching brand name from same manufacturer
dev_w_nans = dev[pd.isna(dev.MODEL_NUMBER)]
dev['n'] = 1
name_frequencies = dev.groupby(['MODEL_NUMBER', 'BRAND_NAME', 'MANUFACTURER_D_NAME'], as_index=False).count()
mn_bn_map = name_frequencies.sort_values(by='n', ascending=False).groupby(['BRAND_NAME', 'MANUFACTURER_D_NAME']).first()['MODEL_NUMBER'].to_dict()
dev['v'] = list(zip(dev.BRAND_NAME, dev.MANUFACTURER_D_NAME))
x = dev['v'].map(mn_bn_map)
dev['MODEL_NUMBER'] = np.where(x.isna(),
                                dev['MODEL_NUMBER'],
                                x)

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
x = dev['MODEL_NUMBER'].map(mn_bn_map)
dev['BRAND_NAME'] = np.where(x.isna(),
                                dev['BRAND_NAME'],
                                x)
print('Brand names harmonized again')

#if there are multiple pns for same bn / mfr, take most common pn
dev['n'] = 1
name_frequencies = dev[~(dev.MODEL_NUMBER == 'nan')].groupby(['MODEL_NUMBER', 'BRAND_NAME', 'MANUFACTURER_D_NAME'], as_index=False).count()
n_distinct = name_frequencies.groupby(['BRAND_NAME', 'MANUFACTURER_D_NAME']).agg(lambda x: len(np.unique(x)))
mns_with_multiple = n_distinct[n_distinct['MODEL_NUMBER']>1]
mn_bn_map = name_frequencies.sort_values(by='n', ascending=False).groupby(['BRAND_NAME', 'MANUFACTURER_D_NAME']).first()['MODEL_NUMBER'][mns_with_multiple.index].to_dict()
dev['v'] = list(zip(dev.BRAND_NAME, dev.MANUFACTURER_D_NAME))
x = dev['v'].map(mn_bn_map)
dev['MODEL_NUMBER'] = np.where(x.isna(),
                                dev['MODEL_NUMBER'],
                                x)
print('Repeat BN/MFR harmonized')

dev.to_csv('data/device/device_cleaned.csv')