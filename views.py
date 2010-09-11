from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, Http404
from django.template import RequestContext
from django.contrib.auth.models import User

def main(request):
  logged_in = False
  user = ''
  if request.user.is_authenticated():
    user = request.user.username
    logged_in = True
  return render_to_response('main.html', { 'logged_in': logged_in, 'user': user })
  
def userinfo(request, user_id):
  if not request.user.is_authenticated():
    return HttpResponseRedirect('/')
  else:
    logged_in = True
  
  try:
    user = User.objects.get(pk = user_id)
  except User.DoesNotExist:
    raise Http404
    
  return render_to_response('userinfo.html',
                           {           'user': request.user.username,
                             'requested_user': user,
                                  'logged_in': logged_in }, context_instance = RequestContext(request))