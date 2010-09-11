from django.shortcuts import render_to_response
from django.db.models import Q
from django.http import HttpResponseRedirect, Http404
from django.template import RequestContext
from django.conf import settings
from django.forms import Form
from gpgvote.polls.forms import PollForm
from django.contrib.auth.models import User
from gpgvote.gpgauth.models import PGPkey
from gpgvote.polls.models import Poll
from gpgvote.polls.models import Choice
from gpgvote.polls.models import Vote
from gnupg import GPG
import datetime
import random
import string
import operator


# Utility functions
def list_has_duplicates(mylist):
  if len(mylist) > len(list(set(mylist))):
    return True
  else:
    return False
  
def dates_check(starts_date, starts_time, ends_date, ends_time):
  error = ''
  starts_datetime = datetime.datetime(
                      year   = starts_date.year,
                      month  = starts_date.month,
                      day    = starts_date.day,
                      hour   = starts_time.hour,
                      minute = starts_time.minute,
                      second = starts_time.second  )
                      
  ends_datetime = datetime.datetime(
                    year   = ends_date.year,
                    month  = ends_date.month,
                    day    = ends_date.day,
                    hour   = ends_time.hour,
                    minute = ends_time.minute,
                    second = ends_time.second  )
  
  if starts_datetime < datetime.datetime.now() + datetime.timedelta(minutes = settings.POLL_START_TIME_THRESHOLD):
    error = '<ul><li>Poll must start at least ' + str(settings.POLL_START_TIME_THRESHOLD) + ' minutes in the future</li></ul>'
  
  duration = ends_datetime - starts_datetime
  if duration < datetime.timedelta(minutes = settings.POLL_MIN_DURATION):
    if duration < datetime.timedelta(microseconds=0):
      error = '<ul><li>Poll must end at least ' + str(settings.POLL_MIN_DURATION) + ' minutes after the start</li></ul>'
    else:
      error = '<ul><li>Poll must last for at least ' + str(settings.POLL_MIN_DURATION) + ' minutes</li></ul>'
  
  return error, starts_datetime, ends_datetime

def num_of_choices_check(num_of_choices, min_choices, max_choices):
  error = ''
  if max_choices < min_choices:
    error = '<ul><li>Max. must be bigger than or equal to Min.</li></ul>'
	
  if (max_choices < 1) or (min_choices < 1):
    error = '<ul><li>Max. and Min. must be bigger than or equal to 1</li></ul>'
  
  if (not error) and (max_choices > num_of_choices):
    error = '<ul><li>Max. and Min. must be smaller than or equal to the number of choices</li></ul>'
  
  return error

