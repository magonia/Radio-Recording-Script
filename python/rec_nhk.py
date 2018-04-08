#!/usr/bin/python
# coding: utf-8
import sys
import subprocess
import urllib2
import json
import xml.etree.ElementTree as ET
from datetime import datetime as DT
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error

# show id3 tag
def show_id3_tags(file_path):
    tags = EasyID3(file_path)
    print(tags.pprint())

if __name__ == '__main__':
    # tools
    ffmpeg_cmd = '/usr/bin/ffmpeg -loglevel quiet -y -i {} -t {} -acodec libmp3lame -ab 128k {}/{}_{}.mp3'
    path = '{}/{}_{}.mp3'
    #path = 'ME_2018-02-17-L38-1.mp3'
    # where are you?
    here = 'tokyo'
    area_code = '130'
    outdir = '.'
    prefix = ''
    # variables for xml parsing
    url = 'http://www.nhk.or.jp/radio/config/config_web.xml'
    nhk_xpath_base = './/stream_url/data/*'
    nhk_xpath = {
        'NHK1':	'.//stream_url/data/r1hls',
        'NHK2': './/stream_url/data/r2hls',
        'FM': './/stream_url/data/fmhls'
    }
    # variables for NHK-API
    api_key = 'KxJ5GY9jzIvokpPuJdaWN4B3F2wM9F5O'
    now_base = 'http://api.nhk.or.jp/v2/pg/now/{}/{}.json?key={}'
    info_base = 'http://api.nhk.or.jp/v2/pg/info/{}/{}/{}.json?key={}'
    nhk_code = {
        'NHK1':	'r1',
        'NHK2': 'r2',
        'FM': 'r3'
    }
    nhk_album = {
        'NHK1':	u'NHKラジオ第一',
        'NHK2': u'NHKラジオ第二',
        'FM': u'NHK-FM'
    }
    timing = 'present'

    # Parameter chech
    args = sys.argv
    if len(args) == 1:
        print( 
        'usage : ' + args[0] + 
        ' channel_name duration(minuites) [outputdir] [prefix]' )
        sys.exit(1)

    if len(args) >= 2:
        channel=args[1]
        prefix=channel
        xpath = nhk_xpath.get( channel , None )
        if xpath is None:
            print( "channel doesn't exist" )
            sys.exit(1)
        else:
	    code = nhk_code.get( channel , None )

    if len(args) >= 3 and args[2].isdigit():
        duration=int( args[2] ) * 60
    else:
        print 'duration must be digit.'
        sys.exit(1)

    if len(args) >= 4:
        outdir=args[3]

    if len(args) >= 5:
        timing = 'present'

    # Parameter chech
    args = sys.argv
    if len(args) == 1:
        print( 
        'usage : ' + args[0] + 
        ' channel_name duration(minuites) [outputdir] [prefix]' )
        sys.exit(1)

    if len(args) >= 2:
        channel=args[1]
        prefix=channel
        xpath = nhk_xpath.get( channel , None )
        if xpath is None:
            print( "channel doesn't exist" )
            sys.exit(1)
        else:
	    code = nhk_code.get( channel , None )

    if len(args) >= 3 and args[2].isdigit():
        duration=int( args[2] ) * 60
    else:
        print "duration must be digit."
        sys.exit(1)

    if len(args) >= 4:
        outdir=args[3]

    if len(args) >= 5:
        prefix=args[4]

    # setting date
    date = DT.now()
    date = date.strftime('%Y-%m-%d-%H_%M')

    resp = urllib2.urlopen( url ).read()
    root = ET.fromstring( resp )

    for child in root.findall( nhk_xpath_base ):
        if child.tag == 'area' and child.text == here:
            dl_url = root.findtext( xpath )

    # NowOnAir API
    now_url = now_base.format( area_code, code, api_key )

    # get program id
    now_program = json.loads(
    urllib2.urlopen(now_url).read())['nowonair_list'][code][timing]
    program_id = now_program['id']

    # ProgramInfo API
    info_url = info_base.format( area_code, code , program_id, api_key)

    # get program information
    program = json.loads(urllib2.urlopen(info_url).read())['list'][code]

    # Recording...
    cmd = ffmpeg_cmd.format( dl_url, duration, outdir, prefix, date )
    path = path.format( outdir, prefix, date )
    proc = subprocess.call( cmd .strip().split(" ") )

    tags = EasyID3(path)
    tags['album'] = nhk_album.get( channel , None )
    if program[0]['title']:
        tags['title'] = program[0]['title']
    if program[0]['subtitle']:
        tags['artist'] = program[0]['subtitle']
    if program[0]['act']:
        tags['artist'] = program[0]['act']

    tags.save()

    logo_url = 'http:' + program[0]['service']['logo_l']['url']
    coverart = urllib2.urlopen(logo_url).read()
    audio = MP3(path)
    audio.tags.add(
            APIC( encoding=3, # 3 is for utf-8 
                mime='image/png', # image/jpeg or image/png 
                type=3, # 3 is for the cover image 
                desc=u'Cover', 
                data=coverart))
    audio.save()
    #show_id3_tags(path)

