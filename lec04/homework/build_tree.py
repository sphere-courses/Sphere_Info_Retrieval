# coding=utf-8

import re
from compress import *
from doc2words import get_hash
from settings import hash_type

SPLIT_RGX = re.compile(r'\w+|[\(\)&\|!]', re.UNICODE)


def extract_hash(mmaped_file, pos):
    chunk_size = struct.calcsize(hash_type + 'II')
    hash_size = struct.calcsize(hash_type)
    return struct.unpack(hash_type, mmaped_file[chunk_size * pos:chunk_size * pos + hash_size])[0]


def extract_chunk(mmaped_file, pos):
    chunk_size = struct.calcsize(hash_type + 'II')
    return struct.unpack(hash_type + 'II', mmaped_file[chunk_size * pos:chunk_size * (pos + 1)])


# find properties of list corresponding to term (term hash, list bias, list len)
# (using binary search) in mmaped support file
def get_list_props(term, mmaped_file):
    term_hash = get_hash(term)
    left_border = 0
    right_border = mmaped_file.size() / struct.calcsize(hash_type + 'II')

    if left_border == right_border:
        return None
    if term_hash <= extract_hash(mmaped_file, left_border):
        return extract_chunk(mmaped_file, left_border)
    if extract_hash(mmaped_file, right_border - 1) < term_hash:
        return extract_chunk(mmaped_file, right_border - 1)

    while left_border < right_border:
        middle = left_border + (right_border - left_border) / 2
        current_hash = extract_hash(mmaped_file, middle)
        if current_hash == term_hash:
            return extract_chunk(mmaped_file, middle)
        elif current_hash < term_hash:
            left_border = middle + 1
        else:
            right_border = middle

    # If you get here there is
    # no such term in support file


class QtreeTypeInfo:
    def __init__(self, value, op=False, bracket=False, term=False):
        self.value = value
        self.is_operator = op
        self.is_bracket = bracket
        self.is_term = term

    def __repr__(self):
        return repr(self.value)

    def __eq__(self, other):
        if isinstance(other, QtreeTypeInfo):
            return self.value == other.value
        return self.value == other

    # initiate necessity properties for executing query tree
    def set_mmap_props(self, support_mmap, dict_mmap, max_docid, encoding):
        pass

    # returns next docid not less than low_mark
    def get_next_docid(self, low_mark):
        pass


class QTreeTerm(QtreeTypeInfo):
    def __init__(self, term):
        QtreeTypeInfo.__init__(self, term, term=True)
        self.dict_mmap = None
        self.hash = None
        self.list_bias = None
        self.list_len = None
        self.read = 0
        self.last_docid = 0
        self.encoding = None
        self.memorized = []
        self.memorized_bias = 0

    def set_mmap_props(self, support_mmap, dict_mmap, max_docid, encoding):
        self.encoding = encoding
        self.dict_mmap = dict_mmap
        self.hash, self.list_bias, self.list_len = get_list_props(self.value.lower(), support_mmap)

    def get_next_docid(self, low_mark):
        if self.encoding == 'varbyte':
            return self.get_next_docid_varbyte(low_mark)
        elif self.encoding == 'simple9':
            return self.get_next_docid_simple9(low_mark)

    def get_next_docid_varbyte(self, low_mark):
        while self.read < self.list_len:
            delta, read_now = get_next_int_varbyte(self.dict_mmap, self.list_bias + self.read)
            self.read += read_now
            self.last_docid += delta
            if self.last_docid >= low_mark:
                return self.last_docid
        return None

    def get_next_docid_simple9(self, low_mark):
        while self.memorized_bias < len(self.memorized) or self.read < self.list_len:
            if self.memorized_bias == len(self.memorized):
                self.memorized_bias = 0
                self.memorized = get_next_int_simple9(self.dict_mmap, self.list_bias + self.read)
                # add byte len on one int
                self.read += 4
            self.last_docid += self.memorized[self.memorized_bias]
            self.memorized_bias += 1
            if self.last_docid >= low_mark:
                return self.last_docid
        return None


