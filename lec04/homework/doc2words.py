# coding=utf-8

import re
from pyhashxx import hashxx


# get 32 bit hash
def get_hash(string):
    return hashxx(string.encode('utf-8'))


SPLIT_RGX = re.compile(r'\w+', re.U)


def extract_words(text):
    words = re.findall(SPLIT_RGX, text)

    def norm_words(word):
        word = word.lower()
        return get_hash(word)
    return map(norm_words, words)
