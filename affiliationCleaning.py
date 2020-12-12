from geotext import GeoText
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from numpy import nan
import re
import pandas as pd
from os.path import isfile
from typing import Dict, Tuple,List

affFields=('aff','address','city','country','lat','lon','count')
geolocator = Nominatim(timeout=1,user_agent="adsAbs")

def cleanAffs(rowAff:str)->Dict:
    affsDF = pd.DataFrame(columns=affFields)
    affsDF['lat']=-999
    affsDF['lon']=-999
    affsDF['aff']=flattenAffs(rowAff)
    counts=pd.DataFrame(affsDF['aff'].value_counts())
    counts=counts.reset_index(level=0)
    counts.columns=['aff','count']
    affsDF=affsDF.drop_duplicates(subset='aff').set_index('aff').join(counts.set_index('aff'))
    affsDF['aff']=affsDF.index
    affsDF=affsDF.reset_index(drop=True)
    
    affsDF['country']=affsDF['aff'].apply(getCountry,axis=1)
    affsDF['address']=affsDF['aff'].apply(getAddress,axis=1)
    affsDF['city']=affsDF.apply(lambda row: getCity(row['address'], row['country']),axis=1)
    affsDF=joinWithCommonCoords(affsDF)
    affsDF['lat','lon']=affsDF.apply(lambda row: getCoords(geolocator,row['address'],
                                     row['city'],row['country']) if row['lat']==-999 or row['lon']==-999 
                                     else (-999,-999),
                                     axis=1,result_type='expand')
    updateCommonCoords(affsDF)
    return affsDF
    
    
def flattenAffs(rowAff:Tuple)->List:
    # unravel situations where one person has two affiliations separated by ';'
    affs=[item for sub in [aff.split(';') for aff in rowAff] for item in sub]
    affs=[aff.replace('&amp',' ') for aff in affs]
    affs=[aff.lstrip() for aff in affs]
    affs=[aff for aff in affs if aff!='']
    return affs

def getCountry(aff:str)->str:
    segm=aff.split(',')
    
    if len(segm)>1:
        country=segm[-1].lstrip()
        if country.endswith(' USA'):
            country='USA'
    return country
    
def getAddress(aff:str)->str:
    segm=aff.split(',')
    
    stopWords=['Department','Departamento','Dipartimento','Faculty','Astronomy','Astrophysics','Physics',
              'University','Institute','Observatory','Laboratory','School','Center','Instituto','Academy',
               'Institut','Institution','Organization','Universitat','Laboratoire','Università',' Inc.',
               'Universtät','Université','Laboratório','Scuola','CNRS','CNES','Observatories','Universidade',
               'Agency','Centre','Facultad','Universitäts','Observatório','Telescope','Universität',
               'ICRANet','ISAS/JAXA','Centro','Institució','Excellence Cluster Universe','Research',
               'Max-Planck','ARI','INFN','INAF','TRIUMF','AAVSO']
    
    for i,s in reversed(list(enumerate(segm))):
        if any(c in s for c in stopWords):
            address=','.join(segm[i+1:])
            address=address.lstrip()
            return address
    return '-999'
    
def getCity(address:str,country:str)->str:
    cityList=address.replace(', '+country,'').split(',')
    cityList=[city.replace('&amp','') for city in cityList]
    cityList=[city for city in cityList if not city.replace(' ','').isdigit()]
    reg=re.compile('^[\s]*[A-Z][A-Z][\s]*[\d-]*[\s]*$')
    cityList=[city for city in cityList if not bool(reg.match(city))]
    reg=re.compile('^[\s]*[A-Z]{0,3}[\s]*[\d-]*[\s]')
    cityList=[re.sub(reg,'',city) for city in cityList]
    reg=re.compile('[\s]*[A-Z]{0,3}[\s]*[\d-]*[\s]*$')
    cityList=[re.sub(reg,'',city) for city in cityList]
    reg=re.compile('[\s][A-Z]{0,3}[\d][\d]*[A-Z]{0,3}[\s]*$')
    cityList=[re.sub(reg,'',city) for city in cityList]
    cityList=[city.replace(' cedex','').replace(' Cedex','') for city in cityList]
    cityList=[city for city in cityList if not city.lstrip()=='']
    cityList=[city for city in cityList if not city.replace(' ','').isdigit()]
    try:
        city=cityList[-1]
    except:
        city=-999
    if city=='':
        city=-999
    return str(city)
    
def updateCommonCoords(affDF:pd.DataFrame,commonCoordsFile:str='commonCoords.csv')->pd.DataFrame:
    coords=affDF['city','country','lat','lon']
    coords=coords.loc[coords['loc']!=-999]
    if isfile(commonCoordsFile):
        commonCoords=pd.read_csv(commonCoordsFile)
    else:
        print('No '+commonCoordsFile+' has been found. Creating a new one')
        commonCoords=pd.DataFrame(columns=['city','country','lat','lon'])
    
    commonCoords=commonCoords.append(coords,ignore_index=True)
    commonCoords=commonCoords.drop_duplicates().reset_index(drop=True)
    commonCoords.to_csv(commonCoordsFile,index=False)
    return commonCoords
    
    
def joinWithCommonCoords(affDF:pd.DataFrame,commonCoords:str='commonCoords.csv')->pd.DataFrame:
    try:
        commonCoords=pd.read_csv(commonCoords)        
    except:
        print('No commonCoords table found')
        return affDF
    commonCoords['city, country']=commonCoords.apply(lambda row: row['city']+' '+row['country'],axis=1)
    affDF['city, country']=affDF.apply(lambda row: row['city']+' '+row['country'],axis=1)
    affDF = pd.merge(affDF, commonCoords,how='left', on=['city, country'])
    affDF=affDF.drop('city, country',axis=1)
    return affDF
    
    
def getCoords(geolocator,address:str,
              city:str,country:str)->Tuple:
    lat=-999
    lon=-999
    location=None
    if city!=-999:
        try:
            location = geolocator.geocode(city+','+country)
            if location:
                lat=round(location.latitude,4)
                lon=round(location.longitude,4)
        except GeocoderTimedOut as e:
            print("Error: geocode failed on input %s with message %s"%(city,country, e))
    if city==-999 or not location:
        try:
            location = geolocator.geocode(address)
            if location:
                lat=round(location.latitude,4)
                lon=round(location.longitude,4)
        except GeocoderTimedOut as e:
            print("Error: geocode failed on input %s with message %s"%(address, e))
    return (lat,lon)