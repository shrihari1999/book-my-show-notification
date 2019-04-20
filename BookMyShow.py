#!/usr/bin/env python3

import requests
import pdb
import sys

from bs4 import BeautifulSoup
from sys import exit
from time import time
from time import sleep
from re import sub as reSub
from datetime import datetime
from json import loads
from sys import stdout
from os import system
from os import remove
from random import randint
from random import randrange
from argparse import ArgumentParser
from argparse import Action
from os.path import expanduser
from os.path import exists
from threading import Thread

def getObject():
    return type( '', (), {} ) # returns a simple object that can be used to add attributes

class NotificationThread( Thread ):
    def __init__( self, title, message, args ):
        Thread.__init__( self )
        self.title = title
        self.message = message
        self.args = args
        self.interval = 10 # will show desktop notification at this intervals ( seconds )

    def run( self ):
        if self.args.pushBullet:
            token = self.args.pushBullet[ 0 ]
            if len( self.args.pushBullet ) > 1:
                deviceList = self.args.pushBullet[ 1: ]
            else:
                # send to all devices
                deviceList = [ None ]
            configFilePath = expanduser( '~' ) + '/.ntfy.yml'
            for device in deviceList:
                with open( configFilePath, 'w+' ) as ntfyFile:
                    # set up config to push to given device
                    ntfyFile.write( 'backends: ["pushbullet"]\n' )
                    ntfyFile.write( 'pushbullet: {"access_token": "' + token + '"' )
                    if device is not None:
                        ntfyFile.write( ', "device_iden": "' + device + '"' )
                    ntfyFile.write( '}' )
                cmd = 'ntfy -t "{0}" send "{1}"'.format( self.title, self.message)
                system( cmd )
            if exists( configFilePath ):
                # we don't need this config anymore
                remove( configFilePath )
        while True:
            # Keep on sending desktop notifications till the program is closed
            start = time()
            cmd = 'ntfy -t "{0}" send "{1}"'.format( self.title, self.message)
            system( cmd )
            stop = time()
            timeRemaining = self.interval - ( stop - start )
            timeRemaining = int( round( timeRemaining if timeRemaining > 0 else 0 ) )
            sleep( timeRemaining )
        
