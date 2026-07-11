# Add this to templates/badge.html in the actions section
# Replace the badge actions with these

# In the actions card, replace the buttons with:

<div class="badge-actions">
    {% if member.badge_issued %}
        <span class="badge bg-success mb-2"><i class="fas fa-check-circle"></i> Issued</span>
        <a href="{{ url_for('download_badge', member_id=member.id) }}" class="btn btn-gold">
            <i class="fas fa-download me-2"></i>Download PNG
        </a>
        <a href="{{ url_for('download_badge', member_id=member.id, format='pdf') }}" class="btn btn-primary">
            <i class="fas fa-file-pdf me-2"></i>Download PDF
        </a>
    {% else %}
        <span class="badge bg-warning mb-2"><i class="fas fa-clock"></i> Pending Payment</span>
        <a href="{{ url_for('payment_page', member_id=member.id) }}" class="btn btn-gold btn-lg">
            <i class="fas fa-credit-card me-2"></i>Pay and Issue Badge
        </a>
        <p class="text-muted small mt-2">
            <i class="fas fa-info-circle me-1"></i>
            Payment required before badge can be issued
        </p>
    {% endif %}
    <a href="{{ url_for('regenerate_badge', member_id=member.id) }}" class="btn btn-warning">
        <i class="fas fa-sync me-2"></i>Regenerate
    </a>
    <a href="{{ url_for('edit_member', member_id=member.id) }}" class="btn btn-secondary">
        <i class="fas fa-edit me-2"></i>Edit
    </a>
    <a href="{{ url_for('dashboard') }}" class="btn btn-outline-secondary">
        <i class="fas fa-arrow-left me-2"></i>Back
    </a>
</div>
