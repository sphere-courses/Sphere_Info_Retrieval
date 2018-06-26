# coding=utf-8

import mmap
import struct
import fileinput

from build_tree import parse_query
from settings import dict_file_name, support_file_name, info_file_name, url_file_name, \
    encoding_varbyte_code, encoding_simple9_code


# return docids specified by query @query
# using index from @dict_mmap, @support_mmap, @info_mmap
def execute_query(query, dict_mmap, support_mmap, info_mmap):
    # extract global dictionary props (max_docid, encoding, ...)
    max_docid = struct.unpack('I', info_mmap[0:struct.calcsize('I')])[0]
    encoding_code = struct.unpack('I', info_mmap[struct.calcsize('I'):2 * struct.calcsize('I')])[0]

    encoding = str
    if encoding_code == encoding_varbyte_code:
        encoding = 'varbyte'
    elif encoding_code == encoding_simple9_code:
        encoding = 'simple9'

    tree = parse_query(query)
    tree.set_mmap_props(support_mmap, dict_mmap, max_docid=max_docid, encoding=encoding)
    result_docid = []
    while True:
        docid = tree.get_next_docid(0)
        if (docid == None):
            break
        result_docid.append(docid)
    return result_docid


dict_file = open(dict_file_name, 'r+')
dict_mmap = mmap.mmap(dict_file.fileno(), 0)

support_file = open(support_file_name, 'r+')
support_mmap = mmap.mmap(support_file.fileno(), 0)

info_file = open(info_file_name, 'r+')
info_mmap = mmap.mmap(info_file.fileno(), 0)

url_file = open(url_file_name, 'r+')
urls = []
for url in url_file.readlines():
    urls.append(url[:-1])


for query in fileinput.input():
    if query[-1] == '\n':
        query = query[:-1]
    result = execute_query(query, dict_mmap, support_mmap, info_mmap)

    print query
    print len(result)
    for docid in result:
        print urls[docid - 1]


dict_mmap.close()
dict_file.close()

support_mmap.close()
support_file.close()

info_mmap.close()
info_file.close()
