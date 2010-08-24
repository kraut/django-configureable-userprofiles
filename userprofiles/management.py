# -*- coding: utf-8 -*-
from django.db.models import signals
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

import models



DEFAULT_FIELDS = getattr(settings, 'USER_PROFILE_FIELDS', {})
DEFAULT_PROFILES = getattr(settings, 'USER_PROFILES')



def initialize_data(sender, **kwargs):
    #--- fields
    fields = {} 
    for name, type_name_and_value in DEFAULT_FIELDS.items():
        displayed_name, description, type_name, is_required = type_name_and_value
        if not models.UserProfileField.objects.filter(name=name):
            fields[name]=models.UserProfileField.objects.set_field(
                    name,
                    displayed_name,
                    description,
                    is_required,
                    type_name)
    
    #--- user profiles
    for name, pfields in DEFAULT_PROFILES.items():
        if models.UserProfile.objects.filter(identifier=name):
            p=models.UserProfile.objects.get(identifier=name)
        else:
            p=models.UserProfile.objects.create(identifier=name)
        for fname in pfields:
            try:
                field2add = fields[fname]
            except KeyError, e:
                db_lookup = models.UserProfileField.objects.filter(name=fname)           
                if db_lookup:
                    field2add = db_lookup[0]
                else:    
                    #@TODO: remove print
                    print "Are youe missed to define field: "+str(e)
            p.fields.add(field2add)
        p.save()
signals.post_syncdb.connect(initialize_data, sender=models)