# Code Changes Summary — PRD Implementation

Detailed breakdown of all code changes made to implement the four PRD features.

---

## File 1: `.env`

### Change:
Replaced `ALLOWED_EMAILS` with `ADMIN_EMAILS`

### Before:
```bash
ALLOWED_EMAILS=rbridge1104@gmail.com
```

### After:
```bash
ADMIN_EMAILS=rbridge1104@gmail.com
```

### Reason:
Admin emails now designate users who are always approved and can manage other users.

---

## File 2: `backend/auth.py`

### Change 1: Updated `handle_callback()` Function
Replaced static email whitelist check with user_store approval flow.

### Key Changes:
- Calls `user_store.request_access(email)` to check status
- Returns `"approved"`, `"pending"`, or `"denied"`
- If approved: creates session, redirects to `/`
- If denied: redirects to `/login.html?error=unauthorized`
- If pending: creates temporary session, redirects to `/pending.html`

### Code Snippet:
```python
# Check user status via user_store
status = user_store.request_access(email)

if status == "approved":
    # Admin or previously approved user - create session immediately
    session_id = session_store.create_session(email)
    # ... set cookie, redirect to dashboard

elif status == "denied":
    # Previously denied user
    return RedirectResponse("/login.html?error=unauthorized")

elif status == "pending":
    # New user - create temporary session, redirect to pending page
    session_id = session_store.create_session(email)
    # ... set cookie with 1 day expiry, redirect to /pending.html
```

---

### Change 2: Added `is_admin_user()` Function
Checks if current user is an admin.

```python
def is_admin_user(request: Request) -> bool:
    """Check if current user is an admin."""
    if not os.getenv("GOOGLE_CLIENT_ID"):
        return True  # Dev mode - everyone is admin

    signed_session_id = request.cookies.get("session")
    if not signed_session_id:
        return False

    session_id = verify_session_id(signed_session_id)
    if not session_id:
        return False

    session = session_store.get_session(session_id)
    if not session:
        return False

    return user_store.is_admin(session["email"])
```

---

### Change 3: Added `get_pending_email()` Function
Extracts email from a pending user's session.

```python
def get_pending_email(request: Request) -> Optional[str]:
    """Get the email address for a pending access request session."""
    signed_session_id = request.cookies.get("session")
    if not signed_session_id:
        return None

    session_id = verify_session_id(signed_session_id)
    if not session_id:
        return None

    session = session_store.get_session(session_id)
    if not session:
        return None

    return session["email"]
```

---

### Change 4: Updated `get_auth_status()` Function
Added `is_admin` field to response.

```python
async def get_auth_status(request: Request) -> dict:
    # ... existing code ...

    email = session["email"]
    is_admin = user_store.is_admin(email)
    is_approved = user_store.is_approved(email)

    return {
        "authenticated": is_approved,  # Only approved users are fully authenticated
        "email": email,
        "created_at": session["created_at"].isoformat(),
        "expires_at": session["expires_at"].isoformat(),
        "is_admin": is_admin  # NEW FIELD
    }
```

---

## File 3: `backend/main.py`

### Change 1: Added Import
```python
from .user_store import user_store
```

---

### Change 2: Updated `/settings.html` Route
Added admin-only check.

```python
@app.get("/settings.html", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Serve the settings page (admin only)."""
    # Check authentication
    if not auth.is_authenticated(request):
        return RedirectResponse("/login.html")

    # Check if user is admin (NEW)
    if not auth.is_admin_user(request):
        return RedirectResponse("/")  # Non-admins redirect to dashboard

    html_path = Path(__file__).parent.parent / "frontend" / "settings.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    return HTMLResponse("<h1>Settings page not found</h1>")
```

---

### Change 3: Added `/pending.html` Route
```python
@app.get("/pending.html", response_class=HTMLResponse)
async def pending_page():
    """Serve the pending access page."""
    html_path = Path(__file__).parent.parent / "frontend" / "pending.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    return HTMLResponse("<h1>Pending page not found</h1>")
```

---

### Change 4: Added `/auth/activate` Route
```python
@app.get("/auth/activate")
async def activate_access(request: Request):
    """Activate a pending user's session after admin approval."""
    email = auth.get_pending_email(request)

    if not email:
        return RedirectResponse("/login.html")

    # Check if user is now approved
    if not user_store.is_approved(email):
        # Still pending or denied
        return RedirectResponse("/pending.html")

    # User is approved - redirect to dashboard (session already exists)
    print(f"Activated approved user: {email}")
    return RedirectResponse("/")
```

