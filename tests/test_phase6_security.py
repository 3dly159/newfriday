import pytest
import os
import json
from core.bridge import FridayBridge, PermissionManager

def test_permissions_logic():
    perm_path = "data/test_perms.json"
    if os.path.exists(perm_path): os.remove(perm_path)

    pm = PermissionManager(config_path=perm_path)

    # Default is ask
    assert pm.check("hid_control") == "ask"

    # Update and save
    pm.permissions["hid_control"] = "allow"
    pm.save()

    pm2 = PermissionManager(config_path=perm_path)
    assert pm2.check("hid_control") == "allow"

    if os.path.exists(perm_path): os.remove(perm_path)

def test_bridge_gating():
    bridge = FridayBridge()
    bridge.permissions.permissions["hid_control"] = "deny"

    result = bridge.move_mouse(10, 10)
    assert "Permission denied" in result

    bridge.permissions.permissions["hid_control"] = "ask"
    result = bridge.move_mouse(10, 10)
    assert "PENDING_APPROVAL" in result
