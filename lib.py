import os
import re
import logging
import unicodedata

from google.appengine.api import memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import users

import settings
from ext.textile import textile as real_textile

def slugify(value):
    "Slugify a string, to make it URL friendly."

    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(re.sub('[^\w\s-]', '', value).strip().lower())
    return re.sub('[-\s]+','-',value)

def textile(value):
    "Stub for adding textile functionality"
    value = real_textile(value, sanitize=1)
    return value

class BaseRequest(webapp.RequestHandler):
    "Extended request object with extra functionality"
    
    def _extra_context(self, context):   
        """
        Common context information is stored here, rather than
        being added to every view
        """
        
        # get a login or logout link depending on whether
        # we are logged in or not
        user = users.get_current_user()
        if user:
            link = users.create_logout_url("/")
        else:
            link = users.create_login_url("/")
             
        extras = {
            'user': user,
            'link': link,
            'debug': settings.DEBUG,
        }
        # update the context passed to render
        context.update(extras)
        return context
        
    def render(self, template_file, context={}):
        "Helper to deal with rendering a context to a template"
        path = os.path.join(os.path.dirname(__file__), 'templates',
            template_file)
        # render the template with the provided context
        # adding in the extra context variables at the same time
        output = template.render(path, self._extra_context(context))
        return output
        
    def render_403(self):
        "Custom authentication required view"
        self.error(403)
        logging.info("unauthorised attempt to access: %s" % self.request.path)
        output = get_cache("error403")
        if output is None:        
            output = self.render("403.html")
            memcache.add("error403", output, 3600)
        self.response.out.write(output)   
            
def get_cache(key):
    "Cache helper which checks if we have the cache enabled first"
    if settings.CACHE:
        return memcache.get(key)
    else:
        return None