---

### Change 5: Added `/api/auth/pending-status` Route
```python
@app.get("/api/auth/pending-status")
async def get_pending_status(request: Request):
    """Check if a pending user has been approved or denied."""
    email = auth.get_pending_email(request)

    if not email:
        return {"status": "unknown"}

    if user_store.is_approved(email):
        return {"status": "approved", "email": email}
    elif email.lower() in [e.lower() for e in user_store._data.get("denied", [])]:
        return {"status": "denied", "email": email}
    else:
        return {"status": "pending", "email": email}
```

---

### Change 6: Added `/api/admin/requests` Route
```python
@app.get("/api/admin/requests")
async def get_pending_requests(request: Request):
    """Get list of pending access requests (admin only)."""
    if not auth.is_admin_user(request):
        raise HTTPException(status_code=403, detail="Admin access required")

    pending = user_store.get_pending_requests()
    return {"pending": pending}
```

---

### Change 7: Added `/api/admin/approve` Route
```python
@app.post("/api/admin/approve")
async def approve_user(request: Request):
    """Approve a pending access request (admin only)."""
    if not auth.is_admin_user(request):
        raise HTTPException(status_code=403, detail="Admin access required")

    data = await request.json()
    email = data.get("email")

    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    success = user_store.approve(email)

    if success:
        print(f"Admin approved access for: {email}")
        return {"success": True, "message": f"Approved {email}"}
    else:
        return {"success": False, "message": "User not found in pending list"}
```

---

### Change 8: Added `/api/admin/deny` Route
```python
@app.post("/api/admin/deny")
async def deny_user(request: Request):
    """Deny a pending access request (admin only)."""
    if not auth.is_admin_user(request):
        raise HTTPException(status_code=403, detail="Admin access required")

    data = await request.json()
    email = data.get("email")

    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    success = user_store.deny(email)

    if success:
        print(f"Admin denied access for: {email}")
        return {"success": True, "message": f"Denied {email}"}
    else:
        return {"success": False, "message": "User not found in pending list"}
```

---

## File 4: `frontend/index.html`

### Change 1: Added User Menu Dropdown in Header

**Location**: After Emergency Stop, before Resources dropdown

```html
<!-- User Menu Dropdown -->
<div class="relative group">
    <button class="flex items-center gap-2 px-3 py-2 bg-slate-700/50 hover:bg-slate-600/50 border border-slate-600/50 rounded-lg text-sm backdrop-blur-sm">
        <div class="w-6 h-6 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-xs font-bold" id="user-avatar">
            ?
        </div>
        <span id="user-email-short" class="text-slate-300">User</span>
        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
        </svg>
    </button>
    <div class="absolute right-0 mt-2 w-56 card rounded-lg shadow-2xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all">
        <div class="p-3 border-b border-slate-700/50">
            <div class="text-xs text-slate-500 mb-1">Signed in as</div>
            <div id="user-email-full" class="text-sm text-slate-200 font-medium break-all">user@example.com</div>
        </div>
        <div class="p-2">
            <button id="sign-out-btn" class="w-full flex items-center gap-3 px-3 py-2 hover:bg-slate-600/50 rounded-md text-sm text-red-400">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
                </svg>
                <span>Sign Out</span>
            </button>
        </div>
    </div>
</div>
```

---

### Change 2: Updated Settings Button
Hidden by default, only shown for admins.

```html
<!-- Settings Button (hidden for non-admins) -->
<button id="settings-btn" class="p-2 bg-slate-700/50 hover:bg-slate-600/50 border border-slate-600/50 rounded-lg backdrop-blur-sm" style="display: none;">
    <!-- SVG icon -->
</button>
```

---

### Change 3: Updated Print Progress Card
Split into two states: no print and active print.

**Before**: Hardcoded dummy data always visible

**After**:
```html
<div id="print-info-container">
    <!-- No active print state -->
    <div id="no-print-state" class="..." style="display: none;">
        <svg>...</svg>
        <p>No active print job</p>
        <p>Upload a G-code file to begin</p>
    </div>

    <!-- Active print state -->
    <div id="active-print-state" style="display: none;">
        <!-- Filename, time remaining, progress -->
        <div id="print-filename">—</div>
        <div id="print-time-remaining">—</div>
        <div id="print-progress-text">—</div>

        <!-- Layer & filament (not available from API) -->
        <div>Layer: — (Not available from API)</div>
        <div>Filament: — (Not available from API)</div>
    </div>
</div>
```

---

