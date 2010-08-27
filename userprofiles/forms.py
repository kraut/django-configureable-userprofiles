# -*- coding: utf-8 -*-
from django import forms
from django.db.models import Q
from django.forms.models import modelform_factory, fields_for_model
from django.contrib.contenttypes.models import ContentType 
from django.utils.translation import ugettext_lazy as _

from django.contrib.auth.forms import UserCreationForm
from  models import UserProfileField, StoreValues, UserProfile
from django import db
from django.contrib.auth.models import User, Group
from django.conf import settings
### --- F O R M S --- ###
class UserProfileFieldForm(forms.ModelForm):
    class Meta:
        model = UserProfileField
    def __init__(self, *a, **kw):
        forms.ModelForm.__init__(self, *a, **kw)
        #@TODO: help me to make this more generic, plz ;)
        self.fields['content_type'].queryset =ContentType.objects.filter( 
                        Q(app_label='userprofiles') ).exclude(Q(name='Field') |
                                Q(name='Value') | Q(name='user profile') | 
                                Q(name="generic field"))




class ValueAdminForm(forms.ModelForm):
    ''' Not really needed cause of inline edit in UserAdmin.
        see below.
    '''
    class Meta:
        model = StoreValues
        exclude =('value_type','value_id')
    value = forms.CharField()
    
    def _get_field(self, cd):
        ''' needed for subforms which do not provide 'field' FormFiel. 
            ie: UserProfileInlineForm.
        '''
        return cd.get('field')

    def __init__(self, *a, **kw):
        super(ValueAdminForm, self).__init__(*a, **kw)
        instance = kw.get('instance')
        if instance:
            #@TODO: add is_required logic
            if hasattr(instance.value_object,'form_field'):
                self.fields['value'] = instance.value_object.form_field()
            elif hasattr(instance.value_object,'widget'):
                self.fields['value'].widget = instance.value_object.widget 
            self.fields['value'].initial = getattr(instance.value_object, 'value', '')

    def clean(self):
        cd = self.cleaned_data
        SettingClass = self._get_field(cd).content_type.model_class()
        if hasattr(self.instance.value_object, 'form_field'):
            SettingClassForm = self.instance.value_object.form_field()
        else:
            SettingClassForm = fields_for_model(SettingClass, fields =('value',))['value']
        value = cd.get('value')

        #@TODO:Needed for boolean Field
        #      Place this in widget
        if value =='on': value='True';

        SettingClassForm.validate(value)
        return cd


    def save(self, *args, **kwargs):
        cd = self.clean()

        #XXX: Whats up with 
        if self.instance and self.instance.value_id:
            value_object = self.instance.value_object
            if hasattr(value_object, 'delete'):value_object.delete()

        switch_vals = { 'on': 1,  #needed cause of Boolean Checkbox Bug!?
                'False':0, }#@TODO: place this in widget
        if cd['value'] in switch_vals.keys():
            value = switch_vals[cd['value']]
        else:
            value = cd['value']
        kwargs['commit'] = False
        instance = super(ValueAdminForm, self).save(*args, **kwargs)
        
        SettingClass = self._get_field(cd).content_type.model_class()

        #prevent double entries
        if SettingClass.objects.all().filter(value=value):
            value_object = SettingClass.objects.get(value=value)
        else:
            value_object= SettingClass.objects.create(value=value)

        value_object.value = bool(cd['value'])
        instance.value_id = value_object.id
        instance.save()
        return instance


