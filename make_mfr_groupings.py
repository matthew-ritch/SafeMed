import numpy as np
import pandas as pd
import codecs
import glob
from difflib import SequenceMatcher 
from multiprocessing import Pool
import matplotlib.pyplot as plt
from sklearn.cluster import DBSCAN

def f(i):
    if i%10 == 0: 
        prog = (i*(2*mfrs.shape[0] - i)/2)/(mfrs.shape[0]*mfrs.shape[0]/2)
        print(f"{prog:.3f}")
    out = np.zeros(mfrs.shape[0])
    out[i] = 1
    for j in range(i+1, mfrs.shape[0]):
        out[j] = SequenceMatcher(None, mfrs[i], mfrs[j]).ratio()
    return out

if __name__ == '__main__':
    if False:
        # get list of pre-agg names
        if False:
            devfiles = glob.glob('data/device/DEVICE*.txt')
            devs = []
            for dfile in devfiles:
                with codecs.open(dfile, 'r', encoding='utf-8', errors='ignore') as f:
                    devs.append(pd.read_csv(f, delimiter='|', on_bad_lines='skip'))
            dev = pd.concat(devs)
            print('Device file loaded')
            dev['MANUFACTURER_D_NAME'] = dev['MANUFACTURER_D_NAME'].str.replace('[.,]|INC|LLC|LTD(?!O)','', regex=True).str.strip(' ,._-/*')
            dev = dev[~(dev['MANUFACTURER_D_NAME'] == '')]
            mfrs = np.unique(dev['MANUFACTURER_D_NAME'].astype(str), return_counts=True)
            np.save('data/device/mfrNames.npy', mfrs[0])
            np.save('data/device/mfrCounts.npy', mfrs[1])
        else:
            mfrs = np.load('data/device/mfrNames.npy', allow_pickle=True)
        # calculate similarity ratio
        with Pool(8) as p:
            x = np.array(list(p.map(f, np.arange(mfrs.shape[0]))))        
        for i in range(mfrs.shape[0]):
            x[:,i] = x[i,:]
        np.save('data/device/mfrSimilarities.npy', x)
    mfrs = np.load('data/device/mfrNames.npy', allow_pickle=True)
    counts = np.load('data/device/mfrCounts.npy', allow_pickle=True)
    x = np.load('data/device/mfrSimilarities.npy')

    if False:
        X = np.apply_along_axis(lambda y: y/np.linalg.norm(y), 1, x)
        print(np.linalg.norm(X[0,:]))

        cossim = X @ X.transpose()

        Y = 1 - cossim
        Y = Y - Y.min()

        labels = DBSCAN(eps=.01, min_samples=2, metric="precomputed", n_jobs=-1).fit_predict(Y)
        np.save('data/device/mfrClusters.npy', labels)
    else:
        labels = np.load('data/device/mfrClusters.npy')

    df = pd.DataFrame({'mfr':mfrs, 'count':counts, 'cluster':labels})
    df = df[~(df.cluster == -1)]

    cluster_to_name_map = df.sort_values(by='count', ascending=False).groupby('cluster').first()['mfr'].to_dict()
    df['mfr2'] = df['cluster'].replace(cluster_to_name_map)

    name_to_name_map = df.set_index('mfr')['mfr2']
    name_to_name_map.to_csv('data/device/mfrNameMap.csv')