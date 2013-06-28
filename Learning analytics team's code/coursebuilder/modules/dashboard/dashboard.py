# Copyright 2012 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Classes and methods to create and manage Courses."""

__author__ = 'Pavel Simakov (psimakov@google.com)'

#################################################################################
## ***************************Code modified by: ********************************
## *** Roderick FANOU (roderick.fanou@gmail.com / 100307524@alumnos.uc3m.es ) ***
## *********** Miriam Marciel (miriam.marciel@imdea.org) **************************
## ************** Omar ALHY  (100298296@alumnos.uc3m.es) ************************
## *work done as part of the class "Platforms for network communities" 2012-2013
## ************** University: "Universidad Carlos III de Madrid" *****************
#################################################################################

import copy
import logging
import os
import pickle
import sys
import math
from tools import verify
import yaml
from models import progress
from models import transforms
from models import vfs
import cgi
import datetime
import os
import urllib
from controllers import sites
from controllers.utils import ApplicationHandler
from controllers.utils import ReflectiveRequestHandler
import jinja2
from models import config
from models import courses
from models.courses import Course
from models import jobs
from models import roles
from models import transforms
from models import vfs
from models.models import Student
from models.models import StudentAnswersEntity
from models.models import StudentPropertyEntity
from models.models import YouTubeEvent
import filer
from filer import AssetItemRESTHandler
from filer import AssetUriRESTHandler
from filer import FileManagerAndEditor
from filer import FilesItemRESTHandler
import messages
import unit_lesson_editor
from unit_lesson_editor import AssessmentRESTHandler
from unit_lesson_editor import ImportCourseRESTHandler
from unit_lesson_editor import LessonRESTHandler
from unit_lesson_editor import LinkRESTHandler
from unit_lesson_editor import UnitLessonEditor
from unit_lesson_editor import UnitLessonTitleRESTHandler
from unit_lesson_editor import UnitRESTHandler
from google.appengine.api import users
from google.appengine.ext import db


