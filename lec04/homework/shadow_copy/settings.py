global dict_file_name
dict_file_name = './files/dict_encoded.bin'
global support_file_name
support_file_name  = './files/dict_support.bin'
global info_file_name
info_file_name = './files/dict_info.bin'
global url_file_name
url_file_name = './files/docid_to_url.bin'

# Codes of encode (for info file)
global encoding_varbyte_code
encoding_varbyte_code = 0
global encoding_simple9_code
encoding_simple9_code = 1

# Specify len of hash len and type (for pack and unpack)
global hash_type
# i - signed int
# I - unsigned int
# Q - unsigned long long
hash_type = 'I'
