from geotext import GeoText
from collections import Counter
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from numpy import nan
import pandas as pd
import re
from collections import Counter

def affParser(aff):
    aff=aff.replace('&amp',' ')
    segm=aff.split(',')
    country=''
    organization=''
    
    if len(segm)>1:
        country=segm[-1].lstrip()
        if country.endswith(' USA'):
            country='USA'
    
    stopWords=['Department','Departamento','Dipartimento','Faculty','Astronomy','Astrophysics','Physics',
              'University','Institute','Observatory','Laboratory','School','Center','Instituto','Academy',
               'Institut','Institution','Organization','Universitat','Laboratoire','Università',' Inc.',
               'Universtät','Université','Laboratório','Scuola','CNRS','CNES','Observatories','Universidade',
               'Agency','Centre','Facultad','Universitäts','Observatório','Telescope','Universität',
               'ICRANet','ISAS/JAXA','Centro','Institució','Excellence Cluster Universe','Research',
               'Max-Planck','ARI','INFN','INAF','TRIUMF','AAVSO']
    for i,s in reversed(list(enumerate(segm))):
        if any(c in s for c in stopWords):
            organization=','.join(segm[:i+1])
            organization=organization.lstrip()
            address=','.join(segm[i+1:])
            address=address.lstrip()
            return organization, address,country
    return organization,aff,country

def affRowFlatten(affAll):
    affAll=list(affAll)
    affAll=[aff.split(';') for aff in affAll]
    affAll=[aff.lstrip() for sublist in affAll for aff in sublist]
    affAll=[aff for aff in affAll if aff!='']
    affAll=Counter(affAll)
    return affAll

def getGeoloc(row,geolocator,addressCol='address',cityCol='city',countryCol='country'):
    loc=''
    lat=''
    lon=''
    location=None
    if row[cityCol]!=-999:
        try:
            location = geolocator.geocode(str(row[cityCol])+','+str(row[countryCol]))
            if location:
                row['loc']=location.address
                row['lat']=round(location.latitude,4)
                row['lon']=round(location.longitude,4)
        except GeocoderTimedOut as e:
            print("Error: geocode failed on input %s with message %s"%(row[addressCol], e))
    if row[cityCol]==-999 or not location:
        try:
            location = geolocator.geocode(row[addressCol])
            if location:
                row['loc']=location.address
                row['lat']=round(location.latitude,4)
                row['lon']=round(location.longitude,4)
        except GeocoderTimedOut as e:
            print("Error: geocode failed on input %s with message %s"%(row[addressCol], e))
    return row

def getYearMonth(data,pubdateCol='pubdate'):
    data['year']=data[pubdateCol].apply(lambda s: int(s[:4]))
    data['month']=data[pubdateCol].apply(lambda s: int(s[5:7]))
    return data

def flattenData(data,affCol='aff'):
    data[affCol]=data[affCol].apply(affRowFlatten)
    data['bibstem']=data['bibstem'].apply(lambda b: b[0])
    data['title']=data['title'].apply(lambda t: t[0])
    return data

def getCity(row,colAddr='address',colCountry='country'):
    cityList=row[colAddr].replace(', '+row[colCountry],'').split(',')
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
    return city

def dataCities(data,colAddr='address',colCountry='country'):
    data['city']=data.apply(lambda row: getCity(row,colAddr,colCountry),axis=1)
    return data

def getCoords(coords,address='address'):
    geolocator = Nominatim(timeout=1,user_agent="adsAbs")
    print(len(coords[coords['lat']==-999]),' addresses not in commonCoords table')
    coords=coords.apply(lambda row: getGeoloc(row,geolocator) if row['lat']==-999 else row,axis=1)
    coords=coords.fillna(-999)
    return coords
    
def getAffiliationTable(data,affCol='aff'):
    # Put all affiliations from data table to list
    allAffs=data[affCol].tolist()
    allAffs=[loc for t in allAffs for loc in t]
    
    # Create coords table and get coords for all affiliations
    coords=pd.DataFrame(data=allAffs,columns=['aff'])
    coords[['organization','address','country']]=coords['aff'].apply(affParser).apply(pd.Series)
    coords=coords.drop_duplicates('address')
    coords=dataCities(coords)
    try:
        commonCoords=pd.read_csv('commonCoords.csv')
        coords = pd.merge(coords, commonCoords,how='left', on=['address'])
    except:
        print('No commonCoords table found')
        coords['loc']=-999
        coords['lat']=-999
        coords['lon']=-999
    coords=coords.fillna(-999)
    return coords

def updateCommonCoords(coords,commonCoordsFile='commonCoords.csv'):
    try:
        commonCoords=pd.read_csv(commonCoordsFile)
        commonCoords=commonCoords.append(coords.loc[coords['loc']!=-999,['address','loc','lat','lon']],
                                         sort=False,ignore_index=True)
    except:
        print('No commonCoords table found. Creating one')
        commonCoords=coords.loc[coords['loc']!=-999,['address','loc','lat','lon']]
    commonCoords=commonCoords.drop_duplicates(subset='address').reset_index(drop=True)
    commonCoords.to_csv(commonCoordsFile,index=False)
    return commonCoords

def getLocationTable(data,affCol='aff'):
    coords=getAffiliationTable(data)
    coords=getCoords(coords)
    updateCommonCoords(coords)
    return coords