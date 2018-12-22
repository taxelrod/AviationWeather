import re
from pyleri import Sequence
from pyleri import Keyword
from pyleri import Grammar
from pyleri import Regex
from pyleri import Choice

class PirepGrammar(Grammar):
    RE_KEYWORDS = re.compile('[^0-9 ]+')
    r_num = Regex('[0-9]+')
    r_stuff = Regex('.*')
    k_base = Keyword('BASE')
    k_bkn = Keyword('BKN')
    k_ovc = Keyword('OVC')

    baseAltType1 = Sequence(Choice(k_base, k_bkn, k_ovc), r_num)
    baseAltType2 = Sequence(r_num, Choice(k_base, k_bkn, k_ovc))

    START = Sequence(Choice(baseAltType1, baseAltType2), r_stuff)
    
# Returns properties of a node object as a dictionary:
def node_props(node, children):
    return {
        'start': node.start,
        'end': node.end,
        'name': node.element.name if hasattr(node.element, 'name') else None,
        'element': node.element.__class__.__name__,
        'string': node.string,
        'children': children}


# Recursive method to get the children of a node object:
def get_children(children):
    return [node_props(c, get_children(c.children)) for c in children]


# View the parse tree:
def view_parse_tree(res):
    start = res.tree.children[0] \
        if res.tree.children else res.tree
    return node_props(start, get_children(start.children))
