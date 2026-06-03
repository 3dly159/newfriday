"""SeelSupport API integration — full CRUD on any resource table.

Handles two auth layers:
  1. InfinityFree AES cookie challenge (hosting-level DDoS protection)
  2. Laravel Sanctum Bearer token (application-level auth)

Endpoints:
    POST   /api/login            — get bearer token
    GET    /api/{table}          — list all
    GET    /api/{table}/{id}     — get one
    POST   /api/{table}          — create
    PUT    /api/{table}/{id}     — update
    DELETE /api/{table}/{id}     — delete

Supported tables: users, projects, tasks, finances, tickets, notifications.
"""

import json
import os
import re
import httpx
from core.atomicio import atomic_write_json
from core.agency.files import is_safe_path

BASE_URL = "https://seelsupport.unaux.com/api"
STATE_PATH = "config/seelsupport_state.json"
CREDS_PATH = "config/seelsupport_creds.json"
TIMEOUT = 20

VALID_TABLES = {"users", "projects", "tasks", "finances", "tickets", "notifications"}

# Module-level cache for the session (cookie + token).
_session_cache = {"cookie": None, "token": None}


# ---------------------------------------------------------------------------
# Auth: AES cookie challenge solver
# ---------------------------------------------------------------------------

def _solve_aes_challenge(body):
    """Extract AES params from InfinityFree challenge page and compute __test cookie."""
    try:
        from Crypto.Cipher import AES as _AES
        vals = re.findall(r'toNumbers\("([a-f0-9]+)"\)', body)
        if len(vals) < 3:
            return None
        a = bytes.fromhex(vals[0])  # key
        b = bytes.fromhex(vals[1])  # iv
        c = bytes.fromhex(vals[2])  # ciphertext
        cipher = _AES.new(a, _AES.MODE_CBC, b)
        return cipher.decrypt(c).hex()
    except Exception:
        return None


def _ensure_cookie():
    """Solve the AES cookie challenge if we don't have a valid cookie cached."""
    if _session_cache["cookie"]:
        return _session_cache["cookie"]
    try:
        resp = httpx.get(BASE_URL + "/tasks", timeout=TIMEOUT, follow_redirects=False)
        if "toNumbers" in resp.text:
            val = _solve_aes_challenge(resp.text)
            if val:
                _session_cache["cookie"] = val
                return val
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Auth: Bearer token via /api/login
# ---------------------------------------------------------------------------

def _load_creds():
    """Load credentials from config file."""
    if not os.path.exists(CREDS_PATH):
        return None
    try:
        with open(CREDS_PATH) as f:
            return json.load(f)
    except (ValueError, OSError):
        return None


def _ensure_token():
    """Login and cache a bearer token. Returns the token string or None."""
    if _session_cache["token"]:
        return _session_cache["token"]

    creds = _load_creds()
    if not creds:
        return None

    try:
        cookies = {}
        cookie_val = _ensure_cookie()
        if cookie_val:
            cookies["__test"] = cookie_val

        resp = httpx.post(
            BASE_URL + "/login",
            json={"phone": creds.get("phone", ""), "password": creds.get("password", "")},
            cookies=cookies,
            timeout=TIMEOUT,
            follow_redirects=True,
        )
        # If we got another challenge page, solve it and retry.
        if "toNumbers" in resp.text:
            val = _solve_aes_challenge(resp.text)
            if val:
                _session_cache["cookie"] = val
                cookies["__test"] = val
                resp = httpx.post(
                    BASE_URL + "/login",
                    json={"phone": creds.get("phone", ""), "password": creds.get("password", "")},
                    cookies=cookies,
                    timeout=TIMEOUT,
                    follow_redirects=True,
                )

        data = resp.json()
        token = data.get("token")
        if token:
            _session_cache["token"] = token
            return token
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Authenticated request helper
# ---------------------------------------------------------------------------

def _request(method, url, json_data=None):
    """Make an authenticated request, handling both auth layers."""
    headers = {"Accept": "application/json"}
    cookies = {}

    cookie_val = _ensure_cookie()
    if cookie_val:
        cookies["__test"] = cookie_val

    token = _ensure_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = httpx.request(
            method, url, json=json_data, headers=headers,
            cookies=cookies, timeout=TIMEOUT, follow_redirects=True,
        )
        # If we got a challenge page again, solve and retry once.
        if "toNumbers" in resp.text:
            val = _solve_aes_challenge(resp.text)
            if val:
                _session_cache["cookie"] = val
                cookies["__test"] = val
                resp = httpx.request(
                    method, url, json=json_data, headers=headers,
                    cookies=cookies, timeout=TIMEOUT, follow_redirects=True,
                )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        try:
            err_body = e.response.json()
            return f"Error ({e.response.status_code}): {err_body}"
        except Exception:
            return f"Error ({e.response.status_code}): {e.response.text[:200]}"
    except Exception as e:
        return f"Request failed: {e}"


