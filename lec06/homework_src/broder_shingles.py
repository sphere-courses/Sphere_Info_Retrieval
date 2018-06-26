#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This just a draft for homework 'near-duplicates'
Use MinshinglesCounter to make result closer to checker
"""

import re
import string
from docreader import DocumentStreamReader
from collections import defaultdict
import sys

import mmh3


class TextNormalizer:
    @staticmethod
    def join_numbers(text):
        regex = re.compile('([\d])[\s]+([\d])')
        return regex.sub('\\1\\2', text)

    @staticmethod
    def clean_out_punct(text):
        regex = re.compile('[%s]' % re.escape(string.punctuation + "«" + "»"))
        return regex.sub(' ', text)

    @staticmethod
    def lower_case(text):
        return text.lower()

    @staticmethod
    def remove_entities(text):
        regex = re.compile('&[0-9a-z_A-Z]+;')
        return regex.sub(' ', text)


class MinshinglesCounter:
    SPLIT_RGX = re.compile(r'\w+', re.U)

    def __init__(self, window=5, n=20):
        self.window = window
        self.n = n

    def count(self, text):
        words = MinshinglesCounter._extract_words(text)
        shs = self._count_shingles(words)
        mshs = self._select_minshingles(shs)

        return None if None in mshs else mshs

    def _get_order_function(self, num):
        basis = [1663, 1999, 2203, 2381, 2411,
                 2657, 2789, 2843, 2861, 2909,
                 2953, 3169, 3217, 3259, 3491,
                 3467, 3469, 3499, 3511, 27644437]
        return lambda x: divmod(x, basis[num])[1]

    def _select_minshingles(self, shs):
        minshingle = [None]*self.n
        order_funcs = []
        for idx in xrange(self.n):
            order_funcs.append(self._get_order_function(idx))
        for sh in shs:
            for idx in xrange(self.n):
                if (not minshingle[idx] or
                        order_funcs[idx](sh) < order_funcs[idx](minshingle[idx])):
                    minshingle[idx] = sh
        return minshingle

    def _count_shingles(self, words):
        shingles = []
        for i in xrange(len(words) - self.window):
            h = mmh3.hash(' '.join(words[i:i+self.window]).encode('utf-8'))
            shingles.append(h)
        return shingles

    @staticmethod
    def _extract_words(text):
        words = re.findall(MinshinglesCounter.SPLIT_RGX, text)
        return words


def normalize_text(text):
    text = TextNormalizer.join_numbers(text) # replace '40 000' with '40000'
    text = TextNormalizer.remove_entities(text) # replace '&nbsp;', '&amp;' and other entities with whitespace
    text = TextNormalizer.clean_out_punct(text) # remove punctuation
    text = TextNormalizer.lower_case(text) # lower case of the whole text
    return text


def main():
    files = sys.argv[1:] # all input files in current test case
    minshingles_counter = MinshinglesCounter(window=5, n=20)
    reader = DocumentStreamReader(files)

    # docid -> set of "Msh_pos"
    groups = []
    # docid -> url
    urls = []

    for idx, doc in enumerate(reader):
        shs = minshingles_counter.count(normalize_text(doc.text))
        urls.append(doc.url)
        sh_idx = set()
        if shs:
            for jdx in xrange(20):
                sh_idx.add(str(shs[jdx]) + '_' + str(jdx))
        groups.append(sh_idx)

    for idx, i_group in enumerate(groups):
        for jdx, j_group in enumerate(groups):
            if idx < jdx:
                measure = float(len(i_group & j_group)) / 20.
                if measure > .75:
                    print urls[idx], urls[jdx], measure


if __name__ == '__main__':
    main()
