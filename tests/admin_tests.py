#!/usr/bin/env python

import sys
import os
import unittest
from webtest import TestApp, AppError

from google.appengine.api import urlfetch, mail_stub, apiproxy_stub_map, urlfetch_stub, user_service_stub, datastore_file_stub
from google.appengine.api.memcache import memcache_stub
from google.appengine.api.urlfetch import DownloadError, InvalidURLError

# insert application path
app_path = os.path.join(
    os.path.realpath(os.path.dirname(__file__)), '../'
)
sys.path.insert(0, app_path)

from admin import application
import settings 

class AdminTest(unittest.TestCase):
    def setUp(self):
                
        self.app = TestApp(application())
        apiproxy_stub_map.apiproxy = apiproxy_stub_map.APIProxyStubMap()
        apiproxy_stub_map.apiproxy.RegisterStub('mail', mail_stub.MailServiceStub())
        apiproxy_stub_map.apiproxy.RegisterStub('user', user_service_stub.UserServiceStub())
        apiproxy_stub_map.apiproxy.RegisterStub('urlfetch', urlfetch_stub.URLFetchServiceStub())
        apiproxy_stub_map.apiproxy.RegisterStub('memcache', memcache_stub.MemcacheServiceStub())        
        stub = datastore_file_stub.DatastoreFileStub('temp', '/dev/null', '/dev/null')
        apiproxy_stub_map.apiproxy.RegisterStub('datastore_v3', stub)
        
        os.environ['APPLICATION_ID'] = "temp"
        os.environ['USER_EMAIL'] = "test@example.com"
        os.environ['SERVER_NAME'] = "example.com"
        os.environ['SERVER_PORT'] = "80"
        

    def test_index_returns_200(self):  
        response = self.app.get('/admin/', expect_errors=True)        
        self.assertEquals("200 OK", response.status)
        response = self.app.get('/admin', expect_errors=True)        
        self.assertEquals("200 OK", response.status)
    
    def test_html_tag_present(self):
        response = self.app.get('/admin/', expect_errors=True)        
        response.mustcontain("<html>")
            
    def test_web_view_return_correct_mime_type(self):
        response = self.app.get('/admin/', expect_errors=True)
        self.assertEquals(response.content_type, "text/html")
                   
    def test_404_handler(self):
        response = self.app.get('/admin/404', expect_errors=True)        
        self.assertEquals("404 Not Found", response.status)

    def test_clearing_cache_doesnt_listen_for_get(self):
        response = self.app.get('/admin/clearcache', expect_errors=True)        
        self.assertEquals("405 Method Not Allowed", response.status)

    def test_redirect_after_clearing_cache(self):
        response = self.app.post('/admin/clearcache', expect_errors=True)        
        self.assertEquals("302 Moved Temporarily", response.status)


                                       
if __name__ == "__main__":
    unittest.main()