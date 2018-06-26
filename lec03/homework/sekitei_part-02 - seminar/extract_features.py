# coding: utf-8

import sys
import re
import random
from operator import itemgetter
from collections import Counter
import urlparse
import urllib
import numpy as np


def count_segments(line):
    if len(line) == 0:
        return 0
    if line[len(line) - 1] == '/':
        line = line[0:len(line) - 1]
    return line.count('/', 0, len(line)) - 2


def extract_subsegments(segment):
    if segment.find(':') == -1:
        return []
    return re.split(':', segment)


def extract_segments(line):
    # drop / at the end of url
    if len(line) > 0 and line[len(line) - 1] == '/':
        line = line[0:len(line) - 1]

    # drop scheme (defined as scheme:[other url])
    schema_end = line.find(':')
    if schema_end != -1:
        line = line[schema_end + 1:len(line)]

    # drop // from the beginning if exists
    if line[0:2] == "//":
        line = line[2:len(line)]

    # drop all stuff before path
    path_begin = line.find('/')
    if path_begin == -1:
        return []
    else:
        line = line[path_begin + 1:len(line)]

    # drop all stuff after path
    query_begin = line.find('?')
    if query_begin != -1:
        line = line[0:query_begin]
    fragment_begin = line.find('#')
    if fragment_begin != -1:
        line = line[0:fragment_begin]

    # drop / at the end of path part
    if len(line) > 0 and line[len(line) - 1] == '/':
        line = line[0:len(line) - 1]

    if len(line) == 0:
        return []
    return re.split('/', line)


def extract_param_names(line):
    names = []
    start_params = line.find('?')
    if start_params == -1:
        return names
    else:
        start_params += 1

    end_params = line.find('#')
    if end_params == -1:
        end_params = len(line)

    for param_sub in re.split('&', line[start_params:end_params]):
        names.append(re.split('=', param_sub)[0])

    return names


def extract_params(line):
    names = []
    start_params = line.find('?')
    if start_params == -1:
        return names
    else:
        start_params += 1

    end_params = line.find('#')
    if end_params == -1:
        end_params = len(line)

    for param_sub in re.split('&', line[start_params:end_params]):
        names.append(re.split('=', param_sub))

    return names


def get_extension(segment):
    ext_begin = segment.rfind('.')
    if ext_begin == -1:
        return ""
    return segment[ext_begin + 1: len(segment)]


def count_commas(segment):
    return np.sum(np.array(list(segment)) == ',')


def count_underscore(segment):
    return np.sum(np.array(list(segment)) == '_')


def is_russian(segment):
    return segment != urlparse.unquote(segment)


def is_correct_url(url):
    try:
        urllib.url2pathname(url)
    except IOError:
        return False
    return True


# reads files with INPUT FILES and writes features with frequency into OUTPUT FILE
def extract_features(INPUT_FILE_1, INPUT_FILE_2, OUTPUT_FILE):
    examined = open(INPUT_FILE_1, "r")
    general = open(INPUT_FILE_2, "r")
    result = open(OUTPUT_FILE, "w")

    sample_size = 1000
    min_count = 100

    examined_lines = random.sample(examined.read().split('\n'), sample_size)
    general_lines = random.sample(general.read().split('\n'), sample_size)

    features = extract_features_from_list(examined_lines, general_lines)

    for key, value in features:
        if value < min_count:
            break
        result.write(key + '\t' + str(value) + '\n')


# returns sorted Counter dictionary with features
def extract_features_from_list(QLINK_LIST, UNKNOWN_URLS_LIST):
    lines = []
    features = Counter()

    examined_lines = QLINK_LIST
    general_lines = UNKNOWN_URLS_LIST
    lines.extend(examined_lines)
    lines.extend(general_lines)

    for line in lines:
        line = line.lower()
        if line.find('\n') != -1:
            line = line[0:len(line) - 1]
        features_from_url = extract_features_from_url(line)
        for feature in features_from_url:
            sys.stdout.flush()
            features[feature] += 1

    features = features.most_common()
    return features


# extracts features from one url
def extract_features_from_url(url):
    # print urlparse.unquote(url)
    features = list()

    # feature 1
    features.append("segments:" + str(count_segments(url)))
    # feature 2
    for name in extract_param_names(url):
        features.append("param_name:" + name)
    # feature 3
    for param in extract_params(url):
        if len(param) == 1:
            param.append("")
        features.append("param:" + param[0] + "=" + param[1])
    # features 4a - 4f ans 5
    segments = extract_segments(url)
    for pos, segment in enumerate(segments):
        segment_decoded = urlparse.unquote(segment)
        regex_res = re.findall("[^\\d]+\\d+[^\\d]+$", segment_decoded)
        # feature 4a
        features.append("segment_name_" + str(pos) + ":" + segment)
#        features.append("segment_name_" + str(pos) + ":" + segment_decoded)
        # feature 4b
        if segment.isdigit():
            features.append("segment_[0-9]_" + str(pos) + ":1")
        # feature 4c
        if len(regex_res) == 1 and regex_res[0] == segment_decoded:
            features.append("segment_substr[0-9]_" + str(pos) + ":1")
        # feature 4d
        extension = get_extension(segment)
        if len(extension) != 0:
            features.append("segment_ext_" + str(pos) + ":" + extension)
        # feature 4e
        if len(regex_res) == 1 and regex_res[0] == segment_decoded and len(extension) != 0:
            features.append("segment_ext_substr[0-9]_" + str(pos) + ":" + extension)
        # feature 4f
        features.append("segment_len_" + str(pos) + ":" + str(len(segment)))
        # feature 5
        # segment contains subsegments like <name>: ... : <name>
        subsegmenst = extract_subsegments(segment_decoded)
        #feature 5.1
        features.append("subsegmenst_" + str(pos) + ":" + str(len(subsegmenst)))
        for spos, subsegmenst in enumerate(subsegmenst):
            features.append("subsegment_name_" + str(pos) + ":" + subsegmenst)
        # feature 6
        if is_russian(segment):
            features.append("segment_lang_" + str(pos) + ":rus")
        #else:
         #   features.append("segment_lang_" + str(pos) + ":nonrus")
        # feature 7
    features.append("commas:" + str(count_commas(url)))
        # feature 8
    features.append("underscore:" + str(count_underscore(url)))
    # feature 9
    if is_correct_url(url):
        features.append("correct:False")
    #else:
        #features.append("correct:True")
    return features


# extract_features("./data/urls.wikipedia.general", "./data/urls.wikipedia.general", "./check/wikipedia.fea.res")