# Views
def poll(request, action, poll_id):
  if not request.user.is_authenticated():
    return HttpResponseRedirect('/')
  else:
    logged_in = True

  choices_error = ''
  dates_error = ''
  num_of_choices_error = ''
  allowed_voters_error = ''
  success = ''
  poll_data = {}
  poll_choices = []
  
  if action == 'edit':
    try:
      poll = Poll.objects.get(pk = poll_id)
    except Poll.DoesNotExist:
      raise Http404
    # allow edit only for creator and only if the poll has not started yet
    if (request.user != poll.creator) or (poll.starts < datetime.datetime.now()):
      return HttpResponseRedirect('/')
    poll_data = {    'question': poll.question,
                  'min_choices': poll.min_choices,
                  'max_choices': poll.max_choices,
                  'starts_date': poll.starts.date(),
                  'starts_time': poll.starts.time(),
                    'ends_date': poll.ends.date(),
                    'ends_time': poll.ends.time()   }
    poll_choices = Choice.objects.filter(poll = poll).order_by('id')
                         
  # Clean PGPkey records to correct is_trusted field
  for key in PGPkey.objects.all():
    key.clean()
  
  # Get trusted users and create allowed voters choices
  trusted_users = User.objects.filter(pgpkey__is_trusted=True).order_by('pgpkey__name')
  allowed_voters = ()
  for user in trusted_users:
    allowed_voters = allowed_voters + ( (user.username, user.pgpkey.name + ' <' + user.username + '>' ), )
  
  if request.POST:
    # allow edit only if the poll has not started yet
    if (action == 'edit'):
      if (poll.starts < datetime.datetime.now()):
        return HttpResponseRedirect('/')
      
    form = PollForm(allowed_voters, request.POST, initial = poll_data)
    if form.is_valid():
      poll_choices = request.POST.getlist('choices')
      if len(poll_choices) < 2:
        choices_error = '<ul><li>You must add at least 2 choices</li></ul>'
      else:
	for choice in poll_choices:
	  if len(choice) > 255:
	    choices_error = '<ul><li>Each choice must be up to 255 characters in length</li></ul>'
      
      (dates_error, starts_datetime, ends_datetime) = dates_check(
                                                        form.cleaned_data['starts_date'],
                                                        form.cleaned_data['starts_time'], 
                                                        form.cleaned_data['ends_date'],
                                                        form.cleaned_data['ends_time'] )
      num_of_choices_error = num_of_choices_check(len(poll_choices), 
                                                  form.cleaned_data['min_choices'], 
                                                  form.cleaned_data['max_choices'])                                                  
      if len(form.cleaned_data['allowed_voters']) < 2:
	allowed_voters_error = '<ul><li>You must select at least 2 voters</li></ul>'
      
      if not (choices_error or dates_error or num_of_choices_error or allowed_voters_error):
	if action == 'create':
	  poll = Poll(
	           creator = request.user,  
	           question = form.cleaned_data['question'],
	           min_choices = form.cleaned_data['min_choices'],
	           max_choices = form.cleaned_data['max_choices'],
	           allowed_voters = '',
	           who_voted = '',
	           starts = starts_datetime,
	           ends = ends_datetime )
	else:
	  poll.question = form.cleaned_data['question']
	  poll.min_choices = form.cleaned_data['min_choices']
	  poll.max_choices = form.cleaned_data['max_choices']
	  poll.allowed_voters = ''
          poll.starts = starts_datetime
	  poll.ends = ends_datetime
        
	for voter in form.cleaned_data['allowed_voters']:
	  poll.add_voter(voter, To = 'allowed_voters')
        poll.save()
        
        # Delete old choices before adding their new versions
        if action == 'edit':
          Choice.objects.filter(poll = poll).delete()
        for choice in poll_choices:
	  choice = Choice(poll = poll, choice = choice)
	  choice.save()

        if action == 'create':
	  success = 'You have successfully created a new poll'
	else:
	  success = 'You have successfully edited the poll'
  else:
    form = PollForm(allowed_voters, initial = poll_data)
  
  if action == 'edit':
    poll_id = poll.id
  else:
    poll_id = ''
    
  return render_to_response('poll.html', 
         {                 'form': form,
                         'action': action,
                        'poll_id': poll_id,
                        'choices': poll_choices,
                  'choices_error': choices_error,
                    'dates_error': dates_error,
           'num_of_choices_error': num_of_choices_error,
           'allowed_voters_error': allowed_voters_error,
                        'success': success,
                           'user': request.user.username,
                      'logged_in': logged_in }, context_instance = RequestContext(request))
                      
def createpoll(request):
  return poll(request, 'create', None)
  
def editpoll(request, poll_id):
  return poll(request, 'edit', poll_id)
  
def deletepoll(request, poll_id):
  if not request.user.is_authenticated():
    return HttpResponseRedirect('/')
  else:
    logged_in = True
    
  try:
      poll = Poll.objects.get(pk = poll_id)
  except Poll.DoesNotExist:
      raise Http404
  
  # Delete poll only if it has not started yet and the user is the creator of the poll
  if (poll.creator == request.user) and (poll.starts > datetime.datetime.now()):
    poll.delete()
  
  return HttpResponseRedirect('/mypolls')
  
