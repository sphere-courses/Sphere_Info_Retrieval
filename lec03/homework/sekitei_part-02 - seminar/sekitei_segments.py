 # coding: utf-8

import sys

reload(sys)
sys.setdefaultencoding('utf8')

from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
import urllib

from extract_features import *

sekitei = None

min_freq = 0.1
max_freq = 0.9
min_features_count = 10
num_clusters = 10
quota = None
min_quota = 100
max_quota = 1000
chosen_features = set()
clusterization = None
classifications = list()
links_distr = None


def get_attrs(chosen_features, features_from_url):
    attrs = np.zeros([len(chosen_features)])
    for j, feature in enumerate(chosen_features):
        if feature in features_from_url:
            attrs[j] = 1
    return attrs


def define_segments(QLINK_URLS, UNKNOWN_URLS, QUOTA):
    global min_freq
    global max_freq
    global num_clusters
    global quota
    global min_quota
    global max_quota
    global min_features_count
    global chosen_features
    global clusterization
    global classification
    global links_distr

    quota = QUOTA

    features = extract_features_from_list(QLINK_URLS, UNKNOWN_URLS)
    sys.stdout.flush()
    input_size = len(QLINK_URLS) + len(UNKNOWN_URLS)
    if np.sum(((np.array(features)[:,1].astype(np.int) > min_freq * input_size) &
                 (np.array(features)[:,1].astype(np.int) < max_freq * input_size))) < min_features_count:
        min_freq /= 1.5

    for key, value in features:
        if (value > min_freq * input_size) and (value < max_freq * input_size):
            chosen_features.add(key)
    print chosen_features

    X = np.zeros([len(QLINK_URLS) + len(UNKNOWN_URLS), len(chosen_features)])
    # 0 - UNKNOWN, 1 - QLINK
    y = np.zeros([len(QLINK_URLS) + len(UNKNOWN_URLS)])
    y[:len(QLINK_URLS)] = np.ones([len(QLINK_URLS)])

    for i, url in enumerate(QLINK_URLS + UNKNOWN_URLS):
        X[i] = get_attrs(chosen_features, set(extract_features_from_url(url)))

    clusterization = KMeans(n_clusters=num_clusters)
    clusterization.fit(X)
    cluster_nums = clusterization.predict(X)

    # reduced_data = PCA(n_components=2).fit_transform(X)
    # kmeans = KMeans(init='k-means++', n_init=10)
    # kmeans.fit(reduced_data)
    #
    # # Step size of the mesh. Decrease to increase the quality of the VQ.
    # h = .02  # point in the mesh [x_min, x_max]x[y_min, y_max].
    #
    # # Plot the decision boundary. For that, we will assign a color to each
    # x_min, x_max = reduced_data[:, 0].min() - 1, reduced_data[:, 0].max() + 1
    # y_min, y_max = reduced_data[:, 1].min() - 1, reduced_data[:, 1].max() + 1
    # xx, yy = np.meshgrid(np.arange(x_min, x_max, h), np.arange(y_min, y_max, h))
    #
    # # Obtain labels for each point in mesh. Use last trained model.
    # Z = kmeans.predict(np.c_[xx.ravel(), yy.ravel()])
    #
    # # Put the result into a color plot
    # Z = Z.reshape(xx.shape)
    # plt.figure(1)
    # plt.clf()
    # plt.imshow(Z, interpolation='nearest',
    #            extent=(xx.min(), xx.max(), yy.min(), yy.max()),
    #            cmap=plt.cm.Paired,
    #            aspect='auto', origin='lower')
    #
    # plt.plot(reduced_data[:, 0], reduced_data[:, 1], 'k.', markersize=2)
    # # Plot the centroids as a white X
    # centroids = kmeans.cluster_centers_
    # plt.scatter(centroids[:, 0], centroids[:, 1],
    #             marker='x', s=169, linewidths=3,
    #             color='w', zorder=10)
    # plt.title('K-means clustering on the digits dataset (PCA-reduced data)\n'
    #           'Centroids are marked with white cross')
    # plt.xlim(x_min, x_max)
    # plt.ylim(y_min, y_max)
    # plt.xticks(())
    # plt.yticks(())
    # plt.show()

    # links | qlinks | already_chosen

    links_distr = np.zeros([num_clusters, 4])
    good_like = np.zeros(num_clusters)
    for cl_num in xrange(num_clusters):
        links_distr[cl_num][0] = np.sum(cluster_nums == cl_num)
        links_distr[cl_num][1] = np.sum(cluster_nums[y == 1] == cl_num)


    in_top_quota = np.percentile(links_distr[:, 0], 25)
    for cl_num in xrange(num_clusters):
        links_distr[cl_num][3] = (links_distr[cl_num][1] + in_top_quota * np.sum(good_like) / num_clusters) / (links_distr[cl_num][0] + in_top_quota)
    links_distr[:, 3] *= quota / (np.sum(links_distr[:, 3]))
    links_distr[links_distr[:, 3] < min_quota, 3] = min_quota
    links_distr[:, 3] *= quota / (np.sum(links_distr[:, 3]))

    # 0 - UNKNOWN, 1 - QLINK
    for i in xrange(num_clusters):
        if X[cluster_nums == i].shape[0] == 0:
            classifications.append(None)
        else:
            classifications.append(RandomForestClassifier(max_depth=5, random_state=0, n_estimators=3))
            #classifications.append(LinearDiscriminantAnalysis())
            classifications[i].fit(X[cluster_nums == i], y[cluster_nums == i])

    print links_distr.astype(np.int)

#
# returns True if need to fetch url
#
def fetch_url(url):
    attrs = get_attrs(chosen_features, set(extract_features_from_url(url)))
    cluster_n = clusterization.predict(attrs.reshape(1, -1))[0]
    is_qlinq = classifications[cluster_n].predict(attrs.reshape(1, -1))
    if is_qlinq > 0.95:
        return True
    if links_distr[cluster_n][3] > links_distr[cluster_n][2]:
        links_distr[cluster_n][2] += 1
        return True
    return False

