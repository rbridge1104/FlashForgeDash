# PRD — FlashForgeDash Auth & UI Fixes

## Summary
Four features requested after Google OAuth was successfully wired up:
1. Sign out functionality
2. Admin-gated access approval flow
3. Settings page restricted to admins only
4. Remove hardcoded dummy file from Print Progress card

---

## 1. Sign Out

**What:** A user menu in the header that shows the logged-in email and a "Sign Out" button.

**Where:** Sticky header on both `index.html` (dashboard) and `settings.html`. Styled as a dropdown matching the existing "Resources" dropdown pattern — avatar initial + chevron, expands on hover to show email and sign out link.

**How:** Button calls `POST /auth/logout` (already exists), then redirects to `/login.html`. The user's email and initial are fetched on page load via the existing `GET /api/auth/status` endpoint.

---

## 2. Admin Approval Flow

**Problem:** Currently, access is controlled by a static `ALLOWED_EMAILS` env var. There's no way for someone new to request access or for an admin to approve them without editing a file and restarting the server.

**New flow:**
1. User clicks "Sign in with Google" on the login page.
2. After Google authenticates them, the backend checks their status:
   - **Admin** (email in `ADMIN_EMAILS` env var) → approved immediately, session created.
   - **Previously approved** (in persistent store) → approved immediately.
   - **Previously denied** → redirected back to login with "unauthorized" error.
   - **New user** → saved as "pending", redirected to a new `/pending.html` page.
3. The pending page shows the user's email, a spinner, and a message that an admin must approve them. It polls `GET /api/auth/pending-status` every 5 seconds.
4. When an admin approves them (via the settings page), the next poll returns `approved` and the pending page redirects to `GET /auth/activate`, which creates the session and sends them to the dashboard.

**Persistence:** Approved, pending, and denied user lists are stored in `data/users.json`. This file persists across server restarts.

**Admin designation:** Via the `ADMIN_EMAILS` env var (replaces `ALLOWED_EMAILS`). Admins are always approved and can never be locked out.

**New backend pieces:**
- `backend/user_store.py` — thread-safe JSON-backed store for user status. *(already created)*
- `frontend/pending.html` — the waiting page. *(already created)*
- `GET /auth/activate` — creates a session for a user whose pending request was just approved.
- `GET /api/auth/pending-status` — returns `pending`, `approved`, or `denied` for the user in the current session.
- `GET /api/admin/requests` — returns the list of pending emails. Admin only (403 otherwise).
- `POST /api/admin/approve` — body `{"email": "..."}`. Moves email from pending → approved. Admin only.
- `POST /api/admin/deny` — body `{"email": "..."}`. Moves email from pending → denied. Admin only.

---

## 3. Settings Page — Admin Only

**What:** Non-admin authenticated users who navigate to `/settings.html` are redirected back to the dashboard (`/`). The settings button in the dashboard header is hidden for non-admins.

**How:** The `/settings.html` route handler already checks `is_authenticated`. An additional `is_admin_user` check is added after it — if the user is not an admin, redirect to `/`. On the frontend, the settings gear icon is only shown after `loadUserInfo` confirms the user is an admin (determined by a new `is_admin` field in the `/api/auth/status` response).

**Admin panel in settings:** A new "Access Management" card appears on the settings page showing all pending requests. Each row has an email address and Approve / Deny buttons that call the admin API endpoints.

---

## 4. Remove Dummy File from Print Progress

**Problem:** The Print Progress card on the dashboard has hardcoded placeholder data (`benchy_final_v3.gcode`, `65%`, `1h 23m`, `145 / 223 layers`, etc.) that stays visible even when no file is printing.

**Fix:** The file info section is split into two states:
- **No active print:** Shows a simple "No active print job — upload a G-code file to begin" message.
- **Active print:** Shows the filename (from API), progress %, and time remaining (from API). Layer count and filament used show "—" since the API does not currently return those values.

The JS `updateUI` function toggles between these two states based on whether `gcode_filename` is present in the status response.

---

## What's Already Done (partial implementation in progress)
- `backend/user_store.py` — created
- `frontend/pending.html` — created
- `backend/auth.py` — `user_store` import added, old `is_email_authorized` function removed. *(callback and admin helper functions still pending)*

## Remaining Work
- Finish `auth.py`: replace `handle_callback` with user_store flow; add `is_admin_user` and `get_admin_user` helpers.
- Edit `main.py`: add new routes, admin-only settings check, import user_store/session_store.
- Edit `index.html`: sign out dropdown in header; dynamic print progress card; hide settings gear for non-admins.
- Edit `settings.html`: sign out dropdown; access management card with approve/deny UI.
- Edit `.env`: replace `ALLOWED_EMAILS` with `ADMIN_EMAILS`.
- Restart server and verify.

## Out of Scope
- Email notifications to pending users when approved/denied.
- Revoking access for already-approved users (not requested).
- Persisting sessions across server restarts (sessions are in-memory).
