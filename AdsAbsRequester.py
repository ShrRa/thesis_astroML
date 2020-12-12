import requests
import pandas as pd
import funcs_DB
from typing import Dict, Tuple,List

class Requester:
    
    url='https://api.adsabs.harvard.edu/v1/search/query'
    fields=['title','author','aff','keyword','citation_count','pubdate','author_count','page_count','bibstem']
    
    def __init__(self, token: str,requestName: str):
        self.token = token
        self.headers = {'Authorization': 'Bearer '+token}
        self.db=requestName
        
    def setParams(self,searchCriteria: Tuple,maxRows: int=None):
        self.searchCriteria=searchCriteria
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
    
    def setParamsForRequest(self,startRow: int):
        params = self.params+(('start', str(startRow)),)
        return params
    
    def loadData(self):
        db=funcs_DB.requestDB(self.db)
        startRow=0
        while True:
            params=self.setParamsForRequest(startRow)
            self.response = requests.get(self.url, headers=self.headers, params=params)
            map(db.addRecords,self.response.json()['response']['docs'])
            startRow+=len(self.response.json()['response']['docs'])

            if len(self.response.json()['response']['docs'])!=2000:
                break
        return