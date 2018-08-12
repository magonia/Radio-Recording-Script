#!/usr/bin/python
# coding: utf-8
import argparse
import os
import sys
import subprocess
import ssl
import urllib
import urllib2
import json
import xml.etree.ElementTree as ET
import base64
import RadioXml as RX
from datetime import datetime as DT
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error

# show id3 tag
def show_id3_tags(file_path):
    tags = EasyID3(file_path)
    print(tags.pprint())

#
# get player
#
def get_player( playerfile, playerurl ):
    if os.path.exists( playerfile ) == False:
        try :
            body = urllib2.urlopen( playerurl ).read()
            f = open( playerfile, "w" )
            f.write(body)
            f.close()
        except URLError, e:
            print e
            sys.exit(1)

#
# get keydata (need swftool)
#
def get_keydata( swfextract, playerfile, keyfile ):
    if os.path.exists( keyfile ) == False:
        cmd = '{} -b 12 {} -o {}'
        cmd = cmd.format( swfextract, playerfile, keyfile )
        subprocess.call( cmd.strip().split(" ") ) 
        if os.path.exists( keyfile ) == False:
            print 'Failed get keydata'
            print 'Following command failed.'
            print cmd
            sys.exit(1)

#
# access auth1_fms
#
def get_auth1_fms( pid ):
    if os.path.exists( 'auth1_fms_{}'.format( pid ) ):
        os.remove('auth1_fms_{}'.format( pid ) )
    auth_response = {}
    url = 'https://radiko.jp/v2/api/auth1_fms'
    headers = {
        'pragma': 'no-cache',
        'X-Radiko-App':'pc_ts',
        'X-Radiko-App-Version':'4.0.0',
        'X-Radiko-User':' test-stream',
        'X-Radiko-Device':'pc'
    }
    values = { '\r\n': '' }
    data = urllib.urlencode(values)
    try :
        req = urllib2.Request( url, data, headers )
        res = urllib2.urlopen(req)
        auth_response['body'] = res.read()
        auth_response['headers'] =  res.info().dict
    except :
        print 'Failed auth1 process'
        sys.exit(1)
    return( auth_response )

def get_auth2_fms( auth_response, keyfile ):
    #
    # get partial key
    #
    authtoken = auth_response['headers']['x-radiko-authtoken']
    offset    = auth_response['headers']['x-radiko-keyoffset']
    length    = auth_response["headers"]["x-radiko-keylength"]

    offset = int(offset)
    length = int(length)

    f = open(keyfile, 'rb+')
    f.seek(offset)
    data = f.read(length)
    partialkey =  base64.b64encode(data)
    #
    # access auth2_fms
    #
    auth_success_response ={}
    url = "https://radiko.jp/v2/api/auth2_fms"
    headers ={
        "pragma":"no-cache",
        "X-Radiko-App":"pc_ts",
        "X-Radiko-App-Version":"4.0.0",
        "X-Radiko-User":"test-stream",
        "X-Radiko-Device":"pc",
        "X-Radiko-Authtoken":authtoken,
        "X-Radiko-Partialkey":partialkey ,  }
    try :
        req = urllib2.Request(url, '\r\n' ,headers )
        res = urllib2.urlopen(req)
        auth_success_response['body'] = res.read()
        auth_success_response['headers'] =  res.info().dict
    except URLError, e:
        print e
        sys.exit(1)

    value = []
    value.append( authtoken )
    value.append( auth_success_response['body'].strip().split(',') )
    return( value )

#
# get stream-url
#
def get_streamurl( channel ):
    url = 'http://radiko.jp/v2/station/stream/{}.xml'
    url = url.format( channel )
    resp = urllib2.urlopen( url ).read()
    root = ET.fromstring( resp )

    stream_url = root[1].text
    url_parts = []
    url_parts.append( stream_url.split( '://' )[0] + '://' + 
                stream_url.split( '://' )[1].split( '/' )[0] )
    url_parts.append( stream_url.split( '://' )[1].split( '/' )[1] + '/' + 
                stream_url.split( '://' )[1].split( '/' )[2] )
    url_parts.append( stream_url.split( '://' )[1].split( '/' )[3] )
    return url_parts

