import pandas as pd

class AirportData:
    def __init__(self, databaseFile):
        self.df = pd.read_csv(databaseFile, index_col=0)

    def getAirportAltitude(self, airportID):
        try:
            airportData = self.df.loc[airportID]
            return airportData['elevation_ft']
        except KeyError:
            return None