def mypolls(request):
  if not request.user.is_authenticated():
    return HttpResponseRedirect('/')
  else:
    logged_in = True
  
  # Polls that are created by the user and polls for which the user is allowed to vote
  mypolls_query = Poll.objects.filter(Q(creator = request.user) 
                                | Q(allowed_voters__contains = request.user.username + ';')).order_by('ends')
  
  pending_polls = []
  ended_polls = []
  for poll in mypolls_query:
    poll_has_ended = False
    if poll.ends < datetime.datetime.now():
       poll_has_ended = True
    if poll.starts < datetime.datetime.now():
      if poll.has_voted(request.user.username):
	if poll.ends < datetime.datetime.now():
	  poll_has_ended = True
	  allowed_actions = 'results'
	else:
	  allowed_actions = 'wait' # You have already voted but the poll has not ended yes, so, wait
      else:
	if poll.is_allowed_voter(request.user.username):
	  allowed_actions = 'vote'
	else:
	  allowed_actions = 'wait_creator' # You cannot vote, but you are the creator of the poll 
	                                   # and allowed to see the results 
    else:
      if poll.creator == request.user:
	allowed_actions = 'edit'
      else:
	allowed_actions = ''
    if poll_has_ended:
      ended_polls = ended_polls + [{ 'poll': poll, 'allowed_actions': allowed_actions }]
    else:
      if allowed_actions:
	pending_polls = pending_polls + [{ 'poll': poll, 'allowed_actions': allowed_actions }]
  
  ''' mypolls_query ordered the polls by ending datetime. So, we reverse ended_polls to have
      the 'fresher' results in the top '''
  ended_polls.reverse()
  
  return render_to_response('mypolls.html',
                           {          'user': request.user.username,
                             'pending_polls': pending_polls,
                               'ended_polls': ended_polls,
                                 'logged_in': logged_in }, context_instance = RequestContext(request))
                                 
def vote(request, poll_id):
  if not request.user.is_authenticated():
    return HttpResponseRedirect('/')
  else:
    logged_in = True
    
  error = ''
  success = ''
  try:
      poll = Poll.objects.get(pk = poll_id)
  except Poll.DoesNotExist:
      raise Http404
  
  username = request.user.username
  if (not poll.is_allowed_voter(username)) \
    or poll.has_voted(username) \
    or (poll.starts > datetime.datetime.now()) \
    or (poll.ends < datetime.datetime.now()):
      return HttpResponseRedirect('/mypolls')
      
  poll_choices = Choice.objects.filter(poll = poll).order_by('id')
  choice_type = "radio"
  if poll.max_choices > 1:
    choice_type = "checkbox"
  
  vote_tag = ''
  vote_receipt_encrypted = ''
  
  if request.POST:
    form = Form(request.POST)
    if form.is_valid():
      choices = request.POST.getlist('choices')
      
      # Check that the submitted choices exist and belong to the poll
      for choice in choices:
        try:
          c = Choice.objects.get(pk = choice, poll = poll)
        except Choice.DoesNotExist:
	  error = "The submitted choices are not valid choices of the poll"
      
      # Check that the submitted choices are between min and max number of choices allowed for the poll
      if len(choices) > poll.max_choices:
	error = 'You cannot vote for more than ' + str(poll.max_choices) + ' choices'
      if len(choices) < poll.min_choices:
	error = 'You must vote for at least ' + str(poll.min_choices) + ' choices'
	if poll.max_choices == 1: # a better error message for single choice polls
	  error = 'You must select a choice'
      if list_has_duplicates(choices):
	error = 'Each choice can be selected only once'
      
      if not error:
	# Construct a unique, random string to use as a vote tag
	while not vote_tag:
	  vote_tag = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(35))
	  try:
	    v = Vote.objects.get(tag = vote_tag)
	    vote_tag = ''
	  except Vote.DoesNotExist:  # our random string is unique so we can use it as a vote tag
	    # Encrypt the vote tag with user's public pgp key and sign it with the key of the system authority
	    gpg = GPG(gpgbinary=settings.GNUPGBINARY, gnupghome=settings.GNUPGHOME)
	    vote_receipt = """GPGVote: Vote Receipt
---------------------

You are voter: 
  %s

You voted for Poll:
  \'%s\'

Created by: 
  %s

Your Vote Tag is: %s
  
You made the following choices:"""  % (request.user.pgpkey.name + ' <' + request.user.username + '>', poll.question, \
                                       poll.creator.pgpkey.name + ' <' + poll.creator.username + '>', vote_tag)
	    
	    for choice in choices:
	      choice = Choice.objects.get(pk = choice, poll = poll)
	      vote_receipt = vote_receipt + '\n  * %s' % choice.choice
	      
	    vote_receipt_encrypted = gpg.encrypt(vote_receipt, request.user.pgpkey.fingerprint, always_trust = True,
	                                     sign = settings.SYSTEM_KEY_FINGERPRINT, 
	                                     passphrase = settings.SYSTEM_KEY_PASSWD)
	    # Create the actual vote records in database
	    for choice in choices:
	      vote = Vote(choice = Choice.objects.get(id = choice), tag = vote_tag)
	      vote.save()
	    poll.add_voter(voter = username, To = 'who_voted')
	    poll.save()
	   
	success = 'You have successfully voted for the poll'
  
  return render_to_response('vote.html',
                           {         'user': username,
                                     'poll': poll,
                                  'choices': poll_choices,
                              'choice_type': choice_type,
                                    'error': error,
                                  'success': success,
                             'vote_receipt': vote_receipt_encrypted,
                                'logged_in': logged_in }, context_instance = RequestContext(request))
  