class DashboardHandler(
    FileManagerAndEditor, UnitLessonEditor, ApplicationHandler,
    ReflectiveRequestHandler):
    """Handles all pages and actions required for managing a course."""

    default_action = 'outline'
    get_actions = [
        default_action, 'assets', 'settings', 'students',
        'edit_settings', 'edit_unit_lesson', 'edit_unit', 'edit_link',
        'edit_lesson', 'edit_assessment', 'add_asset', 'delete_asset',
        'import_course']
    post_actions = [
        'compute_student_stats', 'create_or_edit_settings', 'add_unit',
        'add_link', 'add_assessment', 'add_lesson']

    @classmethod
    def get_child_routes(cls):
        """Add child handlers for REST."""
        return [
            (AssessmentRESTHandler.URI, AssessmentRESTHandler),
            (AssetItemRESTHandler.URI, AssetItemRESTHandler),
            (FilesItemRESTHandler.URI, FilesItemRESTHandler),
            (AssetItemRESTHandler.URI, AssetItemRESTHandler),
            (AssetUriRESTHandler.URI, AssetUriRESTHandler),
            (ImportCourseRESTHandler.URI, ImportCourseRESTHandler),
            (LessonRESTHandler.URI, LessonRESTHandler),
            (LinkRESTHandler.URI, LinkRESTHandler),
            (UnitLessonTitleRESTHandler.URI, UnitLessonTitleRESTHandler),
            (UnitRESTHandler.URI, UnitRESTHandler)
        ]

    def can_view(self):
        """Checks if current user has viewing rights."""
        return roles.Roles.is_course_admin(self.app_context)

    def can_edit(self):
        """Checks if current user has editing rights."""
        return roles.Roles.is_course_admin(self.app_context)

    def get(self):
        """Enforces rights to all GET operations."""
        if not self.can_view():
            self.redirect(self.app_context.get_slug())
            return
        # Force reload of properties. It is expensive, but admin deserves it!
        config.Registry.get_overrides(force_update=True)
        return super(DashboardHandler, self).get()

    def post(self):
        """Enforces rights to all POST operations."""
        if not self.can_edit():
            self.redirect(self.app_context.get_slug())
            return
        return super(DashboardHandler, self).post()

    def get_template(self, template_name, dirs):
        """Sets up an environment and Gets jinja template."""
        jinja_environment = jinja2.Environment(
            autoescape=True,
            loader=jinja2.FileSystemLoader(dirs + [os.path.dirname(__file__)]))
        return jinja_environment.get_template(template_name)

    def _get_alerts(self):
        alerts = []
        if not courses.is_editable_fs(self.app_context):
            alerts.append('Read-only course.')
        if not self.app_context.now_available:
            alerts.append('The course is not publicly available.')
        return '\n'.join(alerts)

    def _get_top_nav(self):
        current_action = self.request.get('action')
        nav_mappings = [
            ('', 'Outline'),
            ('assets', 'Assets'),
            ('settings', 'Settings'),
            ('students', 'Students')]
        nav = []
        for action, title in nav_mappings:
            class_attr = 'class="selected"' if action == current_action else ''
            nav.append(
                '<a href="dashboard?action=%s" %s>%s</a>' % (
                    action, class_attr, title))

        if roles.Roles.is_super_admin():
            nav.append('<a href="/admin">Admin</a>')

        nav.append(
            '<a href="https://code.google.com/p/course-builder/wiki/Dashboard"'
            ' target="_blank">'
            'Help</a>')

        return '\n'.join(nav)

    def render_page(self, template_values):
        """Renders a page using provided template values."""

        template_values['top_nav'] = self._get_top_nav()
        template_values['gcb_course_base'] = self.get_base_href(self)
        template_values['user_nav'] = '%s | <a href="%s">Logout</a>' % (
            users.get_current_user().email(),
            users.create_logout_url(self.request.uri)
        )
        template_values[
            'page_footer'] = 'Created on: %s' % datetime.datetime.now()

        if not template_values.get('sections'):
            template_values['sections'] = []

        self.response.write(
            self.get_template('view.html', []).render(template_values))

    def format_title(self, text):
        """Formats standard title."""
        title = self.app_context.get_environ()['course']['title']
        return ('Course Builder &gt; %s &gt; Dashboard &gt; %s' %
                (cgi.escape(title), text))

    def _get_edit_link(self, url):
        return '&nbsp;<a href="%s">Edit</a>' % url

    def _get_availability(self, resource):
        if not hasattr(resource, 'now_available'):
            return ''
        if resource.now_available:
            return ''
        else:
            return ' <span class="draft-label">(%s)</span>' % (
                unit_lesson_editor.DRAFT_TEXT)

    def render_course_outline_to_html(self):
        """Renders course outline to HTML."""
        course = courses.Course(self)
        if not course.get_units():
            return []

        is_editable = filer.is_editable_fs(self.app_context)

        lines = []
        lines.append('<ul style="list-style: none;">')
        for unit in course.get_units():
            if unit.type == 'A':
                lines.append('<li>')
                lines.append(
                    '<strong><a href="assessment?name=%s">%s</a></strong>' % (
                        unit.unit_id, cgi.escape(unit.title)))
                lines.append(self._get_availability(unit))
                if is_editable:
                    url = self.canonicalize_url(
                        '/dashboard?%s') % urllib.urlencode({
                            'action': 'edit_assessment',
                            'key': unit.unit_id})
                    lines.append(self._get_edit_link(url))
                lines.append('</li>\n')
                continue

            if unit.type == 'O':
                lines.append('<li>')
                lines.append(
                    '<strong><a href="%s">%s</a></strong>' % (
                        unit.href, cgi.escape(unit.title)))
                lines.append(self._get_availability(unit))
                if is_editable:
                    url = self.canonicalize_url(
                        '/dashboard?%s') % urllib.urlencode({
                            'action': 'edit_link',
                            'key': unit.unit_id})
                    lines.append(self._get_edit_link(url))
                lines.append('</li>\n')
                continue

            if unit.type == 'U':
                lines.append('<li>')
                lines.append(
                    ('<strong><a href="unit?unit=%s">Unit %s - %s</a>'
                     '</strong>') % (
                         unit.unit_id, unit.index, cgi.escape(unit.title)))
                lines.append(self._get_availability(unit))
                if is_editable:
                    url = self.canonicalize_url(
                        '/dashboard?%s') % urllib.urlencode({
                            'action': 'edit_unit',
                            'key': unit.unit_id})
                    lines.append(self._get_edit_link(url))

                lines.append('<ol>')
                for lesson in course.get_lessons(unit.unit_id):
                    lines.append(
                        '<li><a href="unit?unit=%s&lesson=%s">%s</a>\n' % (
                            unit.unit_id, lesson.lesson_id,
                            cgi.escape(lesson.title)))
                    lines.append(self._get_availability(lesson))
                    if is_editable:
                        url = self.get_action_url(
                            'edit_lesson', key=lesson.lesson_id)
                        lines.append(self._get_edit_link(url))
                    lines.append('</li>')
                lines.append('</ol>')
                lines.append('</li>\n')
                continue

            raise Exception('Unknown unit type: %s.' % unit.type)

        lines.append('</ul>')
        return ''.join(lines)

    def get_outline(self):
        """Renders course outline view."""

        pages_info = [
            '<a href="%s">Announcements</a>' % self.canonicalize_url(
                '/announcements'),
            '<a href="%s">Course</a>' % self.canonicalize_url('/course')]

        outline_actions = []
        if filer.is_editable_fs(self.app_context):
            outline_actions.append({
                'id': 'edit_unit_lesson',
                'caption': 'Organize',
                'href': self.get_action_url('edit_unit_lesson')})
            outline_actions.append({
                'id': 'add_lesson',
                'caption': 'Add Lesson',
                'action': self.get_action_url('add_lesson'),
                'xsrf_token': self.create_xsrf_token('add_lesson')})
            outline_actions.append({
                'id': 'add_unit',
                'caption': 'Add Unit',
                'action': self.get_action_url('add_unit'),
                'xsrf_token': self.create_xsrf_token('add_unit')})
            outline_actions.append({
                'id': 'add_link',
                'caption': 'Add Link',
                'action': self.get_action_url('add_link'),
                'xsrf_token': self.create_xsrf_token('add_link')})
            outline_actions.append({
                'id': 'add_assessment',
                'caption': 'Add Assessment',
                'action': self.get_action_url('add_assessment'),
                'xsrf_token': self.create_xsrf_token('add_assessment')})
            outline_actions.append({
                'id': 'import_course',
                'caption': 'Import',
                'href': self.get_action_url('import_course')
                })

        data_info = self.list_files('/data/')

        sections = [
            {
                'title': 'Pages',
                'description': messages.PAGES_DESCRIPTION,
                'children': pages_info},
            {
                'title': 'Course Outline',
                'description': messages.COURSE_OUTLINE_DESCRIPTION,
                'actions': outline_actions,
                'pre': self.render_course_outline_to_html()},
            {
                'title': 'Data Files',
                'description': messages.DATA_FILES_DESCRIPTION,
                'children': data_info}]

        template_values = {}
        template_values['page_title'] = self.format_title('Outline')
        template_values['alerts'] = self._get_alerts()
        template_values['sections'] = sections
        self.render_page(template_values)

    def get_action_url(self, action, key=None, extra_args=None):
        args = {'action': action}
        if key:
            args['key'] = key
        if extra_args:
            args.update(extra_args)
        url = '/dashboard?%s' % urllib.urlencode(args)
        return self.canonicalize_url(url)

    def get_settings(self):
        """Renders course settings view."""

        yaml_actions = []

        # Basic course info.
        course_info = [
            ('Course Title', self.app_context.get_environ()['course']['title']),
            ('Context Path', self.app_context.get_slug()),
            ('Datastore Namespace', self.app_context.get_namespace_name())]

        # Course file system.
        fs = self.app_context.fs.impl
        course_info.append(('File system', fs.__class__.__name__))
        if fs.__class__ == vfs.LocalReadOnlyFileSystem:
            course_info.append(('Home folder', sites.abspath(
                self.app_context.get_home_folder(), '/')))

        # Enable editing if supported.
        if filer.is_editable_fs(self.app_context):
            yaml_actions.append({
                'id': 'edit_course_yaml',
                'caption': 'Edit',
                'action': self.get_action_url('create_or_edit_settings'),
                'xsrf_token': self.create_xsrf_token(
                    'create_or_edit_settings')})

        # Yaml file content.
        yaml_info = []
        yaml_stream = self.app_context.fs.open(
            self.app_context.get_config_filename())
        if yaml_stream:
            yaml_lines = yaml_stream.read().decode('utf-8')
            for line in yaml_lines.split('\n'):
                yaml_info.append(line)
        else:
            yaml_info.append('< empty file >')

        # Prepare template values.
        template_values = {}
        template_values['page_title'] = self.format_title('Settings')
        template_values['page_description'] = messages.SETTINGS_DESCRIPTION
        template_values['sections'] = [
            {
                'title': 'About the Course',
                'description': messages.ABOUT_THE_COURSE_DESCRIPTION,
                'children': course_info},
            {
                'title': 'Contents of course.yaml file',
                'description': messages.CONTENTS_OF_THE_COURSE_DESCRIPTION,
                'actions': yaml_actions,
                'children': yaml_info}]

        self.render_page(template_values)

    def list_files(self, subfolder):
        """Makes a list of files in a subfolder."""
        home = sites.abspath(self.app_context.get_home_folder(), '/')
        files = self.app_context.fs.list(
            sites.abspath(self.app_context.get_home_folder(), subfolder))
        result = []
        for abs_filename in sorted(files):
            filename = os.path.relpath(abs_filename, home)
            result.append(vfs.AbstractFileSystem.normpath(filename))
        return result

    def list_and_format_file_list(
        self, title, subfolder,
        links=False, upload=False, prefix=None, caption_if_empty='< none >',
        edit_url_template=None, sub_title=None):
        """Walks files in folders and renders their names in a section."""

        lines = []
        count = 0
        for filename in self.list_files(subfolder):
            if prefix and not filename.startswith(prefix):
                continue
            if links:
                lines.append(
                    '<li><a href="%s">%s</a>' % (
                        urllib.quote(filename), cgi.escape(filename)))
                if edit_url_template:
                    edit_url = edit_url_template % urllib.quote(filename)
                    lines.append('&nbsp;<a href="%s">[Edit]</a>' % edit_url)
                lines.append('</li>\n')
            else:
                lines.append('<li>%s</li>\n' % cgi.escape(filename))
            count += 1

        output = []

        if filer.is_editable_fs(self.app_context) and upload:
            output.append(
                '<a class="gcb-button pull-right" href="dashboard?%s">'
                'Upload</a>' % urllib.urlencode(
                    {'action': 'add_asset', 'base': subfolder}))
            output.append('<div style=\"clear: both; padding-top: 2px;\" />')
        if title:
            output.append('<h3>%s' % cgi.escape(title))
            if count:
                output.append(' (%s)' % count)
            output.append('</h3>')
        if sub_title:
            output.append('<blockquote>%s</blockquote>' % cgi.escape(sub_title))
        if lines:
            output.append('<ol>')
            output += lines
            output.append('</ol>')
        else:
            if caption_if_empty:
                output.append(
                    '<blockquote>%s</blockquote>' % cgi.escape(
                        caption_if_empty))
        return output

    def get_assets(self):
        """Renders course assets view."""

        def inherits_from(folder):
            return '< inherited from %s >' % folder

        lines = []
        lines += self.list_and_format_file_list(
            'Assessments', '/assets/js/', links=True,
            prefix='assets/js/assessment-')
        lines += self.list_and_format_file_list(
            'Activities', '/assets/js/', links=True,
            prefix='assets/js/activity-')
        lines += self.list_and_format_file_list(
            'Images & Documents', '/assets/img/', links=True, upload=True,
            edit_url_template='dashboard?action=delete_asset&uri=%s',
            sub_title='< inherited from /assets/img/ >', caption_if_empty=None)
        lines += self.list_and_format_file_list(
            'Cascading Style Sheets', '/assets/css/', links=True,
            caption_if_empty=inherits_from('/assets/css/'))
        lines += self.list_and_format_file_list(
            'JavaScript Libraries', '/assets/lib/', links=True,
            caption_if_empty=inherits_from('/assets/lib/'))
        lines += self.list_and_format_file_list(
            'View Templates', '/views/',
            caption_if_empty=inherits_from('/views/'))
        lines = ''.join(lines)

        template_values = {}
        template_values['page_title'] = self.format_title('Assets')
        template_values['page_description'] = messages.ASSETS_DESCRIPTION
        template_values['main_content'] = lines
        self.render_page(template_values)

    def get_students(self):
        """Renders course students view."""

        template_values = {}
        template_values['page_title'] = self.format_title('Students')

        details = """
            <h3>Enrollment Statistics</h3>
            <ul><li>pending</li></ul>
            <h3>Assessment Statistics</h3>
            <ul><li>pending</li></ul>
            """

        update_message = ''
        update_action = """
            <form
                id='gcb-compute-student-stats'
                action='dashboard?action=compute_student_stats'
                method='POST'>
                <input type="hidden" name="xsrf_token" value="%s">
                <p>
                    <button class="gcb-button" type="submit">
                        Re-Calculate Now
                    </button>
                </p>
            </form>
        """ % self.create_xsrf_token('compute_student_stats')

        job = ComputeStudentStats(self.app_context).load()
        if not job:
            update_message = """
                Student statistics have not been calculated yet."""
        else:
            if job.status_code == jobs.STATUS_CODE_COMPLETED:
                stats = transforms.loads(job.output)
                enrolled = stats['enrollment']['enrolled']
                unenrolled = stats['enrollment']['unenrolled']

                enrollment = []
                enrollment.append(
                    '<li>previously enrolled: %s</li>' % unenrolled)
                enrollment.append(
                    '<li>currently enrolled: %s</li>' % enrolled)
                enrollment.append(
                    '<li>total students: %s</li>' % (unenrolled + enrolled))
                enrollment = ''.join(enrollment)

                assessment = []
                total = 0
                for key, value in stats['scores'].items():
                    total += value[0]
                    avg_score = 0
                    if value[0]:
                        avg_score = round(value[1] / value[0], 1)
                    assessment.append("""
                        <li>%s: completed %s, average score %s
                        """ % (key, value[0], avg_score))
                assessment.append('<li>total assessments: %s</li>' % total)
                assessment = ''.join(assessment)

                details = """
                    <h3>Enrollment Statistics</h3>
                    <ul>%s</ul>
                    <h3>Assessment Statistics</h3>
                    <ul>%s</ul>
                    """ % (enrollment, assessment)

