from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FloatField, IntegerField, SelectField
from wtforms.validators import Length, ValidationError, InputRequired, NumberRange, Email
from models import User, InventoryItem


class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=150)],
                           render_kw={'placeholder': 'Username'})
    email = StringField('Email', validators=[InputRequired(), Email()],  # Add email field
                        render_kw={'placeholder': 'Email'})
    password = PasswordField('Password', validators=[InputRequired(), Length(min=4, max=150)],
                             render_kw={'placeholder': 'Password'})
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already exists. Please use a different one.')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=150)],
                           render_kw={'placeholder': 'Username'})
    password = PasswordField('Password', validators=[InputRequired(), Length(min=4, max=150)],
                             render_kw={'placeholder': 'Password'})
    submit = SubmitField('Login')


class InventoryItemForm(FlaskForm):
    item_name = StringField('Item Name', validators=[InputRequired(), Length(max=100)],
                            render_kw={'placeholder': 'Item Name'})
    quantity = IntegerField('Quantity', validators=[InputRequired(), NumberRange(min=0)],
                            render_kw={'placeholder': 'Quantity'})
    price = FloatField('Price', validators=[InputRequired(), NumberRange(min=0)],
                       render_kw={'placeholder': 'Price'})
    submit = SubmitField('Save Item')


class SaleForm(FlaskForm):
    item_id = SelectField('Select Item', coerce=int, validators=[InputRequired()])
    quantity = IntegerField('Quantity Sold', validators=[InputRequired(), NumberRange(min=1)],
                            render_kw={'placeholder': 'Quantity Sold'})
    submit = SubmitField('Record Sale')

    def __init__(self, *args, **kwargs):
        super(SaleForm, self).__init__(*args, **kwargs)
        self.item_id.choices = [(item.id, f"{item.item_name} (Stock: {item.quantity})")
                                for item in InventoryItem.query.all()]


class DiscountForm(FlaskForm):
    item_id = SelectField('Select Item', coerce=int, validators=[InputRequired()])
    discount = FloatField('Discount Percentage', validators=[InputRequired(), NumberRange(min=0, max=100)],
                          render_kw={'placeholder': 'Discount %'})
    submit = SubmitField('Apply Discount')

    def __init__(self, *args, **kwargs):
        super(DiscountForm, self).__init__(*args, **kwargs)
        self.item_id.choices = [(item.id, item.item_name) for item in InventoryItem.query.all()]


class SearchForm(FlaskForm):
    search_query = StringField('Search', validators=[InputRequired()],
                               render_kw={'placeholder': 'Search inventory...'})
    submit = SubmitField('Search')