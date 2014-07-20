#!/usr/bin/python
# -*- coding: utf-8 -*-
import _addoncompat
import _common
import _connection
import sys
import urllib
import xbmcgui
import xbmcplugin
import re
import simplejson
from bs4 import BeautifulSoup

pluginHandle = int(sys.argv[1])

AUTHURL = 'http://www.tbs.com/processors/cvp/token.jsp'
SWFURL = 'http://z.cdn.turner.com/xslo/cvp/plugins/akamai/streaming/osmf1.6/2.10/AkamaiAdvancedStreamingPlugin.swf'
BASE = 'http://ht.cdn.turner.com/tbs/big/'

def episodes(SITE):
	episode_url = _common.args.url
	print episode_url
	try:
		season_number = int(episode_url.split('filterBySeasonNumber=')[1])
	except:
		season_number = 0 
	episode_data = _connection.getURL(episode_url)
	episode_tree = BeautifulSoup(episode_data, 'html.parser')
	episode_menu = episode_tree.find_all('episode')
	for episode_item in episode_menu:
		try:
			episode_season_number = int(episode_item['episeasonnumber'])
		except:
			episode_season_number = 0
		print "Es", episode_season_number
		if episode_season_number == season_number or 'filterBySeasonNumber'  not in episode_url:
			print "HRE"
			segments = episode_item.find_all('segment')
			if len(segments) == 0:
				url = episode_item['id']
			else:
				url = ''
				for segment in segments:
					url = url + ',' + segment['id']
				url = url[1:]
			try:
				episode_duration = episode_item['duration']
				episode_duration = int(_common.format_seconds(episode_duration))
			except:
				episode_duration = 0
				for segment_duration in segments:
					episode_duration += float(segment_duration['duration'])
			try:
				episode_airdate = _common.format_date(episode_item['originalpremieredate'].split(' ')[0],'%m/%d/%Y')
			except:
				try:
					episode_airdate = _common.format_date(episode_item['launchdate'].split(' ')[0],'%m/%d/%Y')
				except:
					episode_airdate = -1
			episode_name = episode_item['title']
			try:
				season_number = int(episode_item['episeasonnumber'])
			except:
				season_number = -1
			try:
				episode_number = int(episode_item['episodenumber'][:2])
			except:
				episode_number = -1
			try:
				episode_thumb = episode_item['thumbnailurl']
			except:
				episode_thumb = None
			episode_plot = episode_item.description.text
			u = sys.argv[0]
			u += '?url="' + urllib.quote_plus(url) + '"'
			u += '&mode="' + SITE + '"'
			u += '&sitemode="play_video"'
			infoLabels={	'title' : episode_name,
							'durationinseconds' : episode_duration,
							'season' : season_number,
							'episode' : episode_number,
							'plot' : episode_plot,
							'premiered' : episode_airdate }
			_common.add_video(u, episode_name, episode_thumb, infoLabels = infoLabels)
	_common.set_view('episodes')
	
def play_video(SITE, EPISODE):
	stack_url = ''
	for video_id in _common.args.url.split(','):
		video_url = EPISODE % video_id
		hbitrate = -1
		sbitrate = int(_addoncompat.get_setting('quality')) * 1024
		closedcaption = None
		video_data = _connection.getURL(video_url)
		video_tree = BeautifulSoup(video_data, 'html.parser')
		video_menu = video_tree.find_all('file')
		hbitrate = -1
		file_url = None
		for video_index in video_menu:
			try:
				bitrate = int(video_index['bitrate'])
				type = video_index['type']
				if bitrate > hbitrate and bitrate <= sbitrate:
					hbitrate = bitrate
					file_url = video_index.string
				elif bitrate == hbitrate and bitrate <= sbitrate:
					file_url = video_index.string
			except:
				pass
		if file_url is None:
			file_url = BeautifulSoup(video_data).find_all('file')[0].string
		if 'mp4:'  in file_url:
			filename = file_url[1:len(file_url)-4]
			serverDetails = video_tree.find('akamai')
			server = serverDetails.find('src').string.split('://')[1]
			tokentype = serverDetails.find('authtokentype').string
			window = serverDetails.find('window').string
			aifp = serverDetails.find('aifp').string
			auth=getAUTH(aifp,window,tokentype,video_id,filename.replace('mp4:',''), SITE)      
			rtmp = 'rtmpe://' + server + '?' + auth + ' playpath=' + filename + ' swfurl=' + SWFURL + ' swfvfy=true'
			segurl = rtmp
		elif 'http' not in file_url:
			segurl = BASE + file_url
		else:
			segurl = file_url
		stack_url += segurl.replace(',', ',,') + ' , '
	if ', ' in stack_url:
		stack_url = 'stack://' + stack_url
	finalurl = stack_url[:-3]
	xbmcplugin.setResolvedUrl(pluginHandle, True, xbmcgui.ListItem(path = finalurl))

def getAUTH(aifp, window, tokentype, vid, filename, site):
	parameters = {'aifp' : aifp,
				'window' : window,
				'authTokenType' : tokentype,
				'videoId' : vid,
				'profile' : site,
				'path' : filename
				}
	link = _connection.getURL(AUTHURL, parameters)
	return re.compile('<token>(.+?)</token>').findall(link)[0]
