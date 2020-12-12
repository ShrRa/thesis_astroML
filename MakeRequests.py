import requests
import pandas as pd
import DataCleaning

class Requester:
    
    url='https://api.adsabs.harvard.edu/v1/search/query'
    
    def __init__(self, token):
        self.token = token
        self.headers = {'Authorization': 'Bearer '+token}
        self.dateRange=[]
        
    def setDateRange(self,yearStart,yearEnd):
        self.dateRange=pd.date_range(start=str(int(yearStart))+"-01-01",end=str(int(yearEnd))+"-02-01",freq='MS').strftime("%Y-%m-%d").tolist()
        if self.dateRange==[]:
            print('dateRange is empty. Check that your (yearStart,monthStart) were before (yearEnd,monthEnd)')
            return
        self.dateRange=[l[:-2]+'00' for l in self.dateRange]
        return
    
    def setParams(self,searchCriteria,fields,maxRows=None):
        self.searchCriteria=searchCriteria
        self.fields=fields
        self.maxRows=maxRows
        self.params=[('fq',q) for q in self.searchCriteria]
        self.params[0]=('q',self.params[0][1])
        self.flags=[('fl',','.join(self.fields))]
        if self.maxRows:
            self.rows=[('rows',str(int(self.maxRows)))]
        else:
            self.rows=[('rows',str(int(2000)))]
        self.params=tuple(self.params+self.flags+self.rows)
        return
        
    def setParamsForRequest(self,startRow,pubdate=None):
        if pubdate:
            params = self.params+(('pubdate', pubdate),)
        params = self.params+(('start', str(startRow)),)
        return params
    
    def loadDataMonthly(self):
        self.data=pd.DataFrame(columns=self.fields)
        for pubdate in self.dateRange:
            self.loadData(pubdate)
        return
    
    def loadData(self,pubdate=None):
        self.data=pd.DataFrame(columns=self.fields)
        while True:
            params=self.setParamsForRequest(startRow=len(self.data),pubdate=pubdate)
            response = requests.get(self.url, headers=self.headers, params=params)
            for row in response.json()['response']['docs']:
                try:
                    row['aff']=list(row['aff'])
                    #row['aff']=Counter(row['aff'])
                    #row['aff']=list(set(row['aff'])) # This returns list of affiliations without counts. Not good if I want
                                                     # to detect scientific groups
                except:
                    row['aff']=['-']
                for key,val in row.items():
                    if type(val)==list:
                        row[key]=tuple(val)
                self.data=self.data.append(row,ignore_index=True)
            if len(response.json()['response']['docs'])!=2000:
                break
        return
    
    def processData(self):
        self.data=DataCleaning.flattenData(self.data)
        self.data=DataCleaning.getYearMonth(self.data)
        self.data=self.data.fillna(-999)
        self.coordTable=DataCleaning.getLocationTable(self.data)