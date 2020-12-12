import sqlite3
from sqlite3 import Error
import pandas as pd
from typing import Dict, Tuple,List
import affiliationCleaning

class requestDB:
    
    ########### requests for creating tables #############

    sql_create_articles_table = """ CREATE TABLE IF NOT EXISTS articles (
                                            article_id integer PRIMARY KEY,
                                            title text NOT NULL,
                                            pubdate text,
                                            year integer,
                                            month integer,
                                            citation_count integer,
                                            author_count integer,
                                            page_count integer,
                                            bibstem text,
                                            UNIQUE (title)
                                        ); """

    sql_create_keywords_table = """CREATE TABLE IF NOT EXISTS keywords (
                                        keyword_id integer PRIMARY KEY,
                                        keyword text NOT NULL,
                                        UNIQUE (keyword)
                                    );"""

    sql_create_authors_table = """CREATE TABLE IF NOT EXISTS authors (
                                        author_id integer PRIMARY KEY,
                                        name text NOT NULL,
                                        UNIQUE (name)
                                    );"""

    sql_create_affiliations_table = """CREATE TABLE IF NOT EXISTS affiliations (
                                        aff_id integer PRIMARY KEY,
                                        aff text NOT NULL,
                                        address text,
                                        city text,
                                        country text,
                                        lat real,
                                        lon real,
                                        UNIQUE (aff)
                                    );"""

    ########## requests for creating relation tables ###############

    articles_keywords_table = """ CREATE TABLE IF NOT EXISTS j_articles_keywords (
                                    j_art_keyw_id integer PRIMARY KEY,
                                    article_id integer NOT NULL,
                                    keyword_id integer,
                                    FOREIGN KEY (article_id)
                                       REFERENCES articles (article_id),
                                    FOREIGN KEY (keyword_id)
                                       REFERENCES keywords (keyword_id)
                                ); """
    articles_authors_table = """ CREATE TABLE IF NOT EXISTS j_articles_authors (
                                    j_art_author_id integer PRIMARY KEY,
                                    article_id integer NOT NULL,
                                    author_id integer,
                                    FOREIGN KEY (article_id)
                                       REFERENCES articles (article_id),
                                    FOREIGN KEY (author_id)
                                       REFERENCES authors (author_id)
                                ); """

    articles_affs_table = """ CREATE TABLE IF NOT EXISTS j_articles_affs (
                                    j_art_aff_id integer PRIMARY KEY,
                                    article_id integer NOT NULL,
                                    aff_id integer,
                                    count integer,
                                    FOREIGN KEY (article_id)
                                       REFERENCES articles (article_id),
                                    FOREIGN KEY (aff_id)
                                       REFERENCES affiliations (aff_id)
                                ); """
    
    def __init__(self,dbFile: str='testDb.db'):
        self.dbFile=dbFile
        self.make_db()

    def create_db(self):
        """ create a database connection to a SQLite database """
        conn = None
        try:
            conn = sqlite3.connect(self.dbFile)
        except Error as e:
            print(e)
        finally:
            if conn:
                conn.close()
        return

    def create_connection(self):
        """ create a database connection to a SQLite database """
        conn = None
        try:
            conn = sqlite3.connect(self.dbFile)
            return conn
        except Error as e:
            print(e)
        return            

    def create_table(self,conn, create_table_sql: str):
        """ create a table from the create_table_sql statement
        :param conn: Connection object
        :param create_table_sql: a CREATE TABLE statement
        :return:
        """
        try:
            c = conn.cursor()
            c.execute(create_table_sql)
            c.close()
        except Error as e:
            print(e)
        return
    
    def make_db(self):
        self.create_db()

        # create a database connection
        conn=None
        conn=self.create_connection()

        if conn is not None:
            # create tables
            self.create_table(conn, self.sql_create_articles_table)
            self.create_table(conn, self.sql_create_keywords_table)
            self.create_table(conn, self.sql_create_authors_table)
            self.create_table(conn, self.sql_create_affiliations_table)
            
            # create relation tables
            self.create_table(conn, self.articles_keywords_table)
            self.create_table(conn, self.articles_authors_table)
            self.create_table(conn, self.articles_affs_table)
        else:
            print("Error! cannot create the database connection.")

        if conn:
            conn.close()
        return
    
    def getYearMonth(self,row:Dict,pubdateCol:str='pubdate')->Dict:
        row['year']=row[pubdateCol].apply(lambda s: int(s[:4]))
        row['month']=row[pubdateCol].apply(lambda s: int(s[5:7]))
        return row
    
    def addRecords(self,row:Dict):
        # create a database connection
        conn=None
        conn=self.create_connection()
        c = conn.cursor()
        
        fields=['title','pubdate','year','month','citation_count','author_count','page_count','bibstem']
        row=self.getYearMonth(row)
        articleInfo=(row[f] for f in fields)
        id_article=self.addRowToTable(c,'articles',tuple(fields),articleInfo)
        for k in row['keyword']:
            id_keyword=self.addRowToTable(c,'keywords',tuple('keyword'),k)
            self.addRowToTable(c,'j_articles_keywords',('article_id','keyword_id'),(id_article,id_keyword))
        for a in row['author']:
            id_author=self.addRowToTable(c,'authors',tuple('author'),a)
            self.addRowToTable(c,'j_articles_authors',('article_id','author_id'),(id_article,id_author))
            
        affs=affiliationCleaning.cleanAffs(row['aff'])
        affFields=('aff','address','city','country','lat','lon')
        affs['id_aff']=affs.apply(lambda aff: self.addRowToTable(c,'affiliations',affFields,tuple(aff)),axis=1)
        affs.apply(lambda aff: self.addRowToTable(c,'j_articles_affs',
                                             ('article_id','aff_id','count'),
                                             (id_article,aff['id_aff'],aff['count']),axis=1))
        if c:
            c.close()
        if conn:
            conn.close()
        return
    
    def addRowToTable(self,c,tab:str,fields:Tuple,info:Tuple)->int:
        fieldsStr=' ('+','.join(str(f) for f in fields)+') '
        infoStr=' ('+','.join('"'+str(i)+'"' for i in info)+') '
        addRow="""INSERT or IGNORE INTO """+ tab+fieldsStr+""" VALUES """+infoStr+""";"""
        print(addRow)
        c.execute(addRow)
        id_name=self.getTabCols(tab)[0][1]
        c.execute("""SELECT """+id_name+""" FROM """ +tab +""" WHERE """+fields[0]+"""=?""",(info[0],))
        
        return c.fetchall()[0][0]
    
        
    def getTabList(self)->List:
        conn = None
        try:
            conn = self.create_connection()
            c=conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tabs=c.fetchall()
            tabs=[t[0] for t in tabs]
            c.close()
        except Error as e:
            print(e)
        finally:
            if conn:
                conn.close()
        return tabs
    
    def getTabCols(self,tabName:str)->List:
        conn = None
        try:
            conn = self.create_connection()
            c=conn.cursor()
            c.execute("""PRAGMA table_info("""+tabName+""")""")
            cols=c.fetchall()
            c.close()
        except Error as e:
            print(e)
        finally:
            if conn:
                conn.close()
        return cols
    
    def getTab(self,tabName:str)->List:
        conn = None
        conn = self.create_connection()
        try:
            c=conn.cursor()
            c.execute('SELECT * from '+tabName)
            tab=c.fetchall()
        except Error as e:
            print(e)
        finally:
            if c:
                c.close()
            if conn:
                conn.close()
        return tab
    