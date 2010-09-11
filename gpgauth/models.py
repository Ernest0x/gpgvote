from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from gnupg import GPG

class PGPkey(models.Model):
  user = models.OneToOneField(User)
  name = models.CharField(max_length=100)
  fingerprint = models.CharField(unique=True, max_length=50)
  renew_passwd = models.CharField(max_length=35)
  is_trusted = models.BooleanField(default=False)
  
  def __init__(self, *args, **kwargs):
    super(PGPkey, self).__init__(*args, **kwargs) 
    self.clean()
    
  def clean(self):
    gpg = GPG(gpgbinary=settings.GNUPGBINARY, gnupghome=settings.GNUPGHOME)
    key = gpg.get_key(self.fingerprint)
    if key['ownertrust'] in settings.TRUST_LEVELS:
      self.is_trusted = True
    else:
      self.is_trusted = False
    self.save()
            
  def __unicode__(self):
    return self.fingerprint