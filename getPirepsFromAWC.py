"""
Code to parse raw PIREP text, or collect it from AWC.
Reference for AWC URL generation: https://www.aviationweather.gov/dataserver/example?datatype=airep
"""

import re
import sys
import numpy as np
import requests
from collections import namedtuple
import xml.etree.ElementTree as ET

# these groups are required

reDict = {}

reUA = re.compile(r' UA')
reDict['UA'] = reUA

reUUA = re.compile(r' UUA')
reDict['UUA'] = reUUA

reOV = re.compile(r'/OV')
reDict['OV'] = reOV

reTM = re.compile(r'/TM')
reDict['TM'] = reTM

reFL = re.compile(r'/FL')
reDict['FL'] = reFL

reTP = re.compile(r'/TP')
reDict['TP'] = reTP


# these groups are optional

reSK = re.compile(r'/SK')
reDict['SK'] = reSK

reWX = re.compile(r'/WX')
reDict['WX'] = reWX

reTA = re.compile(r'/TA')
reDict['TA'] = reTA

reWV = re.compile(r'/WV')
reDict['WV'] = reWV

reTB = re.compile(r'/TB')
reDict['TB'] = reTB

reIC= re.compile(r'/IC')
reDict['IC'] = reIC

reRM = re.compile(r'/RM')
reDict['RM'] = reRM

def parsePirep(line):
    ngrp = len(reDict)

    grpBounds = np.zeros((ngrp+1),dtype=int)
    grpPrefixLen = np.zeros((ngrp+1),dtype=int)
    grpName = np.zeros((ngrp+1),dtype=object)
    grpDict = {}
    
    igrp = 0
    for grp,pat in reDict.items():
        sgrp = pat.search(line)
        if sgrp:
            grpBounds[igrp] = sgrp.span()[0]
            grpName[igrp] = grp
            grpPrefixLen[igrp] = len(pat.pattern)
        igrp += 1

    grpBounds[ngrp] = len(line)
    indx = np.argsort(grpBounds)
    sortedBounds = grpBounds[indx]
    sortedName = grpName[indx]
    sortedPrefixLen = grpPrefixLen[indx]

    for n in range(ngrp):
        i0 = sortedBounds[n] + sortedPrefixLen[n]
        i1 = sortedBounds[n+1]
        if i1 > 0:
            grpTxt = line[i0:i1]
            grpDict[sortedName[n]] = grpTxt

    return grpDict

def pirepURL1(hoursBefore):
    return  'https://www.aviationweather.gov/adds/dataserver_current/httpparam?dataSource=aircraftreports&requestType=retrieve&format=xml&hoursBeforeNow={}'.format(hoursBefore)

def pirepURL2(startTime, endTime):
    return 'https://www.aviationweather.gov/adds/dataserver_current/httpparam?dataSource=aircraftreports&requestType=retrieve&format=xml&startTime={}&endTime={}'.format(startTime, endTime)

def filterPireps(url, outFileName=None):

    r = requests.get(url)
    root = ET.fromstring(r.text)
    tree = ET.ElementTree(element=root)
    zapList = []

    for rpt in root.iter('AircraftReport'):
        rtype = rpt.find('report_type').text
        if rtype == 'PIREP':
            raw = rpt.find('raw_text').text
            rptDict  = parsePirep(raw)
            rptRM = rptDict.get('RM')
            if rptRM:
                rmTag = ET.SubElement(rpt, 'remarks')
                rmTag.text = rptRM

            if rpt.find('sky_condition') is None:
                zapList.append(rpt)
        else:
            zapList.append(rpt)

    # this is awful code - it requires that you KNOW that the DIRECT parent of all AircraftReport
    # elements is root.data.  But remove() doesn't work except on the DIRECT parent
    # should be using lxml instead of ET
    
    reportRoot = root.find('data')
    for zap in zapList:
        reportRoot.remove(zap)

    prunedTree = ET.ElementTree(reportRoot)
    if outFileName is not None:
        of = open(outFileName, 'w')
        prunedTree.write(of, encoding='unicode', xml_declaration=True)
        of.close()

    return prunedTree
