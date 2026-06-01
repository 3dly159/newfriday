from core.agency.system import is_dangerous, volume_command


def test_is_dangerous_blocks_catastrophic():
    assert is_dangerous("rm -rf /")
    assert is_dangerous("sudo rm -rf /*")
    assert is_dangerous(":(){ :|:& };:")            # fork bomb
    assert is_dangerous("mkfs.ext4 /dev/sda1")
    assert is_dangerous("dd if=/dev/zero of=/dev/sda")
    assert is_dangerous("echo x > /dev/sda")
    assert is_dangerous("shutdown now")
    assert is_dangerous("reboot")


def test_is_dangerous_allows_normal():
    assert not is_dangerous("echo hello")
    assert not is_dangerous("ls -la")
    assert not is_dangerous("python3 script.py")
    assert not is_dangerous("rm build/tmp.o")       # scoped rm is fine


def test_volume_command_builds_linux_amixer():
    cmd = volume_command(50)
    assert isinstance(cmd, list)
    assert any("50" in str(part) for part in cmd)


from core.agency.system import run_shell, system_info


def test_run_shell_refuses_dangerous():
    out = run_shell("rm -rf /")
    assert "refus" in out["error"].lower() or "danger" in out["error"].lower()


def test_run_shell_runs_safe_command():
    out = run_shell("echo hello-friday")
    assert "hello-friday" in out["stdout"]
    assert out["exit_code"] == 0


def test_system_info_has_core_fields():
    info = system_info()
    for key in ("cpu_percent", "memory_percent", "platform"):
        assert key in info
