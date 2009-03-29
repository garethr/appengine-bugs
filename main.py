#!/usr/bin/env python

import re
import os
import logging
from datetime import datetime

from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.api import users
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import mail

from django.utils import simplejson

from lib import BaseRequest, get_cache
import settings
from models import Project, Issue
from ext.PyRSS2Gen import RSS2, RSSItem

webapp.template.register_template_library('filters')

GITBUG = re.compile('#gitbug[0-9]+')

class Index(BaseRequest):
    def get(self):
        if users.get_current_user():
            projects = Project.all().filter('user =', users.get_current_user()).order('-created_date').fetch(50)
            context = {
                'projects': projects,
            }
            # calculate the template path
            output = self.render("index.html", context)
        else:
            output = get_cache("home")
            if output is None:
                output = self.render("home.html")
                memcache.add("home", output, 3600)
        self.response.out.write(output)

class ProjectHandler(BaseRequest):
    def get(self, slug):
        if self.request.path[-1] != "/":
            self.redirect("%s/" % self.request.path, True)
            return
        
        user = users.get_current_user()
    
        output = None
        if not user:
            output = get_cache("project_%s" % slug)
        
        if output is None:
            project = Project.all().filter('slug =', slug).fetch(1)[0]        
            issues = Issue.all().filter('project =', project).order('fixed').order('created_date')
            
            if project.user == user or users.is_current_user_admin():
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
        if not user:
            memcache.add("project_%s" % slug, output, 3600)
        self.response.out.write(output)
        
    def post(self, slug):
        project = Project.all().filter('slug =', slug).fetch(1)[0]
        name = self.request.get("name")
        description = self.request.get("description")
        email = self.request.get("email")
        
        try:
            if Issue.all().filter('name =', name).filter('project =', project).count() == 0:
                issue = Issue(
                    name=name,
                    description=description,
                    project=project,
                )
                if email:
                    issue.email = email
                issue.put()
                logging.info("issue created: %s in %s" % (name, project.name))
        except Exception, e:
            logging.error("error adding project: %s" % e)
        
        self.redirect("/projects/%s/" % slug)

class ProjectJsonHandler(BaseRequest):
    def get(self, slug):

        output = get_cache("project_%s_json" % slug)
        if output is None:
            project = Project.all().filter('slug =', slug).fetch(1)[0]        
            issues = Issue.all().filter('project =', project).order('fixed').order('created_date')

            issues_data = {}
            for issue in issues:

                if issue.fixed: 
                    status = "Fixed"
                else:
                    status = "Open"

                data = {
                    'internal_url': "%s/projects%s" % (settings.SYSTEM_URL, issue.internal_url),
                    'created_date': str(project.created_date)[0:19],
                    'description': issue.html,
                    'status': status,
                    'identifier': "#gitbug%s" % issue.identifier,
                }
                if issue.fixed and issue.fixed_description:
                    data['fixed_description'] = issue.fixed_description
                issues_data[issue.name] = data

            json = {
                'date': str(datetime.now())[0:19],
                'name': project.name,
                'internal_url': "%s/projects/%s/" % (settings.SYSTEM_URL, project.slug),
                'created_date': str(project.created_date)[0:19],
                'issues': issues_data,
            }
            
            if project.url:
                json['external_url'] = project.url

            output = simplejson.dumps(json)

            memcache.add("project_%s_json" % slug, output, 3600)
        self.response.headers["Content-Type"] = "application/javascript; charset=utf8"
        self.response.out.write(output)
        
class ProjectRssHandler(BaseRequest):
    def get(self, slug):

        output = get_cache("project_%s_rss" % slug)
        if output is None:

            project = Project.all().filter('slug =', slug).fetch(1)[0]        
               
            if self.request.get("open"):
                status_filter = True
                fixed = False
            elif self.request.get("closed"):
                status_filter = True
                fixed = True
            else:
                status_filter = None

            if status_filter:
                issues = Issue.all().filter('project =', project).filter('fixed =', fixed).order('fixed').order('created_date')
            else:
                issues = Issue.all().filter('project =', project).order('fixed').order('created_date')
            
            rss = RSS2(
                title="Issues for %s on GitBug" % project.name,
                link="%s/%s/" % (settings.SYSTEM_URL, project.slug),
                description="",
                lastBuildDate=datetime.now()
            )

            for issue in issues:
                
                if issue.fixed: 
                    pubDate = issue.fixed_date
                    title = "%s (%s)" % (issue.name, "Fixed")
                else:
                    pubDate = issue.created_date
                    title = issue.name
                
                rss.items.append(
                    RSSItem(
                        title=title,
                        link="%s/projects%s" % (settings.SYSTEM_URL, issue.internal_url),
                        description=issue.html,
                        pubDate=pubDate
                    ))

            output = rss.to_xml()

            memcache.add("project_%s_rss" % slug, output, 3600)
        self.response.headers["Content-Type"] = "application/rss+xml; charset=utf8"
        self.response.out.write(output)

