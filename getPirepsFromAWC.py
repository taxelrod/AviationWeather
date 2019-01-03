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
from pirepLark import parseAltitudes
import getAirportData

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

# altitudes in Pireps that are greater than hundredsCutoff are assumed to be in feet rather
# than hundreds of feet

hundredsCutoff = 400

# see comments in correctForAGL()
#
minAltitudeAGL = 200

airportData = getAirportData.AirportData('Data/USairports.csv')

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

def recentPirepURL(hoursAgo):
    return  'https://www.aviationweather.gov/adds/dataserver_current/httpparam?dataSource=aircraftreports&requestType=retrieve&format=xml&hoursBeforeNow={}'.format(hoursAgo)

def intervalPirepURL(startTime, endTime):
    return 'https://www.aviationweather.gov/adds/dataserver_current/httpparam?dataSource=aircraftreports&requestType=retrieve&format=xml&startTime={}&endTime={}'.format(startTime, endTime)

def getPireps(url, outFileName=None):

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

    #
    # Now go through and filter duplicates - these are pireps that are identical in all but receipt_time
    #

    zapList = []
    keepList = []
    for rpt in reportRoot.iter('AircraftReport'):
        # get obsTime, lat, longi
        obsTime = rpt.find('observation_time').text
        lat = rpt.find('latitude').text
        longi = rpt.find('longitude').text
        if (obsTime, lat, longi) not in keepList:
            keepList.append((obsTime, lat, longi))
        else:
            zapList.append(rpt)
            print('filtered: ', obsTime, lat, longi)
            
    for zap in zapList:
        reportRoot.remove(zap)

    #
    # reparse the sky conditions
    #
    reparseSK(prunedTree)
    
    if outFileName is not None:
        of = open(outFileName, 'w')
        try:
            prunedTree.write(of, encoding='unicode', xml_declaration=True)
        except:
            print('exception in prunedTree.write')
        of.close()

    return prunedTree

def getSKfromPireps(ptree):

    root = ptree.getroot()
    SKlist = []

    for rpt in root.iter('AircraftReport'):
        rtype = rpt.find('report_type').text
        if rtype == 'PIREP':
            raw = rpt.find('raw_text').text
            pDict = parsePirep(raw)
            if 'SK' in pDict:
                SKlist.append(pDict['SK'])

    return SKlist

"""
The cloud_base_ft_msl and cloud_top_ft_msl values from AWC are not very reliable.
Reparse the SK field using Lark to do better.

It is assumed that ptree has been generated by getPireps(), so we can assume
that the sky_condition node exists for each Pirep

"""

def reparseSK(ptree):
            
    root = ptree.getroot()

    for rpt in root.iter('AircraftReport'):
        raw = rpt.find('raw_text').text
        pDict = parsePirep(raw)
        if 'SK' not in pDict:
            print('SK missing for: ', raw)
            continue
        else:
            skElement = rpt.find('sky_condition')
            if skElement is None:
                print('sky_condition missing for:', raw)
                continue
            else:
                print(pDict['SK'])
                (baseAlt, topAlt) = parseAltitudes(pDict['SK'])
                skElement.clear()
                if baseAlt is not None:
                    if baseAlt > hundredsCutoff:
                        baseAltFt = baseAlt
                    else:
                        baseAltFt = baseAlt*100
                    baseAltFt = correctForAGL(pDict, baseAltFt)
                    skElement.set('cloud_base_ft_msl', str(baseAltFt))
                    print('set base to: ', baseAltFt)
                if topAlt is not None:
                    if topAlt > hundredsCutoff:
                        topAltFt = topAlt
                    else:
                        topAltFt = topAlt*100
                    topAltFt = correctForAGL(pDict, topAltFt)
                    skElement.set('cloud_top_ft_msl', str(topAltFt))
                    print('set top to: ', topAltFt)


#
# Some altitudes in Pireps are actually AGL and not MSL.  Apply the rule that if the report is directly at an
# airport, and the reported altitude is less than the field altitude + minAltitudeAGL, correct AGL to MSL
#
def correctForAGL(pDict, altFt):
            
    if 'OV' not in pDict:
        print('OV missing for: ', raw)
        return altFt
    else:
        airportID = 'K' + pDict['OV'].strip()
        airportAltitude = airportData.getAirportAltitude(airportID)
        print(airportID,' altitude:', airportAltitude, ' Pirep alt:', altFt)
        if airportAltitude is not None:
            if altFt < airportAltitude + minAltitudeAGL:
                print('Corrected ', altFt, ' AGL to ', altFt + airportAltitude)
                return altFt + airportAltitude
            else:
                return altFt
        else:
            return altFt

               

            