##########################################################################################
################### Roderick FANOU's CODE STARTING POINT #################################
######### Role: Assessment visualisations + Recommandations ##############################
######  Enhancements :                                                             #######
######          - Table showing the percentage of good answers per questions       #######
#######           and the mean of attempts before success                          #######
#######         - Pie charts for each assessment with the percentages of good      #######
#######           and bad attempts                                                 #######
#######         - Histograms with the number of students enrolled, the number of   #######
#######           students having succeed and fail for a given assessment and the  #######
#######           number of students having get more than 75 out of 100.           #######
#######         - Recommendations to improve the results obtained by the students  #######
##########################################################################################  

#REMARK : This part continues at line 1053 till the end
                
                plotcomputation = PlotTreatment() ## This function enables the generalization                 
                answerscomputation = AnswersTreatment()
                course = courses.Course(self)
		data_assess=list(answerscomputation.get_assessments(course))
                details += plotcomputation.plot(data_assess, stats)


##########################################################################################
################### Miriam MARCIEL's CODE STARTING POINT #################################
######### Role: YouTubeEvents() entity design + Plot showing the number of   #############
#######          students having started and/or ended each video             #############
##########################################################################################  
              

                details +=  """
                            <div style="height:20px;"></div>
                            <ul></ul>
			    <h3>Youtube Videos Statistics</h3>
			    <ul></ul><ul></ul>
                            """
                
                data_lessons=answerscomputation.count_students(course)
		details+="""
                    <script type='text/javascript'>//<![CDATA[ 

                    $(function () {
                    $('#container_youtube').highcharts({
                    chart: {
                        type: 'bar'
                    },
                    title: {
                        text: 'Students starting and ending a video lesson'
                    },
                    subtitle: {
                        text: 'Measuring the engagement of students in the course'
                    },
                    xAxis: {
                        categories: ["""
                i=0
                for lesson in data_lessons:
                	details+="'Unit "+str(lesson['unit_id'])+" Lesson "+str(lesson['lesson_id'])+"'"
                	if i==len(data_lessons)-1:
	  			details+="],"
	  		else:
	  			details+=","
	  		i=i+1
                details+="""title: {
                            text: null
                        }
                    },
                    yAxis: {
                        min: 0,
                        title: {
                            text: 'Number of students',
                            align: 'high'
                        },
                        labels: {
                            overflow: 'justify'
                        }
                    },
                    tooltip: {
                        valueSuffix: ' '
                    },
                    plotOptions: {
                        bar: {
                            dataLabels: {
                                enabled: true
                            }
                        }
                    },
                    legend: {
                        layout: 'vertical',
                        align: 'right',
                        verticalAlign: 'top',
                        x: -100,
                        y: 100,
                        floating: true,
                        borderWidth: 1,
                        backgroundColor: '#FFFFFF',
                        shadow: true
                    },
                    credits: {
                        enabled: false
                    },
                    series: [{
                        name: 'Number of students ending the video',
                        data: [
                        """
                i=0
              	for lesson in data_lessons:
                	details+=str(lesson['ended_count'])
                	if i==len(data_lessons)-1:
	  			details+="]"
	  		else:
	  			details+=","
	  		i=i+1
                details+="""
                    }, {
                        name: 'Number of students starting the video',
                        data: ["""
                i=0
                for lesson in data_lessons:
                	details+=str(lesson['started_count'])
                	if i==len(data_lessons)-1:
	  			details+="]"
	  		else:
	  			details+=","
	  		i=i+1
	  	details+="""
                            }]
                        });
                    });
                    
                //]]>  
                </script>"""
		height_chart=50*len(data_lessons)
		details+='<div id="container_youtube" style="min-width: 400px; height: '+str(height_chart)+'px; margin: 0 auto"></div>'

