# -*- coding: utf-8 -*-
from django.db import models
from django.contrib import  auth
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _


from django.forms import widgets
from django.forms import extras

from django import forms

### --- Form Fields for validation --- ###
class IntegerField(forms.fields.RegexField):#, forms.IntegerField):
    default_error_messages = {
        'invalid': _('Enter numbers only .'),
    }
    def __init__(self, *args, **kwargs):
        forms.fields.RegexField.__init__(self,r'^-*\d*$',
            max_length=None, min_length=None, *args, **kwargs)

class PositiveIntegerField(forms.fields.RegexField):#, forms.IntegerField):
    default_error_messages = {
        'invalid': _('Enter (positive) numbers only .'),
    }
    def __init__(self, *args, **kwargs):
        forms.fields.RegexField.__init__(self,r'^\d*$',
            max_length=None, min_length=None, *args, **kwargs)

### --- Value Models ---# 
class BaseField(models.Model):
    widget = widgets.TextInput() 
    class Meta:
        abstract = True

    def __unicode__(self):
        return u'%s' % self.value

class String(BaseField):
    value = models.CharField(max_length=254)

class Integer(BaseField):
    value = models.IntegerField()
    form_field = IntegerField

class PositiveInteger(BaseField):
    value = models.PositiveIntegerField()
    form_field = PositiveIntegerField

class Boolean(BaseField):
    value = models.BooleanField()
    widget = widgets.CheckboxInput(check_test=(lambda a: bool(a)) )

class Date(BaseField):
    value = models.DateField()
    widget = extras.widgets.SelectDateWidget()

from django.contrib.localflavor.de.forms import DEZipCodeField, DEStateSelect
class Zip(BaseField):
    value = models.CharField(max_length=5)
    form_field = DEZipCodeField

class State(BaseField):
    value = models.CharField(max_length=50)
    widget = DEStateSelect()

class GenericField(BaseField):
    #@TODO:!!!!!!!
    value = models.CharField(max_length=255)
    regex = models.CharField(max_length=255) #specifies format of value 

class ValueManager(models.Manager):
    #TODO: remove name attr !?
    def get_value(self, field, user, profile, **kw):
        if 'default' in kw:
            if not self.value_object_exists(name):
                return kw.get('default')
        return self.get(field=field, user=user, profile=profile).\
                value_object.value


    def value_object_exists(self, field, user, profile):
        print "val obj"
        queryset = self.filter(field=field, user=user, profile=profile)
        return queryset.exists() and queryset[0].value_object


    def set_value(self, field, user, profile, FieldClass, value):
        print "set val"
        setting = StoreValues(field=field, user=user, profile=profile)
        print "set val"
        if self.value_object_exists(field,user,profile):
            setting = self.get(field=field, user=user, profile=profile)
            value_object = setting.value_object
            value_object.delete()

        setting.value_object = FieldClass.objects.create(value=value)#,
               
        setting.save()
        return setting


### --- Profile Models --- ###
class ProfileFieldManager(models.Manager):

    def set_field(self, name, displayed_name, desc, is_required, type_name):
        TypeClass = ContentType.objects.get(
                app_label='userprofiles', 
                model=type_name.lower()
                )#.model_class()
        field = UserProfileField.objects.create(name=name, 
                    displayed_name=displayed_name, description=desc,
                    is_required=is_required, content_type=TypeClass)
        field.save()
        return field 

class UserProfileField(models.Model):
    class Meta:
        verbose_name = _('Field')
        verbose_name_plural = _('Fields')
        unique_together=(('name', 'content_type'),)
    
    name = models.CharField(max_length=255)
    displayed_name = models.CharField(max_length=255)
    description = models.TextField(_('description'))
    is_required = models.BooleanField()

    content_type = models.ForeignKey(ContentType)

    objects = ProfileFieldManager()

    def __unicode__(self):
        return u''+self.name

class UserProfile(models.Model):
    #id = models.AutoField(unique=True, blank=False, primary_key=True)
    identifier = models.CharField(max_length=100, blank=False)
    fields = models.ManyToManyField(UserProfileField, blank=True)


    def __unicode__(self):
        return u''+self.identifier

        

### --- Extend auth --- ###
#User
def get_profile(self):
    return self.profile


auth.models.User.add_to_class( 'profile', 
        models.ForeignKey(UserProfile, null=True))
auth.models.User.add_to_class( 'get_profile',
        get_profile)
oldinit=  auth.models.User.__init__
def newinit(self, *a, **kw):
    oldinit(self, *a, **kw)
    try:
        #print "self"
        #print dir(self)
        #print "profile"
        #print self.profile
        if self.profile:
            field_li = self.profile.fields.all()
            for field in field_li:
        #        print field
                def t():
                    qs=field.store_value.filter(profile=self.profile, user=self)#auth.models.Group.objects.filter(profile=self, user=self.user).all())
                    if qs.exists(): return qs[0].value_object.value
                    else: return ''
                
                setattr(self, field.name, t)
        #    print "after self"
        #    print dir(self)
    except ValueError, e:
        pass

auth.models.User.add_to_class( '__init__',
        newinit)
#Groups
# users have one profile type, should automatically become
# members related groups. see UserChangeCustForm
auth.models.Group.add_to_class('profile', 
        models.ForeignKey(UserProfile, verbose_name=_('profiles'), blank=True,
        help_text=_("MISSING"))
        )

class StoreValues(models.Model):
    class Meta:
        verbose_name = _('Value')
        verbose_name_plural = _('Values')
        unique_together = (('field','user','profile'),)

    field = models.ForeignKey(UserProfileField, related_name='store_value')
    profile = models.ForeignKey(UserProfile)
    user = models.ForeignKey(auth.models.User)

    ### - Value
    objects = ValueManager()
    
    #XXX: value_type is a fake field not realy used
    #       need for GenericForeignKey
    #       real contentype is stored in in field model, see __ini__
    value_type =models.ForeignKey(ContentType, null=True)        

    value_id = models.PositiveIntegerField()
    value_object = generic.GenericForeignKey('value_type', 'value_id')
    
    def __init__(self, *a, **kw):
        super(StoreValues, self).__init__(*a, **kw)
        if getattr(self, 'field_id', False):
            setattr(self,'value_type' , self.field.content_type)

        

