"""
Add this to app.py - M-Pesa payment routes and functions
Place these routes after the existing routes but before the error handlers
"""

# ============================================================
# M-PESA PAYMENT ROUTES
# ============================================================

from utils.mpesa import mpesa

# Payment configuration
BADGE_ISSUANCE_AMOUNT = os.environ.get('BADGE_ISSUANCE_AMOUNT', '100')  # Default KES 100

@app.route('/payment/<int:member_id>')
@login_required
def payment_page(member_id):
    """Show payment page for badge issuance"""
    member = get_member(member_id)
    if not member:
        flash('Member not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check if badge already issued
    if member.get('badge_issued'):
        flash('This member already has an issued badge.', 'info')
        return redirect(url_for('view_badge', member_id=member_id))
    
    return render_template('payment.html', 
                         member=member, 
                         amount=BADGE_ISSUANCE_AMOUNT,
                         official_name='BBS (Busia Bodaboda SACCO)')

@app.route('/payment/initiate/<int:member_id>', methods=['POST'])
@login_required
def initiate_payment(member_id):
    """Initiate M-Pesa STK Push payment"""
    member = get_member(member_id)
    if not member:
        return jsonify({'success': False, 'message': 'Member not found'}), 404
    
    phone_number = request.form.get('phone_number', '').strip()
    
    if not phone_number:
        return jsonify({'success': False, 'message': 'Phone number is required'}), 400
    
    # Validate phone number
    if not phone_number.startswith('254') or len(phone_number) != 12:
        return jsonify({'success': False, 'message': 'Phone number must be in format 2547XXXXXXXX'}), 400
    
    try:
        amount = int(request.form.get('amount', BADGE_ISSUANCE_AMOUNT))
    except ValueError:
        amount = int(BADGE_ISSUANCE_AMOUNT)
    
    # Generate unique reference
    reference = f"BBS{member_id}{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Initiate STK Push
    result = mpesa.stk_push(
        phone_number=phone_number,
        amount=amount,
        account_reference=reference,
        transaction_desc=f"Badge Issuance - {member['member_number']}"
    )
    
    if result['success']:
        # Store payment transaction in database
        # For now, just return success
        return jsonify({
            'success': True,
            'message': 'Payment initiated. Check your phone for M-Pesa prompt.',
            'checkout_request_id': result['data']['checkout_request_id'],
            'reference': reference
        })
    else:
        return jsonify({
            'success': False,
            'message': result.get('message', 'Payment initiation failed')
        }), 400

@app.route('/payment/callback', methods=['POST'])
def mpesa_callback():
    """M-Pesa callback endpoint for payment confirmation"""
    try:
        data = request.get_json()
        logger.info(f"M-Pesa Callback received: {data}")
        
        # Extract transaction details
        body = data.get('Body', {})
        stk_callback = body.get('stkCallback', {})
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc')
        checkout_request_id = stk_callback.get('CheckoutRequestID')
        
        if result_code == 0:  # Success
            # Payment successful - extract member_id from reference
            metadata = stk_callback.get('CallbackMetadata', {})
            items = metadata.get('Item', [])
            
            # Extract reference
            reference = None
            for item in items:
                if item.get('Name') == 'AccountReference':
                    reference = item.get('Value')
                    break
            
            # Extract member_id from reference
            if reference and reference.startswith('BBS'):
                member_id = int(reference[3:3+1])  # Extract first digit after BBS
                
                # Mark badge as issued
                member = get_member(member_id)
                if member:
                    now = datetime.now(timezone.utc)
                    update_member(member_id, {
                        'badge_issued': True,
                        'badge_issued_date': now,
                        'badge_issued_by': 'M-Pesa Payment'
                    })
                    log_badge_issuance(
                        member_id,
                        'M-Pesa Payment',
                        'digital',
                        'standard',
                        f'Payment confirmation: {checkout_request_id}'
                    )
                    logger.info(f"✅ Badge issued for member {member_id} via M-Pesa")
            
            return jsonify({'ResultCode': 0, 'ResultDesc': 'Success'})
        else:
            # Payment failed
            logger.warning(f"❌ M-Pesa payment failed: {result_desc}")
            return jsonify({'ResultCode': result_code, 'ResultDesc': result_desc})
            
    except Exception as e:
        logger.error(f"Error processing M-Pesa callback: {e}")
        return jsonify({'ResultCode': 1, 'ResultDesc': 'Internal error'}), 500

@app.route('/payment/status/<checkout_request_id>')
@login_required
def payment_status(checkout_request_id):
    """Query payment status"""
    result = mpesa.query_status(checkout_request_id)
    return jsonify(result)
