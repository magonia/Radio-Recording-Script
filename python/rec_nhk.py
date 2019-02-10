#!/usr/bin/python
# coding: utf-8
import argparse
import sys
import subprocess
import urllib2
import json
import xml.etree.ElementTree as ET
from retry import retry
from datetime import datetime as DT
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error

@retry(tries=4, delay=2, backoff=2)
def urlopen_w_retry( url ):
    headers = {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:47.0) Gecko/20100101 Firefox/47.0",}
    request = urllib2.Request(url, headers=headers)
    resp = urllib2.urlopen( request ).read()
    return( resp )

# show id3 tag
def show_id3_tags(file_path):
    tags = EasyID3(file_path)
    print(tags.pprint())

if __name__ == '__main__':
    parser=argparse.ArgumentParser( description='Recording NHK radio.' )
    parser.add_argument('channel', \
                metavar='channel', \
                help=' Channel Name' )
    parser.add_argument('duration', \
                metavar='duration', \
                type=int, \
                help='Duration(minutes)' )
    parser.add_argument('outputdir', \
                metavar='outputdir', \
                nargs='?', \
                default='.' , \
                help='Output path default:\'.\'' )
    parser.add_argument('prefix', \
                metavar='Prefix name',\
                nargs='?', \
                help='Prefix name for output file.' )
    parser.add_argument('--timing', \
                nargs='?', \
                choices=['previous', 'following', 'present'], \
                default='present')
    args = parser.parse_args()
    channel=args.channel
    duration=args.duration * 60
    outdir=args.outputdir
    timing=args.timing

    if args.prefix is None:
        prefix=args.channel
    else:
        prefix=args.prefix

    # tools
    ffmpeg_cmd = '/usr/bin/ffmpeg ' + \
            '-loglevel quiet -y ' + \
            '-re -y -err_detect aggressive ' + \
            '-i {} -t {} -acodec libmp3lame -ab 128k ' + \
            '{}/{}_{}.mp3'
    path = '{}/{}_{}.mp3'
    # where are you?
    here = 'tokyo'
    area_code = '130'
    # variables for xml parsing
    url = 'https://www.nhk.or.jp/radio/config/config_web.xml'
    nhk_xpath_base = './/stream_url/data/*'
    nhk_xpath = {
        'NHK1':	'.//stream_url/data/r1hls',
        'NHK2': './/stream_url/data/r2hls',
        'FM': './/stream_url/data/fmhls'
    }
    # variables for NHK-API
    api_key = 'Your Api Key'
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

    # setting date
    date = DT.now()
    date = date.strftime('%Y-%m-%d-%H_%M')

    # retrieve download url form xml
    root = ET.fromstring( urlopen_w_retry( url ) )
    xpath = nhk_xpath.get( channel , None )
    if xpath is None:
        print( "channel doesn't exist" )
        sys.exit(1)
    else:
        code = nhk_code.get( channel , None )

    for child in root.findall( nhk_xpath_base ):
        if child.tag == 'area' and child.text == here:
            dl_url = root.findtext( xpath )

    # NowOnAir API
    now_url = now_base.format( area_code, code, api_key )

    # get program id
    now_program = json.loads(
    urlopen_w_retry(now_url))['nowonair_list'][code][timing]
    program_id = now_program['id']

    # Recording...
    cmd = ffmpeg_cmd.format( dl_url, duration, outdir, prefix, date )
    path = path.format( outdir, prefix, date )
    proc = subprocess.call( cmd .strip().split(" ") )

    # ProgramInfo API
    info_url = info_base.format( area_code, code , program_id, api_key)

    # get program information
    program = json.loads(urlopen_w_retry(info_url))['list'][code]
    tags = EasyID3(path)
    tags['album'] = nhk_album.get( channel , None )
    if program[0]['title']:
        tags['title'] = program[0]['title']
    if program[0]['subtitle']:
        tags['artist'] = program[0]['subtitle']
    if program[0]['act']:
        tags['artist'] = program[0]['act']

    tags.save()

    logo = program[0]['program_logo']
    if logo is None:
        logo = program[0]['service']['logo_l']
    elif logo is None:
        logo = program[0]['service']['logo_m']
    elif logo is None:
        logo = program[0]['service']['logo_s']

    if logo is not None:
        logo_url = 'https:' + logo['url']
        coverart = urlopen_w_retry(logo_url)
        audio = MP3(path)
        audio.tags.add(
             APIC( encoding=3,      # 3 is for utf-8 
                 mime='image/png',  # image/jpeg or image/png 
                    type=3,         # 3 is for the cover image 
                    desc=u'Cover', 
                    data=coverart))
        audio.save()

    #show_id3_tags(path)

