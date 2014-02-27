import framework.status as status

from wtforms import fields, Form, PasswordField, BooleanField, IntegerField, \
    DateField, DateTimeField, FileField, HiddenField, RadioField, SelectField, \
    SelectMultipleField, SubmitField, TextAreaField, TextField, FieldList, \
    validators

from wtforms.widgets import TextInput, PasswordInput, html_params, TextArea
from wtforms.validators import ValidationError

from wtfrecaptcha.fields import RecaptchaField

from framework.forms.utils import sanitize


class MyTextInput(TextInput):
    def __init__(self, error_class=u'has_errors'):
        super(MyTextInput, self).__init__()

    def __call__(self, field, **kwargs):
        kwargs.setdefault('class', 'span12')
        return super(MyTextInput, self).__call__(field, **kwargs)

# TODO(sloria): Allow for placeholder text
class BootstrapTextInput(TextInput):
    '''Custom TextInput that sets a field's class to 'form-control'.'''
    def __call__(self, field, **kwargs):
        kwargs.setdefault('class', 'form-control')
        kwargs.setdefault('class_', 'form-control')
        return super(BootstrapTextInput, self).__call__(field, **kwargs)


class BootstrapPasswordInput(PasswordInput):
    '''Custom PasswordInput that sets a field's class to 'form-control'.'''

    def __call__(self, field, placeholder=None, **kwargs):
        kwargs.setdefault('class', 'form-control')
        kwargs.setdefault('class_', 'form-control')
        html = super(BootstrapPasswordInput, self).__call__(field, **kwargs)
        return html

class BootstrapTextArea(TextArea):
    '''Custom TextArea that sets a field's class to 'form-control'.'''

    def __call__(self, field, placeholder=None, **kwargs):
        kwargs.setdefault('class', 'form-control')
        kwargs.setdefault('class_', 'form-control')
        html = super(BootstrapTextArea, self).__call__(field, **kwargs)
        return html

RecaptchaField = RecaptchaField

validators = validators


def push_errors_to_status(errors):
    if errors:
        for field, throwaway in errors.items():
            for error in errors[field]:
                status.push_status_message(error)


class NoHtmlCharacters(object):
    """ Raises a validation error if an email address contains characters that
    we escape for HTML output

    TODO: This could still post a problem if we output an email address to a
    Javascript literal.
    """

    def __init__(self, message=None):
        self.message = message or u'Illegal characters in field'

    def __call__(self, form, field):
        if not field.data == sanitize(field.data):
            raise ValidationError(self.message)

# Filters

def lowered(s):
    if s:
        return s.lower()
    return s

def lowerstripped(s):
    if s:
        return s.lower().strip()
    return s

def stripped(s):
    if s:
        return s.strip()
    return s
