import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from fcntl import LOCK_EX, LOCK_NB, flock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "infra" / "doc" / "provision-tls.sh"
DOMAIN = "klee.doc.ic.ac.uk"


class ProvisionTlsTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.letsencrypt = self.root / "letsencrypt"
        self.tls = self.root / "tls"
        self.webroot = self.root / "webroot"
        self.lock = self.root / "lock" / "klee-web-deployment.lock"
        self.bin_directory = self.root / "bin"
        self.docker_log = self.root / "docker.jsonl"
        self.served_certificate = self.root / "served.pem"
        self.control_directory = self.root / "control"
        self.certificate_directory = self.letsencrypt / "live" / "klee-doc"
        self.bin_directory.mkdir()
        self.control_directory.mkdir()
        self.lock.parent.mkdir()
        self.certificates = self.create_certificates()
        self.write_fixture_script()
        self.write_fake_commands()
        self.install_live_certificate("one")
        shutil.copyfile(self.certificates["one"] / "fullchain.pem", self.served_certificate)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def create_certificates(self):
        certificates = {}
        certificate_root = self.root / "certificates"
        certificate_root.mkdir()
        for name in ("one", "two", "three", "four", "untrusted", "wrong-hostname"):
            directory = certificate_root / name
            directory.mkdir()
            certificate_domain = "wrong.example.test" if name == "wrong-hostname" else DOMAIN
            command = [
                "/usr/bin/openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-days",
                "2",
                "-subj",
                f"/CN={certificate_domain}",
                "-addext",
                f"subjectAltName=DNS:{certificate_domain}",
                "-addext",
                "basicConstraints=critical,CA:true",
                "-keyout",
                str(directory / "privkey.pem"),
                "-out",
                str(directory / "fullchain.pem"),
            ]
            subprocess.run(command, check=True, capture_output=True, text=True)
            certificates[name] = directory
        return certificates

    def write_fixture_script(self):
        source = SCRIPT.read_text()
        replacements = {
            "/etc/letsencrypt": str(self.letsencrypt),
            "/etc/klee-web/tls": str(self.tls),
            "/run/lock/klee-web-deployment.lock": str(self.lock),
            "if ((EUID != 0)); then\n  printf 'provision-tls.sh must run as root\\n' >&2\n  exit 1\nfi": "if false; then\n  printf 'provision-tls.sh must run as root\\n' >&2\n  exit 1\nfi",
        }
        for original, replacement in replacements.items():
            self.assertIn(original, source)
            source = source.replace(original, replacement)
            self.assertNotIn(original, source)
        self.fixture_script = self.root / "provision-tls.sh"
        self.fixture_script.write_text(source)
        self.fixture_script.chmod(self.fixture_script.stat().st_mode | stat.S_IXUSR)

    def write_fake_commands(self):
        self.write_command(
            "docker",
            """#!/usr/bin/env python3
import json
import os
import shutil
import sys
from pathlib import Path

args = sys.argv[1:]
with Path(os.environ["FAKE_DOCKER_LOG"]).open("a") as log:
    log.write(json.dumps(args) + "\\n")
control = Path(os.environ["FAKE_CONTROL_DIRECTORY"])
if args[0] == "ps":
    print("nginx-test-container")
elif args[0] == "inspect":
    print(os.environ["FAKE_DOCKER_MOUNT"])
elif args[0] == "run":
    if (control / "certbot-fail").exists():
        sys.exit(1)
    if (control / "certbot-mutates").exists():
        source = Path(os.environ["FAKE_NEXT_CERTIFICATE"])
        live = Path(os.environ["FAKE_LIVE_CERTIFICATE"])
        shutil.copyfile(source / "fullchain.pem", live / "fullchain.pem")
        shutil.copyfile(source / "privkey.pem", live / "privkey.pem")
elif args[0] == "exec":
    command = args[2:]
    if command == ["nginx", "-t"] and (control / "nginx-test-fails").exists():
        sys.exit(1)
    if command == ["nginx", "-s", "reload"]:
        failure_marker = control / "reload-failure-recorded"
        if os.environ.get("FAKE_RELOAD_FAIL_ONCE") == "1" and not failure_marker.exists():
            failure_marker.touch()
            sys.exit(1)
        if not (control / "reload-keeps-old-certificate").exists():
            current = Path(os.environ["FAKE_TLS_DIRECTORY"]) / "current" / "fullchain.pem"
            shutil.copyfile(current, os.environ["FAKE_SERVED_CERTIFICATE"])
""",
        )
        self.write_command(
            "openssl",
            """#!/usr/bin/env bash
if [[ ${1:-} == s_client ]]; then
  cat "$FAKE_SERVED_CERTIFICATE"
  exit 0
fi
exec /usr/bin/openssl "$@"
""",
        )
        self.write_command("sleep", "#!/usr/bin/env bash\nexit 0\n")

    def write_command(self, name, contents):
        command = self.bin_directory / name
        command.write_text(contents)
        command.chmod(command.stat().st_mode | stat.S_IXUSR)

    def install_live_certificate(self, name, key_name=None):
        self.certificate_directory.mkdir(parents=True, exist_ok=True)
        key_name = key_name or name
        shutil.copyfile(self.certificates[name] / "fullchain.pem", self.certificate_directory / "fullchain.pem")
        shutil.copyfile(self.certificates[key_name] / "privkey.pem", self.certificate_directory / "privkey.pem")

    def run_script(
        self, action, next_certificate="two", check=True, mounted_directory=None, reload_fails_once=False
    ):
        trusted_certificates = "".join(
            (self.certificates[name] / "fullchain.pem").read_text()
            for name in ("one", "two", "three", "four")
        )
        trust_store = self.root / "trusted-certificates.pem"
        trust_store.write_text(trusted_certificates)
        environment = os.environ | {
            "ACME_WEBROOT_DIRECTORY": str(self.webroot),
            "TLS_CERTIFICATE_DIRECTORY": str(self.tls),
            "SSL_CERT_FILE": str(trust_store),
            "PATH": f"{self.bin_directory}:{os.environ['PATH']}",
            "FAKE_DOCKER_LOG": str(self.docker_log),
            "FAKE_CONTROL_DIRECTORY": str(self.control_directory),
            "FAKE_DOCKER_MOUNT": str(mounted_directory or self.tls),
            "FAKE_NEXT_CERTIFICATE": str(self.certificates[next_certificate]),
            "FAKE_LIVE_CERTIFICATE": str(self.certificate_directory),
            "FAKE_TLS_DIRECTORY": str(self.tls),
            "FAKE_SERVED_CERTIFICATE": str(self.served_certificate),
            "FAKE_RELOAD_FAIL_ONCE": "1" if reload_fails_once else "0",
        }
        return subprocess.run(
            [str(self.fixture_script), action],
            check=check,
            capture_output=True,
            text=True,
            env=environment,
        )

    def docker_calls(self):
        if not self.docker_log.exists():
            return []
        return [json.loads(line) for line in self.docker_log.read_text().splitlines()]

    def prepare(self):
        return self.run_script("prepare-webroot")

    def current_certificate(self):
        return (self.tls / "current" / "fullchain.pem").read_bytes()

    def test_prepare_initializes_generation_and_legacy_aliases(self):
        result = self.prepare()

        self.assertIn("Prepared the webroot", result.stdout)
        self.assertTrue((self.webroot / ".well-known" / "acme-challenge").is_dir())
        self.assertTrue((self.tls / "current").is_symlink())
        self.assertEqual(os.readlink(self.tls / "selfsigned.crt"), "current/fullchain.pem")
        self.assertEqual(os.readlink(self.tls / "selfsigned.key"), "current/privkey.pem")
        self.assertEqual(self.current_certificate(), (self.certificates["one"] / "fullchain.pem").read_bytes())

    def test_noop_renew_skips_nginx_reload(self):
        self.prepare()
        self.docker_log.unlink(missing_ok=True)

        result = self.run_script("renew")

        self.assertIn("already serves the current certificate", result.stdout)
        self.assertFalse(any(call[:1] == ["exec"] for call in self.docker_calls()))

    def test_stale_temporary_symlink_does_not_block_activation(self):
        self.prepare()
        (self.tls / ".current-next").symlink_to("generation.interrupted")
        (self.control_directory / "certbot-mutates").touch()

        self.run_script("renew", "two")

        self.assertEqual(self.current_certificate(), (self.certificates["two"] / "fullchain.pem").read_bytes())
        self.assertFalse((self.tls / ".current-next").is_symlink())

    def test_signal_after_success_keeps_selected_generation(self):
        self.prepare()
        (self.control_directory / "certbot-mutates").touch()
        source = self.fixture_script.read_text()
        completed_activation = "  activation_pending=false\n  candidate_directory=''"
        self.assertEqual(source.count(completed_activation), 1)
        self.fixture_script.write_text(source.replace(
            completed_activation,
            "  activation_pending=false\n  kill -TERM \"$$\"\n  candidate_directory=''",
        ))

        result = self.run_script("renew", "two", check=False)

        self.assertEqual(result.returncode, 143)
        self.assertTrue((self.tls / "current" / "fullchain.pem").exists())
        self.assertEqual(self.current_certificate(), (self.certificates["two"] / "fullchain.pem").read_bytes())

    def test_rotated_valid_certificate_reloads_and_serves_new_generation(self):
        self.prepare()
        (self.control_directory / "certbot-mutates").touch()

        result = self.run_script("renew", "two")

        self.assertIn("nginx serves the selected certificate", result.stdout)
        self.assertEqual(self.current_certificate(), (self.certificates["two"] / "fullchain.pem").read_bytes())
        self.assertEqual(self.served_certificate.read_bytes(), (self.certificates["two"] / "fullchain.pem").read_bytes())
        self.assertIn(["exec", "nginx-test-container", "nginx", "-s", "reload"], self.docker_calls())

    def test_invalid_candidate_never_switches_current_or_reloads(self):
        self.prepare()
        original = self.current_certificate()
        self.install_live_certificate("two", "three")
        key_mismatch = self.run_script("renew", "two", check=False)
        self.assertNotEqual(key_mismatch.returncode, 0)
        self.assertIn("Certificate and private key do not match", key_mismatch.stderr)
        self.assertEqual(self.current_certificate(), original)
        self.assertFalse(any(call[:1] == ["exec"] for call in self.docker_calls()))

    def test_wrong_hostname_candidate_never_switches_current_or_reloads(self):
        self.prepare()
        original = self.current_certificate()
        self.install_live_certificate("wrong-hostname")
        self.docker_log.unlink(missing_ok=True)

        result = self.run_script("renew", check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.current_certificate(), original)
        self.assertFalse(any(call[:1] == ["exec"] for call in self.docker_calls()))

        self.docker_log.unlink(missing_ok=True)
        (self.control_directory / "certbot-mutates").touch()
        untrusted = self.run_script("renew", "untrusted", check=False)
        self.assertNotEqual(untrusted.returncode, 0)
        self.assertEqual(self.current_certificate(), original)
        self.assertFalse(any(call[:1] == ["exec"] for call in self.docker_calls()))

    def test_failed_certbot_renewal_leaves_current_certificate_and_skips_reload(self):
        self.prepare()
        original = self.current_certificate()
        self.docker_log.unlink(missing_ok=True)
        (self.control_directory / "certbot-fail").touch()

        result = self.run_script("renew", check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.current_certificate(), original)
        self.assertFalse(any(call[:1] == ["exec"] for call in self.docker_calls()))

    def test_nginx_configuration_failure_rolls_back_current_generation(self):
        self.prepare()
        original = self.current_certificate()
        (self.control_directory / "certbot-mutates").touch()
        (self.control_directory / "nginx-test-fails").touch()

        result = self.run_script("renew", "two", check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Restoring the previous certificate selection", result.stderr)
        self.assertEqual(self.current_certificate(), original)
        self.assertEqual(sorted(self.tls.glob("generation.*")), [self.tls / os.readlink(self.tls / "current")])

    def test_nginx_reload_failure_rolls_back_and_reloads_previous_generation(self):
        self.prepare()
        original = self.current_certificate()
        (self.control_directory / "certbot-mutates").touch()

        result = self.run_script("renew", "two", check=False, reload_fails_once=True)

        self.assertTrue(
            (self.control_directory / "reload-failure-recorded").exists(), self.docker_calls()
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Restoring the previous certificate selection", result.stderr)
        self.assertEqual(self.current_certificate(), original)
        self.assertEqual(self.served_certificate.read_bytes(), original)
        self.assertEqual(
            self.docker_calls().count(["exec", "nginx-test-container", "nginx", "-s", "reload"]),
            2,
        )

    def test_served_fingerprint_mismatch_rolls_back_but_retains_live_certificate(self):
        self.prepare()
        original = self.current_certificate()
        (self.control_directory / "certbot-mutates").touch()
        (self.control_directory / "reload-keeps-old-certificate").touch()

        result = self.run_script("renew", "two", check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("nginx did not serve the selected certificate", result.stderr)
        self.assertEqual(self.current_certificate(), original)
        self.assertEqual(
            (self.certificate_directory / "fullchain.pem").read_bytes(),
            (self.certificates["two"] / "fullchain.pem").read_bytes(),
        )
        self.assertGreaterEqual(
            self.docker_calls().count(["exec", "nginx-test-container", "nginx", "-s", "reload"]),
            2,
        )

    def test_dry_run_and_reconfigure_do_not_publish_or_reload(self):
        self.prepare()
        original = self.current_certificate()
        (self.control_directory / "certbot-mutates").touch()

        for action in ("dry-run", "reconfigure"):
            with self.subTest(action=action):
                self.docker_log.unlink(missing_ok=True)
                self.install_live_certificate("one")
                result = self.run_script(action, "two")
                self.assertEqual(result.returncode, 0)
                self.assertEqual(self.current_certificate(), original)
                self.assertFalse(any(call[:1] == ["exec"] for call in self.docker_calls()))

    def test_mount_mismatch_stops_before_certbot(self):
        self.prepare()
        environment_mount = self.tls.with_name("wrong-tls-directory")
        result = self.run_script("renew", check=False, mounted_directory=environment_mount)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("nginx must mount the configured certificate directory", result.stderr)
        self.assertFalse(any(call[:1] == ["run"] for call in self.docker_calls()))

    def test_held_deployment_lock_stops_before_docker_or_certificate_changes(self):
        self.prepare()
        original = self.current_certificate()
        self.docker_log.unlink(missing_ok=True)
        with self.lock.open("w") as lock_file:
            flock(lock_file, LOCK_EX | LOCK_NB)
            result = self.run_script("renew", check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Another deployment or TLS operation", result.stderr)
        self.assertEqual(self.current_certificate(), original)
        self.assertEqual(self.docker_calls(), [])

    def test_legacy_provision_copies_flat_certificate_files(self):
        environment = os.environ | {
            "PATH": f"{self.bin_directory}:{os.environ['PATH']}",
            "FAKE_DOCKER_LOG": str(self.docker_log),
            "FAKE_CONTROL_DIRECTORY": str(self.control_directory),
        }

        result = subprocess.run(
            [str(self.fixture_script)], check=True, capture_output=True, text=True, env=environment
        )

        self.assertIn("Reused the existing certificate", result.stdout)
        self.assertTrue((self.tls / "fullchain.pem").is_file())
        self.assertTrue((self.tls / "privkey.pem").is_file())
        self.assertFalse((self.tls / "current").exists())

    def test_three_renewals_retain_only_current_and_previous_generations(self):
        self.prepare()
        (self.control_directory / "certbot-mutates").touch()

        for certificate in ("two", "three", "four"):
            self.run_script("renew", certificate)

        current = os.readlink(self.tls / "current")
        generations = sorted(path.name for path in self.tls.glob("generation.*"))
        self.assertEqual(self.current_certificate(), (self.certificates["four"] / "fullchain.pem").read_bytes())
        self.assertEqual(len(generations), 2)
        self.assertIn(current, generations)
        self.assertEqual(
            (self.tls / next(name for name in generations if name != current) / "fullchain.pem").read_bytes(),
            (self.certificates["three"] / "fullchain.pem").read_bytes(),
        )

        self.run_script("renew", "four")
        self.assertEqual(sorted(path.name for path in self.tls.glob("generation.*")), generations)


if __name__ == "__main__":
    unittest.main()