# ---------------------------------------------------------------------------
# Generic CRUD
# ---------------------------------------------------------------------------

def _url(table, item_id=None):
    base = f"{BASE_URL}/{table.strip('/')}"
    return f"{base}/{item_id}" if item_id else base


def _not_configured():
    return ("SeelSupport is not configured. Save credentials to "
            "config/seelsupport_creds.json — see docs/seelsupport-setup.md.")


def seel_fetch(table, item_id=None):
    """GET items from a table. Returns parsed JSON or an error string."""
    if table not in VALID_TABLES:
        return f"Unknown table '{table}'. Valid: {', '.join(sorted(VALID_TABLES))}"
    if not _load_creds():
        return _not_configured()
    return _request("GET", _url(table, item_id))


def seel_create(table, data):
    """POST a new record to a table. Returns created object or error string."""
    if table not in VALID_TABLES:
        return f"Unknown table '{table}'. Valid: {', '.join(sorted(VALID_TABLES))}"
    if not _load_creds():
        return _not_configured()
    return _request("POST", _url(table), json_data=data)


def seel_update(table, item_id, data):
    """PUT/update a record by ID. Returns updated object or error string."""
    if table not in VALID_TABLES:
        return f"Unknown table '{table}'. Valid: {', '.join(sorted(VALID_TABLES))}"
    if not item_id:
        return "item_id is required for update."
    if not _load_creds():
        return _not_configured()
    return _request("PUT", _url(table, item_id), json_data=data)


def seel_delete(table, item_id):
    """DELETE a record by ID. Returns confirmation or error string."""
    if table not in VALID_TABLES:
        return f"Unknown table '{table}'. Valid: {', '.join(sorted(VALID_TABLES))}"
    if not item_id:
        return "item_id is required for delete."
    if not _load_creds():
        return _not_configured()
    result = _request("DELETE", _url(table, item_id))
    if isinstance(result, dict):
        return result.get("message", f"Deleted {table}/{item_id} successfully.")
    return result


# ---------------------------------------------------------------------------
# Proactive: notification state tracking
# ---------------------------------------------------------------------------

def _load_state():
    if not os.path.exists(STATE_PATH):
        return {"last_notified_id": 0}
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except (ValueError, OSError):
        return {"last_notified_id": 0}


def _save_state(state):
    atomic_write_json(STATE_PATH, state)


def check_new_notifications():
    """Fetch notifications and return only those newer than last_notified_id.
    Updates persistent state atomically. Returns [] on any failure."""
    if not _load_creds():
        return []
    state = _load_state()
    last_id = state.get("last_notified_id", 0)
    result = _request("GET", f"{BASE_URL}/notifications")
    if not isinstance(result, list):
        return []
    new = [n for n in result if n.get("id", 0) > last_id]
    if new:
        max_id = max(n["id"] for n in new)
        state["last_notified_id"] = max_id
        _save_state(state)
    return new


def seel_import_tasks_from_file(filepath):
    """Read a JSON tasks file and upload all to the SeelSupport portal."""
    if not is_safe_path(filepath):
        return f"Refused: '{filepath}' is not a safe relative path."
    if not os.path.exists(filepath):
        return f"Error: File '{filepath}' does not exist."
    if not _load_creds():
        return _not_configured()

    try:
        with open(filepath, "r") as f:
            data = json.load(f)
    except Exception as e:
        return f"Error parsing JSON: {e}"

    if not isinstance(data, list):
        return "Error: JSON file must contain a list of tasks."

    success_count = 0
    fail_count = 0
    errors = []

    # Ensure cookie and token are warmed up/cached
    _ensure_cookie()
    _ensure_token()

    for idx, item in enumerate(data):
        task_data = {
            "project_id": item.get("project_id"),
            "ticket_id": item.get("ticket_id"),
            "worker_id": item.get("worker_id"),
            "title": item.get("title"),
            "description": item.get("description"),
            "status": item.get("status", "pending"),
            "start_date": item.get("start_date"),
            "due_date": item.get("due_date"),
        }
        
        result = _request("POST", f"{BASE_URL}/tasks", json_data=task_data)
        if isinstance(result, dict) and "id" in result:
            success_count += 1
        else:
            fail_count += 1
            errors.append(f"Task #{idx} ('{task_data.get('title')}'): {result}")

    msg = f"Successfully imported {success_count} tasks to SeelSupport portal."
    if fail_count > 0:
        msg += f" Failed to import {fail_count} tasks. Sample error: {errors[0]}"
    return msg