### Change 4: Added JavaScript Functions

#### Added `loadUserInfo()`:
```javascript
async function loadUserInfo() {
    try {
        const response = await fetch('/auth/status');
        const data = await response.json();

        if (data.authenticated && data.email) {
            const email = data.email;
            const initial = email.charAt(0).toUpperCase();

            document.getElementById('user-avatar').textContent = initial;
            document.getElementById('user-email-short').textContent = email.split('@')[0];
            document.getElementById('user-email-full').textContent = email;

            // Show settings button only for admins
            if (data.is_admin) {
                document.getElementById('settings-btn').style.display = 'block';
            }
        }
    } catch (error) {
        console.error('Error loading user info:', error);
    }
}
```

---

#### Updated `updateUI()`:
Added dynamic print progress logic.

```javascript
// Print progress card - toggle between active print and no print states
const noPrintState = document.getElementById('no-print-state');
const activePrintState = document.getElementById('active-print-state');

if (data.gcode_filename) {
    // Active print - show print info
    if (noPrintState) noPrintState.style.display = 'none';
    if (activePrintState) activePrintState.style.display = 'block';

    // Update filename
    const printFilename = document.getElementById('print-filename');
    if (printFilename) printFilename.textContent = data.gcode_filename;

    // Update time remaining
    const timeRemaining = document.getElementById('print-time-remaining');
    if (timeRemaining && data.time_remaining_formatted) {
        timeRemaining.textContent = data.time_remaining_formatted.substring(0, data.time_remaining_formatted.lastIndexOf(':'));
    }

    // Update progress text
    const progressText = document.getElementById('print-progress-text');
    if (progressText) progressText.textContent = `${data.progress}%`;
} else {
    // No active print - show placeholder
    if (noPrintState) noPrintState.style.display = 'block';
    if (activePrintState) activePrintState.style.display = 'none';
}
```

---

#### Added Sign-Out Handler:
```javascript
// Sign out button
const signOutBtn = document.getElementById('sign-out-btn');
if (signOutBtn) {
    signOutBtn.addEventListener('click', async () => {
        try {
            await fetch('/auth/logout', { method: 'POST' });
            window.location.href = '/login.html';
        } catch (error) {
            console.error('Error signing out:', error);
        }
    });
}
```

---

#### Call `loadUserInfo()` on Page Load:
```javascript
document.addEventListener('DOMContentLoaded', () => {
    loadUserInfo(); // NEW

    // ... existing initialization code
});
```

---

## File 5: `frontend/settings.html`

### Change 1: Added User Menu Dropdown
Identical to `index.html`, added after Emergency Stop button.

---

### Change 2: Added Access Management Card

**Location**: Before "Save All Settings" card

```html
<!-- Access Management (Admin Only) -->
<div id="access-management-card" class="card rounded-xl p-6" style="display: none;">
    <div class="flex items-center gap-3 mb-6">
        <!-- Icon and title -->
        <h3>Access Management</h3>
        <p>Review and approve pending access requests</p>
    </div>

    <div id="pending-requests-container">
        <div id="pending-requests-empty" class="..." style="display: none;">
            <p>No pending requests</p>
        </div>

        <div id="pending-requests-list" class="space-y-3">
            <!-- Pending requests dynamically inserted here -->
        </div>
    </div>

    <button id="refresh-requests">Refresh Requests</button>
</div>
```

---

### Change 3: Added JavaScript Functions

#### Added `loadUserInfo()`:
```javascript
async function loadUserInfo() {
    try {
        const response = await fetch('/auth/status');
        const data = await response.json();

        if (data.authenticated && data.email) {
            const email = data.email;
            const initial = email.charAt(0).toUpperCase();

            document.getElementById('user-avatar').textContent = initial;
            document.getElementById('user-email-short').textContent = email.split('@')[0];
            document.getElementById('user-email-full').textContent = email;

            // Show access management card for admins
            if (data.is_admin) {
                document.getElementById('access-management-card').style.display = 'block';
                loadPendingRequests();
            }
        }
    } catch (error) {
        console.error('Error loading user info:', error);
    }
}
```

---

#### Added `loadPendingRequests()`:
```javascript
async function loadPendingRequests() {
    try {
        const response = await fetch('/api/admin/requests');
        const data = await response.json();

        const listContainer = document.getElementById('pending-requests-list');
        const emptyState = document.getElementById('pending-requests-empty');

        if (data.pending && data.pending.length > 0) {
            listContainer.innerHTML = '';
            emptyState.style.display = 'none';

            data.pending.forEach(email => {
                const row = createRequestRow(email);
                listContainer.appendChild(row);
            });
        } else {
            listContainer.innerHTML = '';
            emptyState.style.display = 'block';
        }
    } catch (error) {
        console.error('Error loading pending requests:', error);
    }
}
```