#***************************************************************************************************************
#*******************************************                         *******************************************							
#******************************************* OMAR'S CODE STARTS HERE *******************************************
#*******************************************                         *******************************************
#***************************************************************************************************************
                numOfevents = 0
                numOfvideos = 0
                numOfstudents=0
                numOfevents2= 0
                ForwardCount= 0
                RewindCount= 0
                PauseCount= 0
                students= []
                studentNumber=[]  # ********** LIST WITH ALL THE STUDENTS
                videosWatched = [] # ********* LIST WITH ALL THE VIDEOS
                videoNumber = []
                timeList=[]
                timeListForward= [] # forward events intervals list
                timeListRewind= [] # rewind events intervals list
                timeListPause= [] # pause events intervals list
                Youtubecomputation = YoutubeVideosTreatment()
                nothing = 0
                chart_div = []
                i = 0
                j=0
                k=1
                num=0
                timeForward= []
                timeRewind= []
                timePause= [] 
                list1=[]
                list2=[]
                list3=[]

                query5 = db.GqlQuery('SELECT * FROM %s' %YouTubeEvent().__class__.__name__, batch_size=10000)
				
#********************************** TO KNOW THE STUDENTS THAT WE HAVE IN THE DATASTORE 	
	
                for typeinfo in query5.run():
                    if numOfstudents == 0:
                        students = query5.get(offset= numOfstudents).user_id
                        studentNumber.append(students)
                        numOfstudents= numOfstudents+1
                    elif (query5.get(offset= numOfstudents).user_id== students):
                        numOfstudents=numOfstudents+1
                    else:
                        students= query5.get(offset= numOfstudents).user_id
                        if students in studentNumber:
                            numOfstudents=numOfstudents+1
                        else:
                            studentNumber.append(students)
                            numOfstudents= numOfstudents+1

					
#****************************************************************************************

                    


 #***********TO KNOW THE VIDEOS THAT WE HAVE IN THE DATASTORE AND GIVE CHART ID FOR EACH VIDEO
				
                for typeinfo in query5.run():
                    if numOfvideos == 0:
                        videoNumber = query5.get(offset = numOfvideos).video
                        videosWatched.append(videoNumber)
                        numOfvideos= numOfvideos+1
                        chart_div.append(numOfvideos)
                    elif (query5.get(offset= numOfvideos).video == videoNumber):
                        numOfvideos= numOfvideos+1
                    else:
                        videoNumber = query5.get(offset = numOfvideos).video
                        if videoNumber in videosWatched:
                            numOfvideos=numOfvideos+1
                        else:
                            videosWatched.append(videoNumber)
                            numOfvideos= numOfvideos+1
                            chart_div.append(numOfvideos)
							
           
                  
                
#************************************************************************************************
                
				
#***************************PLOT THE BEHAVIOUR OF EACH STUDENT TO EACH GIVEN VIDEO (THE EVENTS GENERATED BY EACH STUDENT)
						 
                for number in videosWatched:                    
                    details += """<script type="text/javascript" src="https://www.google.com/jsapi"></script>
    <script type="text/javascript">
    
      google.load("visualization", "1", {packages:["corechart"]});
      google.setOnLoadCallback(drawChart);
      function drawChart() {
        var data= google.visualization.arrayToDataTable([
          ['Time','Forward Events','Rewind Events','Pause Events'],
                           """
                    
                    for typeinfo in query5.run():
                        videoLesson = query5.get(offset=numOfevents).video
                        

                        
                        if (videoLesson == videosWatched[i]):
                            eventType= query5.get(offset=numOfevents).event
                            eventInfo= query5.get(offset= numOfevents).info
                            eventStudent = query5.get(offset=numOfevents).user_id
                            studentID= studentNumber.index(eventStudent) + 1                           
                            if eventType == "forward":
                                timeForward = float(eventInfo[14:20])
                                details += """[ %s,      %s,null,null], """ %( timeForward,studentID)
                                numOfevents= numOfevents+1
                                ForwardCount=ForwardCount+1
                                timeList.append(timeForward)
                            elif eventType == "rewind": 
                                timeRewind= float(eventInfo[14:19])
                                details += """[ %s,   null,   %s,null], """ %( timeRewind,studentID )
                                numOfevents= numOfevents+1
                                RewindCount=RewindCount+1
                                timeList.append(timeRewind)
                            elif eventType == "pause":
                                timePause = float(eventInfo[9:13])
                                details += """[ %s,   null,null,   %s], """ %( timePause,studentID)
                                numOfevents= numOfevents+1
                                PauseCount=PauseCount+1
                                timeList.append(timePause)
                            else:
                                nothing = nothing +1
                                numOfevents= numOfevents+1
                        else:
                            numOfevents= numOfevents+1 
                    videoLength= max(timeList)
                             							
                    details += """ ]);            
                    var options = { """
                    details += """title: 'Students Behaviour in Lesson %s', """ %(videosWatched[i])
                    details += """hAxis: {title: 'Time in Seconds' , minValue: 0, maxValue: 15}, """
                    details += """vAxis: {title: "Students ID's "} , minValue:0,minValue:%s, gridlines: {color:'gray', count: %s}}; """ %(len(studentNumber),len(studentNumber))                                       
                    details += """var chart = new google.visualization.ScatterChart(document.getElementById('%s')); """  %(chart_div[i])
                    details += """chart.draw(data, options);
					} </script>"""
                    details+= """
                 <center><div id="%s" style="width: 1000px; height: 700px;"></div></center> """ %(chart_div[i])

                    ForwardCount=0
                    RewindCount=0
                    PauseCount = 0
                    Intervals, rem = divmod(videoLength,30)
                    Intervals= Intervals+1
                    timeListForward= [0]*int(Intervals)
                    timeListRewind= [0]*int(Intervals)
                    timeListPause= [0]*int(Intervals)


				 
                    details += """ <script type="text/javascript" src="https://www.google.com/jsapi"></script>
    <script type="text/javascript">
					google.load("visualization", "1", {packages:["corechart"]});
      google.setOnLoadCallback(drawChart);
      function drawChart() {
        var data2 = google.visualization.arrayToDataTable([['time','Forward Events', 'Rewind Events', 'Pause Events'],"""						
		                  								  				                 				 
                    for typeinfo in query5.run():
                        videoLesson = query5.get(offset=numOfevents2).video
                        eventType= query5.get(offset=numOfevents2).event
                        eventInfo= query5.get(offset= numOfevents2).info
                        if (videoLesson == videosWatched[i]):
                            if eventType == "forward":
                                timeForward = float(eventInfo[14:19])
                                if (timeForward < 30):
                                    timeListForward[0] +=1
                                else:                              	                               
                                    timeForward1, rem= divmod(float(eventInfo[14:19]),30)
                                   # timeForward1+=1
                                    timeListForward[int(timeForward1)]+=1
                                numOfevents2= numOfevents2+1
                            elif eventType == "rewind": 
                                timeRewind= float(eventInfo[14:19])
                                if (timeRewind < 30):
                                   timeListRewind[0] +=1
                                else: # event in any interval
                                    timeRewind1, rem= divmod(float(eventInfo[14:19]), 30)
                                  #  timeRewind1+=1
                                    timeListRewind[int(timeRewind1)]+=1
                                numOfevents2= numOfevents2+1
                            elif eventType == "pause":
                                timePause= float(eventInfo[9:13])
                                if (timePause <30):
                                    timeListPause[0] +=1
                                else:
                                    timePause1, rem = divmod(float(eventInfo[9:13]),30)
                                 #   timePause1+=1
                                    timeListPause[int(timePause1)]+=1
                                numOfevents2= numOfevents2+1
                            else:
                                numOfevents2= numOfevents2+1
                        else:
                            numOfevents2= numOfevents2+1 
                    for number in timeListRewind:
                        details += """  ['%s',%s,%s,%s], """ %(k,timeListForward[k-1],timeListRewind[k-1],timeListPause[k-1])
                        k+=1
					
                    yAxis= max(max(timeListForward), max(timeListRewind),max(timeListPause)) 						
                    #yAxisgrid= yAxis/
                    
                    details+= """ ]);
					
					 
                     
                      var options2 = {title: 'Commulative Students Behaviour in Lesson %s',hAxis:{title: 'Time Intervals of 30 seconds each'},
					   vAxis:{title: 'Event Types', gridlines:{color: 'gray', count:%s},
					  minValue:0 ,maxValue:%s }};"""	%(videosWatched[i], math.floor(yAxis*0.75),yAxis)				
                    details+= """var chart2 = new google.visualization.ColumnChart(document.getElementById('%s'));""" %(chart_div[i]+500)
                    details +=""" chart2.draw(data2, options2);
                       
      }
    </script>
	  """
	
                    details += """<center><div id="%s" style="width: 1100px; height: 850px;"></div></center>""" %(chart_div[i]+500)
                  #  details += """Forward events in each interval:  %s <br>Rewind 
					#events in each interval:  %s <br>Pause events in each interval:  %s """ %(timeListForward,timeListRewind,timeListPause)
                    ForwardEvents= sum(timeListForward)
                    RewindEvents= sum(timeListRewind)
                    PauseEvents= sum(timeListPause)
                    EventSum= ForwardEvents+ RewindEvents
                    if (ForwardEvents > RewindEvents):
                        details+= """<u><b>Recommendations:</b></u> Students have skipped too many parts of this lesson. It's compulsory to review it. """
                    else:
                        details+= """<u><b>Recommendations:</b></u> Students have found this lesson difficult. It's compulsory to review it.  """
                    
              		                     
                        
				 

                    if (i> len(videosWatched)):
                        details += """
                    <br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>"""
                    i=i+1
                    k=1
                    numOfevents= 0
                    numOfevents2= 0
                    ForwardCount= 0
                    RewindCount=0
                    PauseCount=0
                    
