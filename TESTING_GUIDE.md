# Testing Guide — PRD Implementation

Quick guide to test all four implemented features.

## Prerequisites

1. **Server is running**:
   ```bash
   cd /mnt/c/Users/Robert\ Bridge/FlashForgeDash
   source venv/bin/activate
   python -m backend.main
   ```

2. **Browser**: Chrome/Firefox in normal and incognito mode
3. **Admin account**: `rbridge1104@gmail.com` (configured in `.env`)
4. **Test account**: Any other Google account you have access to

---

## Test 1: Sign Out Functionality (2 minutes)

### Steps:
1. Navigate to http://127.0.0.1:8000
2. Sign in with `rbridge1104@gmail.com`
3. Look at the header — you should see your avatar (initial "R") and email
4. Hover over the user menu
5. Click "Sign Out"

### Expected Results:
- ✅ User menu shows avatar with letter "R"
- ✅ Dropdown shows full email: `rbridge1104@gmail.com`
- ✅ "Sign Out" button visible
- ✅ After clicking, redirected to `/login.html`
- ✅ Session cleared (can't go back to dashboard without signing in again)

### Test on Settings Page:
1. Sign in again
2. Click settings gear icon
3. User menu should also be visible in settings header
4. Sign out should work the same way

---

## Test 2: Admin Approval Flow (5 minutes)

### Part A: New User Experience

1. **Sign out completely** from admin account
2. **Clear all cookies** for localhost:8000 (DevTools → Application → Cookies → Clear)
3. **Sign in with a different Google account** (not `rbridge1104@gmail.com`)
4. After OAuth, you should be redirected to `/pending.html`

### Expected Results:
- ✅ Pending page shows your email address
- ✅ Spinner animation visible
- ✅ Message: "An admin must approve your access..."
- ✅ Page polls every 5 seconds (check Network tab)
- ✅ "Back to Sign In" link works

---

### Part B: Admin Approves Request

1. **Open incognito/private window**
2. Navigate to http://127.0.0.1:8000
3. **Sign in as `rbridge1104@gmail.com`** (admin account)
4. Click **settings gear icon** (top right)
5. Scroll to **"Access Management"** section

### Expected Results:
- ✅ "Access Management" card visible (admins only)
- ✅ Pending requests list shows the test account email
- ✅ Each row has email, avatar initial, "Approve" and "Deny" buttons

6. Click **"Approve"** next to test account
7. Toast notification: "Approved [email]"
8. Request disappears from list

---

### Part C: New User Gets Access

1. **Switch back to the pending page** (normal browser window)
2. Within 5 seconds, page should auto-redirect to dashboard
3. You're now signed in as the test user!

### Expected Results:
- ✅ Auto-redirect to dashboard after approval
- ✅ Dashboard fully functional
- ✅ User menu shows test account email
- ✅ **Settings gear icon NOT visible** (non-admin user)

---

### Part D: Test Denial Flow

1. Sign out from test account
2. Clear cookies
3. Sign in with **ANOTHER new Google account**
4. Redirected to pending page
5. In admin window, go to settings
6. Click **"Deny"** for this user
7. Confirmation dialog appears, click OK
8. In pending page window, within 5 seconds:
   - ✅ Redirected to `/login.html?error=unauthorized`
   - ✅ Login page may show error message

---

## Test 3: Settings Page — Admin Only (2 minutes)

### Part A: Admin Access
1. Sign in as `rbridge1104@gmail.com`
2. **Settings gear icon should be VISIBLE** in header
3. Click settings gear
4. Settings page loads successfully
5. "Access Management" card visible

### Expected Results:
- ✅ Settings gear visible
- ✅ Settings page accessible
- ✅ Access Management card shown
- ✅ Can approve/deny users

---

### Part B: Non-Admin Blocked
1. Sign out
2. Sign in with a previously approved test account (from Test 2)
3. **Settings gear icon should be HIDDEN**
4. Manually navigate to: `http://127.0.0.1:8000/settings.html`

### Expected Results:
- ✅ Settings gear NOT visible in dashboard
- ✅ Manual navigation redirects to `/` (dashboard)
- ✅ Cannot access settings page

---

## Test 4: Dynamic Print Progress Card (3 minutes)

### Part A: No Active Print
1. Sign in (any account)
2. Go to dashboard
3. Look at "Print Progress" card (middle row, left side)

### Expected Results:
- ✅ Card shows icon and message: "No active print job"
- ✅ Subtitle: "Upload a G-code file to begin"
- ✅ No hardcoded filename or dummy data
- ✅ Clean, centered placeholder state

---

### Part B: Active Print
1. Ensure printer is connected (or mock data is available)
2. Upload a G-code file via file management section
3. Start print
4. Look at "Print Progress" card again

### Expected Results:
- ✅ No print message HIDDEN
- ✅ Card now shows:
   - Filename from API (e.g., "benchy_final_v3.gcode")
   - Time remaining (e.g., "45m")
   - Progress percentage (e.g., "65%")
   - Layer count: "—" (with note "Not available from API")
   - Filament used: "—" (with note "Not available from API")
- ✅ Progress bar animates
- ✅ Data updates every 2 seconds

---

### Part C: Print Completes
1. Wait for print to complete (or stop manually)
2. Card should switch back to "No active print job" message

### Expected Results:
- ✅ Card reverts to placeholder state
- ✅ No stale data visible

---

## Data Persistence Test (2 minutes)

1. Approve a new user as admin
2. Check that `data/users.json` exists:
   ```bash
   cat data/users.json
   ```
3. Restart the server:
   ```bash
   # Kill server (Ctrl+C)
   python -m backend.main
   ```
4. Sign in as the approved user again

### Expected Results:
- ✅ `data/users.json` contains approved user email
- ✅ After restart, approved user can still sign in
- ✅ Admin doesn't need to approve again
- ✅ Pending/denied lists also persist

---

## Troubleshooting

### Issue: Settings gear not visible for admin
- **Check**: `.env` has `ADMIN_EMAILS=rbridge1104@gmail.com`
- **Check**: Browser console shows `is_admin: true` in `/auth/status` response
- **Fix**: Clear cache, hard reload

### Issue: Pending page doesn't redirect after approval
- **Check**: Network tab shows polling to `/api/auth/pending-status` every 5s
- **Check**: Response returns `{"status": "approved"}`
- **Fix**: Manually navigate to `/auth/activate`

### Issue: Access Management card not visible
- **Check**: User is admin (check `/auth/status` endpoint)
- **Check**: Browser console for JS errors
- **Fix**: Hard reload settings page

### Issue: Print progress card shows old data
- **Check**: `/api/status` endpoint returns `gcode_filename: null`
- **Check**: JS console for errors in `updateUI()`
- **Fix**: Refresh page

---

## Automated Testing Script

Create a test script to verify endpoints:

```bash
#!/bin/bash
BASE_URL="http://127.0.0.1:8000"

echo "Testing public endpoints..."
curl -s "$BASE_URL/login.html" | head -5
curl -s "$BASE_URL/pending.html" | head -5

echo -e "\nTesting auth endpoints (requires session)..."
curl -s -b cookies.txt "$BASE_URL/auth/status" | jq .

echo -e "\nTesting admin endpoints (requires admin session)..."
curl -s -b admin_cookies.txt "$BASE_URL/api/admin/requests" | jq .

echo -e "\nAll tests complete!"
```

---

## Success Criteria Checklist

### Feature 1: Sign Out ✅
- [ ] User menu visible in header with avatar and email
- [ ] Sign out button works
- [ ] Redirects to login page
- [ ] Session cleared after sign out

### Feature 2: Admin Approval Flow ✅
- [ ] New users redirected to pending page
- [ ] Pending page polls every 5 seconds
- [ ] Admin sees pending requests in settings
- [ ] Approve button moves user to approved list
- [ ] Deny button moves user to denied list
- [ ] Approved users auto-redirected to dashboard
- [ ] Denied users redirected to login with error
- [ ] `data/users.json` persists across restarts

### Feature 3: Settings Restriction ✅
- [ ] Settings gear hidden for non-admins
- [ ] Non-admins redirected if manually accessing `/settings.html`
- [ ] Admins can access settings normally
- [ ] Access Management card visible only to admins

### Feature 4: Print Progress ✅
- [ ] Shows "No active print" when no file printing
- [ ] Switches to active state when print starts
- [ ] Shows real filename from API
- [ ] Shows time remaining from API
- [ ] Shows progress percentage from API
- [ ] Layer/filament show "—" (not available)
- [ ] Reverts to placeholder when print completes

---

## Performance Testing

Test with multiple concurrent users:

1. Open 5 browser tabs
2. Sign in with 5 different Google accounts
3. All should be pending
4. Admin approves all 5
5. All 5 should redirect to dashboard within 5-10 seconds

### Expected:
- ✅ No race conditions
- ✅ All approvals persisted correctly
- ✅ Thread-safe user_store operations

---

## Final Validation

Run this checklist to confirm everything works:

1. ✅ Admin can sign in and out
2. ✅ Non-admin can sign in and out
3. ✅ New user goes to pending page
4. ✅ Admin sees pending requests
5. ✅ Admin can approve users
6. ✅ Admin can deny users
7. ✅ Approved users get dashboard access
8. ✅ Denied users stay on login
9. ✅ Non-admins can't access settings
10. ✅ Settings gear hidden for non-admins
11. ✅ Print progress shows placeholder when no print
12. ✅ Print progress shows real data when printing
13. ✅ User data persists across server restarts
14. ✅ No JS errors in console
15. ✅ No Python errors in server logs

---

🎉 **If all tests pass, the implementation is production-ready!**
