from django.shortcuts import render_to_response, redirect
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import validate_email
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from gpgvote.gpgauth.forms import RegisterForm, RenewForm, LoginForm
from gpgvote.gpgauth.models import PGPkey
from gnupg import GPG
from hashlib import md5


# Utility Functions
def delete_keys(gpg, fingerprints, del_existed=False):
  # Make sure that fingerprint is a list
  if type(fingerprints).__name__ != 'list':
    fingerprints = [fingerprints]
    
  for fp in fingerprints:
    # Delete key only if it does not exist in database or del_existed is True
    try:
      key = PGPkey.objects.get(fingerprint = fp)
      if del_existed:
        gpg.delete_keys(fp)
    except ObjectDoesNotExist:
      gpg.delete_keys(fp)

    
def key_import(gpg, keyfile):
  if keyfile.size > 100000: # accept files of a normal size
    error = 'Key file size is too big'
  else:
    error = ''
    try:
      import_result = gpg.import_keys(keyfile.read())
    except UnicodeDecodeError:
      error = 'There was an error in importing your key'
      return error, None
      
    if import_result.count == 0:
      error = 'There was an error in importing your key'
		
    if import_result.count > 1: # accept only single-key files
      error = 'Your key file includes more than one keys'
      delete_keys(gpg, import_result.fingerprints)
	  
    if import_result.count == 1:
      fp = import_result.fingerprints[0]
      if gpg.key_is_expired(fp):
	error = 'Your key is expired'
        delete_keys(gpg, import_result.fingerprints)
      else:
	return error, gpg.get_key(fp)
        
  return error, None
  
def login_common_checks(username):
  try:
    user = User.objects.get(username = username)
    if user.is_active:
      gpg = GPG(gpgbinary=settings.GNUPGBINARY, gnupghome=settings.GNUPGHOME)
      if not gpg.key_is_expired(user.pgpkey.fingerprint):
        key = gpg.get_key(user.pgpkey.fingerprint)
        if key['ownertrust'] in settings.TRUST_LEVELS:
	  error = False
        else:
          error = 'PGP key for user \'%s\' is not trusted (yet)' % username
      else: 
        error = 'PGP key for user \'%s\' has expired' % username
    else:
      error = 'Account for user \'%s\' is disabled' % username
      gpg = None
  except ObjectDoesNotExist:
    error = 'User \'%s\' does not exist' % username
    user = None
    gpg = None
    
  return user, error, gpg


# Views

def register(request):
  if request.user.is_authenticated():
    return HttpResponseRedirect('/')
  error = ''
  success = ''
  if request.POST:
    form = RegisterForm(request.POST, request.FILES)
    if form.is_valid():
      keyfile = request.FILES['keyfile']
      gpg = GPG(gpgbinary=settings.GNUPGBINARY, gnupghome=settings.GNUPGHOME)
      (error, imported_key) = key_import(gpg, keyfile)
      if not error:
	# check for user existance in database to accept registration only for new users
        try:
	  user = User.objects.get(email = imported_key['email'])
	  error = 'User \'%s\' is already registered' % imported_key['email']
	  if user.pgpkey.fingerprint != imported_key['fingerprint']: 
	    delete_keys(gpg, imported_key['fingerprint'])
        except ObjectDoesNotExist:
          newuser = User.objects.create_user(username = imported_key['email'], 
	                                        email = imported_key['email'],
	                                     password = '')
	  newuser.set_unusable_password()
	  newuser.save()
	  pgpkey = PGPkey(user = newuser, name = imported_key['name'], fingerprint = imported_key['fingerprint'])
	  pgpkey.save()
	  success = 'You are now registered'
  
  else:
    form = RegisterForm()
    
  return render_to_response('register.html', 
         {    'form': form, 
             'error': error, 
           'success': success }, context_instance = RequestContext(request))


