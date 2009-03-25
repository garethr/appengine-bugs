#!/usr/bin/env python

import re
import os
import logging

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.api import users
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import mail

from django.utils import simplejson

from lib import BaseRequest
import settings
from models import Project, Issue

webapp.template.register_template_library('filters')

GITBUG = re.compile('#gitbug[0-9]+')

class Index(BaseRequest):
    def get(self):
            
        projects = Project.all().filter('user =', users.get_current_user()).order('-created_date').fetch(50)
        context = {
            'projects': projects,
        }
        # calculate the template path
        output = self.render("index.html", context)
        self.response.out.write(output)

class ProjectHandler(BaseRequest):
    def get(self, slug):
        if self.request.path[-1] != "/":
            self.redirect("%s/" % self.request.path, True)
            return
        
        project = Project.all().filter('slug =', slug).fetch(1)[0]
        
        issues = Issue.all().filter('project =', project).order('fixed').order('created_date')
        
        user = users.get_current_user()
        if project.user == user:
            owner = True
        else:
            owner = False            
            
        context = {
            'project': project,
            'issues': issues,
            'owner': owner,
        }
        # calculate the template path
        output = self.render("project.html", context)
        self.response.out.write(output)
        
    def post(self, slug):
        project = Project.all().filter('slug =', slug).fetch(1)[0]
        name = self.request.get("name")
        description = self.request.get("description")
        email = self.request.get("email")
        issue = Issue(
            name=name,
            description=description,
            project=project,
        )
        if email:
            issue.email = email
        issue.put()
        
        self.redirect("/projects/%s/" % slug)

class IssueHandler(BaseRequest):
    def get(self, project_slug, issue_slug):
        if self.request.path[-1] != "/":
            self.redirect("%s/" % self.request.path, True)
            return
            
        issue = Issue.all().filter('internal_url =', "/%s/%s/" % (project_slug, issue_slug)).fetch(1)[0]
        issues = Issue.all().filter('project =', issue.project).filter('name !=', issue.name).filter('fixed =', False).order('-created_date').fetch(10)

        user = users.get_current_user()            
        if issue.project.user == user:
            owner = True
        else:
            owner = False
            
        context = {
            'issue': issue,
            'issues': issues,
            'owner': owner,
        }
        # calculate the template path
        output = self.render("issue.html", context)
        self.response.out.write(output)
    
    def post(self, project_slug, issue_slug):
        issue = Issue.all().filter('internal_url =', "/%s/%s/" % (project_slug, issue_slug)).fetch(1)[0]
        
        user = users.get_current_user()
        
        if issue.project.user == user:
        
            name = self.request.get("name")
            description = self.request.get("description")
            email = self.request.get("email")
            fixed = self.request.get("fixed")
            fixed_description = self.request.get("fixed_description")
        
            issue.name = name
            issue.description = description
            if email:
                issue.email = email
            else:
                issue.email = None
            issue.fixed = bool(fixed)
            if fixed:
                issue.fixed_description = fixed_description
            else:
                issue.fixed_description = None
        
            issue.put()

        self.redirect("/projects%s" % issue.internal_url)

class IssueDeleteHandler(BaseRequest):
    def get(self, project_slug, issue_slug):
        if self.request.path[-1] != "/":
            self.redirect("%s/" % self.request.path, True)
            return

        issue = Issue.all().filter('internal_url =', "/%s/%s/" % (project_slug, issue_slug)).fetch(1)[0]        

        user = users.get_current_user()            
        if issue.project.user == user:
            owner = True
        else:
            owner = False
            
        context = {
            'issue': issue,
            'owner': owner,
        }
        # calculate the template path
        output = self.render("issue_delete.html", context)
        self.response.out.write(output)

    def post(self, project_slug, issue_slug):

        issue = Issue.all().filter('internal_url =', "/%s/%s/" % (project_slug, issue_slug)).fetch(1)[0]        

        return_url = "/projects/%s" % issue.project.slug

        user = users.get_current_user()            
        if issue.project.user == user:
            issue.delete()

        self.redirect(return_url)

class ProjectsHandler(BaseRequest):
    def get(self):
        if self.request.path[-1] != "/":
            self.redirect("%s/" % self.request.path, True)
            return
        
        projects = Project.all().order('-created_date').fetch(50)
        context = {
            'projects': projects,
        }
        # calculate the template path
        output = self.render("projects.html", context)
        self.response.out.write(output)

    def post(self):
        try:
            name = self.request.get("name")
            project = Project(
                name=name,
                user=users.get_current_user(),       
            )
            project.put()
        except db.BadValueError:
            pass
        self.redirect('/')

class WebHookHandler(BaseRequest):
    def post(self, slug):
        project = Project.all().filter('slug =', slug).fetch(1)[0]
        
        key = self.request.get("key")
        
        if key == project.__key__:        
            payload = self.request.get("payload")
            representation = simplejson.loads(payload)
            commits = representation['commits']
            for commit in commits:
                message = commit['message']
                search = GITBUG.search(message)
                if search:
                    identifier = search.group()[7:]                                
                    issue = Issue.all().filter('project =', project).filter('identifier =', int(identifier)).fetch(1)[0]
                    issue.fixed = True
                    issue.put()
            
        self.response.out.write("")

class NotFoundPageHandler(BaseRequest):
    def get(self):
        self.error(404)
        output = self.render("404.html")
        self.response.out.write(output)

class FaqPageHandler(BaseRequest):
    def get(self):
        if self.request.path[-1] != "/":
            self.redirect("%s/" % self.request.path, True)
            return
        output = self.render("faq.html")
        self.response.out.write(output)

# Log a message each time this module get loaded.
logging.info('Loading %s, app version = %s',
    __name__, os.getenv('CURRENT_VERSION_ID'))
                        
def main():
    "Run the application"
    # wire up the views
    ROUTES = [
        ('/', Index),
        ('/projects/?$', ProjectsHandler),
        ('/projects/([A-Za-z0-9-]+)/hook/?$', WebHookHandler),
        ('/projects/([A-Za-z0-9-]+)/([A-Za-z0-9-]+)/?$', IssueHandler),
        ('/projects/([A-Za-z0-9-]+)/([A-Za-z0-9-]+)/delete/?$', IssueDeleteHandler),
        ('/projects/([A-Za-z0-9-]+)/?$', ProjectHandler),
        ('/faq/?$', FaqPageHandler),
        ('/.*', NotFoundPageHandler),
    ]
    application = webapp.WSGIApplication(ROUTES, debug=settings.DEBUG)
    run_wsgi_app(application)

if __name__ == '__main__':
    main()