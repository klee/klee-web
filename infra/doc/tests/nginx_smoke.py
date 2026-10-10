#!/usr/bin/env python3
"""Exercise nginx TLS rotation against the built frontend image."""

import hashlib
import http.client
import json
import os
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
NGINX_CONFIG = ROOT / "frontend" / "nginx.conf"
DOMAIN = "klee.doc.ic.ac.uk"
IMAGE = os.environ.get("TLS_NGINX_IMAGE", "klee-web-frontend")


def run(*command: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=check, capture_output=True, text=True)


def check(name: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(name)
    print(f"{name}: ok")


def generate_certificate(directory: Path) -> None:
    run(
        "openssl",
        "req",
        "-x509",
        "-newkey",
        "rsa:2048",
        "-nodes",
        "-days",
        "2",
        "-subj",
        f"/CN={DOMAIN}",
        "-addext",
        f"subjectAltName=DNS:{DOMAIN}",
        "-addext",
        "basicConstraints=critical,CA:true",
        "-keyout",
        str(directory / "privkey.pem"),
        "-out",
        str(directory / "fullchain.pem"),
    )


def replace_current(certificate_directory: Path, generation: str) -> None:
    replacement = certificate_directory / ".current-next"
    replacement.unlink(missing_ok=True)
    replacement.symlink_to(generation)
    os.replace(replacement, certificate_directory / "current")


def published_ports(container: str) -> tuple[int, int]:
    result = run("docker", "inspect", "--format", "{{json .NetworkSettings.Ports}}", container)
    ports = json.loads(result.stdout)
    return (
        int(ports["80/tcp"][0]["HostPort"]),
        int(ports["443/tcp"][0]["HostPort"]),
    )


def request(port: int, method: str, path: str) -> tuple[int, dict[str, str], bytes]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request(method, path, headers={"Host": DOMAIN})
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


def certificate_der(port: int, trusted_certificate: Path) -> bytes:
    context = ssl.create_default_context(cafile=str(trusted_certificate))
    with socket.create_connection(("127.0.0.1", port), timeout=5) as connection:
        with context.wrap_socket(connection, server_hostname=DOMAIN) as tls_connection:
            return tls_connection.getpeercert(binary_form=True)


def wait_for_certificate(port: int, trusted_certificate: Path, expected_der: bytes) -> None:
    expected_fingerprint = hashlib.sha256(expected_der).digest()
    deadline = time.monotonic() + 10
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            served_der = certificate_der(port, trusted_certificate)
            if hashlib.sha256(served_der).digest() == expected_fingerprint:
                return
        except (OSError, ssl.SSLError) as error:
            last_error = error
        time.sleep(0.1)
    raise AssertionError(f"TLS certificate did not rotate: {last_error}")


def main() -> int:
    container = ""
    with tempfile.TemporaryDirectory(prefix="nginx-smoke-") as temporary_directory:
        root = Path(temporary_directory)
        certificates = root / "certificates"
        webroot = root / "webroot"
        secret = root / "admin_htpasswd"
        certificates.mkdir()
        (webroot / ".well-known" / "acme-challenge").mkdir(parents=True)
        secret.write_text("smoke:{PLAIN}smoke\n")

        generation_one = certificates / "generation-one"
        generation_two = certificates / "generation-two"
        invalid_generation = certificates / "generation-invalid"
        for generation in (generation_one, generation_two, invalid_generation):
            generation.mkdir()
        generate_certificate(generation_one)
        generate_certificate(generation_two)
        (invalid_generation / "fullchain.pem").write_bytes(
            (generation_one / "fullchain.pem").read_bytes()
        )
        (invalid_generation / "privkey.pem").write_bytes(
            (generation_two / "privkey.pem").read_bytes()
        )
        (certificates / "current").symlink_to(generation_one.name)
        (certificates / "selfsigned.crt").symlink_to("current/fullchain.pem")
        (certificates / "selfsigned.key").symlink_to("current/privkey.pem")

        token = "nginx-smoke-token"
        contents = b"challenge-response\n"
        (webroot / ".well-known" / "acme-challenge" / token).write_bytes(contents)
        label = f"klee-web.nginx-smoke={uuid.uuid4()}"
        container = f"klee-web-nginx-smoke-{uuid.uuid4().hex}"

        try:
            run(
                "docker",
                "run",
                "--detach",
                "--rm",
                "--name",
                container,
                "--label",
                label,
                "--add-host",
                "api:127.0.0.1",
                "--publish",
                "127.0.0.1::80",
                "--publish",
                "127.0.0.1::443",
                "--volume",
                f"{NGINX_CONFIG}:/etc/nginx/conf.d/default.conf:ro",
                "--volume",
                f"{certificates}:/etc/nginx/certs:ro",
                "--volume",
                f"{webroot}:/var/www/certbot:ro",
                "--volume",
                f"{secret}:/run/secrets/admin_htpasswd:ro",
                IMAGE,
            )
            http_port, https_port = published_ports(container)
            check("nginx configuration", run("docker", "exec", container, "nginx", "-t").returncode == 0)

            for path in ("/", "/api", "/admin"):
                status, headers, _ = request(http_port, "GET", path)
                check(f"HTTP redirect {path}", status == 301 and headers.get("Location") == f"https://{DOMAIN}{path}")
            status, _, body = request(http_port, "GET", f"/.well-known/acme-challenge/{token}")
            check("challenge GET", status == 200 and body == contents)
            status, headers, body = request(http_port, "HEAD", f"/.well-known/acme-challenge/{token}")
            check("challenge HEAD", status == 200 and not body and headers.get("Content-Length") == str(len(contents)))
            status, _, _ = request(http_port, "GET", "/.well-known/acme-challenge/missing")
            check("challenge missing", status == 404)
            status, _, _ = request(http_port, "POST", f"/.well-known/acme-challenge/{token}")
            check("challenge POST", status == 403)

            certificate_one = (generation_one / "fullchain.pem").read_bytes()
            certificate_two = (generation_two / "fullchain.pem").read_bytes()
            expected_one = ssl.PEM_cert_to_DER_cert(certificate_one.decode())
            check("initial TLS certificate", certificate_der(https_port, generation_one / "fullchain.pem") == expected_one)
            container_id = run("docker", "inspect", "--format", "{{.Id}}", container).stdout.strip()

            replace_current(certificates, generation_two.name)
            check("rotated nginx configuration", run("docker", "exec", container, "nginx", "-t").returncode == 0)
            run("docker", "exec", container, "nginx", "-s", "reload")
            expected_two = ssl.PEM_cert_to_DER_cert(certificate_two.decode())
            wait_for_certificate(https_port, generation_two / "fullchain.pem", expected_two)
            check("rotated TLS certificate", certificate_der(https_port, generation_two / "fullchain.pem") == expected_two)
            check("reload keeps container", run("docker", "inspect", "--format", "{{.Id}}", container).stdout.strip() == container_id)

            replace_current(certificates, invalid_generation.name)
            try:
                check("invalid keypair rejected", run("docker", "exec", container, "nginx", "-t", check=False).returncode != 0)
                check("failed validation keeps TLS", certificate_der(https_port, generation_two / "fullchain.pem") == expected_two)
            finally:
                replace_current(certificates, generation_two.name)
        finally:
            if container:
                run("docker", "rm", "--force", container, check=False)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"nginx smoke failed: {error}", file=sys.stderr)
        raise SystemExit(1)
