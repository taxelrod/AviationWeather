#!/usr/bin/env python

from lark import Lark, Transformer, Token
import sys

pirep_grammar = """
    ?start: base
          | tops
          | base tops

    ?base: base_kw altitude -> basealt0
         | altitude base_kw -> basealt1
         | words base
         | base words

    ?altitude: number
             | unkn

    ?number.9: NUMBER

    ?unkn.9: "UNKN"

    ?words: CNAME
         | words CNAME

    ?base_kw.8: "BASE"
         | "BASES"
         | "BKN"
         | "OVC"
         | "B"
         | "SCT"

    ?tops: tops_kw
         | tops_kw altitude -> topalt0
         | altitude tops_kw -> topalt1
         | tops words
         | words tops
    
    ?tops_kw.8: "TOPS"
            | "TOP"
            | "T"

    %import common.CNAME
    %import common.NUMBER
    %import common.WS_INLINE

    %ignore WS_INLINE
"""

def getAltitudesFromTree(tree):

    baseAltitude = None
    for node in tree.find_pred(lambda n: (n.data == 'basealt0') or (n.data == 'basealt1')):
        for child in node.children:
            if isinstance(child, Token):
                baseAltitude = int(child)
        
    topAltitude = None
    for node in tree.find_pred(lambda n: (n.data == 'topalt0') or (n.data == 'topalt1')):
        for child in node.children:
            if isinstance(child, Token):
                topAltitude = int(child)

    return (baseAltitude, topAltitude)
        
if __name__ == '__main__':
#    pirep_parser = Lark(pirep_grammar, ambiguity='explicit', debug=True)
    pirep_parser = Lark(pirep_grammar, ambiguity='resolve', debug=True)
    pirep = pirep_parser.parse

    inF = None
    if len(sys.argv) > 1:
        inFileName = sys.argv[1]
        inF = open(inFileName, 'r')
    if inF is None:
        while True:
            try:
                s = input('> ')
            except EOFError:
                break
            ptree = pirep(s)
            print(ptree)
            print(s)
            print(getAltitudesFromTree(ptree))
            
    else:
        for line in inF:
            tline = line.translate({ord('-'):u' ', ord('/'):u' ', ord('\\'):u' ', ord('.'):u' '})
            try:
                ptree = pirep(tline.rstrip())
#                print(ptree)
                print(tline.rstrip(), ' -> ', getAltitudesFromTree(ptree))
            except:
                print('parse error on: ', tline)
                continue
        inF.close()
                      
           

    
