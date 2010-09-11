from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^gpgvote/', include('gpgvote.foo.urls')),
    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve', 
    {'document_root': '/path/to/gpgvote/templates/media'}),
    url(r'^captcha/', include('captcha.urls')),
    (r'^$', 'gpgvote.views.main'),
    (r'^userinfo/(?P<user_id>\d+)/$', 'gpgvote.views.userinfo'),
    (r'^register/$', 'gpgvote.gpgauth.views.register'),
    (r'^renew/(?P<username>.*)$', 'gpgvote.gpgauth.views.renew'),
    (r'^login/$', 'gpgvote.gpgauth.views.login_view'),
    (r'^logout/$', 'gpgvote.gpgauth.views.logout_view'),
    (r'^createpoll/$', 'gpgvote.polls.views.createpoll'),
    (r'^editpoll/(?P<poll_id>\d+)/$', 'gpgvote.polls.views.editpoll'),
    (r'^deletepoll/(?P<poll_id>\d+)/$', 'gpgvote.polls.views.deletepoll'),
    (r'^mypolls/$', 'gpgvote.polls.views.mypolls'),
    (r'^voters_list/(?P<poll_id>\d+)/$', 'gpgvote.polls.views.voters_list'),
    (r'^vote/(?P<poll_id>\d+)/$', 'gpgvote.polls.views.vote'),
    (r'^results/(?P<poll_id>\d+)/$', 'gpgvote.polls.views.results'),
    (r'^results/(?P<poll_id>\d+)/votes_list/$', 'gpgvote.polls.views.votes_list')
    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)
