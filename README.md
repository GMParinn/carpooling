# 🚗 CarPoolNet — Node-Based Carpooling System

A full-featured carpooling platform built with **Django**, **Django REST Framework**, **PostgreSQL**, **Docker**, and **Nginx**. Drivers publish trips along a directed road network graph; passengers request rides and confirm driver offers with automatic fare calculation.

---

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Quick Start (Local)](#quick-start-local)
- [Running with Docker](#running-with-docker)
- [Deployment to VPS](#deployment-to-vps)
- [API Reference](#api-reference)
- [Fare Calculation](#fare-calculation)
- [Project Structure](#project-structure)

---

## Features

### Phase 1 — Core
- **Role-based auth**: Driver, Passenger, Admin (Django built-in)
- **Road network graph**: Directed, admin-managed nodes and edges
- **BFS pathfinding**: Shortest path computed automatically on trip creation
- **Trip lifecycle**: Pending → Active → Completed (node-by-node advancement)
- **Carpool requests**: Proximity matching (within 2 hops), detour calculation, fare display
- **Offer system**: Driver sends offer → Passenger confirms → Route updated
- **Fare formula**: `fare = p × Σ(1/nᵢ) + base_fee`
- **Admin panel**: Manage nodes, edges, view live trips, suspend service

### Phase 2 — Enhanced
- **Mid-ride carpooling**: Passengers can join trips already in progress
- **Wallet system**: Passengers top up, fare auto-deducted on trip completion
- **Driver earnings**: Accumulated in wallet, visible on profile
- **Transaction history**: Every top-up, fare deduction, and earning logged
- **PostgreSQL**: Production-ready database

### Phase 3 — Deployment
- **Docker**: Separate containers for app, database, nginx
- **Gunicorn**: WSGI server with multiple workers
- **Nginx**: Reverse proxy, static file serving, SSL termination
- **Let's Encrypt**: Free HTTPS certificates with auto-renewal

### Extras
- **Interactive network graph**: Canvas-rendered graph on admin page
- **DRF API endpoints**: RESTful API for node advancement and request fetching
- **Auto-refresh UI**: Passenger request page refreshes every 15s; driver page every 30s
- **Demo seed command**: One command to populate the database with sample data

---

## Architecture

```
Browser ──► Nginx (port 80/443)
                │
                ├── /static/  ──► staticfiles volume (direct serve)
                │
                └── /         ──► Gunicorn (port 8000)
                                       │
                                  Django App
                                  ├── accounts/   (users, wallet, transactions)
                                  ├── network/    (nodes, edges, BFS routing)
                                  └── trips/      (trips, requests, offers, fares)
                                       │
                                  PostgreSQL (port 5432)
```

---

## Quick Start (Local — SQLite, no Docker)

### Prerequisites
- Python 3.12+
- pip

### Setup

```bash
# 1. Clone / enter the project
cd carpooling

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run migrations
python manage.py migrate

# 5. Seed demo data (creates users + road network)
python manage.py seed_demo

# 6. Start the development server
python manage.py runserver
```

Open http://127.0.0.1:8000

**Demo credentials:**

| Role      | Username   | Password  | Wallet |
|-----------|------------|-----------|--------|
| Admin     | admin      | admin123  | —      |
| Driver    | driver1    | demo1234  | —      |
| Driver    | driver2    | demo1234  | —      |
| Passenger | passenger1 | demo1234  | $100   |
| Passenger | passenger2 | demo1234  | $50    |

---

## Running with Docker

### Development (HTTP, SQLite-free, PostgreSQL)

```bash
# Copy env file
cp .env.example .env

# Start all services
docker compose -f docker-compose.dev.yml up --build

# Seed demo data (in a second terminal)
docker compose -f docker-compose.dev.yml exec web python manage.py seed_demo
```

Open http://localhost

### Production

```bash
# 1. Set your real values in .env
cp .env.example .env
nano .env   # Set SECRET_KEY, ALLOWED_HOSTS, POSTGRES_PASSWORD

# 2. Build and start
docker compose up --build -d

# 3. Seed demo data (optional)
docker compose exec web python manage.py seed_demo

# 4. Create your own superuser
docker compose exec web python manage.py createsuperuser
```

---

## Deployment to VPS

### 1. Provision a VPS
Sign up at DigitalOcean, Hetzner, AWS EC2, or similar. Create an Ubuntu 22.04 server.

```bash
# Connect via SSH
ssh root@YOUR_SERVER_IP
```

### 2. Install Docker on the VPS

```bash
apt update && apt upgrade -y
apt install -y docker.io docker-compose-plugin git
systemctl enable --now docker
```

### 3. Clone and configure the project

```bash
git clone https://github.com/yourname/carpooling.git
cd carpooling

cp .env.example .env
nano .env
# Set:
#   SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_urlsafe(50))">
#   DEBUG=False
#   ALLOWED_HOSTS=yourdomain.com www.yourdomain.com
#   POSTGRES_PASSWORD=<strong password>
```

### 4. Configure Nginx with your domain

```bash
# Edit nginx/nginx.conf — replace YOUR_DOMAIN_HERE with your actual domain
nano nginx/nginx.conf
```

### 5. Obtain SSL certificate (Let's Encrypt)

First, start Nginx in HTTP-only mode to allow ACME challenge:

```bash
# Temporarily use the dev config to get the cert
docker compose run --rm certbot certonly \
  --webroot --webroot-path=/var/www/certbot \
  --email you@example.com --agree-tos --no-eff-email \
  -d yourdomain.com -d www.yourdomain.com
```

### 6. Start production stack

```bash
docker compose up --build -d

# Check logs
docker compose logs -f web
docker compose logs -f nginx
```

### 7. Seed and create admin

```bash
docker compose exec web python manage.py seed_demo
docker compose exec web python manage.py createsuperuser
```

Your app is now live at https://yourdomain.com 🎉

---

## API Reference

All API endpoints require session authentication (login via `/accounts/login/`).

### `POST /api/trips/<trip_id>/advance/`

Driver advances to the next node on their route.

**Response:**
```json
{
  "message": "Arrived at Downtown.",
  "current_node": { "id": 2, "name": "Downtown" },
  "trip_completed": false,
  "status": "active"
}
```

---

### `GET /api/trips/<trip_id>/requests/`

Returns all eligible carpool requests for a driver's trip, with calculated detour and fare.

**Response:**
```json
{
  "trip_id": 1,
  "status": "active",
  "current_node": "Airport",
  "remaining_stops": 4,
  "capacity_available": true,
  "eligible_requests": [
    {
      "request_id": 7,
      "passenger": "passenger1",
      "pickup": { "id": 3, "name": "Suburb" },
      "dropoff": { "id": 5, "name": "Mall" },
      "detour_nodes": 1,
      "fare": 3.50
    }
  ],
  "pending_offers": [...],
  "confirmed_passengers": [...]
}
```

---

### `GET /api/graph/`

Returns the complete road network graph.

**Response:**
```json
{
  "nodes": [
    { "id": 1, "name": "Airport", "latitude": 28.56, "longitude": 77.10 }
  ],
  "edges": [
    { "id": 1, "from_node_id": 1, "to_node_id": 2 }
  ]
}
```

---

## Fare Calculation

The fare formula is:

```
fare = p × Σ(1/nᵢ) + base_fee
```

Where:
- `p` = unit price per hop (default: **$1.50**, configurable via `FARE_UNIT_PRICE`)
- `nᵢ` = total number of passengers in the vehicle at hop `i` (including the new passenger)
- The sum runs only over hops where the passenger is on board (from pickup to dropoff)
- `base_fee` = flat base charge (default: **$2.00**, configurable via `FARE_BASE_FEE`)

**Example:**

Driver route: A → B → C → D → E  
Passenger pickup: B, dropoff: D  
Existing confirmed passenger in car from A to E.

At hops B→C and C→D, there are **2** passengers in the car.

```
fare = 1.50 × (1/2 + 1/2) + 2.00
     = 1.50 × 1.0 + 2.00
     = $3.50
```

If the passenger were the only one in the car:
```
fare = 1.50 × (1/1 + 1/1) + 2.00 = $5.00
```

Passengers get a **cheaper fare when sharing** with other confirmed passengers.

---

## Project Structure

```
carpooling/
├── carpooling/                 # Django project config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── accounts/                   # Users, wallet, transactions
│   ├── models.py               # User (driver/passenger), Transaction
│   ├── views.py                # register, login, logout, profile, topup
│   ├── forms.py
│   └── urls.py
│
├── network/                    # Road network graph
│   ├── models.py               # Node, Edge, ServiceStatus
│   ├── graph_utils.py          # BFS pathfinding, proximity, route insertion
│   ├── views.py                # Admin CRUD for nodes/edges/service toggle
│   ├── urls.py
│   └── management/commands/
│       └── seed_demo.py        # Demo data seeder
│
├── trips/                      # Core carpool logic
│   ├── models.py               # Trip, RouteNode, CarpoolRequest, CarpoolOffer
│   ├── views.py                # All SSR views (driver + passenger)
│   ├── api_views.py            # DRF API views
│   ├── fare_service.py         # Fare calculation
│   ├── forms.py
│   ├── urls.py                 # SSR URLs
│   └── api_urls.py             # API URLs
│
├── templates/
│   ├── base.html               # Bootstrap 5 layout + sidebar nav
│   ├── registration/
│   │   ├── login.html
│   │   └── register.html
│   ├── accounts/
│   │   ├── profile.html
│   │   └── topup.html
│   ├── network/
│   │   └── admin.html          # Node/edge management + canvas graph
│   └── trips/
│       ├── driver_dashboard.html
│       ├── create_trip.html
│       ├── trip_detail_driver.html
│       ├── driver_incoming_requests.html
│       ├── passenger_dashboard.html
│       ├── create_request.html
│       ├── request_detail.html
│       └── admin_active_trips.html
│
├── static/                     # Static assets (CSS/JS)
├── nginx/
│   ├── nginx.conf              # Production (HTTPS + SSL)
│   └── nginx.dev.conf          # Development (HTTP only)
│
├── Dockerfile
├── docker-compose.yml          # Production stack
├── docker-compose.dev.yml      # Development stack
├── requirements.txt
├── manage.py
├── .env.example
└── .gitignore
```

---

## Admin Panel

Access the Django admin at `/admin/` (login with superuser credentials).

The custom network admin at `/network/admin/` (staff required) provides:
- Visual graph of all nodes and edges (canvas-rendered)
- Add/remove nodes with optional lat/lng coordinates
- Add/remove directed edges
- Toggle the carpooling service on/off

---

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | (required) | Django secret key |
| `DEBUG` | `True` | Debug mode |
| `ALLOWED_HOSTS` | `localhost 127.0.0.1` | Space-separated allowed hosts |
| `POSTGRES_DB` | `carpooling` | Database name |
| `POSTGRES_USER` | `carpooling` | Database user |
| `POSTGRES_PASSWORD` | (required) | Database password |
| `POSTGRES_HOST` | `db` | Database host |
| `FARE_BASE_FEE` | `2.00` | Flat base fee per carpool |
| `FARE_UNIT_PRICE` | `1.50` | Price per hop unit |
# carpooling