class QTreeOperator(QtreeTypeInfo):
    def __init__(self, val):
        QtreeTypeInfo.__init__(self, val, op=True)
        self.priority = get_operator_prio(val)
        self.left = None
        self.right = None

    def set_mmap_props(self, support_mmap, dict_mmap, max_docid, encoding):
        if self.left != None:
            self.left.set_mmap_props(support_mmap, dict_mmap, max_docid, encoding)
        if self.right != None:
            self.right.set_mmap_props(support_mmap, dict_mmap, max_docid, encoding)

    def get_next_docid(self, low_mark):
        pass


class QTreeOperatorNot(QTreeOperator):
    def __init__(self):
        QTreeOperator.__init__(self, '!')
        self.last_given_docid = 0
        self.last_got_docid = 0
        self.max_docid = 0

    def set_mmap_props(self, support_mmap, dict_mmap, max_docid, encoding):
        QTreeOperator.set_mmap_props(self, support_mmap, dict_mmap, max_docid, encoding)
        self.max_docid = max_docid

    def get_next_docid(self, low_mark):
        self.get_next_docid_proxy(low_mark)
        if self.last_given_docid > self.max_docid:
            return None
        return self.last_given_docid

    def get_next_docid_proxy(self, low_mark):
        # operand on Not is always on the right
        if self.last_got_docid == None:
            self.last_given_docid = max(self.last_given_docid + 1, low_mark)
            return self.last_given_docid

        low_mark = max(low_mark, self.last_given_docid + 1)
        if self.last_got_docid < low_mark:
            self.last_got_docid = self.right.get_next_docid(low_mark)
            if self.last_got_docid == None:
                self.last_given_docid = low_mark
                return self.last_given_docid

        if self.last_got_docid != low_mark:
            self.last_given_docid = low_mark
            return self.last_given_docid


        while True:
            prev_got_docid = self.last_got_docid
            self.last_got_docid = self.right.get_next_docid(prev_got_docid + 1)
            if self.last_got_docid == None:
                self.last_given_docid = prev_got_docid + 1
                break
            if prev_got_docid + 1 < self.last_got_docid:
                self.last_given_docid = prev_got_docid + 1
                break

        return self.last_given_docid


class QTreeOperatorAnd(QTreeOperator):
    def __init__(self):
        QtreeTypeInfo.__init__(self, '&')
        self.last_given_gocid = 0

    def get_next_docid(self, low_mark):
        if self.last_given_gocid == None:
            return self.last_given_gocid

        low_mark = max(low_mark, self.last_given_gocid + 1)
        got_left = self.left.get_next_docid(low_mark)
        got_right = self.right.get_next_docid(low_mark)
        while True:
            if (got_left == None) or (got_right == None):
                self.last_given_gocid = None
                return self.last_given_gocid

            if got_left == got_right:
                self.last_given_gocid = got_left
                return self.last_given_gocid

            if got_left < got_right:
                got_left = self.left.get_next_docid(got_right)
            if got_right < got_left:
                got_right = self.right.get_next_docid(got_left)


