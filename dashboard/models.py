from django.db import models
from django.contrib.auth.models import User

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


class Service(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)



class Expenses(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    expenses_name = models.ForeignKey(Service, on_delete=models.CASCADE)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()

    class Meta:
        verbose_name_plural = 'Expenses'