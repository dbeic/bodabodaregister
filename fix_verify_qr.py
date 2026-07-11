@app.route('/verify-qr', methods=['GET', 'POST'])
def verify_qr():
    form = QRVerificationForm()
    pin_form = QRPinVerificationForm()
    member = None
    error = None
    qr_token = None
    show_pin_form = False
    verified_member = None
    verification_error = None

    # Check session for token after successful PIN verification
    if 'qr_verification_token' in session:
        qr_token = session.get('qr_verification_token')
        member = get_member_by_qr_token(qr_token)
        if member:
            session.pop('qr_verification_token', None)
            verified_member = member
            log_qr_pin_verification(member['id'], 'Public', True, request.remote_addr, request.user_agent.string)
            return render_template('verify_qr.html', 
                                 form=form, 
                                 pin_form=pin_form,
                                 verified_member=verified_member,
                                 error=None)

    # Handle POST requests
    if request.method == 'POST':
        qr_data = request.form.get('qr_data', '').strip()
        pin = request.form.get('pin', '').strip()
        
        # === PIN VERIFICATION (when PIN is submitted) ===
        if pin:
            try:
                # Validate PIN format
                if not pin or not pin.isdigit() or len(pin) != 4:
                    verification_error = 'PIN must be exactly 4 digits.'
                    # Try to find member to show PIN form again
                    member = get_member_by_qr_token(qr_data)
                    if not member and qr_data.startswith('BBS-'):
                        parts = qr_data.split('-')
                        if len(parts) >= 2:
                            member = get_member_by_number(parts[1])
                    show_pin_form = True
                    qr_token = qr_data
                    return render_template('verify_qr.html', form=form, pin_form=pin_form, 
                                         show_pin_form=True, member=member, qr_token=qr_token, 
                                         error=verification_error)
                
                # Find member by QR token
                member = get_member_by_qr_token(qr_data)
                
                if not member and qr_data.startswith('BBS-'):
                    parts = qr_data.split('-')
                    if len(parts) >= 2:
                        member = get_member_by_number(parts[1])
                
                if not member:
                    verification_error = 'Invalid QR code. Member not found.'
                    return render_template('verify_qr.html', form=form, pin_form=pin_form, error=verification_error)
                
                # Verify PIN
                result = verify_qr_pin(member['id'], pin, bcrypt)
                
                if result['success']:
                    # PIN correct - show member details
                    verified_member = member
                    log_qr_pin_verification(member['id'], 'Public', True, request.remote_addr, request.user_agent.string)
                    session.pop('qr_verification_token', None)
                    return render_template('verify_qr.html', 
                                         form=form, 
                                         pin_form=pin_form,
                                         verified_member=verified_member,
                                         error=None)
                else:
                    # PIN incorrect - show error and keep PIN form
                    verification_error = result.get('error', 'Invalid PIN')
                    log_qr_pin_verification(member['id'], 'Public', False, request.remote_addr, request.user_agent.string)
                    show_pin_form = True
                    qr_token = qr_data
                    return render_template('verify_qr.html', 
                                         form=form, 
                                         pin_form=pin_form, 
                                         show_pin_form=True,
                                         member=member,
                                         qr_token=qr_token,
                                         error=verification_error)
            
            except Exception as e:
                verification_error = 'Error verifying PIN. Please try again.'
                return render_template('verify_qr.html', form=form, pin_form=pin_form, error=verification_error)
        
        # === QR CODE VERIFICATION (when QR data is submitted) ===
        elif qr_data:
            try:
                print(f"[DEBUG] QR Data submitted: {qr_data}")  # Will show in terminal
                
                # Try direct token lookup
                member = get_member_by_qr_token(qr_data)
                print(f"[DEBUG] Token lookup result: {member['full_name'] if member else 'None'}")
                
                # If not found, try extracting member number from BBS-xxx format
                if not member and qr_data.startswith('BBS-'):
                    parts = qr_data.split('-')
                    if len(parts) >= 2:
                        member_number = parts[1]
                        print(f"[DEBUG] Extracted member number: {member_number}")
                        member = get_member_by_number(member_number)
                        if member:
                            print(f"[DEBUG] Found by number: {member['full_name']}")
                            # Update database with correct token
                            update_member(member['id'], {'qr_code_data': qr_data})
                
                # If still not found, try as raw member number
                if not member:
                    member = get_member_by_number(qr_data)
                    print(f"[DEBUG] Number lookup result: {member['full_name'] if member else 'None'}")
                
                if not member:
                    error = 'Invalid QR code. Member not found.'
                    print(f"[DEBUG] ❌ No member found")
                    return render_template('verify_qr.html', form=form, pin_form=pin_form, error=error)
                
                print(f"[DEBUG] ✅ Member found: {member['full_name']}")
                print(f"[DEBUG] Has PIN: {has_qr_pin(member['id'])}")
                
                # Check if PIN is required
                if has_qr_pin(member['id']):
                    print(f"[DEBUG] 🔒 PIN required - showing PIN form")
                    session['qr_verification_token'] = qr_data
                    show_pin_form = True
                    qr_token = qr_data
                    return render_template('verify_qr.html', 
                                         form=form, 
                                         pin_form=pin_form, 
                                         show_pin_form=True,
                                         member=member,
                                         qr_token=qr_token,
                                         error=None)
                else:
                    print(f"[DEBUG] 🔓 No PIN - showing details directly")
                    verified_member = member
                    log_qr_pin_verification(member['id'], 'Public', True, request.remote_addr, request.user_agent.string)
                    return render_template('verify_qr.html', 
                                         form=form, 
                                         pin_form=pin_form,
                                         verified_member=verified_member,
                                         error=None)
            
            except Exception as e:
                print(f"[DEBUG] ❌ Error: {e}")
                error = 'Error verifying QR code. Please try again.'
                return render_template('verify_qr.html', form=form, pin_form=pin_form, error=error)

    return render_template('verify_qr.html', form=form, pin_form=pin_form, error=error or verification_error)
