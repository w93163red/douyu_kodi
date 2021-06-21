# -*- coding: utf-8 -*-
# Module: default
# Author: Yangqian
# Created on: 26.12.2015
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
# Largely following the example at 
# https://github.com/romanvm/plugin.video.example/blob/master/main.py
# get from https://github.com/chrippa/livestreamer/blob/develop/src/livestreamer/plugins/douyutv.py
# further from https://github.com/soimort/you-get/issues/580
# and from https://github.com/yan12125/douyu-hack


import requests
import xbmc, xbmcgui, re, xbmcplugin
from bs4 import BeautifulSoup
from urllib.parse import parse_qsl
import sys
import json, urllib
import hashlib, time, uuid
import xbmcaddon
import html
import logging
from BulletScreen import BulletScreen
from douyudanmu import douyudanmu
from Douyu import Douyu_HTTP_Server
from xbmc import log

__addon__ = xbmcaddon.Addon()
__language__ = __addon__.getLocalizedString
API_URL = "http://www.douyutv.com/swf_api/room/{0}?cdn={1}&nofan=yes&_t={2}&sign={3}"
API_SECRET = u'bLFlashflowlad92'
PAGE_LIMIT = 10
NEXT_PAGE = __language__(32001)
headers = {'Accept':
               'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Accept-Encoding': 'gzip, deflate',
           'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 8_1_3 like Mac OS X) AppleWebKit/600.1.4 (KHTML, like Gecko) Version/8.0 Mobile/12B466 Safari/600.1.4'}

# APPKEY = 'Y237pxTx2In5ayGz' #from android-hd client (https://gist.github.com/ERioK/d73f76dbb0334618ff905f1bf3363401)
APPKEY = 'zNzMV1y4EMxOHS6I5WKm'  # from https://github.com/soimort/you-get/commit/04b5f9f95adf4f584b26417bff19950cc7a46ef4#diff-d0fafb6251bc8f273f8afa0256ffd6f1R54

# Initialize logging
logging.getLogger().setLevel(logging.INFO)
logging.basicConfig(format='[%(module)s][%(funcName)s] %(message)s')

TORRENT2HTTP_POLL = 1000
XBFONT_LEFT = 0x00000000
XBFONT_RIGHT = 0x00000001
XBFONT_CENTER_X = 0x00000002
XBFONT_CENTER_Y = 0x00000004
XBFONT_TRUNCATED = 0x00000008
XBFONT_JUSTIFY = 0x00000010

VIEWPORT_WIDTH = 1920.0
VIEWPORT_HEIGHT = 1088.0
OVERLAY_WIDTH = int(VIEWPORT_WIDTH * 0.4)  # 70% size
OVERLAY_HEIGHT = 150

# Get the plugin url in plugin:// notation.
_url = sys.argv[0]
# Get the plugin handle as an integer number.
_handle = int(sys.argv[1])


def list_categories(offset):
    # f=urllib2.urlopen('http://www.douyutv.com/directory')
    rr = BeautifulSoup(requests.get('https://www.douyu.com/directory', headers=headers).text, features='html.parser')
    catel = rr.findAll('a', {'class': 'Aside-menu-item'}, limit=offset + PAGE_LIMIT + 1)
    log("catel: " + str(catel), level=xbmc.LOGERROR)
    rrr = [(x['href'], x.text, "") for x in catel]
    offset = int(offset)
    if offset + PAGE_LIMIT < len(rrr):
        rrr = rrr[offset:offset + PAGE_LIMIT]
        nextpageflag = True
    else:
        rrr = rrr[offset:]
        nextpageflag = False
    listing = []
    for classname, textinfo, img in rrr:
        list_item = xbmcgui.ListItem(label=textinfo)
        # list_item.setProperty('fanart_image',img)
        url = u'{0}?action=listing&category={1}&offset=0'.format(_url, classname)
        is_folder = True
        listing.append((url, list_item, is_folder))
    if nextpageflag:
        list_item = xbmcgui.ListItem(label=NEXT_PAGE)
        url = u'{0}?offset={1}'.format(_url, str(offset + PAGE_LIMIT))
        is_folder = True
        listing.append((url, list_item, is_folder))
    xbmcplugin.addDirectoryItems(_handle, listing, len(listing))
    xbmcplugin.endOfDirectory(_handle)