class ProjectDeleteHandler(BaseRequest):
    def get(self, slug):
        if self.request.path[-1] != "/":
            self.redirect("%s/" % self.request.path, True)
            return
            
        # if we don't have a user then throw
        # an unauthorised error
        user = users.get_current_user()
        if not user:
            self.render_403()
            return
            
        project = Project.all().filter('slug =', slug).fetch(1)[0]
        
        if project.user == user or users.is_current_user_admin():
            owner = True
        else:
            owner = False

        context = {
            'project': project,
            'owner': owner,
        }
        # calculate the template path
        output = self.render("project_delete.html", context)
        self.response.out.write(output)

    def post(self, slug):
        
        # if we don't have a user then throw
        # an unauthorised error
        user = users.get_current_user()
        if not user:
            self.render_403()
            return

        project = Project.all().filter('slug =', slug).fetch(1)[0]

        user = users.get_current_user()            
        if project.user == user:
            try:
                logging.info("project deleted: %s" % project.name)
                project.delete()
            except Exception, e:
                logging.error("error deleting project: %s" % e)

        self.redirect("/")
        
class ProjectSettingsHandler(BaseRequest):
    def get(self, slug):
        if self.request.path[-1] != "/":
            self.redirect("%s/" % self.request.path, True)
            return

        project = Project.all().filter('slug =', slug).fetch(1)[0]

        user = users.get_current_user()

        if project.user == user or users.is_current_user_admin():
            owner = True
        else:
            self.render_403()
            return

        context = {
            'project': project,
            'owner': owner,
        }
        # calculate the template path
        output = self.render("project_settings.html", context)
        self.response.out.write(output)

    def post(self, slug):

        # if we don't have a user then throw
        # an unauthorised error
        user = users.get_current_user()
        if not user:
            self.render_403()
            return

        user = users.get_current_user()            

        project = Project.all().filter('slug =', slug).fetch(1)[0]

        if project.user == user:
            try:
                other_users = self.request.get("other_users")
                if other_users:
                    list_of_users = other_users.split(" ")
                    project.other_users = list_of_users
                else:
                    project.other_users = []
                    
                if self.request.get("url"):
                    project.url = self.request.get("url")                
                else:
                    project.url = None
                project.put()
                logging.info("project modified: %s" % project.name)
            except db.BadValueError, e:
                logging.error("error modifiying project: %s" % e)

        self.redirect('/projects/%s/settings/' % project.slug)

class IssueHandler(BaseRequest):
    def get(self, project_slug, issue_slug):
        if self.request.path[-1] != "/":
            self.redirect("%s/" % self.request.path, True)
            return
            
        user = users.get_current_user()
        
        output = None
        if not user:
            output = get_cache("/%s/%s/" % (project_slug, issue_slug))
                    
        if output is None:
            issue = Issue.all().filter('internal_url =', "/%s/%s/" % (project_slug, issue_slug)).fetch(1)[0]
            issues = Issue.all().filter('project =', issue.project).filter('name !=', issue.name).filter('fixed =', False).order('-created_date').fetch(10)
            if issue.project.user == user or users.is_current_user_admin() or user.email() in issue.project.other_users:
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

        if not user:
            memcache.add("/%s/%s/" % (project_slug, issue_slug), output, 60)   

        self.response.out.write(output)
    
    def post(self, project_slug, issue_slug):
        
        # if we don't have a user then throw
        # an unauthorised error
        user = users.get_current_user()
        if not user:
            self.render_403()
            return
        
        issue = Issue.all().filter('internal_url =', "/%s/%s/" % (project_slug, issue_slug)).fetch(1)[0]
        
        user = users.get_current_user()
        
        if issue.project.user == user:
        
            try:
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
                logging.info("issue edited: %s in %s" % (issue.name, issue.project.name))
                
            except Exception, e:
                logging("error editing issue: %s" % e)

        self.redirect("/projects%s" % issue.internal_url)

