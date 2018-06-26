# coding=utf-8

# !/usr/bin/env python
import struct
import gzip
import pickle
import os.path
import argparse
import document_pb2

from settings import dict_file_name, support_file_name, info_file_name, url_file_name
from create_dict import create_dict_varbyte, create_dict_simple9


class DocumentStreamReader:
    def __init__(self, paths):
        self.paths = paths

    def open_single(self, path):
        return gzip.open(path, 'rb') if path.endswith('.gz') else open(path, 'rb')

    def __iter__(self):
        for path in self.paths:
            with self.open_single(path) as stream:
                while True:
                    sb = stream.read(4)
                    if sb == '':
                        break
                    size = struct.unpack('i', sb)[0]
                    msg = stream.read(size)
                    doc = document_pb2.document()
                    doc.ParseFromString(msg)
                    yield doc


def parse_command_line():
    parser = argparse.ArgumentParser(description='compressed documents reader')
    parser.add_argument('encoding', nargs=1)
    parser.add_argument('files', nargs='+', help='Input files (.gz or plain) to process')
    return parser.parse_args()


if __name__ == '__main__':

    encoding = None

    if os.path.isfile(dict_file_name + 'pickle'):
        files_pickle_file = open(dict_file_name + '_files_pickle', 'rb')
        files = pickle.load(files_pickle_file)
        files_pickle_file.close()

        reader = DocumentStreamReader(files)

        create_dict_varbyte(dict_file_name, support_file_name, info_file_name, url_file_name, reader, True)
        quit()
    else:
        encoding = parse_command_line().encoding[0]
        files = parse_command_line().files

        # Crutch
        if encoding == 'make_dict':
            quit()

        if encoding == 'varbyte':
            reader = DocumentStreamReader(files[:len(files)/2])

            files_pickle_file = open(dict_file_name + '_files_pickle', 'wb')
            pickle.dump(files[len(files)/2:], files_pickle_file)
            files_pickle_file.close()
        else:
            reader = DocumentStreamReader(files)

    if encoding == 'varbyte':
        create_dict_varbyte(dict_file_name, support_file_name, info_file_name, url_file_name, reader, False)
    elif encoding == 'simple9':
        create_dict_simple9(dict_file_name, support_file_name, info_file_name, url_file_name, reader)