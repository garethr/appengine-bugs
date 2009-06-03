from datetime import datetime

from google.appengine.ext import db
from google.appengine.ext import search
from google.appengine.api import mail

from lib import slugify, textile
import settings

class Project(db.Model):
    "Represents a single project"
    name = db.StringProperty(required=True)
    url = db.LinkProperty()
    description = db.TextProperty()
    html = db.TextProperty()
    slug = db.StringProperty()
    created_date = db.DateTimeProperty(auto_now_add=True)
    user = db.UserProperty(required=True)
    other_users = db.StringListProperty()

    @property
    def open_issues(self):
        "Get a list of the open issues against this project"
        return self.issue_set.filter('fixed =', False)

    @property
    def closed_issues(self):
        "Get a list of previously closed issues for this project"
        return self.issue_set.filter('fixed =', True)

    def put(self):
        # we set the slug on the first save
        # after which it is never changed
        self.html = textile(unicode(self.description))
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
    "Issue or bug representation"
    name = db.StringProperty(required=True)
    description = db.TextProperty()
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
        "Overridden save method"
        # we save the html here as it's faster than processing 
        # everytime we display it
        self.html = textile(unicode(self.description))
        
        # internal url is set on first save and then not changed
        # as the admin interface doesn't allow for changing name
        if not self.internal_url:
            slug = slugify(unicode(self.name))
            self.internal_url = "/%s/%s/" % (self.project.slug, slug)
        
        # each issue has a per project unique identifier which is based
        # on an integer. This integer is stored in counter in the datastore
        # which is associated with the project
        if not self.identifier:
            counter = Counter.get_by_key_name("counter/%s" % self.project.name)
            if counter is None:
                # if it's the first issue we need to create the counter
                counter = Counter(
                    key_name="counter/%s" % self.project.name,
                    project=self.project,
                    count=0,
                )
            # increment the count
            counter.count += 1
            counter.put()
        
            # save the count against the issue for use in the identifier
            self.identifier = counter.count

        # if the bug gets fixed then we store that date
        # if it's later marked as open we clear the date
        if self.fixed:
            self.fixed_date = datetime.now()
        else:
            self.fixed_date = None
        
        # if the bug has been fixed then send an email
        if self.fixed and self.email:
            mail.send_mail(sender="gareth.rushgrove@gmail.com",
                to=self.email,
                subject="[GitBug] Your bug has been fixed",
                body="""You requested to be emailed when a bug on GitBug was fixed:
              
Issue name: %s
Description: %s

-------

%s

-------

Thanks for using GitBug <http://gitbug.appspot.com>. A very simple issue tracker.
""" % (self.name, self.description, self.fixed_description))
        
        super(Issue, self).put()