class IssueJsonHandler(BaseRequest):
    def get(self, project_slug, issue_slug):

        output = get_cache("/%s/%s.json" % (project_slug, issue_slug))

        if output is None:
            issue = Issue.all().filter('internal_url =', "/%s/%s/" % (project_slug, issue_slug)).fetch(1)[0]

            if issue.fixed: 
                status = "Fixed"
            else:
                status = "Open"

            json = {
                'date': str(datetime.now())[0:19],
                'name': issue.name,
                'project': issue.project.name,
                'project_url': "%s/projects/%s" % (settings.SYSTEM_URL, issue.project.slug),
                'internal_url': "%s/projects/%s/" % (settings.SYSTEM_URL, issue.internal_url),
                'created_date': str(issue.created_date)[0:19],
                'description': issue.html,
                'status': status,
                'identifier': "#gitbug%s" % issue.identifier,
            }
            if issue.fixed and issue.fixed_description:
                json['fixed_description'] = issue.fixed_description

            output = simplejson.dumps(json)

            memcache.add("/%s/%s.json" % (project_slug, issue_slug), output, 3600)   
        self.response.headers["Content-Type"] = "application/javascript; charset=utf8"
        self.response.out.write(output)
        
class IssueDeleteHandler(BaseRequest):
    def get(self, project_slug, issue_slug):
        
        if self.request.path[-1] != "/":
            self.redirect("%s/" % self.request.path, True)
            return
        
        # if we don't have a user then throw
        # an unauthorised error
        user = users.get_current_user()
        if not user:
            self.render_403()
            return
            
        issue = Issue.all().filter('internal_url =', "/%s/%s/" % (project_slug, issue_slug)).fetch(1)[0]        
            
        if issue.project.user == user or users.is_current_user_admin():
            context = {
                'issue': issue,
                'owner': True,
            }
            output = self.render("issue_delete.html", context)
            self.response.out.write(output)
        else:
            self.render_403()
            return

    def post(self, project_slug, issue_slug):
        
        # if we don't have a user then throw
        # an unauthorised error
        user = users.get_current_user()
        if not user:
            self.render_403()
            return

        issue = Issue.all().filter('internal_url =', "/%s/%s/" % (project_slug, issue_slug)).fetch(1)[0]        

        user = users.get_current_user()
        if issue.project.user == user:
            try:
                logging.info("deleted issue: %s in %s" % (issue.name, issue.project.name))
                issue.delete()
            except Exception, e:
                logging.error("error deleting issue: %s" % e)
            self.redirect("/projects/%s" % issue.project.slug)
        else:
            self.render_403()
            return

class ProjectsHandler(BaseRequest):
    def get(self):
        if self.request.path[-1] != "/":
            self.redirect("%s/" % self.request.path, True)
            return
        
        user = users.get_current_user()
        output = None
        if not user:
            output = get_cache("projects")
        if output is None:
            projects = Project.all().order('-created_date').fetch(50)
            context = {
                'projects': projects,
            }
            # calculate the template path
            output = self.render("projects.html", context)
            if not user:
                memcache.add("projects", output, 3600)
        self.response.out.write(output)

    def post(self):
        
        # if we don't have a user then throw
        # an unauthorised error
        user = users.get_current_user()
        if not user:
            self.render_403()
            return
        
        name = self.request.get("name")
        if Project.all().filter('name =', name).count() == 0:
            try:
                project = Project(
                    name=name,
                    user=users.get_current_user(),       
                )
                project.put()
                logging.info("project added: %s" % project.name)
            except db.BadValueError, e:
                logging.error("error adding project: %s" % e)
        self.redirect('/')
        
