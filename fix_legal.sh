#!/bin/bash

# Fix app.py
cat > app.py << 'APP_EOF'
[content from above - paste the entire app.py content]
APP_EOF

# Create legal.html
cat > templates/legal.html << 'LEGAL_EOF'
[content from above - paste the legal.html content]
LEGAL_EOF

# Create acceptable_use_policy.md
cat > legal/acceptable_use_policy.md << 'AUP_EOF'
[content from above]
AUP_EOF

# Create consent_form.md
cat > legal/consent_form.md << 'CONSENT_EOF'
[content from above]
CONSENT_EOF

# Update eula.md
cat > legal/eula.md << 'EULA_EOF'
[content from above]
EULA_EOF

# Update privacy_policy.md
cat > legal/privacy_policy.md << 'PRIVACY_EOF'
[content from above]
PRIVACY_EOF

# Update terms_of_service.md
cat > legal/terms_of_service.md << 'TERMS_EOF'
[content from above]
TERMS_EOF

echo "✅ All legal files fixed!"
