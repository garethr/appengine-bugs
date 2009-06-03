#!/usr/bin/env python

import logging

from google.appengine.api import memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from lib import BaseRequest, get_cache
import settings

class Index(BaseRequest):
    def get(self):
        stats = memcache.get_stats()
        context = {
            'stats': stats,
        }        
        output = self.render("admin.html", context)
        self.response.out.write(output)
        
class ClearCache(BaseRequest):
    def post(self):
        clear = memcache.flush_all()    
        if clear:
            logging.info("Cache cleared")
        else:
            logging.error("Problem clearing cache")

        self.redirect("/admin/")
        
class NotFoundPageHandler(BaseRequest):
    def get(self):
        self.error(404)
        output = get_cache("error404")
        if output is None:        
            output = self.render("404.html")
            memcache.add("error404", output, 3600)
        self.response.out.write(output)

def application():
    "Run the application"
    # wire up the views
    ROUTES = [
        ('/admin/?$', Index),
        ('/admin/clearcache/?$', ClearCache),
        ('/.*', NotFoundPageHandler),
    ]
    application = webapp.WSGIApplication(ROUTES, debug=settings.DEBUG)
    return application

def main():
    "Run the application"
    run_wsgi_app(application())


if __name__ == '__main__':
    main()