class QTreeOperatorOr(QTreeOperator):
    def __init__(self):
        QTreeOperator.__init__(self, '|')
        self.last_given_docid = 0
        self.last_got_left = 0
        self.last_got_right = 0

    def get_next_docid(self, low_mark):
        if self.last_given_docid == None:
            return self.last_given_docid

        low_mark = max(low_mark, self.last_given_docid + 1)

        if self.last_got_left == None:
            self.last_given_docid = self.last_got_right = self.right.get_next_docid(low_mark)
            return self.last_given_docid
        if self.last_got_right == None:
            self.last_given_docid = self.last_got_left = self.left.get_next_docid(low_mark)
            return self.last_given_docid

        if self.last_got_left == self.last_got_right:
            self.last_got_left = self.left.get_next_docid(low_mark)
            self.last_got_right = self.right.get_next_docid(low_mark)
            if (self.last_got_left == None) and (self.last_got_right == None):
                self.last_given_docid = None
            elif (self.last_got_left == None):
                self.last_given_docid = self.last_got_right
            elif (self.last_got_right == None):
                self.last_given_docid = self.last_got_left
            else:
                self.last_given_docid = min(self.last_got_left, self.last_got_right)
        else:
            # Note that on previous step of executing the lowest value between
            # last_got_left and last_got_right was returned,
            # so last_given_docid = min(last_got_left, last_got_right)

            # Swap branches to make left value less than right
            if self.last_got_left > self.last_got_right:
                self.left, self.right = self.right, self.left
                self.last_got_left, self.last_got_right = self.last_got_right, self.last_got_left

            self.last_got_left = self.left.get_next_docid(low_mark)
            if(self.last_got_right < low_mark):
                self.last_got_right = self.right.get_next_docid(low_mark)

            if self.last_got_left == None:
                self.last_given_docid = self.last_got_right
            else:
                self.last_given_docid = min(self.last_got_left, self.last_got_right)

        return self.last_given_docid


class QTreeBracket(QtreeTypeInfo):
    def __init__(self, bracket, is_open):
        QtreeTypeInfo.__init__(self, bracket, bracket=True)
        self.is_open = is_open


def get_operator_prio(s):
    if s == '|':
        return 0
    if s == '&':
        return 1
    if s == '!':
        return 2

    return None


def is_operator(s):
    return get_operator_prio(s) is not None


def tokenize_query(q):
    tokens = []
    for t in map(lambda w: w.lower(), re.findall(SPLIT_RGX, q.decode('utf-8'))):
        if t == '(':
            tokens.append(QTreeBracket(t, True))
        elif t == ')':
            tokens.append(QTreeBracket(t, False))
        elif is_operator(t):
            if t == '!':
                tokens.append(QTreeOperatorNot())
            elif t == '&':
                tokens.append(QTreeOperatorAnd())
            elif t == '|':
                tokens.append(QTreeOperatorOr())
            else:
                tokens.append(QTreeOperator(t))
        else:
            tokens.append(QTreeTerm(t))

    return tokens


def check_if_enclosed(tokens):
    if tokens[0].is_bracket:
        # check if the all statement is enclosed with brackets
        cur_nest = 0
        for cur_pos, token in enumerate(tokens):
            if token.is_bracket:
                if token.is_open:
                    cur_nest += 1
                else:
                    cur_nest -= 1
            if cur_nest == 0 and cur_pos != len(tokens) - 1:
                return False
        return True
    else:
        return False


def build_query_tree(tokens):
    if len(tokens) == 0:
        return None
    if len(tokens) == 1:
        return tokens[0]
    if check_if_enclosed(tokens):
        return build_query_tree(tokens[1:-1])

    best_op_pos = -1
    best_op_prio = -1
    best_op_nest = -1
    cur_nest = 0
    for cur_pos, token in enumerate(tokens):
        if token.is_bracket:
            if token.is_open:
                cur_nest += 1
            else:
                cur_nest -= 1
        elif token.is_term:
            continue
        else:
            if best_op_pos == -1 or \
                    cur_nest < best_op_nest or \
                    (cur_nest == best_op_nest and get_operator_prio(token) <= best_op_prio):
                best_op_pos = cur_pos
                best_op_nest = cur_nest
                best_op_prio = get_operator_prio(token)

    tokens[best_op_pos].left = build_query_tree(tokens[:best_op_pos])
    tokens[best_op_pos].right = build_query_tree(tokens[best_op_pos + 1:])
    return tokens[best_op_pos]


def parse_query(q):
    tokens = tokenize_query(q)
    return build_query_tree(tokens)

