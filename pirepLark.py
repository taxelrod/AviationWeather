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
             | "UNKN"

    ?number.9: NUMBER

    ?words: CNAME
         | words CNAME

    ?base_kw: "BASE"
         | "BASES"
         | "BKN"
         | "OVC"
         | "B"
         | "SCT"

    ?tops: tops_kw
         | tops_kw altitude
         | tops words
         | words tops
    
    ?tops_kw: "TOPS"
            | "TOP"
            | "T"

    %import common.CNAME
    %import common.NUMBER
    %import common.WS_INLINE

    %ignore WS_INLINE
"""

def getAltitudesFromTree(tree):

    for node in tree.find_data('basealt0'):
        for child in node.children:
            if isinstance(child, Token):
                print('Altitude: ', int(child))
        
    for node in tree.find_data('basealt1'):
        for child in node.children:
            if isinstance(child, Token):
                print('Altitude: ', int(child))
        
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
            getAltitudesFromTree(ptree)
            
    else:
        for line in inF:
            tline = line.translate({ord('-'):u' ', ord('/'):u' ', ord('\\'):u' '})
            try:
                ptree = pirep(tline.rstrip())
                print(ptree)
                print(tline)
            except:
                print('parse error on: ', tline)
                continue
        inF.close()
                      
           

    
