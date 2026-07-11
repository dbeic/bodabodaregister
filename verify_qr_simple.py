@app.route('/verify-qr', methods=['GET', 'POST'])
def verify_qr():
    error = None
    verified_member = None
    show_pin_form = False
    member = None
    qr_token = None
    
    # Check session for token after PIN verification
    if 'qr_verification_token' in session:
        qr_token = session.get('qr_verification_token')
        member = get_member_by_qr_token(qr_token)
        if member:
            session.pop('qr_verification_token', None)
            verified_member = member
            log_qr_pin_verification(member['id'], 'Public', True, request.remote_addr, request.user_agent.string)
            return render_template('verify_qr.html', 
                                 form=QRVerificationForm(), 
                                 pin_form=QRVerificationWithPinForm(),
                                 verified_member=verified_member,
                                 error=None)
    
    # Handle POST request
    if request.method == 'POST':
        # Check if this is the PIN submission
        if 'pin' in request.form and 'qr_data' in request.form:
            # PIN submission
            qr_data = request.form.get('qr_data')
            pin = request.form.get('pin')
            
            # Find member
            member = get_member_by_qr_token(qr_data)
            if not member and qr_data.startswith('BBS-'):
                parts = qr_data.split('-')
                if len(parts) >= 2:
                    member = get_member_by_number(parts[1])
            
            if not member:
                error = 'Invalid QR code. Member not found.'
                return render_template('verify_qr.html', 
                                     form=QRVerificationForm(), 
                                     pin_form=QRVerificationWithPinForm(),
                                     error=error)
            
            # Verify PIN
            result = verify_qr_pin(member['id'], pin, bcrypt)
            
            if result['success']:
                verified_member = member
                log_qr_pin_verification(member['id'], 'Public', True, request.remote_addr, request.user_agent.string)
                session.pop('qr_verification_token', None)
                return render_template('verify_qr.html', 
                                     form=QRVerificationForm(), 
                                     pin_form=QRVerificationWithPinForm(),
                                     verified_member=verified_member,
                                     error=None)
            else:
                error = result.get('error', 'Invalid PIN')
                log_qr_pin_verification(member['id'], 'Public', False, request.remote_addr, request.user_agent.string)
                show_pin_form = True
                qr_token = qr_data
                return render_template('verify_qr.html', 
                                     form=QRVerificationForm(), 
                                     pin_form=QRVerificationWithPinForm(),
                                     show_pin_form=True,
                                     member=member,
                                     qr_token=qr_token,
                                     error=error)
        
        # QR code submission
        elif 'qr_data' in request.form:
            qr_data = request.form.get('qr_data').strip()
            
            # Try direct token lookup
            member = get_member_by_qr_token(qr_data)
            
            # If not found, try extracting member number
            if not member and qr_data.startswith('BBS-'):
                parts = qr_data.split('-')
                if len(parts) >= 2:
                    member = get_member_by_number(parts[1])
                    if member:
                        update_member(member['id'], {'qr_code_data': qr_data})
            
            # If still not found, try as member number
            if not member:
                member = get_member_by_number(qr_data)
            
            if not member:
                error = 'Invalid QR code. Member not found.'
                return render_template('verify_qr.html', 
                                     form=QRVerificationForm(), 
                                     pin_form=QRVerificationWithPinForm(),
                                     error=error)
            
            # Check if PIN is required
            if has_qr_pin(member['id']):
                session['qr_verification_token'] = qr_data
                show_pin_form = True
                qr_token = qr_data
                return render_template('verify_qr.html', 
                                     form=QRVerificationForm(), 
                                     pin_form=QRVerificationWithPinForm(),
                                     show_pin_form=True,
                                     member=member,
                                     qr_token=qr_token,
                                     error=None)
            else:
                verified_member = member
                log_qr_pin_verification(member['id'], 'Public', True, request.remote_addr, request.user_agent.string)
                return render_template('verify_qr.html', 
                                     form=QRVerificationForm(), 
                                     pin_form=QRVerificationWithPinForm(),
                                     verified_member=verified_member,
                                     error=None)
    
    # GET request or fallback
    return render_template('verify_qr.html', 
                         form=QRVerificationForm(), 
                         pin_form=QRVerificationWithPinForm(),
                         error=error)
