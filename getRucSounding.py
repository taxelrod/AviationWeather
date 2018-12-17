from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
import xml.etree.ElementTree as ET
from collections import namedtuple
import numpy as np
import requests
import re
import io

MetersToFeet = 3.28084

#Pirep = namedtuple('Pirep', ['time', 'lat', 'long', 'alt', 'temp', 'aircraft', 'sky', 'icing', 'turb'])

class Pirep:
    def __init__(self):
        self.time = None
        self.lat = None
        self.long = None
        self.alt = None
        self.temp = None
        self.aircraft = None
        self.sky = None
        self.icing = None
        self.turb = None
        self.cloudBase = None
        self.cloudTop = None
    def __repr__(self):
        return 't: {} lat: {} long: {} alt: {} temp: {} AC: {} sky: {} icing: {} turb: {} cloudBase: {} cloudTop: {}'\
              .format(self.time, self.lat, self.long, self.alt, self.temp, self.aircraft, self.sky, self.icing, self.turb, self.cloudBase, self.cloudTop)

def getRucSounding(pirep, model='Op40'):

    url = 'https://rucsoundings.noaa.gov/get_soundings.cgi?startSecs={}&n_hrs=1&airport={},{}&data_source={}'.format(pirep.time, pirep.lat, pirep.long, model)

    print(url)

    r = requests.get(url)
    data = r.text

    # This keeps only the first dataset of the N they insist on delivering.  Else we could just initialize the dataframe from the url!
    
    i = 0
    for m in re.finditer(model,data):
        if i==1:
            hdr = data[0:m.start()-1]
        elif i==2:
            data1hr = data[0:m.start()-1]
            break
        i += 1

    f = io.StringIO(data1hr)
    df=pd.read_table(f,delim_whitespace=True,skiprows=6,names=['type','press','height','temp','dewpt','wind dir','wind spd'])

    dfmask = df.mask(df==99999)

    press = dfmask['press'].astype(float)
    height = dfmask['height'].astype(float)
    temp = dfmask['temp'].astype(float)/10.0
    dewpt = dfmask['dewpt'].astype(float)/10.0
    wdir = dfmask['wind dir'].astype(float)
    wspd = dfmask['wind spd'].astype(float)
    
    return press, height, temp, dewpt, wdir, wspd, hdr


def plotRucSoundingForPirep(pirep, fileName=None, model='Op40'):

    p, h, t, dw, wdir, wspd, hdr = getRucSounding(pirep, model)

    fig=plt.figure()
    ymax = 20000
    xmin = np.min(dw)
    xmax = np.max(t)

    plt.plot(t, h*MetersToFeet)
    plt.plot(dw, h*MetersToFeet)
    plt.title('{} {}'.format(pirep.sky, pirep.icing))
    plt.xlabel('deg C')
    plt.ylabel('ft MSL')
    if pirep.cloudBase is not None:
        cloudBase = float(pirep.cloudBase)
        plt.plot([xmin, xmax], [cloudBase, cloudBase], linestyle='-.')
        ymax = np.max([ymax, 1.2*cloudBase])
    if pirep.cloudTop is not None:
        plt.plot([xmin, xmax], [pirep.cloudTop, pirep.cloudTop], linestyle=':')
        ymax = np.max([ymax, 1.2*float(pirep.cloudTop)])
        
    print(ylim)
    plt.ylim(0,ymax)
    plt.xlim(xmin, xmax)
    plt.show()

    return p, h, t, dw, wdir, wspd, hdr

"""
load the data needed for getting the soundings and making the plots
from xmlTree, and elementTree.  It is assumed this tree has been returned,
and thus filtered for usefulness by getPirepsFromAWC.filterPireps()
"""

def loadPirepData(xmlTree):
    pirepList = []

    for rpt in xmlTree.findall('AircraftReport'):
        p = Pirep()
        t = rpt.find('observation_time')
        if t is not None:
            tCompatible = t.text.replace('Z','+0000')
            p.time = datetime.strptime(tCompatible, '%Y-%m-%dT%H:%M:%S%z').timestamp()
        else:
            print('rejected: ', rpt)
            continue

        lat = rpt.find('latitude')
        if lat is not None:
            p.lat = lat.text
        else:
            print('rejected: ', rpt)
            continue

        longi = rpt.find('longitude')
        if longi is not None:
            p.long = longi.text
        else:
            print('rejected: ', rpt)
            continue
        
        sky = rpt.find('sky_condition')
        if sky is not None:
            p.sky = ""
            for s in sky.items():
                if s[0] == 'cloud_base_ft_msl':
                    p.cloudBase = s[1]
                if s[0] == 'cloud_top_ft_msl':
                    p.cloudTop = s[1]
                    
                p.sky += '{}: {} '.format(s[0], s[1])
                
        turb = rpt.find('turbulence_condition')
        if turb is not None:
            p.turb = ""
            for t in turb.items():
                p.turb += '{}: {} '.format(t[0], t[1])
                
        ice = rpt.find('icing_condition')
        if ice is not None:
            p.ice = ""
            for i in ice.items():
                p.ice += '{}: {} '.format(i[0], i[1])

        pirepList.append(p)

    return(pirepList)
                
        
        
                             
                             
    
    
    
