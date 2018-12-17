from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
import xml.etree.ElementTree as ET
import numpy as np
import requests
import re
import io

MetersToFeet = 3.28084

plotFile = None

def setPlotFile(fileName):
    global plotFile
    plotFile = PdfPages(fileName)
    plt.interactive(False)

def closePlotFile():
    global plotFile
    if plotFile is not None:
        plotFile.close()
        plotFile = None
        plt.interactive(True)

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
        self.iceBase = None
        self.iceTop = None
        self.rawText = None

    def __repr__(self):
        return 't: {} lat: {} long: {} alt: {} temp: {} AC: {} sky: {} icing: {} turb: {} cloudBase: {} cloudTop: {}'\
              .format(self.time, self.lat, self.long, self.alt, self.temp, self.aircraft, self.sky, self.icing,\
                      self.turb, self.cloudBase, self.cloudTop, self.iceBase, self.iceTop)
class Sounding:
    def __init__(self):
        self.hdr = None
        self.press = None
        self.height = None
        self.temp = None
        self.dewpt = None
        self.wdir = None
        self.wspd = None

        
    def plot(self, p):
        global plotFile
        
        pirepMissingAlt = 60000
        
        fig = plt.figure()
        ymin = 0
        ymax = 20000
        xmin = np.min(self.dewpt)
        xmax = np.max(self.temp)

        plt.plot(self.temp, self.height*MetersToFeet)
        plt.plot(self.dewpt, self.height*MetersToFeet)
        plt.title(p.raw, fontsize='x-small')
        plt.xlabel('deg C')
        plt.ylabel('ft MSL')
        if p.cloudBase is not None:
            cloudBase = float(p.cloudBase)
            if cloudBase != pirepMissingAlt:
                plt.plot([xmin, xmax], [cloudBase, cloudBase], linestyle='-.', color='black')
                ymax = np.max([ymax, 1.2*cloudBase])

        if p.cloudTop is not None:
            cloudTop = float(p.cloudTop)
            if cloudTop != pirepMissingAlt:
                plt.plot([xmin, xmax], [cloudTop, cloudTop], linestyle=':', color='black')
                ymax = np.max([ymax, 1.2*cloudTop])

        if p.iceBase is not None:
            iceBase = float(p.iceBase)
            if iceBase != pirepMissingAlt:
                plt.plot([xmin, xmax], [iceBase, iceBase], linestyle='-.', linewidth=3, color='blue')
                ymax = np.max([ymax, 1.2*iceBase])

        if p.iceTop is not None:
            iceTop = float(p.iceTop)
            if iceTop != pirepMissingAlt:
                plt.plot([xmin, xmax], [iceTop, iceTop], linestyle=':', linewidth=3, color='blue')
                ymax = np.max([ymax, 1.2*iceTop])

        plt.ylim(ymin,ymax)
        plt.xlim(xmin, xmax)
        if plotFile is None:
            plt.show()
        else:
            plotFile.savefig()

        plt.close(fig)
        

def getRucSounding(pirep, model='Op40'):

    s = Sounding()
    
    url = 'https://rucsoundings.noaa.gov/get_soundings.cgi?startSecs={}&n_hrs=1&airport={},{}&data_source={}'.format(pirep.time, pirep.lat, pirep.long, model)

    print(url)

    r = requests.get(url)
    data = r.text

    # This keeps only the first dataset of the N they insist on delivering.  Else we could just initialize the dataframe from the url!
    
    i = 0
    data1hr = None
    for m in re.finditer(model,data):
        if i==1:
            hdr = data[0:m.start()-1]
        elif i==2:
            data1hr = data[0:m.start()-1]
            break
        i += 1

    if data1hr is None:
        print('getRucSounding failed')
        return None
    
    f = io.StringIO(data1hr)
    df=pd.read_table(f,delim_whitespace=True,skiprows=6,names=['type','press','height','temp','dewpt','wind dir','wind spd'])

    dfmask = df.mask(df==99999)

    s.press = dfmask['press'].astype(float)
    s.height = dfmask['height'].astype(float)
    s.temp = dfmask['temp'].astype(float)/10.0
    s.dewpt = dfmask['dewpt'].astype(float)/10.0
    s.wdir = dfmask['wind dir'].astype(float)
    s.wspd = dfmask['wind spd'].astype(float)
    
    return s


def plotRucSoundingForPirep(pirep, model='Op40'):

    s = getRucSounding(pirep, model)

    if s is not None:
        s.plot(pirep)
        return s

def plotRucSoundingForPirepList(plist, outFileName, model='Op40'):
    setPlotFile(outFileName)

    for p in plist:
        plotRucSoundingForPirep(p, model)

    closePlotFile()
    
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
                
        ice = rpt.find('icing_condition')
        if ice is not None:
            p.icing = ""
            for i in ice.items():
                if i[0] == 'icing_base_ft_msl':
                    p.iceBase = i[1]
                if i[0] == 'icing_top_ft_msl':
                    p.iceTop = i[1]
                    
                p.icing += '{}: {} '.format(i[0], i[1])
                
        turb = rpt.find('turbulence_condition')
        if turb is not None:
            p.turb = ""
            for t in turb.items():
                p.turb += '{}: {} '.format(t[0], t[1])

        raw = rpt.find('raw_text')
        if raw is not None:
            p.raw = raw.text
    
        pirepList.append(p)

    return(pirepList)
                
        
        
                             
                             
    
    
    