class UserChangeCustForm(forms.ModelForm):
    ''' UserChangeForm including UserProfile.
        Inherit from this to customize it, instead of changing this class.
        Because this is the generic user change form for several subforms.
    '''
    profile = None
    def __init__(self, *a, **kw):
        super(UserChangeCustForm, self).__init__(*a, **kw)
        instance = kw.get('instance')
        if not self.profile:
            if instance:
                profile = instance.profile
        else:
            profile = self.profile
        i=0
        if profile:
            field_names=()
            field_name_mapping={}
            for field in profile.fields.all():
                field_name_mapping[field.name]='pfield%s'%i
                self.fields['pfield%s'%i] = forms.CharField(max_length=255)
                #cutom form field (non CharFields)
                if hasattr(field.content_type.model_class(),'form_field'):
                    self.fields['pfield%s'%i] = field.content_type.model_class().form_field()
                elif hasattr(field.content_type.model_class(),'widget'):
                    self.fields['pfield%s'%i].widget = field.content_type.model_class().widget 
                #value
                val_lookup=StoreValues.objects.filter(user=instance, profile=profile, field=field)
                if val_lookup: 
                    self.fields['pfield%s'%i].initial = val_lookup[0].value_object.value
                self.fields['pfield%s'%i].label = field.displayed_name
                self.fields['pfield%s'%i].help_text = field.description
                self.fields['pfield%s'%i].required = field.is_required
                field_names += ('pfield%s'%i,)
                i+=1
            self.field_count=i;#need for save, clean
            self.fieldset_el= ('Profile', {'fields': field_names})

            #adjust fieldorder
            #@XXX: Its a hack, only default fields are oderable
            #@TODO: create a new model fieldorder with int position and fk to field, profile
            field_names=getattr(settings, 'USER_PROFILES')[profile.identifier]
            tmp_order_list=()
            for f in self.fields.keyOrder:
                if not 'pfield' in f:
                    tmp_order_list+=(f,)

            for fname in field_names:
                tmp_order_list += (field_name_mapping[fname],)
            
            self.fields.keyOrder=tmp_order_list


    def save(self, *args, **kwargs):
        cd = self.clean()
        switch_vals = { 'on': 1,  #needed cause of Boolean Checkbox Bug!?
                'False':0, }#@TODO: place this in widget
        #groups
        if getattr(cd, 'profile', None):
            groups=Group.objects.filter(profile=cd['profile'])
            cd['groups'] = groups
        # users have one profile type, should automatically become
        # members of related groups. 
        instance = super(UserChangeCustForm, self).save(*args, **kwargs)
        if not self.profile:
            self.profile = getattr(cd, 'profile', None)
        if self.profile:
            instance.profile =self.profile
            instance.groups = Group.objects.filter(profile=self.profile)
            #create values
        try:
            i=0
            for field in instance.profile.fields.all():
                    
                if cd['pfield%s'%i] in switch_vals.keys():
                    value = switch_vals[cd['pfield%s'%i]]
                else:
                    value = cd['pfield%s'%i]
                StoreValues.objects.set_value(field,instance, 
                        instance.profile, field.content_type.model_class(), 
                        value)
                i+=1
        except KeyError, e:
            pass # if userprofile is set the first time
        instance.save()
        return instance
            
    class Meta:
        model = User

class UserCreateForm(UserChangeCustForm, UserCreationForm):
    ''' Simple form to create Users '''

    def __init__(self, *a, **kw):
        UserCreationForm.__init__(self,*a, **kw)
        UserChangeCustForm.__init__(self,*a, **kw)

    class Meta:
        model = User
        exclude = (  'groups',  'profile','password', 'user_permissions', 'last_login',
                    'date_joined', 'is_superuser', 'is_active', 'is_staff')

class UserCreateNoUsernameForm(UserCreateForm):
    ''' Simple form to create users 'without' username. 
        Email is used as username instead.
        username and email field will get the same values.
    '''
    class Meta:
        exclude = UserCreateForm.Meta.exclude + ('email',)
        model =  UserChangeCustForm.Meta.model
    def __init__(self, *a, **kw):
        if a: a[0][u'email'] = a[0][u'username']
        super(UserCreateNoUsernameForm, self).__init__(*a, **kw)
        self.fields['username'] = forms.EmailField()
        self.fields['username'].label = _("Email") 

    def save(self, *a, **kw):
        user = super(UserCreateNoUsernameForm, self).save(*a, **kw)
        user.email = user.username
        user.save()
        return user
    
