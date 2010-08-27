# -*- coding: utf-8 -*-
import django
from django.contrib import admin
from django.contrib.contenttypes import generic
from models import UserProfileField, UserProfile, StoreValues
from forms import UserProfileFieldForm
from forms import ValueAdminForm
from forms import UserChangeCustForm
from django.utils.translation import ugettext, ugettext_lazy as _
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from django.contrib.auth.forms import UserCreationForm

def get_value(obj):
    return obj.value_object.value
get_value.short_description = _('Value')

#def get_setting_description(obj):
#    return obj.setting_object.description



class UserProfileFieldAdmin(admin.ModelAdmin):
    model = UserProfileField
    form = UserProfileFieldForm
admin.site.register(UserProfileField, UserProfileFieldAdmin)


from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType 
from django.db.models import Q
from django.forms.models import modelform_factory
from django.forms.models import inlineformset_factory

class UserProfileFieldInline(admin.TabularInline ):
    model = UserProfile.fields.through
    verbose_name = _("User profile field")
    verbose_name_plural = _("User profile fields")
    extra= 1

class UserProfileAdmin(admin.ModelAdmin):
    #model = models.UserProfile
    #inlines = [ UserProfileFieldInline, ]
    pass

class StoreValuesAdmin(admin.ModelAdmin):
    form = ValueAdminForm
    list_display=('field',get_value, 'user')
admin.site.register(UserProfile, UserProfileAdmin)

#not realy needed only for testing
#admin.site.register(StoreValues, StoreValuesAdmin)


admin.site.unregister(User)
from django.forms.formsets import formset_factory

class GenericUserChangeAdminForm(UserChangeCustForm):
    def __init__(self,*a, **kw):
        try:
            admin_class = kw['admin_class']
            del kw['admin_class']
        except KeyError, e:
            raise Exception('%s needs admin_class as keyword argument' %
                    'GenericUserChangeAdminForm')

        super(GenericUserChangeAdminForm, self).__init__(*a, **kw)

        #@XXX: i dont know how to make this better, help me ;)
        #       without this admin does not show dynamic fields.
        fset_idx =-1
        idx=None
        for s in admin_class.fieldsets:
            fset_idx+=1
            if s[0] == 'Profile':
                idx = fset_idx
                break
        #replace profile section
        if hasattr(self, 'fieldset_el'):
            if idx :#len(admin.UserCustAdmin.fieldsets)> fset_idx>-1:
                temp = list(admin_class.fieldsets)
                temp[idx] = self.fieldset_el
                admin_class.fieldsets = tuple(temp)
            else:
                admin_class.fieldsets+=(self.fieldset_el,)


class UserChangeAdminForm(GenericUserChangeAdminForm):
    def __init__(self,*a, **kw):
        kw['admin_class'] = UserCustAdmin
        super(UserChangeAdminForm, self).__init__(*a, **kw)

        
class UserCustAdmin(UserAdmin):
    model =User

    #note: it has to stand here, not in ctor
    #fieldsets =UserAdmin.fieldsets + (('Profiltyp', {'fields':('profile',)}),)

    form = UserChangeAdminForm
    list_display = UserAdmin.list_display + ('get_profile',)
    def __init__(self, *a, **kw):
        super(UserCustAdmin, self).__init__(*a, **kw)
        self.add_fieldsets+=((_('Misc'),{ 'fields':('profile',)}),)

admin.site.register(User, UserCustAdmin)
