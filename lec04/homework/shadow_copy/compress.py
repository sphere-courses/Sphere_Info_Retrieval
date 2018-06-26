# coding=utf-8

import struct


# Convert integer value to string of bytes in VarByte encoding
def integer_to_varbyte(value):
    str_ = ''
    while value >= 0x80:
        str_ += chr(value & 0x7f)
        value >>= 7
    if value == 0 and len(str_) > 0:
        str_[len(str_) - 1] = chr(ord(str_[len(str_) - 1]) | 0x80)
    else:
        str_ += chr(value | 0x80)
    return str_[::-1]


# Convert string of bytes in VarByte encoding to integer value
def get_next_int_varbyte(mmaped_file, bias):
    value = ord(mmaped_file[bias]) - 0x80
    readed = 1
    while bias + readed < mmaped_file.size() and not(ord(mmaped_file[bias + readed]) & 0x80):
        value = (value << 7) | ord(mmaped_file[bias + readed])
        readed += 1
    return value, readed


# Magic constant 28 - bit_len of 4 byte integer sub 4 bit len codeword
# Various precomputed things to make coding faster by eliminating if statements
'''
len    code     code to decimal  code to hex
1      0001     1                   0x1
2      0010     2                   0x2
3      0011     3                   0x3
4      0100     4                   0x4
5      0101     5                   0x5
7      0111     7                   0x7
9      1001     9                   0x9
14     1110     14                  0xe
28     1111     15                  0xf
'''
masks = [0,          # -
         0x10,       # 1
         0x30,       # 2
         0x70,       # 3
         0xf0,       # 4
         0x1f0,      # 5
         0,          # -
         0x7f0,      # 7
         0,          # -
         0x1ff0,     # 9
         0,          # -
         0,          # -
         0,          # -
         0,          # -
         0x3fff0,    # 14
         0xfffffff0  # 15
         ]
bit_len_to_code_bit_len = [
    0,      # -
    1,      # 1
    2,      # 2
    3,      # 3
    4,      # 4
    5,      # 5
    7,      # -
    7,      # 7
    9,      # -
    9,      # 9
    14,     # -
    14,     # -
    14,     # -
    14,     # -
    14,     # 14
    28,     # 15
    28,     # -
    28,     # -
    28,     # -
    28,     # -
    28,     # -
    28,     # -
    28,     # -
    28,     # -
    28,     # -
    28,     # -
    28,     # -
    28,     # -
    28,     # 28
]
bit_len_to_code = [
    0,    # -
    0x1,  # 1
    0x2,  # 2
    0x3,  # 3
    0x4,  # 4
    0x5,  # 5
    0,    # -
    0x7,  # 7
    0,    # -
    0x9,  # 9
    0,    # -
    0,    # -
    0,    # -
    0,    # -
    0xe,  # 14
    0,    # -
    0,    # -
    0,    # -
    0,    # -
    0,    # -
    0,    # -
    0,    # -
    0,    # -
    0,    # -
    0,    # -
    0,    # -
    0,    # -
    0,    # -
    0xf,  # 28
]
code_to_bit_len = [
    0,   # -
    1,   # 0x1
    2,   # 0x2
    3,   # 0x3
    4,   # 0x4
    5,   # 0x5
    0,   # -
    7,   # 0x7
    0,   # -
    9,   # 0x9
    0,   # -
    0,   # -
    0,   # -
    0,   # -
    14,  # 0xe
    28,  # 0xf
]


# Convert list of integers to integer of size 4 byte (packed by struct) in Simple9 encoding
def integer_to_simple9(values, bit_len):
    value = bit_len_to_code[bit_len]

    # Append necessary number of zeros to satisfy list len
    # to conformity of list len and bit len of numbers in list
    values += [0] * (28 / bit_len - len(values))

    for i in xrange(28 / bit_len):
        value |= (values[i] << (i * bit_len + 4))
    return struct.pack('I', value)


# Convert integer of size 4 byte (packed by struct) in Simple9 encoding to list of integers
# We greately use, that sequence contain only NON ZERO positive numbers
def get_next_int_simple9(mmaped_file, bias):
    value = struct.unpack('I', mmaped_file[bias:bias+struct.calcsize('I')])[0]
    code = value & 0xf
    bit_len = code_to_bit_len[code]
    mask = masks[code]
    values = []
    for i in xrange(28 / bit_len):
        next_value = (value & (mask << (i * bit_len))) >> (i * bit_len + 4)
        if next_value > 0:
            values.append(next_value)
        else:
            return values
    return values


# [...] <- ()
# Check if we can append number with @new_value
# to list of @cur_num numbers of len @cur_bit_len
# return (True/False, new_bit_len)
def decider(cur_bit_len, cur_num, new_value):
    new_bit_len = max(cur_bit_len, bit_len_to_code_bit_len[new_value.bit_length()])
    return 28 - (cur_num + 1) * new_bit_len >= 0, new_bit_len


# compress list of NON ZERO integers in string in Simple9 encoding
def compress_list_simple9(list_):
    compressed_str = ''
    cur_bit_len = 0
    accumulate = []
    for value in list_:
        decision, new_bit_len = decider(cur_bit_len, len(accumulate), value)
        if decision:
            cur_bit_len = new_bit_len
            accumulate.append(value)
        else:
            compressed_str += integer_to_simple9(accumulate, cur_bit_len)
            cur_bit_len = bit_len_to_code_bit_len[value.bit_length()]
            accumulate = [value]
    compressed_str += integer_to_simple9(accumulate, cur_bit_len)
    return compressed_str