class ProjectsJsonHandler(BaseRequest):
        def get(self):
            output = get_cache("projects_json")
            if output is None:
                projects = Project.all().order('-created_date').fetch(50)
                projects_data = {}

                for project in projects:
                    data = {
                        'internal_url': "%s/projects/%s/" % (settings.SYSTEM_URL, project.slug),
                        'created_date': str(project.created_date)[0:19],
                        'open_issues': project.open_issues.count(),
                        'closed_issues': project.closed_issues.count(),
                    }
                    if project.url:
                        data['external_url'] = project.url
                    projects_data[project.name] = data

                json = {
                    'date': str(datetime.now())[0:19],
                    'projects': projects_data,
                }

                output = simplejson.dumps(json)            
                memcache.add("projects_json", output, 3600)
            self.response.headers["Content-Type"] = "application/javascript; charset=utf8"
            self.response.out.write(output)

class ProjectsRssHandler(BaseRequest):
        def get(self):
            output = get_cache("projects_rss")
            if output is None:
                
                projects = Project.all().order('-created_date').fetch(20)
                rss = RSS2(
                    title="GitBug projects",
                    link="%s" % settings.SYSTEM_URL,
                    description="A list of the latest 20 projects on GitBug",
                    lastBuildDate=datetime.now()
                )

                for project in projects:
                    rss.items.append(
                        RSSItem(
                            title=project.name,
                            link="%s/projects/%s/" % (settings.SYSTEM_URL, project.slug),
                            description="",
                            pubDate=project.created_date
                        ))

                output = rss.to_xml()

                memcache.add("projects_rss", output, 3600)
            self.response.headers["Content-Type"] = "application/rss+xml; charset=utf8"
            self.response.out.write(output)

class WebHookHandler(BaseRequest):
    def post(self, slug):
        project = Project.all().filter('slug =', slug).fetch(1)[0]
        
        key = self.request.get("key")
        
        if key == project.__key__: 
            try:
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
                        logging.info("issue updated via webhook: %s in %s" % (issue.name, issue.project.name))
            except Exception, e:
                logging.error("webhook error: %s" % e)
        else:
            logging.info("webhook incorrect key provided: %s" % project.name)
            
        self.response.out.write("")

class NotFoundPageHandler(BaseRequest):
    def get(self):
        self.error(404)
        user = users.get_current_user()
        output = None
        if not user:
            output = get_cache("error404")
        if output is None:        
            output = self.render("404.html")
            if not user:
                memcache.add("error404", output, 3600)
        self.response.out.write(output)
        
class FaqPageHandler(BaseRequest):
    def get(self):
        if self.request.path[-1] != "/":
            self.redirect("%s/" % self.request.path, True)
            return
            
        user = users.get_current_user()
        output = None
        if not user:
            output = get_cache("faq")
        if output is None:        
            output = self.render("faq.html")
            if not user:
                memcache.add("faq", output, 3600)
        self.response.out.write(output)
                        
def main():
    "Run the application"
    # wire up the views
    ROUTES = [
        ('/', Index),
        ('/projects.json$', ProjectsJsonHandler),
        ('/projects.rss$', ProjectsRssHandler),
        ('/projects/?$', ProjectsHandler),
        ('/projects/([A-Za-z0-9-]+)/hook/?$', WebHookHandler),
        ('/projects/([A-Za-z0-9-]+)/delete/?$', ProjectDeleteHandler),
        ('/projects/([A-Za-z0-9-]+)/settings/?$', ProjectSettingsHandler),
        ('/projects/([A-Za-z0-9-]+)/([A-Za-z0-9-]+).json$', IssueJsonHandler),
        ('/projects/([A-Za-z0-9-]+)/([A-Za-z0-9-]+)/?$', IssueHandler),
        ('/projects/([A-Za-z0-9-]+)/([A-Za-z0-9-]+)/delete/?$', IssueDeleteHandler),
        ('/projects/([A-Za-z0-9-]+).json$', ProjectJsonHandler),
        ('/projects/([A-Za-z0-9-]+).rss$', ProjectRssHandler),
        ('/projects/([A-Za-z0-9-]+)/?$', ProjectHandler),
        ('/faq/?$', FaqPageHandler),
        ('/.*', NotFoundPageHandler),
    ]
    application = webapp.WSGIApplication(ROUTES, debug=settings.DEBUG)
    run_wsgi_app(application)

if __name__ == '__main__':
    main()