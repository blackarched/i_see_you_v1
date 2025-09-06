
# Quick Start (single-command)

This project includes a `start.sh` helper that will generate secure defaults and launch the system using Docker Compose.

**Prerequisites**
- Docker & docker-compose installed.

**One command**
```bash
./start.sh
```

This will:
- Create a `.env` file with a secure `ISEEYOU_SECRET` and a bcrypt admin password hash
- Launch the dashboard and Redis using `docker-compose`
- The dashboard will be available at `http://localhost:8000`

If you prefer to run outside Docker, `start.sh` prints the manual steps.


ISeeYou Monitoring Suite (Production Grade)

ISeeYou is a secure, resilient, and observable local network monitoring tool. It uses active and passive techniques to discover devices and presents the data through a hardened, HTTPS-enabled web dashboard.

## Production-Ready Features

* **Security:** HTTPS-enabled dashboard, expiring token authentication, secure file permissions for configuration, and Content Security Policy (CSP) headers.
* **Resilience:** Robust error handling in all threads, graceful shutdown and restart, and a thread-safe architecture.
* **Observability:** Structured JSON logging for easy parsing, log rotation, and a `/api/health` endpoint to monitor the status of all background services.
* **Maintainability:** A modular design with a dedicated scheduler, a clean project structure with separated concerns, and a CI pipeline template for automated testing.
* **Dependency Management:** Pinned dependencies in `requirements.txt` for reproducible builds.

## Installation

1.  **Prerequisites:** Python 3.8+ is required.
2.  **Clone & Install:**
    ```bash
    git clone <your_repo_url>
    cd iseeyou_project
    pip install -r requirements.txt
    ```
3.  **Generate SSL Certificate (for local development):**
    The dashboard requires HTTPS. For local testing, you can use `openssl` to generate a self-signed certificate.
    ```bash
    openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
    ```
    Then, update `iseeyou.ini` to point to these files. For production, use a certificate from a trusted Certificate Authority.

## Configuration (`iseeyou.ini`)

Create and edit the `iseeyou.ini` file. **This file contains secrets and will be automatically locked to read-only for the owner (`chmod 600`) on startup.**

| Section     | Key                    | Description                                                                                             | Example                                    |
|-------------|------------------------|---------------------------------------------------------------------------------------------------------|--------------------------------------------|
| `server`    | `enable_api`           | `true` or `false` to enable the web dashboard.                                                          | `true`                                     |
| `network`   | `subnet`               | The network range to scan in CIDR notation.                                                             | `192.168.1.0/24`                           |
| `network`   | `interface`            | The network adapter for passive sniffing (use `ip addr` or `ipconfig`).                                 | `eth0`                                     |
| `network`   | `scan_interval`        | How often the active scanner runs, in seconds.                                                          | `300`                                      |
| `logging`   | `level`                | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`).                                                | `INFO`                                     |
| `logging`   | `file_path`            | Path for the log file. Logs are automatically rotated.                                                  | `iseeyou.log`                              |
| `logging`   | `json_format`          | `true` for structured JSON logs, `false` for plain text.                                                | `true`                                     |
| `dashboard` | `auth_token`           | **SECRET:** A long, random string to access the dashboard.                                              | `your-super-secret-random-string-here`     |
| `dashboard` | `token_lifetime_seconds` | How long the token is valid before the server needs a restart.                                          | `86400`                                    |
| `dashboard` | `enable_https`         | `true` to enable HTTPS. **Required for modern browsers.** | `true`                                     |
| `dashboard` | `ssl_cert_path`        | Path to your SSL certificate (`.pem` file). Use `adhoc` for Flask's self-signed cert (dev only).        | `cert.pem`                                 |
| `dashboard` | `ssl_key_path`         | Path to your SSL private key (`.key` file). Use `adhoc` for Flask's self-signed cert (dev only).         | `key.pem`                                  |

## Running the Service

The service must be run with root/administrator privileges for network packet sniffing.

```bash
# On Linux or macOS
sudo python iseeyou_server.py

# On Windows (in an Administrator terminal)
python iseeyou_server.py
Access the dashboard at https://<your_server_ip>:5000. You will be prompted for the auth_token.

API Documentation (OpenAPI/Swagger Style)
All endpoints require an Authorization: Bearer <your_token> header.

GET /api/health

Summary: Checks the health of all running threads.

Responses:

200 OK: Returns a JSON object with the status of each thread (alive or dead).

GET /api/devices

Summary: Retrieves the list of all discovered devices.

Responses:

200 OK: Returns a JSON object where keys are IP addresses and values are device details.

POST /api/scan/start

Summary: Triggers a new on-demand active scan of the network.

Responses:

202 Accepted: The scan has been successfully initiated in the background.

Troubleshooting
Permission Denied (Sniffing): Ensure you are running the script with sudo or as an Administrator.

Invalid Interface: Double-check the interface name using ip addr or ipconfig.

Dashboard Not Loading: Verify enable_api=true and that no other service is using port 5000. Check the iseeyou.log for errors.

HTTPS Browser Warning: This is expected with self-signed certificates. You can safely proceed for local access.

Unauthorized (401 Error): Ensure your Authorization: Bearer <token> header is correct and that the token has not expired.


## Deployment (production) — recommendations

**Secrets & environment**
- Set `ISEEYOU_SECRET` to a long, random value. **Required** in production.
- Create a bcrypt hash of your admin password and set `ISEEYOU_ADMIN_PASS_HASH`. Avoid using plaintext envs in production.
  ```
  python -c "import bcrypt; print(bcrypt.hashpw(b'your-password', bcrypt.gensalt()).decode())"
  ```
- Optionally set `REDIS_URL` (e.g. `redis://localhost:6379/0`) to enable server-side session revocation and simple persistence.

**Docker**
A sample `Dockerfile` and `docker-compose.yml` are included. When running the container you must give it limited network capabilities to sniff packets (preferred over running as root):

```bash
# Using docker-compose (recommended)
export ISEEYOU_SECRET="your_secret_here"
export ISEEYOU_ADMIN_PASS_HASH="your_bcrypt_hash_here"
docker-compose up --build
```

`docker-compose.yml` adds `cap_add: [NET_RAW, NET_ADMIN]` to grant minimal capabilities for packet sniffing. Do not run the container as root in production unless you understand the implications.

**Notes**
- If you run the frontend on a different origin, configure CORS to allow that origin and `Access-Control-Allow-Credentials: true`.
- Redis is used for session revocation if `REDIS_URL` is set. Sessions will be stored while valid and deleted on logout.
- Ensure system packages required for `scapy` are available on the host/container (`libpcap-dev` or system-provided pcap).