---

#### Added `createRequestRow()`:
```javascript
function createRequestRow(email) {
    const row = document.createElement('div');
    row.className = 'flex items-center justify-between p-4 bg-slate-900/50 rounded-lg border border-slate-700/50';

    row.innerHTML = `
        <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center text-sm font-bold text-blue-400">
                ${email.charAt(0).toUpperCase()}
            </div>
            <div>
                <div class="font-medium text-slate-200">${email}</div>
                <div class="text-xs text-slate-500">Pending approval</div>
            </div>
        </div>
        <div class="flex items-center gap-2">
            <button onclick="approveUser('${email}')" class="px-4 py-2 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-500 hover:to-green-600 rounded-lg text-sm font-medium border border-green-500/50">
                Approve
            </button>
            <button onclick="denyUser('${email}')" class="px-4 py-2 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 rounded-lg text-sm font-medium border border-red-500/50">
                Deny
            </button>
        </div>
    `;

    return row;
}
```

---

#### Added `approveUser()`:
```javascript
async function approveUser(email) {
    try {
        const response = await fetch('/api/admin/approve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });

        const data = await response.json();

        if (data.success) {
            showToast(`Approved ${email}`, 'success');
            loadPendingRequests();
        } else {
            showToast('Failed to approve user', 'error');
        }
    } catch (error) {
        showToast('Error approving user', 'error');
    }
}
```

---

#### Added `denyUser()`:
```javascript
async function denyUser(email) {
    if (!confirm(`Deny access for ${email}?`)) return;

    try {
        const response = await fetch('/api/admin/deny', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });

        const data = await response.json();

        if (data.success) {
            showToast(`Denied ${email}`, 'success');
            loadPendingRequests();
        } else {
            showToast('Failed to deny user', 'error');
        }
    } catch (error) {
        showToast('Error denying user', 'error');
    }
}
```

---

#### Updated DOMContentLoaded:
```javascript
document.addEventListener('DOMContentLoaded', () => {
    loadConfig();
    loadUserInfo(); // NEW

    // Sign out button (NEW)
    const signOutBtn = document.getElementById('sign-out-btn');
    if (signOutBtn) {
        signOutBtn.addEventListener('click', async () => {
            try {
                await fetch('/auth/logout', { method: 'POST' });
                window.location.href = '/login.html';
            } catch (error) {
                console.error('Error signing out:', error);
            }
        });
    }

    // Refresh requests button (NEW)
    const refreshBtn = document.getElementById('refresh-requests');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', loadPendingRequests);
    }
});
```

---

## Summary of Changes

### Backend (Python)
- **1 file modified**: `.env`
- **2 files modified**: `auth.py`, `main.py`
- **0 new files**: (user_store.py and session_store.py already existed)

### Frontend (HTML/JS)
- **2 files modified**: `index.html`, `settings.html`
- **0 new files**: (pending.html already existed)

### Total Lines Changed
- **Backend**: ~150 lines added/modified
- **Frontend**: ~200 lines added/modified
- **Total**: ~350 lines of code changed

---

## No Breaking Changes

All changes are **additive** or **modifications to existing functionality**:
- ✅ Existing routes still work
- ✅ Existing API endpoints unchanged (except `/auth/status` now includes `is_admin`)
- ✅ No database migrations required
- ✅ No dependencies added
- ✅ Backward compatible (existing approved users still work)

---

## Testing Each Change

### Test `.env` change:
```bash
cat .env | grep ADMIN_EMAILS
# Should show: ADMIN_EMAILS=rbridge1104@gmail.com
```

### Test `auth.py` changes:
```bash
python3 -c "from backend.auth import is_admin_user, get_pending_email; print('✓ Functions imported')"
```

### Test `main.py` changes:
```bash
curl http://127.0.0.1:8000/api/admin/requests
# Should return 401 or 403 (not authenticated/not admin)
```

### Test `index.html` changes:
1. Open dashboard
2. Check browser console for errors
3. User menu should be visible
4. Settings gear should be hidden/visible based on admin status

### Test `settings.html` changes:
1. Sign in as admin
2. Go to settings
3. "Access Management" card should be visible
4. Pending requests list should load

---

🎉 **All changes documented and ready for review!**