#********************************************************************************************************************    


#***************************************************************************************************************
#*******************************************                         *******************************************							
#******************************************* OMAR ALHY'S CODE ENDS HERE   *******************************************
#*******************************************                         *******************************************
#***************************************************************************************************************               
 

                update_message = """
                    Student statistics were last updated on
                    %s in about %s second(s).""" % (
                        job.updated_on, job.execution_time_sec)
            elif job.status_code == jobs.STATUS_CODE_FAILED:
                update_message = """
                    There was an error updating student statistics.
                    Here is the message:<br>
                    <blockquote>
                      <pre>\n%s</pre>
                    </blockquote>
                    """ % cgi.escape(job.output)
            else:
                update_action = ''
                update_message = """
                    Student statistics update started on %s and is running
                    now. Please come back shortly.""" % job.updated_on

        lines = []
        lines.append(details)
        lines.append(update_message)
        lines.append(update_action)
        lines = ''.join(lines)

        template_values['main_content'] = lines
        self.render_page(template_values)

    def post_compute_student_stats(self):
        """Submits a new student statistics calculation task."""
        job = ComputeStudentStats(self.app_context)
        job.submit()
        self.redirect('/dashboard?action=students')

class YoutubeVideosTreatment(object):
    def _init_(self):
        self.time = []
        self.event = []
        self.info = []

    def retrieve_event(self, typeevent):
        if typeevent.event:
            self.event=transforms.loads(typeevent.event)
	
    def retrieve_info(self, typeinfo):
		if typeinfo.info:
			self.info=transforms.loads(typeinfo.info)

      
class ScoresAggregator(object):
    """Aggregates scores statistics."""

    def __init__(self):
        # We store all data as tuples keyed by the assessment type name. Each
        # tuple keeps:
        #     (student_count, sum(score))
        self.name_to_tuple = {}

    def visit(self, student):
        if student.scores:
            scores = transforms.loads(student.scores)
            for key in scores.keys():
                if key in self.name_to_tuple:
                    count = self.name_to_tuple[key][0]
                    score_sum = self.name_to_tuple[key][1]
                else:
                    count = 0
                    score_sum = 0
                self.name_to_tuple[key] = (
                    count + 1, score_sum + float(scores[key]))


class EnrollmentAggregator(object):
    """Aggregates enrollment statistics."""

    def __init__(self):
        self.enrolled = 0
        self.unenrolled = 0

    def visit(self, student):
        if student.is_enrolled:
            self.enrolled += 1
        else:
            self.unenrolled += 1


class ComputeStudentStats(jobs.DurableJob):
    """A job that computes student statistics."""

    def run(self):
        """Computes student statistics."""

        enrollment = EnrollmentAggregator()
        scores = ScoresAggregator()
        query = db.GqlQuery(
            'SELECT * FROM %s' % Student().__class__.__name__,
            batch_size=10000)
        for student in query.run():
            enrollment.visit(student)
            scores.visit(student)

        data = {
            'enrollment': {
                'enrolled': enrollment.enrolled,
                'unenrolled': enrollment.unenrolled},
            'scores': scores.name_to_tuple}

        return data


class YoutubeVideosTreatment(object):
    ## Author: Omar ALHY
    def _init_(self):
        self.time = []
        self.event = []
        self.info = []

    def retrieve_event(self, typeevent):
        if typeevent.event:
            self.event=transforms.loads(typeevent.event)
	
    def retrieve_info(self, typeinfo):
	if typeinfo.info:
	    self.info=transforms.loads(typeinfo.info)
            


