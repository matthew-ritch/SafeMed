import numpy as np
import pandas as pd
import codecs
import glob
from difflib import SequenceMatcher 
from multiprocessing import Pool
import matplotlib.pyplot as plt
from sklearn.cluster import DBSCAN

brands = np.load('data/device/brandNames.npy', allow_pickle=True)

def f(i):
    if i%10 == 0: 
        prog = (i*(2*brands.shape[0] - i)/2)/(brands.shape[0]*brands.shape[0]/2)
        print(f"{prog:.3f}")
    out = np.zeros(brands.shape[0])
    out[i] = 1
    for j in range(i+1, brands.shape[0]):
        out[j] = SequenceMatcher(None, brands[i], brands[j]).quick_ratio()
    return out

if __name__ == '__main__':
    if True:
        # get list of pre-agg names
        if False:
            devfiles = glob.glob('data/device/DEVICE*.txt')
            devs = []
            for dfile in devfiles:
                with codecs.open(dfile, 'r', encoding='utf-8', errors='ignore') as f:
                    devs.append(pd.read_csv(f, delimiter='|', on_bad_lines='skip'))
            dev = pd.concat(devs)
            print('Device file loaded')
            brands = np.unique(dev['BRAND_NAME'].astype(str), return_counts=True)
            np.save('data/device/brandNames.npy', brands[0])
            np.save('data/device/brandCounts.npy', brands[1])
        else:
            brands = np.load('data/device/brandNames.npy', allow_pickle=True)

        # calculate similarity ratio
        with Pool(8) as p:
            x = np.array(list(p.map(f, np.arange(brands.shape[0]))))        
        for i in range(brands.shape[0]):
            x[:,i] = x[i,:]
        np.save('data/device/brandSimilarities.npy', x)
    brands = np.load('data/device/brandNames.npy', allow_pickle=True)
    counts = np.load('data/device/brandCounts.npy', allow_pickle=True)
    x = np.load('data/device/brandSimilarities.npy')

    if True:
        X = np.apply_along_axis(lambda y: y/np.linalg.norm(y), 1, x)
        print(np.linalg.norm(X[0,:]))

        cossim = X @ X.transpose()

        Y = 1 - cossim
        Y = Y - Y.min()

        labels = DBSCAN(eps=.005, min_samples=2, metric="precomputed", n_jobs=-1).fit_predict(Y)
        np.save('data/device/brandClusters.npy', labels)
    else:
        labels = np.load('data/device/brandClusters.npy')

    df = pd.DataFrame({'brand':brands, 'count':counts, 'cluster':labels})
    df = df[~(df.cluster == -1)]

    cluster_to_name_map = df.sort_values(by='count', ascending=False).groupby('cluster').first()['brand'].to_dict()
    df['brand2'] = df['cluster'].replace(cluster_to_name_map)

    name_to_name_map = df.set_index('brand')['brand2']
    name_to_name_map.to_csv('data/device/brandNameMap.csv')