def live_rec( url_parts, playerurl, auth_token, prefix, duration, date, outdir ):
    rtmpdump='/usr/bin/rtmpdump'
    ffmpeg='/usr/bin/ffmpeg'
    # Recording...
    cmd = '{} -q'.format( rtmpdump )
    cmd = cmd + ' -r {}'.format( url_parts[0] )
    cmd = cmd + ' --app {}'.format( url_parts[1] )
    cmd = cmd + ' --playpath {}'.format( url_parts[2] )
    cmd = cmd + ' -W {} -C S:"" -C S:"" -C S:""'.format( playerurl )
    cmd = cmd + ' -C S:{}'.format( auth_token )
    cmd = cmd + ' --live --stop {}'.format( duration )
    path = '{}/{}_{}'
    cmd = cmd + ' --flv ' + path.format( '/tmp', prefix, date )
    # Exec rtpmdump
    subprocess.call( cmd.strip().split(" ")  )

    cmd = '{} -loglevel quiet -y'.format( ffmpeg )
    cmd = cmd + ' -i {}'.format( path.format( '/tmp', prefix, date ) )
    path = '{}/{}_{}.mp3'.format( outdir, prefix, date )
    cmd = cmd + ' -acodec libmp3lame -ab 128k -vn {}'.format( path )
    # Exec ffmpeg
    subprocess.call( cmd.strip().split(" ")  ) 
    # clean up
    path = '{}/{}_{}'
    os.remove( path.format( '/tmp', prefix, date ) )

def tf_rec( auth_token, channel, ft, to, outdir, prefix, date ):
    ffmpeg = '/usr/bin/ffmpeg'
    headers = ' -headers "X-Radiko-AuthToken: {}"'.format( auth_token )
    url = ' -i "https://radiko.jp/v2/api/ts/playlist.m3u8?station_id={}&ft={}&to={}"'.format( channel, ft, to )
    path = '{}/{}_{}.mp3'.format( outdir, prefix, date )

    cmd = '{} -loglevel quiet -y'.format( ffmpeg )
    cmd = cmd + headers + url
    cmd = cmd + ' -acodec libmp3lame -ab 128k -vn {}'.format( path )
    # Exec ffmpeg
    subprocess.call( cmd.strip().split(" ")  ) 

if __name__ == '__main__':
    parser=argparse.ArgumentParser( description='Recording Radiko.' )
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
    parser.add_argument('-tf', '--timefree', \
                metavar='timefree id', \
                nargs=1, \
                default=None, \
                help='Time Free Progam ID' )
    args = parser.parse_args()
    channel=args.channel
    duration=args.duration * 60
    outdir=args.outputdir

    if args.prefix is None:
        prefix=args.channel
    else:
        prefix=args.prefix

    # variables
    pid  = os.getpid()
    # setting date
    date = DT.now()
    date = date.strftime('%Y-%m-%d-%H_%M')
    #playerurl='http://radiko.jp/player/swf/player_3.0.0.01.swf'
    #playerurl='http://radiko.jp/player/swf/player_4.1.0.00.swf'
    playerurl='http://radiko.jp/apps/js/flash/myplayer-release.swf'
    playerfile="/tmp/player.{}.swf".format( date )
    keyfile="/tmp/authkey.{}.png".format( date )
    swfextract='/usr/bin/swfextract'

    # get player file
    get_player( playerfile, playerurl )

    # get key data
    get_keydata( swfextract, playerfile, keyfile )

    # get auth1_fms
    auth_response = get_auth1_fms( pid )

    # get auth2_fms
    ret = get_auth2_fms( auth_response, keyfile )
    auth_token = ret[0]
    areaid = ret[1][0]

    # Construct RadikoXml
    program = RX.RadikoXml( areaid )
    # Check whether channel is available
    if program.is_avail( channel ) == False:
        print 'Specified station {} is not found.'.format( channel )
        exit(1)

    # get program meta via radiko api
    url_parts = get_streamurl( channel )

    if args.timefree is None:
        index = 1
        live_rec( url_parts, playerurl, auth_token, prefix, \
                duration, date, outdir )
    else:
        index = 0
        tf_rec( auth_token, channel, ft, to, outdir, prefix, date )

    # clean up
    os.remove( keyfile )

    #
    # set program meta by mutagen
    #
    program.get_now( channel )
    path = '{}/{}_{}.mp3'.format( outdir, prefix, date )
    tags = EasyID3(path)
    tags['album'] = channel
    if program.title[index].text is not None:
        tags['title'] = program.title[index].text
    if program.pfm[index].text is not None:
        tags['artist'] = program.pfm[index].text

    tags.save()

    if program.img[index].text is not None:
        logo_url = program.img[index].text
        coverart = urllib2.urlopen(logo_url).read()
        audio = MP3(path)
        audio.tags.add(
            APIC( encoding=3, # 3 is for utf-8 
                mime='image/jpeg', # image/jpeg or image/png 
                type=3, # 3 is for the cover image 
                desc=u'Cover', 
                data=coverart))
        audio.save()

    #show_id3_tags(path)