class AnswersTreatment(object):
    ## Authors: Miriam MARCIEL and Roderick FANOU
    def _init_(self):
	self.name_to_tuple = {}
	self.data =[]

        
    def number_quest(self, student):
        if student.data:
            self.data = transforms.loads(student.data)

   
    def count_students(self,course):
    	lessons=self.get_lessons(course)
    	data=[];
    	for lesson in lessons:	        
    		query_str="SELECT DISTINCT user_id FROM YouTubeEvent where video='"+lesson['video']+"' and event='started'"
	        query = db.GqlQuery(query_str,batch_size=10000)
	        started_count=query.count()
	        
	        query_str="SELECT DISTINCT user_id FROM YouTubeEvent where video='"+lesson['video']+"' and event='ended'"
	        query = db.GqlQuery(query_str,batch_size=10000)
	        ended_count=query.count()
	        
	        data_lesson={"unit_id":lesson['unit_id'], "lesson_id":lesson['lesson_id'], "started_count":started_count,"ended_count":ended_count}
	        data.append(data_lesson)	
        return data

        
    def get_lessons(self,course):
	units=course.get_units()
	data=[]
	for unit in units:
		lessons=course.get_lessons(unit.unit_id)
		for lesson in lessons:
			lesson_dic={"unit_id":lesson.unit_id, "lesson_id":lesson.lesson_id, "video":lesson.video}
			data.append(lesson_dic)
     	return data


    def get_assessments(self,course):
        ## Returns a list of dictionnaries each of which contains the assessment id and the
        ## assessment name only if the corresponding assessment is available.
        assessment_ids=self.get_assessment_id(course)
        assessment_names=self.get_assessment_name(course)
        assessment_avs=self.get_assessment_av(course)
        Assessmt= []
        for i in range(0, len(assessment_ids) ):
            assess_dict={}
            assessment_ids[i] = assessment_ids[i].encode('ascii', 'ignore')
            assessment_names[i] = assessment_names[i].encode('ascii', 'ignore')

            if str(assessment_avs[i]) == "TRUE" or str(assessment_avs[i]) == "True":
                assess_dict= {assessment_ids[i]: assessment_names[i]}
                Assessmt.append(assess_dict)
        return Assessmt



    def get_assessment_id(self, course):
        ## Returns a list assessments id 
        assessment_id = []      
        for unit in course.get_units():
            if verify.UNIT_TYPE_ASSESSMENT == unit.type:
                assessment_id.append(unit.unit_id)
        return assessment_id


    def get_assessment_av(self, course):
        ## Returns a list of assessments availability
        assessment_av = []
        for unit in course.get_units():
            if verify.UNIT_TYPE_ASSESSMENT == unit.type:
                assessment_av.append(unit.now_available)
        return assessment_av


    def get_assessment_name(self, course):
        ## Returns a list of assessments name."""
        assessment_name = []
        for unit in course.get_units():
            if verify.UNIT_TYPE_ASSESSMENT == unit.type:
                assessment_name.append(unit.title)
        return assessment_name

			
class PropertyTreatment(object):
    ## Author: Roderick FANOU
    def _init_(self):
        self.data =[]
        
    def number_attempts(self, student_property):
        if student_property.value:
            self.data = transforms.loads(student_property.value)


class StudentTreatment(object):
    ## Author: Roderick FANOU
    def _init_(self):
        self.data =[]
        
    def scores(self, student):
        if student.scores:
            self.data = transforms.loads(student.scores)

  
