from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from guardian.shortcuts import get_users_with_perms, get_objects_for_user
from crispy_forms.helper import FormHelper, Layout
from crispy_forms.layout import Div, Field, HTML

from core.mixins.forms import G3WRequestFormMixin, G3WProjectFormMixin
from usersmanage.models import Group as AuthGroup
from usersmanage.utils import get_users_for_object, get_groups_for_object, userHasGroups, get_viewers_for_object
from usersmanage.forms import label_users
from usersmanage.configs import *


class ActiveEditingLayerForm(G3WRequestFormMixin, G3WProjectFormMixin, forms.Form):

    active = forms.BooleanField(label=_('Active'), required=False)
    scale = forms.IntegerField(label=_('Scale'), required=False, help_text=_('Scale after that editing mode is active'))
    viewer_users = forms.MultipleChoiceField(choices=[], label=_('Viewers'), required=False,
                                             help_text=_('Select user with viewer role can do editing on layer'))
    user_groups_viewer = forms.MultipleChoiceField(
        choices=[], required=False,  help_text=_('Select VIEWER groups can do editing on layer'),
        label=_('User viewer groups')
    )

    def __init__(self, *args, **kwargs):

        super(ActiveEditingLayerForm, self).__init__(*args, **kwargs)

        # set choices
        self._set_viewer_users_choices()
        self._set_viewer_user_groups_choices()

        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.layout = Layout(
            HTML(_('Check on uncheck to attive/deactive editing layer capabilities:')),
            'active',
            'scale',
            HTML(_('Select viewers with \'view permission\' on project that can edit layer:')),
            Field('viewer_users', css_class='select2', style="width:100%;"),
            Field('user_groups_viewer', css_class='select2', style="width:100%;"),
        )

    def _set_viewer_users_choices(self):
        """
        Set choices for viewer_users select by permission on project and by user main role
        """

        with_anonymous = getattr(settings, 'EDITING_ANONYMOUS', False)
        viewers = get_viewers_for_object(self.project, self.request.user, 'view_project', with_anonymous=with_anonymous)

        # get Editor Level 1 and Editor level 2 to clear from list
        editor_pk = self.project.editor.pk if self.project.editor else None
        editor2_pk = self.project.editor2.pk if self.project.editor2 else None

        self.fields['viewer_users'].choices = [(v.pk, label_users(v)) for v in viewers
                                               if v.pk not in (editor_pk, editor2_pk)]

    def _set_viewer_user_groups_choices(self):
        """
        Set choices for viewer_user_groups select by permission on project and by user main role
        """

        # add user_groups_viewer choices
        user_groups_viewers = get_groups_for_object(self.project, 'view_project', grouprole='viewer')

        # for Editor level filter by his groups
        if userHasGroups(self.request.user, [G3W_EDITOR1]):
            editor1_user_gorups_viewers = get_objects_for_user(self.request.user, 'auth.change_group',
                                 AuthGroup).order_by('name').filter(grouprole__role='viewer')

            user_groups_viewers = list(set(user_groups_viewers).intersection(set(editor1_user_gorups_viewers)))

        self.fields['user_groups_viewer'].choices = [(v.pk, v) for v in user_groups_viewers]