# Find this in app.py - the QRPinVerificationForm class
# Replace it with this:

class QRVerificationWithPinForm(FlaskForm):
    qr_data = HiddenField('QR Data', validators=[DataRequired()])
    pin = StringField('PIN', validators=[DataRequired(), Length(min=4, max=4, message='PIN must be exactly 4 digits')])
