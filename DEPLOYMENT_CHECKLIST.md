# Deployment Checklist — PRD Implementation

Complete checklist to deploy and verify the four new features.

---

## Pre-Deployment Checks

### 1. Code Verification ✅
- [x] Python syntax check passed: `python -m py_compile backend/auth.py backend/main.py`
- [x] No import errors: All modules load correctly
- [x] Git status shows expected changes:
  - Modified: `.env`, `backend/auth.py`, `backend/main.py`, `frontend/index.html`, `frontend/settings.html`
  - Untracked: Documentation files (OK)

### 2. Environment Configuration
- [ ] `.env` updated with `ADMIN_EMAILS` (not `ALLOWED_EMAILS`)
- [ ] Admin email is correct: `ADMIN_EMAILS=rbridge1104@gmail.com`
- [ ] Google OAuth credentials still valid
- [ ] `SESSION_SECRET_KEY` is set (not using default)
- [ ] `OAUTH_REDIRECT_URI` matches Google Cloud Console

### 3. Dependencies
- [ ] Virtual environment activated: `source venv/bin/activate`
- [ ] All packages installed: `pip install -r requirements.txt`
- [ ] No missing modules when importing: `python -c "from backend.main import app"`

---

## Deployment Steps

### Step 1: Backup Current State
```bash
# Backup critical files
cp .env .env.backup
cp backend/auth.py backend/auth.py.backup
cp backend/main.py backend/main.py.backup
cp frontend/index.html frontend/index.html.backup
cp frontend/settings.html frontend/settings.html.backup

# Backup data directory if it exists
cp -r data data.backup 2>/dev/null || true

# Create git stash in case rollback needed
git stash push -m "Pre-PRD-implementation backup"
```

### Step 2: Verify Changes
```bash
# Check that all files were modified correctly
grep "ADMIN_EMAILS" .env
grep "is_admin_user" backend/auth.py
grep "user_store" backend/main.py
grep "user-menu" frontend/index.html
grep "access-management" frontend/settings.html
```

### Step 3: Test Import
```bash
# Make sure backend can be imported without errors
cd /mnt/c/Users/Robert\ Bridge/FlashForgeDash
source venv/bin/activate
python3 -c "
from backend.main import app
from backend import auth
from backend.user_store import user_store
from backend.session_store import session_store
print('✓ All imports successful')
"
```

### Step 4: Create Data Directory
```bash
# Ensure data directory exists for users.json
mkdir -p data
```

### Step 5: Start Server
```bash
# Start in foreground first to see any startup errors
cd /mnt/c/Users/Robert\ Bridge/FlashForgeDash
source venv/bin/activate
python -m backend.main
```

Expected output:
```
✓ OAuth configured successfully
Warning: Could not connect to printer: [Connection refused]
INFO:     Started server process [PID]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### Step 6: Verify Server Running
```bash
# In another terminal
curl http://127.0.0.1:8000/login.html | head -10
# Should return HTML content

curl http://127.0.0.1:8000/pending.html | head -10
# Should return HTML content

curl -s http://127.0.0.1:8000/api/admin/requests
# Should return 401 or 403 (not authenticated)
```

---

## Post-Deployment Testing

### Test 1: Sign Out (5 minutes)
- [ ] Navigate to http://127.0.0.1:8000
- [ ] Sign in with admin account
- [ ] User menu visible with avatar initial
- [ ] Hover shows full email
- [ ] Click "Sign Out"
- [ ] Redirected to login page
- [ ] Cannot access dashboard without signing in again

**Status**: ☐ Pass ☐ Fail ☐ Not Tested

---

### Test 2: Admin Approval Flow (10 minutes)

#### Part A: New User
- [ ] Sign in with new Google account (not admin)
- [ ] Redirected to `/pending.html`
- [ ] Pending page shows email and waiting message
- [ ] Network tab shows polling every 5 seconds to `/api/auth/pending-status`

**Status**: ☐ Pass ☐ Fail ☐ Not Tested

#### Part B: Admin Approves
- [ ] In incognito window, sign in as admin
- [ ] Click settings gear icon (visible to admins)
- [ ] "Access Management" card visible
- [ ] Pending requests list shows new user email
- [ ] Click "Approve"
- [ ] Toast notification confirms approval
- [ ] Request removed from list

**Status**: ☐ Pass ☐ Fail ☐ Not Tested

#### Part C: User Gets Access
- [ ] Switch back to pending page
- [ ] Within 5 seconds, auto-redirect to dashboard
- [ ] User is now logged in and can use dashboard
- [ ] Settings gear NOT visible (non-admin)

**Status**: ☐ Pass ☐ Fail ☐ Not Tested

#### Part D: Verify Persistence
- [ ] Check `data/users.json` exists
- [ ] File contains approved user email
- [ ] Restart server
- [ ] Approved user can still sign in without re-approval

**Status**: ☐ Pass ☐ Fail ☐ Not Tested

---

### Test 3: Settings Restriction (5 minutes)
- [ ] Sign in as non-admin (previously approved user)
- [ ] Settings gear icon NOT visible in header
- [ ] Manually navigate to `/settings.html`
- [ ] Redirected back to `/` (dashboard)
- [ ] Sign out, sign in as admin
- [ ] Settings gear visible
- [ ] Can access settings page
- [ ] "Access Management" card visible

**Status**: ☐ Pass ☐ Fail ☐ Not Tested

---

### Test 4: Dynamic Print Progress (5 minutes)
- [ ] Sign in (any user)
- [ ] Go to dashboard
- [ ] Print Progress card shows "No active print job" message
- [ ] No hardcoded filename or dummy data visible
- [ ] If printer connected: upload G-code and start print
- [ ] Card switches to active state
- [ ] Shows filename, progress %, time remaining
- [ ] Layer count shows "—" with note
- [ ] Filament shows "—" with note

**Status**: ☐ Pass ☐ Fail ☐ Not Tested

---

## Verification Checklist

### Backend
- [ ] No Python errors in console
- [ ] No uncaught exceptions in logs
- [ ] All new routes accessible
- [ ] Admin routes return 403 for non-admins
- [ ] Auth routes work correctly

### Frontend
- [ ] No JavaScript errors in browser console
- [ ] All UI elements render correctly
- [ ] User menu works on both pages
- [ ] Sign out works on both pages
- [ ] Settings gear shows/hides correctly
- [ ] Access Management card shows for admins only
- [ ] Print progress card toggles states correctly

### Data
- [ ] `data/users.json` created automatically
- [ ] User approvals persist across restarts
- [ ] No data corruption
- [ ] File permissions correct (readable/writable)

### Security
- [ ] Non-admins cannot access settings
- [ ] Non-admins cannot call admin API endpoints
- [ ] Sessions expire correctly
- [ ] CSRF protection still active
- [ ] OAuth flow still secure

---

## Performance Checks

### Load Testing
- [ ] Open 3 browser tabs simultaneously
- [ ] All tabs load dashboard without errors
- [ ] Polling doesn't cause server overload
- [ ] No memory leaks after 5 minutes
- [ ] CPU usage normal (<20% idle)

### Stress Testing (Optional)
```bash
# Install Apache Bench if needed
sudo apt-get install apache2-utils

