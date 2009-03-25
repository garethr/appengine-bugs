from datetime import datetime

from google.appengine.ext import db
from google.appengine.ext import search
from google.appengine.api import mail

from lib import slugify, textile
import settings

class Project(db.Model):
    name = db.StringProperty(required=True)
    url = db.LinkProperty()
    slug = db.StringProperty()
    created_date = db.DateTimeProperty(auto_now_add=True)
    user = db.UserProperty(required=True)

    def put(self):
        # we set the slug on the first save
        # after which it is never changed
        # TODO: make sure slug is not already in use
        if not self.slug:
            self.slug = slugify(unicode(self.name))
        super(Project, self).put()

class Counter(db.Model):
    "Project specific counter"
    count = db.IntegerProperty()
    project = db.ReferenceProperty(Project, required=True)
    
    # make it easy to retrieve the object based on key
    key_template = 'counter/%(project)s'

class Issue(search.SearchableModel):
    name = db.StringProperty(required=True)
    description = db.TextProperty(required=True)
    html = db.TextProperty()
    created_date = db.DateTimeProperty(auto_now_add=True)
    email = db.EmailProperty()
    project = db.ReferenceProperty(Project, required=True)
    internal_url = db.StringProperty()
    fixed = db.BooleanProperty(default=False)
    fixed_date = db.DateTimeProperty()
    fixed_description = db.TextProperty()
    identifier = db.IntegerProperty()

    def put(self):
        
        self.html = textile(unicode(self.description))
        
        if not self.internal_url:
            slug = slugify(unicode(self.name))
            self.internal_url = "/%s/%s/" % (self.project.slug, slug)
        
        if not self.identifier:
            counter = Counter.get_by_key_name("counter/%s" % self.project.name)
            if counter is None:
                counter = Counter(
                    key_name="counter/%s" % self.project.name,
                    project=self.project,
                    count=0,
                )
            counter.count += 1
            counter.put()
        
            self.identifier = counter.count

        if self.fixed:
            self.fixed_date = datetime.now()
        else:
            self.fixed_date = None
        
        if self.fixed and self.email:
            mail.send_mail(sender="gitbug@gmail.com",
                to=self.email,
                subject="You Bug has been fixed",
                body="""You requested to be emailed when a bug on GitBug was fixed:
              
Issue name: %s
Description: %s

-------

%s

-------

Thanks for using GitBug <http://gitbug.appspot.com>. A very simple issue tracker.
""" % (self.name, self.description, self.fixed_description))
        
        super(Issue, self).put()