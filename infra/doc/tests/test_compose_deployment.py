import json
import os
import stat
import subprocess
import tempfile
import unittest
from fcntl import LOCK_EX, LOCK_NB, flock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "deploy" / "compose-deployment.sh"


class ComposeDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.deployment_directory = self.root / "deployment"
        self.deployment_env = self.root / "deployment.env"
        self.runtime_env = self.root / "runtime.env"
        self.lock = self.root / "lock" / "klee-web-deployment.lock"
        self.bin_directory = self.root / "bin"
        self.docker_log = self.root / "docker.jsonl"
        self.systemctl_log = self.root / "systemctl.jsonl"
        self.provision_log = self.root / "provision.jsonl"
        self.deployment_directory.mkdir()
        self.bin_directory.mkdir()
        self.lock.parent.mkdir()
        self.runtime_env.touch()
        for name in ("docker-compose.yml", "compose.production.yml", "compose.worker.yml", "compose.acme.yml"):
            (self.deployment_directory / name).touch()
        self.write_fixture_script()
        self.write_fake_commands()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def write_fixture_script(self):
        source = SCRIPT.read_text()
        replacements = {
            "/etc/klee-web/deployment.env": str(self.deployment_env),
            "/etc/klee-web/runtime.env": str(self.runtime_env),
            "/opt/klee-web": str(self.deployment_directory),
            "/run/lock/klee-web-deployment.lock": str(self.lock),
            "if ((EUID != 0)); then\n  printf 'compose-deployment.sh must run as root\\n' >&2\n  exit 1\nfi": "if false; then\n  printf 'compose-deployment.sh must run as root\\n' >&2\n  exit 1\nfi",
        }
        for original, replacement in replacements.items():
            self.assertIn(original, source)
            source = source.replace(original, replacement)
            self.assertNotIn(original, source)
        self.fixture_script = self.root / "compose-deployment.sh"
        self.fixture_script.write_text(source)
        self.fixture_script.chmod(self.fixture_script.stat().st_mode | stat.S_IXUSR)

    def write_fake_commands(self):
        self.write_command(
            "docker",
            """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
with Path(os.environ["FAKE_DOCKER_LOG"]).open("a") as log:
    log.write(json.dumps(sys.argv[1:]) + "\\n")
""",
        )
        self.write_command(
            "systemctl",
            """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
with Path(os.environ["FAKE_SYSTEMCTL_LOG"]).open("a") as log:
    log.write(json.dumps(sys.argv[1:]) + "\\n")
""",
        )
        self.write_command(
            "provision-tls.sh",
            """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
with Path(os.environ["FAKE_PROVISION_LOG"]).open("a") as log:
    log.write(json.dumps(sys.argv[1:]) + "\\n")
""",
        )
        (self.deployment_directory / "provision-tls.sh").symlink_to(self.bin_directory / "provision-tls.sh")

    def write_command(self, name, contents):
        command = self.bin_directory / name
        command.write_text(contents)
        command.chmod(command.stat().st_mode | stat.S_IXUSR)

    def run_script(self, action, role="single", acme=False, check=True):
        environment_lines = [f"DEPLOYMENT_ROLE={role}"]
        if acme:
            environment_lines.append(f"ACME_WEBROOT_DIRECTORY={self.root / 'webroot'}")
        self.deployment_env.write_text("\n".join(environment_lines) + "\n")
        environment = os.environ | {
            "PATH": f"{self.bin_directory}:{os.environ['PATH']}",
            "FAKE_DOCKER_LOG": str(self.docker_log),
            "FAKE_SYSTEMCTL_LOG": str(self.systemctl_log),
            "FAKE_PROVISION_LOG": str(self.provision_log),
        }
        return subprocess.run(
            [str(self.fixture_script), action], check=check, capture_output=True, text=True, env=environment
        )

    def calls(self, log):
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text().splitlines()]

    def assert_overlay_selection(self, role, acme, expected, absent):
        self.run_script("config", role=role, acme=acme)
        command = self.calls(self.docker_log)[0]
        for compose_file in expected:
            self.assertIn(str(self.deployment_directory / compose_file), command)
        for compose_file in absent:
            self.assertNotIn(str(self.deployment_directory / compose_file), command)

    def test_default_web_and_single_use_only_production_overlay(self):
        for role in ("web", "single"):
            with self.subTest(role=role):
                self.docker_log.unlink(missing_ok=True)
                self.assert_overlay_selection(role, False, ["compose.production.yml"], ["compose.acme.yml"])

    def test_worker_ignores_acme_configuration(self):
        self.assert_overlay_selection("worker", True, ["compose.worker.yml"], ["compose.acme.yml"])

    def test_configured_web_and_single_include_acme_overlay(self):
        for role in ("web", "single"):
            with self.subTest(role=role):
                self.docker_log.unlink(missing_ok=True)
                self.assert_overlay_selection(role, True, ["compose.production.yml", "compose.acme.yml"], [])

    def test_prepare_provisions_then_prepares_webroot_before_daemon_reload(self):
        self.run_script("prepare", role="single", acme=True)

        self.assertEqual(self.calls(self.provision_log), [[], ["prepare-webroot"]])
        self.assertEqual(self.calls(self.systemctl_log), [["daemon-reload"]])

    def test_missing_acme_overlay_fails_before_docker(self):
        (self.deployment_directory / "compose.acme.yml").unlink()

        result = self.run_script("config", role="web", acme=True, check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Required Compose file is missing", result.stderr)
        self.assertEqual(self.calls(self.docker_log), [])

    def test_held_shared_lock_stops_up_and_down_before_docker(self):
        with self.lock.open("w") as lock_file:
            flock(lock_file, LOCK_EX | LOCK_NB)
            for action in ("up", "down"):
                with self.subTest(action=action):
                    self.docker_log.unlink(missing_ok=True)
                    result = self.run_script(action, check=False)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("Another deployment or TLS operation", result.stderr)
                    self.assertEqual(self.calls(self.docker_log), [])


if __name__ == "__main__":
    unittest.main()
