#!/usr/bin/env python

import re
import sys
import os
import unittest

# insert application path
app_path = os.path.join(
    os.path.realpath(os.path.dirname(__file__)), '../'
)
sys.path.insert(0, app_path)

# we get the right settings file because we inserted the path
# at the start above
import settings

URL_RE = re.compile(
    r'^https?://' # http:// or https://
    r'(?:(?:[A-Z0-9-]+\.)+[A-Z]{2,6}|' #domain...
    r'localhost|' #localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
    r'(?::\d+)?' # optional port
    r'(?:/?|/\S+)$', re.IGNORECASE)

class SettingsTest(unittest.TestCase):

    def test_presense_of_debug(self):  
        try:
            settings.DEBUG
            self.assertTrue("DEBUG present in settings")
        except AttributeError:
            self.assertFalse("DEBUG not defined in settings")

    def test_presense_of_cache(self):  
        try:
            settings.CACHE
            self.assertTrue("CACHE present in settings")
        except AttributeError:
            self.assertFalse("CACHE not defined in settings")

    def test_presense_of_system_url(self):  
        try:
            url = settings.SYSTEM_URL
            if not URL_RE.match(url):
                self.assertFalse("SYSTEM_URL defined but not a valid URL")
            self.assertTrue("SYSTEM_URL defined in settings")
        except AttributeError:
            self.assertFalse("SYSTEM_URL not defined in settings")
            
    def test_value_of_debug(self):
        self.assertFalse(settings.debug)
                                       
if __name__ == "__main__":
    unittest.main()