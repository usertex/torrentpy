import urllib2
import os
import sys
import unittest
from mock import patch, Mock

from test_path import DOWNLOADER_PATH
sys.path.append(DOWNLOADER_PATH)

import downloader
from settings import DOWNLOADS_FOLDER
from errors import DownloaderError
from test_resources.general_search_results import search_results
from test_resources.tracker_results import tracker_results
from BeautifulSoup import BeautifulSoup

#to mock out urlopen
FakeSearchSock = Mock()
FakeSearchSock.read = Mock(return_value=search_results)
FakeSearchUrlOpen = Mock(return_value=FakeSearchSock)
FakeTrackerSock = Mock()
FakeTrackerSock.read = Mock(return_value=tracker_results)
FakeTrackerUrlOpen = Mock(return_value=FakeTrackerSock)
FakeEmptySock = Mock()
FakeEmptySock.read = Mock(return_value='')
FakeEmptyUrlOpen = Mock(return_value=FakeEmptySock)
#to mock out a system call running wget
fake_good_system_call = Mock(return_value=0)
fake_bad_system_call = Mock(return_value=1)
class FakeChangingSystemCall(object):
    def __init__(self):
        self._call_count = 0
        self.args = []
        
    def call(self, *args):
        self.args = args
        if self._call_count == 0:
            self._call_count += 1
            return 1
        else:
            return 0
changing_system_call = FakeChangingSystemCall()
#to mock out dynamic tracker loading
def fake_tracker_giver(*args):
    return FakeTracker()

class DownloaderTest(unittest.TestCase):
    def setUp(self):
        self._mock_listdir = Mock(return_value=['test.py'])
        self._fake_soup = BeautifulSoup(search_results)
        self._correct_parsed_results = \
        {'The Beatles Greatest Hits Remastered/2009/MP3 Bubanee':
        'http://www.torrentz.com/0898a4b562c1098eb69b9b801c61a51d788df0f5'}
        self._correct_link = 'http://www.torrentz.com/0898a4b562c109' + \
          '8eb69b9b801c61a51d788df0f5'
        self._correct_trackers = {
          'torrenthound': 'http://www.torrenthound.com/hash/0898a4b5' + \
            '62c1098eb69b9b801c61a51d788df0f5/torrent-info/The-Beatl' + \
            'es-2009-Greatest-Hits-CDRip-Remastered-Bubanee-',
          'btmon': 'http://www.btmon.com/Audio/Unsorted/The_Beatles_' + \
            '2009_Remastered_Greatest_Hits_41_Songs_CDRips_Bubanee.t' + \
            'orrent.html',
          'btjunkie': 'http://btjunkie.org/torrent/The-Beatles-Great' + \
            'est-Hits-Remastered-2009-MP3-Bubanee/43580898a4b562c109' + \
            '8eb69b9b801c61a51d788df0f5',
          'thepiratebay': 'http://thepiratebay.org/torrent/5079924',
          'fenopy': 'http://fenopy.com/torrent/The+Beatles+2009+Grea' + \
            'test+Hits+41+Songs+CDRip+Remastered+/MzYzODQxMA'}
        self._downloader_ut = downloader.Downloader()
        
    def test_get_trackers(self):
        with patch('os.listdir', self._mock_listdir):
            trackers = self._downloader_ut._get_trackers()
            self.assertEqual(['test'], trackers)
   
    @patch.object(urllib2, 'urlopen', FakeSearchUrlOpen)  
    def test_torrentz_search(self):
        search_term = 'TeSt QuERY'
        result = self._downloader_ut._torrentz_search(search_term)
        self.assertEquals(self._fake_soup, result)
        
    def test_parse_general_search_results__good_results(self):
        parsed_results = \
          self._downloader_ut._parse_general_search(self._fake_soup)
        self.assertEquals(self._correct_parsed_results, parsed_results)
        
    def test_parse_general_search_results__bad_results(self):
        empty_soup = BeautifulSoup('<html></html>')
        self.assertRaises(DownloaderError,
          self._downloader_ut._parse_general_search, empty_soup)
          
    def test_general_results_link__good_result(self):
        parsed_results = \
          self._downloader_ut._parse_general_search(self._fake_soup)
        link = \
          self._downloader_ut._general_result_link(parsed_results,
          'tHe bEatlEs')
        self.assertEquals(self._correct_link, link)
          
    def test_general_results_link__bad_result(self):
        parsed_results = \
          self._downloader_ut._parse_general_search(self._fake_soup)
        self.assertRaises(DownloaderError,
          self._downloader_ut._general_result_link, parsed_results,
          'huh?')
          
    @patch.object(urllib2, 'urlopen', FakeTrackerUrlOpen)  
    def test_find_trackers__good_results(self):
        found_trackers = \
          self._downloader_ut._find_trackers(self._correct_link)
        self.assertDictEqual(self._correct_trackers, found_trackers)
        
    @patch.object(urllib2, 'urlopen', FakeEmptyUrlOpen)  
    def test_find_trackers__bad_results(self):
          self.assertRaises(DownloaderError,
            self._downloader_ut._find_trackers, 'http://nada.com')
            
    @patch.object(os, 'system', fake_good_system_call)
    @patch.object(downloader.Downloader, '_get_tracker_object', fake_tracker_giver)
    def test_download_torrent_file__work_first_time(self):
        torrent_file_name ='GreatestHits.torrent'
        base_file_path = DOWNLOADS_FOLDER
        correct_file_path = os.path.join(base_file_path, torrent_file_name)
        result_file_path = self._downloader_ut._download_torrent_file('Greatest Hits',
          self._correct_trackers)
        self.assertEquals(correct_file_path, result_file_path)
        first_tracker, first_tracker_url = self._correct_trackers.items()[0]
        system_call_args = fake_good_system_call.call_args[0][0].split()
        download_url = system_call_args[3].replace('"', '')
        self.assertEquals(download_url, first_tracker_url)
        
    @patch.object(os, 'system', changing_system_call.call)
    @patch.object(downloader.Downloader, '_get_tracker_object', fake_tracker_giver)
    def test_download_torrent_file__work_second_time(self):
        torrent_file_name ='GreatestHits.torrent'
        base_file_path = DOWNLOADS_FOLDER
        correct_file_path = os.path.join(base_file_path, torrent_file_name)
        result_file_path = self._downloader_ut._download_torrent_file('Greatest Hits',
          self._correct_trackers)
        self.assertEquals(correct_file_path, result_file_path)
        first_tracker, first_tracker_url = self._correct_trackers.items()[1]
        system_call_args = changing_system_call.args[0].split()
        download_url = system_call_args[3].replace('"', '')
        self.assertEquals(download_url, first_tracker_url)
        
    @patch.object(os, 'system', fake_bad_system_call)
    @patch.object(downloader.Downloader, '_get_tracker_object', fake_tracker_giver)
    def test_download_torrent_file__doesnt_work(self):
        self.assertRaises(DownloaderError,
          self._downloader_ut._download_torrent_file, 'Greatest Hits',
          self._correct_trackers)
    
class FakeTracker(object):
    def __init__(self):
        pass
    
    def extract_download_url(self, start_url):
        return start_url