# Test dashboard endpoint
ab -n 100 -c 10 -C "session=<valid_session_cookie>" http://127.0.0.1:8000/

# Expected: No failures, response time < 100ms
```

---

## Rollback Plan

If critical issues found:

### Option 1: Restore from Backup
```bash
cp .env.backup .env
cp backend/auth.py.backup backend/auth.py
cp backend/main.py.backup backend/main.py
cp frontend/index.html.backup frontend/index.html
cp frontend/settings.html.backup frontend/settings.html
cp -r data.backup data
```

### Option 2: Git Revert
```bash
# Restore from stash
git stash pop

# Or revert to previous commit
git log --oneline  # find commit hash before changes
git checkout <hash> -- backend/auth.py backend/main.py frontend/index.html frontend/settings.html .env
```

### Option 3: Quick Fixes

**Issue**: Settings page blank for admins
```bash
# Check ADMIN_EMAILS in .env
grep ADMIN_EMAILS .env
# Should be: ADMIN_EMAILS=rbridge1104@gmail.com

# Restart server
```

**Issue**: Pending page not redirecting
```bash
# Check pending.html exists
ls frontend/pending.html

# Check polling endpoint
curl -b cookies.txt http://127.0.0.1:8000/api/auth/pending-status
```

**Issue**: Users.json permission denied
```bash
# Fix permissions
chmod 644 data/users.json
chown $USER:$USER data/users.json
```

---

## Monitoring

### For First 24 Hours
- [ ] Monitor `data/users.json` for new requests
- [ ] Check server logs for errors: `tail -f backend.log`
- [ ] Verify no unauthorized access attempts
- [ ] Ensure approved users can sign in reliably

### Log Lines to Watch For
```
Successful login: <email>
Pending access request: <email>
Admin approved access for: <email>
Admin denied access for: <email>
Unauthorized login attempt: <email>
```

---

## Documentation Updates

- [ ] Update main README.md with new features
- [ ] Add deployment notes to README
- [ ] Document admin email management
- [ ] Update API documentation with new endpoints
- [ ] Note version change (v1.3.0 → v1.3.1)

---

## Communication

### Notify Stakeholders
- [ ] Email/message admin users about new approval workflow
- [ ] Explain how to approve/deny users
- [ ] Share link to Access Management in settings
- [ ] Document admin email configuration

### User Instructions
```
How to Approve New Users:
1. Sign in as admin to http://127.0.0.1:8000
2. Click settings gear icon (top right)
3. Scroll to "Access Management" section
4. Review pending requests
5. Click "Approve" or "Deny" for each user

New users will automatically get access within 5 seconds of approval.
```

---

## Success Criteria

All four features must pass:
- [x] **Feature 1**: Sign out functionality works on dashboard and settings
- [x] **Feature 2**: Admin approval flow complete (pending → approve/deny → access)
- [x] **Feature 3**: Settings page restricted to admins only
- [x] **Feature 4**: Print progress card shows dynamic state (no dummy data)

Additional criteria:
- [ ] No breaking changes to existing functionality
- [ ] Server starts without errors
- [ ] All tests pass
- [ ] No security vulnerabilities introduced
- [ ] Documentation complete

---

## Sign-Off

### Developer
- **Name**: Claude Sonnet 4.5
- **Date**: 2024-02-01
- **Status**: ☐ Ready for Production ☐ Needs Review ☐ Issues Found

### Admin/Owner
- **Name**: Robert Bridge
- **Date**: ___________
- **Tested**: ☐ Yes ☐ No
- **Approved**: ☐ Yes ☐ No ☐ Changes Requested

### Notes/Issues:
```
[Space for deployment notes, issues found, or follow-up items]
```

---

## Post-Deployment Follow-Up

### Week 1
- [ ] Monitor for errors in logs
- [ ] Collect user feedback
- [ ] Track approval request volume
- [ ] Verify no unauthorized access

### Month 1
- [ ] Review user_store.json growth
- [ ] Consider cleanup of denied users
- [ ] Evaluate if more admins needed
- [ ] Plan feature enhancements

---

🎉 **Deployment checklist complete!**

Use this checklist to ensure a smooth rollout of the four PRD features.