def renew(request, username):
  if request.user.is_authenticated():
    return HttpResponseRedirect('/')
  error = ''
  success = ''
  try:
    validate_email(username)
  except:
    error = 'Invalid username'
  if not error:
    (user, error, gpg) = login_common_checks(username)
    if not error:
       error = 'Your key is not expired yet'
    if error.endswith('expired'):
      error = ''
    
  if request.POST:
    form = RenewForm(request.POST, request.FILES)
    if form.is_valid():
      if user.pgpkey.renew_passwd != md5(form.cleaned_data['password']).hexdigest():
	passwd = User.objects.make_random_password()
	user.pgpkey.renew_passwd = md5(passwd).hexdigest()
	user.pgpkey.save()
	msg = 'Use the following password to renew your key:\n' + passwd
	user.email_user('Renew Key', msg)
	error = 'Wrong Password. The correct password has been sent to: %s' % username
      else:
        keyfile = request.FILES['keyfile']
        (error, imported_key) = key_import(gpg, keyfile)
      if not error:
	if imported_key['fingerprint'] == user.pgpkey.fingerprint:
	  error = 'The uploaded key already exists'
	else:
	  update_user = False
	  # Check if the email of the uploaded key is already used by a different user
	  try:
	    user = User.objects.get(username = imported_key['email'])
	    if username != imported_key['email']:
	      error = 'There is another user with username: \'%s\'' % imported_key['email']
	      delete_keys(gpg, imported_key['fingerprint'])
	    else:
	     update_user = True
	  except:
	     update_user = True
	  
	  if update_user:
	    delete_keys(gpg, user.pgpkey.fingerprint, del_existed=True)
	    user.pgpkey.fingerprint = imported_key['fingerprint']
	    user.pgpkey.name = imported_key['name']
	    user.pgpkey.save()
	    user.username = imported_key['email']
	    user.email = imported_key['email']
	    user.save()
            success = 'Your key was successfuly renewed'
            
  else:
    form = RenewForm()
  
  return render_to_response('renew.html',
         {     'form': form, 
              'error': error, 
            'success': success,
           'username': username }, context_instance = RequestContext(request))


def login_view(request):
  if request.user.is_authenticated():
    return HttpResponseRedirect('/')
  error = ''
  password = ''    
  try:
    goto_stage = request.POST['stage']
  except:
    goto_stage = 'password'
  if request.POST:
    form = LoginForm(request.POST)
    if goto_stage == 'password':
      try:
        validate_email(request.POST['username'])
      except:
        error = 'Invalid username'
      if not error:
        (user, error, gpg) = login_common_checks(request.POST['username'])
        if not error:
          password = User.objects.make_random_password()
	  user.set_password(password)
	  user.save()
	  password = gpg.encrypt(password, user.pgpkey.fingerprint, always_trust=True) # Trust level is checked earlier
	  if password.ok:
	    goto_stage = 'afterpass'
	  else:
	    user.set_unusable_password()
	    user.save()
	    error = 'Encryption error (%s)' % password.status
	elif error.endswith('expired'):
	  return redirect('/renew/%s' % request.POST['username'])
	else:
	  pass
	  
    elif goto_stage == 'afterpass':
      if form.is_valid():
	# Run common checks again to disappoint those who try to bypass first login step
	(user, error, gpg) = login_common_checks(form.cleaned_data['username'])
        if not error:
	  user = authenticate(username=form.cleaned_data['username'], password = form.cleaned_data['password'] )
	  if user is not None:
	    login(request, user)
	    return HttpResponseRedirect('/')
	  else:
	    error = 'Wrong password'
	    form = '';
	else:
	  goto_stage = 'password'
      else:
        error = 'Invalid username or password'
        goto_stage = 'password'
      
  else:
    form = LoginForm()
    
  return render_to_response('login.html', {       'form': form, 
                                            'goto_stage': goto_stage, 
                                                 'error': error, 
                                              'password': password   }, context_instance = RequestContext(request))
                                              
                                              
def logout_view(request):
  logout(request)
  return HttpResponseRedirect('/')