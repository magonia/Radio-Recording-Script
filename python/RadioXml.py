#!/usr/bin/python
# coding: utf-8
from datetime import datetime as DT
import urllib2
import xml.etree.ElementTree as ET

class RadikoXml:
    def __init__(self, location):
        self.d = DT.today()
        self.title = self.url = self.desc = self.info = self.pfm = []
        self.img = []
        if location is not None:
            self.location = location
        url = 'http://radiko.jp/v3/program/now/{}.xml'
        url = url.format( self.location )
        resp = urllib2.urlopen( url ).read()
        self.root = ET.fromstring( resp )

    def is_avail( self, station ):
        xpath_tmp = './/station[@id="{}"]//*'
        xpath = xpath_tmp.format( station )
        if self.root.findall( xpath ) == []:
            return False
        else:
            return True

    def show_channel( self ):
        list1 = self.root.findall( './/station[@id]' )
        list2 = self.root.findall( './/station/name' )
        dic = {}
        for i, data in enumerate( list1 ):
            dic.update( { data.attrib['id']:list2[i].text } )
        return dic

    def get_now( self, station ):
        url = 'http://radiko.jp/v3/program/now/{}.xml'
        url = url.format( self.location )
        resp = urllib2.urlopen( url ).read()
        root = ET.fromstring( resp )

        xpath_tmp = './/station[@id="{}"]//*/{}'
        xpath = xpath_tmp.format( station , 'title' )
        self.title = self.root.findall( xpath )
        xpath = xpath_tmp.format( station , 'url' )
        self.url = self.root.findall( xpath )
        xpath = xpath_tmp.format( station , 'desc' )
        self.desc = self.root.findall( xpath )
        xpath = xpath_tmp.format( station , 'info' )
        self.info = self.root.findall( xpath )
        xpath = xpath_tmp.format( station , 'pfm' )
        self.pfm = self.root.findall( xpath )
        xpath = xpath_tmp.format( station , 'img' )
        self.img = self.root.findall( xpath )

    def dump( self ):
        print self.d
        for m in self.title:
            print m
        for m in self.url:
            print m
        for m in self.desc: 
            print m
        for m in self.info:
            print m
        for m in self.pfm:
            print m
        for m in self.img:
            print m

if __name__ == '__main__':
    main = RadikoXml( 'JP13' )
    main.get_now('TBS')
    dic = main.show_channel()
    print '--------------------'
    for i, data in enumerate( dic.keys() ):
        print data + ':\t' + dic.values()[i]
    print '--------------------'
    #main.dump()
