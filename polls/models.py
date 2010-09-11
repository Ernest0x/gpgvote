from django.db import models
from django.conf import settings
from django.contrib.auth.models import User

class Poll(models.Model):
  creator = models.ForeignKey(User)
  question = models.TextField()
  min_choices = models.PositiveIntegerField()
  max_choices = models.PositiveIntegerField()
  allowed_voters = models.TextField('voters allowed to vote')
  who_voted = models.TextField('voters who have already voted')
  starts = models.DateTimeField()
  ends = models.DateTimeField()
    
  def __unicode__(self):
    return self.question
  
  def has_voted(self, voter):
    if voter in self.who_voted.split(';'):
      return True
    else:
      return False
 
  def add_voter(self, voter, To):
    if To == 'allowed_voters': 
      self.allowed_voters = self.allowed_voters + voter + ';' 
    elif To == 'who_voted':
      if voter in self.allowed_voters.split(';'):
        self.who_voted = self.who_voted + voter + ';'
      
  def remove_voter(self, voter, From):
    if From == 'allowed_voters': 
      self.allowed_voters = self.allowed_voters.replace(voter+';', '')
    elif From == 'who_voted':
      self.who_voted = self.who_voted.replace(voter+';', '')
      
  def is_allowed_voter(self, voter):
    if voter in self.allowed_voters.split(';'):
      return True
    else:
      return False
      
class Choice(models.Model):
  poll = models.ForeignKey(Poll)
  choice = models.CharField(max_length=255)
  
  def __unicode__(self):
    return self.choice
    
class Vote(models.Model):
  choice = models.ForeignKey(Choice)
  tag = models.CharField(max_length=35)
  
  def __unicode__(self):
    return '\'' + self.tag + '\' vote tag includes choice: ' + '\'' + str(self.choice) + '\''