def list_videos(category, offset=0):
    log("category: " + category, xbmc.LOGINFO)
    rr = BeautifulSoup(requests.get('http://www.douyu.com' + category, headers=headers).text, features='html.parser')
    videol = rr.findAll('a', {'class': 'DyListCover-wrap'}, limit=offset + PAGE_LIMIT + 1)
    listing = []
    if offset + PAGE_LIMIT < len(videol):
        videol = videol[offset:offset + PAGE_LIMIT]
        nextpageflag = True
    else:
        videol = videol[offset:]
        nextpageflag = False
    for x in videol:
        xbmc.log("video element: " + str(x), xbmc.LOGINFO)
        roomid = x['href'][1:]
        title = x.find('h3', {'class': 'DyListCover-intro'}).text
        nickname = ""
        if x.find('div', {'class': 'DyListCover-userName'}):
            nickname = x.find('div', {'class': 'DyListCover-userName'}).text
        liveinfo = f'{nickname}:{title}'
        list_item = xbmcgui.ListItem(label=liveinfo)
        url = '{0}?action=play&video={1}'.format(_url, roomid)
        is_folder = False
        listing.append((url, list_item, is_folder))
    if nextpageflag:
        list_item = xbmcgui.ListItem(label=NEXT_PAGE)
        url = '{0}?action=listing&category={1}&offset={2}'.format(_url, category, offset + PAGE_LIMIT)
        is_folder = True
        listing.append((url, list_item, is_folder))
    xbmcplugin.addDirectoryItems(_handle, listing, len(listing))
    xbmcplugin.endOfDirectory(_handle)


def get_room(roomid, cdn):
    ts = int(time.time() / 60)
    sign = hashlib.md5(("{0}{1}{2}".format(roomid, API_SECRET, ts)).encode("utf-8")).hexdigest()
    url = API_URL.format(roomid, cdn, ts, sign)
    res = requests.get(url).text
    room = json.loads(res)
    return room

def get_play_item(roomid, cdn):
    xbmc.log("room_id: " + str(roomid), xbmc.LOGINFO)
    realurl = requests.get(f"http://192.168.50.213:5000/room/{roomid}").text
    xbmc.log("url: " + str(realurl), xbmc.LOGINFO)
    path = realurl
    combinedname = '1'
    play_item = xbmcgui.ListItem(combinedname, path=path)
    play_item.setInfo(type="Video", infoLabels={"Title": combinedname})
    return (roomid, path, play_item)


def play_video(roomid):
    """
    Play a video by the provided path.
    :param path: str
    :return: None
    """
    cdnindex = __addon__.getSetting("cdn")
    player = xbmc.Player()
    cdndict = {"0": "", "1": "ws", "2": "ws2", "3": "lx", "4": "dl", "5": "tct"}
    cdn = cdndict[cdnindex]
    # directly play the item.
    roomid, path, play_item = get_play_item(roomid, cdn)
    logging.debug(path)
    if path == '':
        return
    # Pass the item to the Kodi player.
    xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)
    player.play(path)

def router(paramstring):
    """
    Router function that calls other functions
    depending on the provided paramstring
    :param paramstring:
    :return:
    """
    # Parse a URL-encoded paramstring to the dictionary of
    # {<parameter>: <value>} elements
    params = dict(parse_qsl(paramstring))
    # Check the parameters passed to the plugin
    if 'action' in params:
        if params['action'] == 'listing':
            # Display the list of videos in a provided category.
            list_videos(params['category'], int(params['offset']))
        elif params['action'] == 'play':
            # Play a video from a provided URL.
            play_video(params['video'])
    else:
        # If the plugin is called from Kodi UI without any parameters,
        # display the list of video categories
        if 'offset' in params:
            list_categories(int(params['offset']))
        else:
            list_categories(0)


if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    log(f"SYSTEM ARGS: {str(sys.argv)}", xbmc.LOGINFO)
    router(sys.argv[2][1:])