def results(request, poll_id):
  if not request.user.is_authenticated():
    return HttpResponseRedirect('/')
  else:
    logged_in = True
    
  try:
      poll = Poll.objects.get(pk = poll_id)
  except Poll.DoesNotExist:
      raise Http404
 
  username = request.user.username
  if ((not poll.is_allowed_voter(username)) and (poll.creator != request.user)) or (poll.ends > datetime.datetime.now()):
      return HttpResponseRedirect('/mypolls')
  
  total_abstention = False
  try:
    votes = Vote.objects.filter(choice__poll = poll)
  except Vote.DoesNotExist:
    total_abstention = True
  
  if not votes: total_abstention = True
  
  results = {}
  if not total_abstention:
    choices = Choice.objects.filter(poll = poll)
    for choice in choices:
      results[choice.choice] = (0, 0)
    for vote in votes:
      votes_count = results[vote.choice.choice][0] + 1
      votes_percent = str(float(votes_count) / float(len(votes)) * 100)[0:5]
      results[vote.choice.choice] = (votes_count, votes_percent)
      
    results = sorted(results.iteritems(), key = operator.itemgetter(1))
    results.reverse()

  return render_to_response('results.html',
                           {             'user': username,
                                         'poll': poll,
                                      'results': results,
                             'total_abstention': total_abstention,
                             'logged_in': logged_in }, context_instance = RequestContext(request))
                             
def votes_list(request, poll_id):
  if not request.user.is_authenticated():
    return HttpResponseRedirect('/')
  else:
    logged_in = True
    
  try:
      poll = Poll.objects.get(pk = poll_id)
  except Poll.DoesNotExist:
      raise Http404
 
  username = request.user.username
  if ((not poll.is_allowed_voter(username)) and (poll.creator != request.user)) or (poll.ends > datetime.datetime.now()):
      return HttpResponseRedirect('/mypolls')
  
  total_abstention = False
  try:
    votes = Vote.objects.filter(choice__poll = poll).order_by('tag')
  except Vote.DoesNotExist:
    total_abstention = True
  
  vote_tags = {}
  if not votes: 
    total_abstention = True
  else:
    for vote in votes:
      try: 
        vote_tags[vote.tag]
      except KeyError: 
        vote_tags[vote.tag] = []
      vote_tags[vote.tag] = vote_tags[vote.tag] + [vote.choice]
	
  vote_tags = sorted(vote_tags.iteritems(), key = operator.itemgetter(1))
  
  return render_to_response('votes_list.html',
                           {             'user': username,
                                         'poll': poll,
                                        'votes': vote_tags,
                             'total_abstention': total_abstention,
                             'logged_in': logged_in }, context_instance = RequestContext(request))
                             
def voters_list(request, poll_id):
  if not request.user.is_authenticated():
    return HttpResponseRedirect('/')
  else:
    logged_in = True
    
  try:
      poll = Poll.objects.get(pk = poll_id)
  except Poll.DoesNotExist:
      raise Http404
 
  username = request.user.username
  if ((not poll.is_allowed_voter(username)) and (poll.creator != request.user)):
      return HttpResponseRedirect('/mypolls')
  
  allowed_voters = poll.allowed_voters.split(';')
  
  qobject = Q()
  for voter in allowed_voters:
    if voter == '': 
      continue
    else:
      qobject = qobject | Q(username=voter)
  
  voters = User.objects.filter(qobject).order_by('pgpkey__name')
    
  return render_to_response('voters_list.html',
                           {      'user': username,
                                  'poll': poll,
                                'voters': voters,
                             'logged_in': logged_in }, context_instance = RequestContext(request))