class BookMyShow( object ):

    def __init__( self, args ):
        self.args = args
        self.regionCode = self.args.regionCode.upper()
        self.date = self.args.date
        self.cinema = self.args.cinema
        self.movie = self.args.movie
        self.ss = requests.session()
        self.title = ''
        self.setRegionDetails( self.regionCode )

    def notification( self, title, message ):
        nThread = NotificationThread( title, message, self.args )
        nThread.start()
        # the thread will run till eternity or unless terminated using Ctrl-C

    def ringSineBell( self ):
        totalDuration = 0.0
        while totalDuration < 10.0:
            duration = 1.0 / randint(5,10)  # seconds
            freq = randrange( 200, 2000, 200 )  # Hz
            system('play --no-show-progress --null --channels 1 synth {} sine {}'.format(duration, freq))
            totalDuration += duration

    def ringBell( self ):
        totalDuration = 0.0
        while totalDuration < 10.0:
            duration = 1.0 / randint(5,10)  # seconds
            print( '\a', end="\r" )
            sleep( duration )
            totalDuration += duration

    def setRegionDetails( self, regionCode ):
        '''
        returns region codes required to form url
        '''
        curDate = datetime.now().strftime("%Y%m%d%H")
        regionData = self.ss.get( "https://in.bookmyshow.com/serv/getData/?cmd=GETREGIONS&t=" + curDate )
        assert regionData.status_code == 200
        regionData = regionData.text
        # extract data in json format from above javascript variables
        regionData = loads( regionData[ ( regionData.find( "=" ) + 1 ) : regionData.find( ";" ) ] )
        # TODO: one does not need to remember the city code, the city name should be good enough
        self.regionData = regionData.get( regionCode )[ 0 ]
        assert self.regionData

    def getSearchUrl( self, searchTerm ):
        curTime = int( round( time() * 1000 ) )
        url = "https://in.bookmyshow.com/quickbook-search.bms?d[mrs]=&d[mrb]=&cat=&_=" + str( curTime ) + "&q=" + searchTerm.replace( " ", "+" ) + "&sz=8&st=ON&em=&lt=&lg=&r=" + self.regionData.get( "code" ) + "&sr="
        return url

    def getMovieUrl( self, movieData ):
        '''
        `movieData` is similar to below:

        {'ST': 'NS', 'GRP': 'Event', 'IS_NEW': False, 'L_URL': '', 'DESC': ['Chris Evans', ' Robert Downey Jr.'], 'CODE': 'EG00068832', 'REGION_SLUG': '', 'EVENTSTRTAGS': [], 'IS_TREND': False, 'RATING': '', 'WTS': '9,14,847', 'TITLE': 'Avengers: Endgame', 'ID': 'ET00090482', 'TYPE': 'MT', 'TYPE_NAME': 'Movies', 'CAT': ''}
        '''

        curDate = datetime.now().strftime("%Y%m%d") if self.date is None else self.date
        movieName = reSub('[^0-9a-zA-Z ]+', '', movieData.get('TITLE') ).lower().replace( " ", "-" )

        movieUrl = "https://in.bookmyshow.com/buytickets/"
        movieUrl += movieName
        movieUrl += "-" + self.regionData.get( 'alias' ) + "/movie-" + self.regionData.get( 'code' ).lower() + "-"
        movieUrl += movieData.get( 'ID' )
        movieUrl += "-MT/"
        movieUrl += curDate
        return movieUrl

    def getCinemaUrl( self, cinemaData ):
        '''
        `cinemaData` is similar to below:

        {"CC":"PVR","ST":"NS","REGION_SLUG":"","GRP":"Venue","EVENTSTRTAGS":[],"RATING":"","L_URL":"","WTS":"","TITLE":"PVR: Forum Mall, Koramangala","ID":"PVBN","TYPE_NAME":"Venues","TYPE":"|MT|","CAT":""}
        '''

        curDate = datetime.now().strftime("%Y%m%d") if self.date is None else self.date
        cinemaName = reSub('[^0-9a-zA-Z ]+', '', cinemaData.get('TITLE') ).lower().replace( " ", "-" )

        cinemaUrl = "https://in.bookmyshow.com/buytickets/"
        cinemaUrl += cinemaName
        cinemaUrl += "/cinema-" + self.regionData.get( 'code' ).lower() + "-"
        cinemaUrl += cinemaData.get( 'ID' )
        cinemaUrl += "-MT/"
        cinemaUrl += curDate
        return cinemaUrl

    def getUrlDataJSON( self, searchTerm ):
        '''
        returns all matched results after searching on bms
        '''

        url = self.getSearchUrl( searchTerm )
        headers = {
                'x-requested-from' : 'WEB',
        }
        data = self.ss.get( url, headers=headers )
        assert data.status_code == 200
        jsonResp = data.json()
        return jsonResp

    def search( self, searchTerm, typeName="Movies" ):
        jsonResp = self.getUrlDataJSON( searchTerm )
        # return the first hit belonging to typeName
        data = {}
        for movieInfo in jsonResp[ 'hits' ]:
            if movieInfo.get( 'TYPE_NAME' ) == typeName:
                data = movieInfo
                break
        
        url = None
        if typeName == "Movies":
            if data.get( 'SHOWDATE' ) is None:
                # Check if show is on
                print( "The show counters are yet to be opened!" )
                return None
            url = self.getMovieUrl( data )
        elif typeName == "Venues":
            url = self.getCinemaUrl( data )
        self.title = data.get( 'TITLE', '' )

        return url
    
    def checkAvailability( self, movieLink ):
        '''
        movieLink refers to moviePage where we have information about the movie, the cast and other stuff
        '''
        pass

    def checkCinemaAvailability( self, cinemaLink, movieName ):
        '''
        Notifies if a show is available in your requested cinema
        '''
        cinemaDetails = self.ss.get( cinemaLink )
        assert cinemaDetails.status_code == 200
        cinemaSoup = BeautifulSoup( cinemaDetails.content, 'html5lib' )
        # get movie name
        jsonRespOfMovies = self.getUrlDataJSON( movieName )
        # return the first hit belonging to movieName
        data = {}
        for movieInfo in jsonRespOfMovies[ 'hits' ]:
            if movieInfo.get( 'TYPE_NAME' ) == "Movies":
                data = movieInfo
                break
        movieName = data.get( 'TITLE', movieName )

        # find if your requested cinema is in the list
        found = False
        for movieTitle in cinemaSoup.find_all( "strong" ):
            if movieTitle.getText().strip().lower() == movieName.lower():
                found = True
                break
        if found:
            # Movie tickets are now available
            print( "HURRAY! Movie tickets are now available" )
            self.notification( "Hurray!", "Tickets for " + movieName + " at " + self.title + " are now available" )
            self.ringBell()
            return True
        else:
            print( "Movie tickets aren't available yet" )
            return False
        
    def checkMovie( self, name ):
        movieLink = self.search( name )
        if movieLink is None:
            exit( 0 )
        self.checkAvailability( movieLink )

    def checkCinema( self ):
        cinemaLink = self.search( self.cinema, typeName="Venues" )
        if cinemaLink is None:
            exit( 0 )
        return self.checkCinemaAvailability( cinemaLink, self.movie )

def parser():
    parser = ArgumentParser( prog=sys.argv[ 0 ],
                             description="A script to check if tickets are available for the movie in the specified cinema at a given date",
                             epilog="And you will be the first one to be notified as soon as the show is available" )
    parser.add_argument( '-m', '--movie', required=True, action='store', type=str, help="The movie you're looking to book tickets for" )
    parser.add_argument( '-c', '--cinema', required=True, action='store', type=str, help="The cinema in which you want to watch the movie" )
    parser.add_argument( '-d', '--date', required=True, action='store', type=str, help="Format: YYYYMMDD | The date on which you want to book tickets." )
    parser.add_argument( '-r', '--regionCode', required=True, action='store', type=str, help="The region code of your area; BANG for Bengaluru" )
    parser.add_argument( '-i', '--interval', action='store', type=int, help="BMS server will be queried every interval seconds", default=60 )
    parser.add_argument( '-b', '--pushBullet', action='store', metavar=( "ACCESS_TOKEN", "DEVICE_ID" ), type=str, nargs='+', help="Send notification to your device using pushbullet" )
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = parser()
    interval = args.interval
    status = False
    while not status:
        start = time()
        retry = 0
        while retry < 5:
            # only retry for some time on connectivity issues
            # bms = BookMyShow( args )
            # status = bms.checkCinema()
            try:
                bms = BookMyShow( args )
                status = bms.checkCinema()
                break
            except AssertionError:
                print( "Seems like we lost the connection mid-way, will retry..." )
                retry += 1
            except KeyboardInterrupt:
                sys.exit( 1 )
            except Exception as e:
                print( "Something unexpected happened; Recommended to re-run this script with correct values" )
                break
        if not status:
            stop = time()
            timeRemaining = interval - ( stop - start )
            timeRemaining = int( round( timeRemaining if timeRemaining > 0 else 0 ) )
            sleep( timeRemaining )
