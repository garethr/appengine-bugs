#!/usr/bin/env python

import logging

from google.appengine.api import memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from lib import BaseRequest, get_cache
import settings

class Index(BaseRequest):
    def get(self):
        output = get_cache("admin")
        if output is None:
            output = self.render("admin.html")
            memcache.add("admin", output, 3600)
        self.response.out.write(output)
        
class ClearCache(BaseRequest):
    def get(self):
        
        clear = memcache.flush_all()    
        if clear:
            logging.info("Cache cleared")
        else:
            logging.error("Problem clearing cache")

        self.redirect("/admin/")
        
class CacheStats(BaseRequest):
    def get(self):
        
        stats = memcache.get_stats()
        self.response.out.write(stats)
        

class NotFoundPageHandler(BaseRequest):
    def get(self):
        self.error(404)
        output = get_cache("error404")
        if output is None:        
            output = self.render("404.html")
            memcache.add("error404", output, 3600)
        self.response.out.write(output)

def main():
    "Run the application"
    # wire up the views
    ROUTES = [
        ('/admin/?$', Index),
        ('/admin/clearcache/?$', ClearCache),
        ('/admin/cachestats/?$', CacheStats),
        ('/.*', NotFoundPageHandler),
    ]
    application = webapp.WSGIApplication(ROUTES, debug=settings.DEBUG)
    run_wsgi_app(application)

if __name__ == '__main__':
    main()