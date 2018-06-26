import re
import unittest

SPLIT_RGX = re.compile(r'\w+|[\(\)&\|!]', re.U)


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


class QTreeTerm(QtreeTypeInfo):
    def __init__(self, term):
        QtreeTypeInfo.__init__(self, term, term=True)


class QTreeOperator(QtreeTypeInfo):
    def __init__(self, val):
        QtreeTypeInfo.__init__(self, val, op=True)
        self.priority = get_operator_prio(val)
        self.left = None
        self.right = None


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
    for t in map(lambda w: w.encode('utf-8'), re.findall(SPLIT_RGX, q)):
        if t == '(':
            tokens.append(QTreeBracket(t, True))
        elif t == ')':
            tokens.append(QTreeBracket(t, False))
        elif is_operator(t):
            tokens.append(QTreeOperator(t))
        else:
            tokens.append(QTreeTerm(t))

    return tokens


def build_query_tree(tokens):
    if len(tokens) == 0:
        return None
    if len(tokens) == 1:
        return tokens[0]
    if tokens[0].is_bracket and tokens[-1].is_bracket:
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
            if best_op_pos == -1 or (cur_nest <= best_op_nest and get_operator_prio(token) <= best_op_prio):
                best_op_pos = cur_pos
                best_op_nest = cur_nest
                best_op_prio = get_operator_prio(token)

    tokens[best_op_pos].left = build_query_tree(tokens[:best_op_pos])
    tokens[best_op_pos].right = build_query_tree(tokens[best_op_pos + 1:])
    return tokens[best_op_pos];

def parse_query(q):
    tokens = tokenize_query(q)
    return build_query_tree(tokens)


""" Collect query tree to sting back. It needs for tests. """


def qtree2str(root, depth=0):
    if root.is_operator:
        need_brackets = depth > 0 and root.value != '!'
        res = ''
        if need_brackets:
            res += '('

        if root.left:
            res += qtree2str(root.left, depth + 1)

        if root.value == '!':
            res += root.value
        else:
            res += ' ' + root.value + ' '

        if root.right:
            res += qtree2str(root.right, depth + 1)

        if need_brackets:
            res += ')'

        return res
    else:
        return root.value


""" Test tokenizer and parser itself """


class QueryParserTest(unittest.TestCase):
    @staticmethod
    def parsed_tree(q):
        return qtree2str(parse_query(q)).decode('utf-8')

    def test_tokenizer(self):
        self.assertEqual(['foxy', '&', 'lady'], tokenize_query('foxy & lady'))
        self.assertEqual(['foxy', '&', 'lady', '|', 'madam'], tokenize_query('foxy & lady | madam'))
        self.assertEqual(['foxy', '&', '(', 'lady', '|', 'madam', ')'], tokenize_query('foxy & (lady | madam)'))
        self.assertEqual(['foxy', '&', '(', '!', 'lady', '|', 'madam', ')'], tokenize_query('foxy & (!lady | madam)'))

    def test_parser(self):
        self.assertEqual('foxy & lady', QueryParserTest.parsed_tree('foxy & lady'))
        self.assertEqual('(foxy & lady) | madam', QueryParserTest.parsed_tree('foxy & lady | madam'))
        self.assertEqual('foxy & (lady | madam)', QueryParserTest.parsed_tree('foxy & (lady | madam)'))

    def test_right_order(self):
        self.assertEqual('((one & two) & three) & four', QueryParserTest.parsed_tree('one & two & three & four'))

    def test_neg(self):
        self.assertEqual('foxy & !(lady | madam)', QueryParserTest.parsed_tree('foxy & !(lady | madam)'))


suite = unittest.TestLoader().loadTestsFromTestCase(QueryParserTest)
unittest.TextTestRunner().run(suite)