class PlotTreatment(object):
    ## Author: Roderick FANOU
    def _init_(self):
	self.name_to_tuple = {}
	self.data =[]

    def plot(self, assess_list, stats):
        # Plot the differents charts taking into account the available assessments
        # and the computed statistics
        
        #Initialisations
        Graphs = ''
        #compute the number of available assessments
        Num_av_assess= len(assess_list)
        Num_attempts = []
        Num_bad_attempts = []
        Num_student_having_succeed = []
        dict_bests =[]
        test_legend = int(0)
        Cat =''
        Rec =''
        
        ## Dictionnaries to keep the aggregate number of good and bad attempts 
        for j in range(0, Num_av_assess):
            Num_attempts.append(int(0)) # Num attempts before succeeding
            Num_bad_attempts.append(int(0)) #Num of attempts leading to failure
            ##students having get a score >= 50 out of 100 in a given assessment
            Num_student_having_succeed.append(int(0)) 
            dict_bests.append(int(0))
        
        for kindex in range(0, Num_av_assess):
            
            for key, value in assess_list[kindex].items():
                Assessment_id = """%s""" %(key)
                Assessment_id = Assessment_id.strip()
                Assessment_name = """%s""" %(value)
                Assessment_name = Assessment_name.strip()
                Cat += "'"+ Assessment_name +"',"


                #Initialisations
                answerscomputation = AnswersTreatment()
                Correct_answers = [] # Number of correct answer per question
                Num_questions_Pre = 0 #Number of questions for each assessment

                recommendations4 = 'The mean of attempts before success is too bad (still at 0 for the whole class).'
                recommendations5 = 'The mean of attempts before success is average.'
                recommendations6 = 'The mean of attempts before success is excellent.'
                recommendations7 = 'The mean of attempts before success too high. You have many persistent students. You need to encourage them.'

                ## Computes aggregate percentage of success in answering the questions
                query1 = db.GqlQuery('SELECT * FROM %s' %StudentAnswersEntity().__class__.__name__, batch_size=10000)

                for student_answers in query1.run():
                    answerscomputation.number_quest(student_answers)
                    
                    if Assessment_id in answerscomputation.data.keys():
                        Num_questions_Pre = len(answerscomputation.data[Assessment_id])
                        
                        if (len(Correct_answers)==0):
                            for i in range(0, Num_questions_Pre):
                                Correct_answers.append(int(0))
                                
                        # An answer is considered as good when the field correct contains true or True 
                        i = 0
                        while i < Num_questions_Pre :
                            if (str(answerscomputation.data[str(Assessment_id)][i]["correct"]) == "true") or (str(answerscomputation.data[Assessment_id][i]["correct"]) == "True"):
                                Correct_answers[i] += 1
                            i += 1

                
                ## Accesses the StudentPropertyEntity class and process the data of all the students
                propertycomputation = PropertyTreatment()
                studentcomputation = StudentTreatment()

                ##Future work: This line is planned to be used to joined the two tables (Student and StudentPropertyEntity) with GQL and
                ##improve the following queries (ref improv1)
                query2 = db.GqlQuery('SELECT * FROM %s' %Student().__class__.__name__, batch_size=10000)
                query3 = db.GqlQuery('SELECT * FROM %s' %StudentPropertyEntity().__class__.__name__, batch_size=10000)

                line_pre = 0
                dict_lines = []
                
                ##Total number of students in the whole class
                total_student = 0
                
                for student in query2.run():
                    studentcomputation.scores(student)
                    Graphs += """%s""" %(student)
                    # studentcomputation.user_id(student)  ## (ref improv1)
                    total_student += 1
                    line_pre +=1

                    try:
                        if Assessment_id in studentcomputation.data.keys():
                            if studentcomputation.data[Assessment_id] >= 50 :
                                    Num_student_having_succeed[kindex] += 1
                                    dict_lines.append(int(line_pre))
                                    
                            if studentcomputation.data[Assessment_id] >= 75 :
                                    dict_bests[kindex] += 1
                    except:
                        continue

                line_pre = 0

                i = 0
                val = str(Assessment_id)
                title = 's.'+ val.strip()
 
                ##Searches how many attempts the students have done before passing the assessment (aggregate number and then divided to obtain the mean)
                ##Searches how many bad attempts have done the students who have not passed a given exam (aggregate number and then divided to obtain the mean)
                for student_property in query3.run():
                    propertycomputation.number_attempts(student_property)
                    line_pre += 1
                    try:
                        if i < len(dict_lines):
                            if (int(line_pre) == int(dict_lines[i])):
                               if title in propertycomputation.data.keys():
                                  Num_attempts[kindex] += int(propertycomputation.data[title])

                                  i += 1
                            else:
                               if title in propertycomputation.data.keys():
                                  Num_bad_attempts[kindex] += int(propertycomputation.data[title])
                                  
                        else:
                            if title in propertycomputation.data.keys():
                                Num_bad_attempts[kindex] += int(propertycomputation.data[title])
                               
                    except:
                        continue         
                
                if (Num_questions_Pre > 0):
                    Graphs += """<table align="center">  
                        <tr>
                            <td> <b>Assessment </b>
                        </td>"""
                    ##Starts Displaying the table with the computed data corresponding to the Pre-assessment         
                    l = 0
                    while l < Num_questions_Pre:
                        Graphs += """ <td><b><center>Question %s</center> </td></b> """ % (l+1)
                        l += 1
                    Graphs += """ <td><b><center>%s</center> </td></b> """ %("Attempts before success")
                        
                    Graphs += """
                            </tr> 
                            <tr>
                            <td> <b> %s </b>
                            </td>
                            """ %(Assessment_name)

                    ## Starts recommendations establishment: Either the results are bad, either they are good or very good.
                    ## Future work: we intend to transfer these variables into a dictionnary depending of the recomandations that have been finally retained
                    
                    red = 0
                    yel = 0
                    gre = 0

                    recommendations_pre = ''
                    
                    recommendations_red = ''
                    recommendations_yel = ''
                    recommendations_gre = ''

                    recommendations1 = '<span style="text-decoration: underline;"><b> %s :</b></span> It is compulsory to better explain in your videos the concepts covered in the questions '%(Assessment_name)
                    recommendations2 = '<span style="text-decoration: underline;"><b> %s :</b></span> To improve these results, we advice you to better explain in your videos the concepts covered in the following questions: ' %(Assessment_name)
                    recommendations3 = '<span style="text-decoration: underline;"><b> %s :</b></span> Your students have a very good backgroung concerning the topic. They will easily understand your course if the videos are attractive and the explanations, exhaustive.'%(Assessment_name)

        

                    for key, value in stats['scores'].items():
                        #Graphs += """ Voici la cle: %s  """ %(key)
                        Graphs += """ <ul> </ul> """ 
                        if str(key) == str(Assessment_id):
                            for m in range(0,Num_questions_Pre ):
                                Per_success_Pre = ((float(Correct_answers[m])*100)/ float(stats['scores'][Assessment_id][0]))
                                
                                # Displays the aggregate percentage of success for each questions
                                if ( Per_success_Pre < 33) and (Per_success_Pre >= 0):
                                    Graphs += """ <td bgcolor="red"><center> %.2f &#37;</center></td> """ %(Per_success_Pre) 
                                    if (m == Num_questions_Pre - 1):
                                        recommendations_red += str(m+1)
                                    else:
                                        recommendations_red += str(m+1)+", "
                                    red += 1
                                elif (Per_success_Pre  < 67) and ( Per_success_Pre  >= 33):
                                    Graphs += """ <td bgcolor="yellow"><center> %.2f &#37;</center></td> """ %(Per_success_Pre)
                                    if (m == Num_questions_Pre - 1):
                                        recommendations_yel += str(m+1)+". "
                                    else:
                                        recommendations_yel += str(m+1)+", "
                                    yel += 1
                                elif (Per_success_Pre >= 67) and (Per_success_Pre  <= 100):
                                    Graphs += """ <td  bgcolor="green"><center> %.2f &#37;</center></td> """ %(Per_success_Pre ) 
                                    if (m == Num_questions_Pre - 1):
                                        recommendations_gre += str(m+1)+". "
                                    else:
                                        recommendations_gre += str(m+1)+", "
                                    gre += 1

                            ##Recommandations
                            if red > yel and red > gre:
                                recommendations_pre = recommendations1 + recommendations_red + " and to reformulate them." 

                            if yel > red and yel > gre:
                                recommendations_pre = recommendations2 + recommendations_yel 

                            if gre > yel and gre > red:
                                recommendations_pre = recommendations3 + recommendations_gre


                            # Displays the mean of attempts done by the students having succeed before passing the exam
                            try:
                                if (int(Num_student_having_succeed[kindex]) > int(0)):
                                    Mean_good_attempts = float(Num_attempts[kindex]//Num_student_having_succeed[kindex])
                                                       
                                    if Mean_good_attempts == 1:
                                        Graphs += """ <td bgcolor="#298A08"><center> %.2f </center></td> """  %(Mean_good_attempts)
                                        recommendations_pre += " " + recommendations6
                                    
                                    if Mean_good_attempts > 1 and  Mean_good_attempts <=2:
                                        Graphs += """ <td bgcolor="#FFFF00"><center> %.2f </center></td> """  %(Mean_good_attempts)
                                        recommendations_pre += " " + recommendations5
                                        
                                    if Mean_good_attempts > 3:
                                        Graphs += """ <td bgcolor="#FF0000"><center> %.2f </center></td> """  %(Mean_good_attempts)
                                        recommendations_pre += " " + recommendations7

                                else:
                                    Mean_good_attempts = float(0)
                                    Graphs += """ <td bgcolor="#FF0000"><center> %.2f </center></td> """  %(Mean_good_attempts)
                                    recommendations_pre += " " + recommendations4


                            except:
                                Mean_good_attempts = float(0)
                                Graphs += """ <td bgcolor="#FF0000"><center> %.2f </center></td> """  %(Mean_good_attempts)
                                recommendations_pre += " " + recommendations4

                    test_legend += 1

                    Rec += recommendations_pre + "<ul></ul>"
                    
                    if (test_legend == int(Num_av_assess)):       
                        #Displays the legend of the table : Red: 0-33%, Yellow: 33-67%, Green: 67%-100%
                        Graphs += """
                                    </tr> 	
                                    </table>			   
                                    <h5><span style="text-decoration: underline;">Legend for the questions:</span>
                                    &nbsp;&nbsp; &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                                    <span style="text-decoration: underline;">Legend for the mean of attempts:</span></h5>    	    
                                    <span style="background-color:red;width:100px;height:20px;border:1px solid #000"> &nbsp;&nbsp; &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>&nbsp;&nbsp;<span>
                                    0 - 33 &#37;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                                    </span><span style="background-color:red;width:100px;height:20px;border:1px solid #000"> &nbsp;&nbsp; &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>&nbsp;&nbsp;<span>Mean = 0 or Mean >= 3 
                                    <p> </p>
                                    <span style="background-color:yellow;width:100px;height:20px;border:1px solid #000"> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>&nbsp;&nbsp;<span>
                                    33 &#37; - 67 &#37; &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                                    </span><span style="background-color:yellow;width:100px;height:20px;border:1px solid #000"> &nbsp;&nbsp; &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>&nbsp;&nbsp;<span>1 > Mean >= 2 
                                    <p> </p>
                                    <span style="background-color:green;width:100px;height:20px;border:1px solid #000">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; </span>&nbsp;&nbsp;<span>
                                    67 &#37; - 100 &#37; </span> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                                    </span><span style="background-color:green;width:100px;height:20px;border:1px solid #000"> &nbsp;&nbsp; &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>&nbsp;&nbsp;<span> Mean = 1 
                                    <p> </p>
                                    <ul></ul><ul></ul><ul></ul><ul></ul><div style="height:20px;"></div>
                                    """        


        Graphs5=""
        Graphs1 = """
          <script type='text/javascript' src='https://ajax.googleapis.com/ajax/libs/jquery/1.7.2/jquery.min.js'></script>
          
          <link rel="stylesheet" type="text/css" href="/css/result-light.css">
          
          <style type='text/css'>
            
          </style>
          
          <script type='text/javascript'>//<![CDATA[

          $(function () {
            $('#container').highcharts({
                chart: {
                    type: 'column'
                },
                title: {
                    text: 'Percentage of success per assessement'
                },
                subtitle: {
                    text: 'Source: Datastore'
                },
                xAxis: {
                
                    categories: [%s
                        ]"""%(Cat)

        Graphs1 += """
        },
        yAxis: {
            min: 0,
            title: {
                text: 'Number of students '
            }
        },
        tooltip: {
            headerFormat: '<span style="font-size:10px">{point.key}</span><table>',
            pointFormat: '<tr><td style="color:{series.color};padding:0">{series.name}: </td>' +
                '<td style="padding:0"><b>{point.y:.1f} students</b></td></tr>',
            footerFormat: '</table>',
            shared: true,
            useHTML: true
        },
        plotOptions: {
            column: {
                pointPadding: 0.2,
                borderWidth: 0
            }
        },
        series: [{
            name: 'Students enrolled',
            data: [ %d, %d, %d ],"""  %(int(total_student), int(total_student), int(total_student) )


        Graphs1 +="""
                
            color: '#08298A'

        }"""


        show=""
        show1=""
        show2=""
        show3=""

        for kindex in range(0, Num_av_assess):
            #Graphs += """ kindex: %d  """ %(kindex)
            for key, value in assess_list[kindex].items():
                Assessment_id = """%s""" %(key)
                Assessment_id = Assessment_id.strip()
                Assessment_name = """%s""" %(value)
                Assessment_name = Assessment_name.strip()
                #Graphs += """ Assess_id: %s  """ %(Assessment_id)
                #Graphs += """ Assess_name: %s """ %(Assessment_name)
                if kindex == Num_av_assess-1:
                    try:
                        search = stats['scores'][Assessment_id][0]
                        show += str(search)
                        search1 =  stats['scores'][Assessment_id][0]- Num_student_having_succeed[kindex]
                        show1 += str(search1)
                        search2 =  Num_student_having_succeed[kindex]
                        show2 += str(search2)
                        search3 =  dict_bests[kindex]
                        show3 += str(search3)
                    except:
                        continue
                else:
                    try:
                        search = stats['scores'][Assessment_id][0]
                        show += str(search)
                        show += ","
                        search1 = stats['scores'][Assessment_id][0] -Num_student_having_succeed[kindex]
                        show1 += str(search1)
                        show1 += ","
                        search2 = Num_student_having_succeed[kindex]
                        show2 += str(search2)
                        show2 += ","
                        search3 = dict_bests[kindex]
                        show3 += str(search3)
                        show3 += ","
                    except:
                        continue

        Graphs1 += """,

            {
                name: 'Students having done the assessment',

                    data: [ %s ],  color: 'blue'

            },""" %(show)


        Graphs1 += """

            {
                name: 'Students having got < 50',

                    data: [ %s ],  color: 'red'

            },""" %(show1)

            
        Graphs1 += """

            {
                name: 'Student having got > 50',

                    data: [ %s ],  color: '#FFFF00'

            },""" %(show2)
        

        Graphs1 += """

            {
                name: 'Student having got >= 75',

                    data: [ %s ],  color: '#298A08'

            },""" %(show3)
                
        
        Graphs1 += """
            ]
            });
            });
                    """

                                   
        text =''
        for kindex in range(0, Num_av_assess):
            for key, value in assess_list[kindex].items():
                Assessment_id = """%s""" %(key)
                Assessment_id = Assessment_id.strip()
                Assessment_name = """%s""" %(value)
                Assessment_name = Assessment_name.strip()               
                cont= '#container'+str(kindex)+str(kindex)
                cont1= 'container'+str(kindex)+str(kindex)
                text += """<div id="%s" style="min-width: 400px; height: 400px; margin: 0 auto"></div>                     
                            <div style="height:20px;"></div>""" %(cont1)        
                
                
                ## Chart showing a deep overview of the attempts per assessments
  
                Graphs0 = """

                    $(function () {
                    $('%s').highcharts({""" %(cont)


                Graphs0 += """
                    chart: {
                        plotBackgroundColor: null,
                        plotBorderWidth: null,
                        plotShadow: false
                    },
                    title: {
                        text: 'Deep overview of the attempts done by the students having completed %s'"""%(Assessment_name)

                Graphs0 += """
                
                    },subtitle: {
                        text: 'Source: Datastore'
                    },
                    tooltip: {
                            pointFormat: '{series.name}: <b>{point.percentage}%</b>',
                        percentageDecimals: 1
                    },
                    plotOptions: {
                        pie: {
                            allowPointSelect: true,
                            cursor: 'pointer',
                            dataLabels: {
                                enabled: true,
                                color: '#000000',
                                connectorColor: '#000000',
                                formatter: function() {
                                    return '<b>'+ this.point.name +'</b>: '+ this.percentage +' %';
                                }
                            }
                        }
                    },"""

                
                Graphs0 += """
                    series: [{
                        type: 'pie',
                        name: 'attemtps',
                        data: [{
                                name: 'Percentage of good attempts for %s',
                                y: %.2f """ %(Assessment_id, float(Num_attempts[kindex]))

                

                Graphs0 += """
                        ,sliced: true,
                        selected: true
                    },
                    ['Percentage of bad attempts for %s', %.2f]""" %(Assessment_id,float(Num_bad_attempts[kindex]))


            Graphs0 += """
                ]
            }]
        });
    });

                            """


            Graphs5 += str(Graphs0)


        Graphs2= """
//]]>  

</script>
  <script src="http://code.highcharts.com/highcharts.js"></script>
<script src="http://code.highcharts.com/modules/exporting.js"></script>""" +str(text)+'<ul> </ul><div id="container"  style="min-width: 600px; height: 600px; margin: 0 auto"></div>'


        Graphs += Graphs1+Graphs5+Graphs2


        if (test_legend == int(Num_av_assess)):
            Graphs += """
                                <div style="height:20px;"></div>
                                <ul></ul>
                                <ul></ul>
                                <ul></ul>
                                <h3>Recommendations:</h3>
                                <b></b> 
                                <ul></ul>
                                """

            Graphs += Rec + "<ul></ul><ul></ul>"
        
        return Graphs
