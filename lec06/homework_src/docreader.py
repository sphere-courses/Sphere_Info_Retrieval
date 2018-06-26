#!/usr/bin/env python
# -*- coding: utf-8 -*-

import document_pb2
import struct
import gzip
import sys


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

def main():
    """
    Every 'document' is a protobuf with 3 fields: url, raw text and already extracted _clean_ text
    You should use clean text for shingling
    """
    reader = DocumentStreamReader(sys.argv[1:])
    for doc in reader:
        print "%s\tbody: %d, text: %d" % (
            doc.url,
            len(doc.body) if doc.HasField('body') else 0,
            len(doc.text) if doc.HasField('text') else 0
        )


if __name__ == '__main__':
    main()
