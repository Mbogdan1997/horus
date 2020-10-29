from flask_wtf import FlaskForm
from wtforms import SelectField, SelectMultipleField, SubmitField, validators, widgets
from wtforms.validators import DataRequired
from wtforms.widgets import CheckboxInput, html_params
from wtforms.fields.html5 import DateField
from flask_wtf.file import FileField, FileRequired, FileAllowed
from markupsafe import Markup
import datetime


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def select_multi_checkbox(field, div_class='form-check', **kwargs):
    kwargs.setdefault('type', 'checkbox')
    field_id = kwargs.pop('id', field.id)
    html = [u'<div %s>' % html_params(id=field_id, class_=div_class)]
    for value, label, checked in field.iter_choices():
        choice_id = u'%s-%s' % (field_id, value)
        options = dict(kwargs, name=field.name+value, value=value, id=choice_id)
        options['class'] = 'form-check-input'
        if checked:
            options['checked'] = 'checked'
        html.append(u'<div class="form-check form-check-inline"><input %s /> ' % html_params(**options))
        html.append(u'<label class="form-check-label for="%s">%s</label></div>' % (field_id, label))
    html.append(u'</div>')
    return Markup(u''.join(html))


class HorusForm(FlaskForm):
    list_of_files = [' ']
    files = [(x, x) for x in list_of_files]
    satelite = SelectField('satelite', 
                            choices=[('SENTINEL2_L2A', 'SENTINEL 2'), ('LANDSAT8_L1C', 'LANDSAT'), ('MODIS', 'MODIS')], 
                            validators=[DataRequired()])
    bands = SelectMultipleField('bands', 
                                 choices=files, 
                                 widget=select_multi_checkbox)
    indexes = SelectMultipleField('indexes', 
                                  choices=files, 
                                  widget=select_multi_checkbox)
    extra = SelectMultipleField('extra', 
                                 choices=files, 
                                 widget=select_multi_checkbox)
    weather = SelectMultipleField('weather', 
                                   choices=[('TEMP', 'TEMP'), ('HUM', 'HUM'), ('PRES','PRES')], 
                                   widget=select_multi_checkbox)
    date_from = DateField('startdate', 
                           validators = [validators.DataRequired()], 
                           format='%Y-%m-%d')
    date_to = DateField('enddate', 
                         validators = [validators.DataRequired(message="End date must be selected.")], 
                         format='%Y-%m-%d')
    poi = FileField('measurepoints', 
                     validators=[FileRequired()])
    learning = SelectField('satelite', 
                            choices=[('Supervised', 'Supervised'), ('Unsupervised', 'Unsupervised'), ('Semi-supervised', 'Semi-supervised')], 
                            validators=[DataRequired()])
    submit = SubmitField('Submit')

    def validate_on_submit(self):
        result = super(HorusForm, self).validate()
        
        if (self.date_from.data>self.date_to.data):
            return False
        else:
            return result
