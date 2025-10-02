from django.db import models

# Create your models here.

class Settings(models.Model):
    inventory = models.BooleanField(default=False)
    human_resources = models.BooleanField(default=False)
    pos = models.BooleanField(default=False)
    accounting = models.BooleanField(default=False)
    authentication = models.BooleanField(default=False)
    authorization = models.BooleanField(default=False)
    active = models.BooleanField(default=False)
    
    class Meta:
        verbose_name_plural = 'settings'


