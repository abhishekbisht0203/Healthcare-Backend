# Healthcare Backend API

A backend system for a healthcare application built with **Django**, **Django REST Framework** and **PostgreSQL**. Users register and log in, then manage patient and doctor records and assign doctors to patients, all secured with JWT authentication.

---

## Table of contents

- [Tech stack](#tech-stack)
- [Features](#features)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [Environment variables](#environment-variables)
- [API reference](#api-reference)
- [Response formats](#response-formats)
- [Error handling](#error-handling)
- [Filtering, search and pagination](#filtering-search-and-pagination)
- [Permissions model](#permissions-model)
- [Running tests](#running-tests)
- [Trying it with cURL](#trying-it-with-curl)
- [Postman setup](#postman-setup)
- [Design notes](#design-notes)

---

## Tech stack

| Concern | Choice |
| --- | --- |
| Framework | Django 5+ |
| API layer | Django REST Framework |
| Database | PostgreSQL |
| Authentication | `djangorestframework-simplejwt` (JWT access + refresh) |
| Filtering | `django-filter` + DRF Search/Ordering |
| CORS | `django-cors-headers` |
| Config | `python-dotenv` (all secrets from `.env`) |
| Tests | Django `APITestCase` (80 tests) |

---

## Features

- **Email-based custom user model** with a custom manager, unique email constraint and Django password validators.
- **JWT authentication** — short-lived access token, rotating refresh token, `GET /api/auth/me/`, password change.
- **Patient CRUD** scoped to the records created by the authenticated user.
- **Doctor CRUD** over a shared, browsable directory with ownership-guarded writes.
- **Patient ↔ doctor assignments** with duplicate prevention enforced by a database unique constraint.
- **Consistent error envelope** for every failure, produced by a custom DRF exception handler.
- **Filtering, search and ordering** on the list endpoints, plus page-number pagination.
- **Throttling** on authentication endpoints.
- **Database-level integrity** — `UNIQUE` constraints on email, license number and assignment pairs; cascading deletes and indexes on hot query paths.
- **Comprehensive test suite** covering auth, permissions, validation, CRUD and mapping rules.

---

## Project structure

```
.
├── config/                  # Django project configuration
│   ├── settings.py          # Settings, all values read from environment variables
│   └── urls.py              # Root URLconf + API discovery document at "/"
├── common/                  # Cross-cutting concerns
│   ├── exceptions.py        # Single error-envelope exception handler
│   ├── pagination.py        # Shared page-number pagination class
│   ├── permissions.py       # IsOwnerOrReadOnly, IsMappingParticipantOrReadOnly
│   └── tests.py             # Error-envelope and API-root tests
├── users/                   # Custom user model + auth endpoints
│   ├── models.py            # AbstractBaseUser with email as USERNAME_FIELD
│   ├── serializers.py       # Register / Login / ChangePassword validation
│   └── views.py             # register, login, me, change-password
├── patients/                # Patient records
├── doctors/                 # Doctor directory
├── mappings/                # Patient-doctor assignments
├── .env.example             # Template for environment configuration
└── requirements.txt
```

Each app follows the standard Django layout: `models.py`, `serializers.py`, `views.py`, `urls.py`, `admin.py`, `tests.py`, `migrations/`.

---

## Getting started

### 1. Prerequisites

- Python 3.10+
- PostgreSQL 12+ running locally

### 2. Install dependencies

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure the environment

```bash
# Windows
copy .env.example .env
# macOS / Linux
cp .env.example .env
```

Edit `.env` and set your PostgreSQL credentials:

```ini
POSTGRES_DB=healthcare
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_postgres_password
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
```

Create the database if it does not exist yet:

```bash
psql -U postgres -c "CREATE DATABASE healthcare;"
```

> `.env` is git-ignored. Never commit real credentials.

### 4. Apply migrations

```bash
python manage.py migrate
```

This creates the `users`, `doctors`, `patients` and `patient_doctor_mappings` tables along with Django's built-in auth tables.

### 5. Create an admin user (optional, for `/admin/`)

```bash
python manage.py createsuperuser
```

### 6. Run the server

```bash
python manage.py runserver
```

The API is now available at <http://127.0.0.1:8000/>. Visit the root for a machine-readable list of endpoints.

---

## Environment variables

All configuration is read through helpers in `config/settings.py` — no secrets are hard-coded.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | dev placeholder | Django secret key |
| `DJANGO_DEBUG` | `True` | Debug mode |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,testserver` | Comma-separated host allowlist |
| `DJANGO_TIME_ZONE` | `UTC` | Time zone |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_HOST` / `POSTGRES_PORT` | — | Database connection |
| `POSTGRES_CONN_MAX_AGE` | `60` | Persistent connection lifetime (seconds) |
| `JWT_SIGNING_KEY` | falls back to `DJANGO_SECRET_KEY` | JWT signing secret |
| `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` | `30` | Access token lifetime |
| `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | `7` | Refresh token lifetime |
| `JWT_ROTATE_REFRESH_TOKENS` | `True` | Issue a new refresh token on use |
| `JWT_UPDATE_LAST_LOGIN` | `True` | Update `last_login` on refresh |
| `AUTH_PASSWORD_MIN_LENGTH` | `8` | Minimum password length |
| `API_DEFAULT_PAGE_SIZE` | `20` | Default page size |
| `THROTTLE_AUTH_RATE` | `20/min` | Rate limit for register/login |
| `THROTTLE_ANON_RATE` | `30/min` | Rate limit for anonymous traffic |
| `CORS_ALLOWED_ORIGINS` | empty | Comma-separated allowed origins |
| `CORS_ALLOW_ALL_ORIGINS` | `False` | Allow any origin (dev only) |
| `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` | `not DEBUG` | Secure cookie flags |
| `SECURE_SSL_REDIRECT` | `False` | Force HTTPS |
| `SECURE_HSTS_SECONDS` | `0` | HSTS max-age |

---

## API reference

**Base URL:** `http://127.0.0.1:8000`
**Authentication:** `Authorization: Bearer <access_token>` on every endpoint except register, login and refresh.

### 1. Authentication

| Method | Endpoint | Auth | Description |
| --- | --- | --- | --- |
| `POST` | `/api/auth/register/` | No | Register a new user |
| `POST` | `/api/auth/login/` | No | Log in and receive JWT tokens |
| `POST` | `/api/auth/refresh/` | No | Exchange a refresh token for a new access token |
| `GET` | `/api/auth/me/` | Yes | Current user profile |
| `PATCH` | `/api/auth/change-password/` | Yes | Change the current user's password |

**Register** — `POST /api/auth/register/`

```json
{
  "name": "Dr Asha Mehta",
  "email": "asha@example.com",
  "password": "Str0ng-Pass!23",
  "password_confirm": "Str0ng-Pass!23"
}
```

`201 Created`

```json
{
  "success": true,
  "message": "Account created successfully.",
  "data": {
    "user": { "id": 1, "name": "Dr Asha Mehta", "email": "asha@example.com", "date_joined": "..." },
    "tokens": { "access": "<jwt>", "refresh": "<jwt>" }
  }
}
```

**Login** — `POST /api/auth/login/`

```json
{ "email": "asha@example.com", "password": "Str0ng-Pass!23" }
```

`200 OK` with the same `data.user` / `data.tokens` shape as register. Login is case-insensitive on email. An unknown email and a wrong password return the **same** error message so the API does not reveal which addresses are registered.

**Refresh** — `POST /api/auth/refresh/`

```json
{ "refresh": "<jwt>" }
```

`200 OK`

```json
{ "access": "<new jwt>", "refresh": "<new jwt>" }
```

**Change password** — `PATCH /api/auth/change-password/`

```json
{ "current_password": "Str0ng-Pass!23", "new_password": "N3w-Str0ng!45" }
```

### 2. Patients

| Method | Endpoint | Auth | Description |
| --- | --- | --- | --- |
| `POST` | `/api/patients/` | Yes | Add a new patient |
| `GET` | `/api/patients/` | Yes | List patients created by the request user |
| `GET` | `/api/patients/<id>/` | Yes | Retrieve a patient |
| `PUT` | `/api/patients/<id>/` | Yes | Full update |
| `PATCH` | `/api/patients/<id>/` | Yes | Partial update |
| `DELETE` | `/api/patients/<id>/` | Yes | Delete a patient |

**Create** — `POST /api/patients/`

```json
{
  "name": "Ravi Kumar",
  "email": "ravi.patient@example.com",
  "phone": "+919876543210",
  "date_of_birth": "1990-05-20",
  "gender": "male",
  "blood_group": "O+",
  "address": "12 MG Road",
  "medical_history": "Hypertension",
  "allergies": "Penicillin"
}
```

`201 Created`

```json
{
  "id": 1,
  "name": "Ravi Kumar",
  "email": "ravi.patient@example.com",
  "phone": "+919876543210",
  "date_of_birth": "1990-05-20",
  "gender": "male",
  "blood_group": "O+",
  "address": "12 MG Road",
  "medical_history": "Hypertension",
  "allergies": "Penicillin",
  "is_active": true,
  "age": 36,
  "created_by": 1,
  "doctors": [ { "id": 2, "name": "Dr Kavita Iyer", "specialization": "cardiology" } ],
  "created_at": "2026-10-09T12:00:00Z",
  "updated_at": "2026-10-09T12:00:00Z"
}
```

`age` is derived server-side from `date_of_birth`; `doctors` lists the currently assigned doctors.

**Field rules**

| Field | Rules |
| --- | --- |
| `name` | Required, minimum 2 characters |
| `email` | Optional, valid email, stored lowercased |
| `phone` | Required, 8–15 digits with an optional `+` prefix |
| `date_of_birth` | Required, cannot be in the future, after 1900, age ≤ 120 |
| `gender` | One of `male`, `female`, `other` |
| `blood_group` | One of `A+ A- B+ B- AB+ AB- O+ O- unknown` |

### 3. Doctors

| Method | Endpoint | Auth | Description |
| --- | --- | --- | --- |
| `POST` | `/api/doctors/` | Yes | Add a new doctor |
| `GET` | `/api/doctors/` | Yes | List doctors (shared directory) |
| `GET` | `/api/doctors/<id>/` | Yes | Retrieve a doctor |
| `PUT` | `/api/doctors/<id>/` | Yes | Full update |
| `PATCH` | `/api/doctors/<id>/` | Yes | Partial update |
| `DELETE` | `/api/doctors/<id>/` | Yes | Delete a doctor |

**Create** — `POST /api/doctors/`

```json
{
  "name": "Dr Kavita Iyer",
  "email": "kavita@example.com",
  "phone": "+919812345678",
  "specialization": "cardiology",
  "license_number": "MCI-1001",
  "experience_years": 12,
  "consultation_fee": "750.00",
  "qualification": "MD, DM Cardiology",
  "is_available": true
}
```

`201 Created`

```json
{
  "id": 1,
  "name": "Dr Kavita Iyer",
  "email": "kavita@example.com",
  "phone": "+919812345678",
  "specialization": "cardiology",
  "specialization_display": "Cardiology",
  "license_number": "MCI-1001",
  "experience_years": 12,
  "consultation_fee": "750.00",
  "qualification": "MD, DM Cardiology",
  "is_available": true,
  "patients_count": 0,
  "created_by": 1,
  "created_at": "2026-10-09T12:00:00Z",
  "updated_at": "2026-10-09T12:00:00Z"
}
```

**Field rules**

| Field | Rules |
| --- | --- |
| `email` | Required and **unique** |
| `license_number` | Required and **unique** |
| `specialization` | One of `general_medicine cardiology dermatology neurology pediatrics orthopedics gastroenterology psychiatry radiology surgery oncology` |
| `experience_years` | 0–70 |
| `consultation_fee` | Optional decimal ≥ 0 |

### 4. Patient-doctor mappings

| Method | Endpoint | Auth | Description |
| --- | --- | --- | --- |
| `POST` | `/api/mappings/` | Yes | Assign a doctor to a patient |
| `GET` | `/api/mappings/` | Yes | List assignments involving your records |
| `GET` | `/api/mappings/<patient_id>/` | Yes | All doctors assigned to a specific patient |
| `GET` | `/api/mappings/patient/<patient_id>/` | Yes | Alias of the above |
| `PATCH` / `PUT` | `/api/mappings/<id>/` | Yes | Update an assignment |
| `DELETE` | `/api/mappings/<id>/` | Yes | Remove an assignment |

> `GET /api/mappings/<id>/` uses the path segment as a **patient id** (as specified in the brief), while `DELETE /api/mappings/<id>/` uses it as a **mapping id**. Use the `mapping_id` returned in the doctors list when you need to remove an assignment.

**Create** — `POST /api/mappings/`

```json
{ "patient_id": 1, "doctor_id": 2, "notes": "Follow-up in two weeks" }
```

`patient` / `doctor` are accepted as aliases for `patient_id` / `doctor_id`.

`201 Created`

```json
{
  "success": true,
  "message": "Doctor assigned to patient successfully.",
  "data": {
    "id": 1,
    "patient": 1,
    "patient_id": 1,
    "patient_name": "Ravi Kumar",
    "doctor": 2,
    "doctor_id": 2,
    "doctor_name": "Dr Kavita Iyer",
    "doctor_specialization": "Cardiology",
    "notes": "Follow-up in two weeks",
    "is_active": true,
    "assigned_by": 1,
    "created_at": "2026-10-09T12:00:00Z",
    "updated_at": "2026-10-09T12:00:00Z"
  }
}
```

A doctor cannot be assigned to the same patient twice — enforced both in the serializer and by a database `UNIQUE (patient_id, doctor_id)` constraint.

**Doctors for a patient** — `GET /api/mappings/<patient_id>/`

```json
{
  "success": true,
  "data": {
    "patient_id": 1,
    "patient_name": "Ravi Kumar",
    "count": 1,
    "doctors": [
      {
        "mapping_id": 1,
        "id": 2,
        "name": "Dr Kavita Iyer",
        "specialization": "cardiology",
        "specialization_display": "Cardiology",
        "phone": "+919812345678",
        "email": "kavita@example.com",
        "experience_years": 12,
        "is_available": true
      }
    ]
  }
}
```

**Delete** — `DELETE /api/mappings/<id>/`

```json
{ "success": true, "message": "Dr. Kavita Iyer unassigned from Ravi Kumar." }
```

### 5. Utility endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/` | API discovery document listing every route |
| `GET` | `/admin/` | Django admin site |

---

## Response formats

**Paginated list**

```json
{
  "count": 42,
  "next": "http://127.0.0.1:8000/api/patients/?page=2",
  "previous": null,
  "results": [ { "id": 1, "...": "..." } ]
}
```

**Non-paginated object** — the resource fields at the top level.

**Action response** — wrapped with `success`, `message` and `data`.

---

## Error handling

A custom DRF exception handler (`common/exceptions.py`) guarantees one error shape for every failure:

```json
{
  "success": false,
  "error": {
    "code": "validation_error",
    "message": "Enter a valid phone number (8-15 digits, optional + prefix).",
    "details": {
      "phone": ["Enter a valid phone number (8-15 digits, optional + prefix)."]
    }
  }
}
```

| Status | `code` | When |
| --- | --- | --- |
| `400` | `validation_error` | Field or serializer validation failed |
| `401` | `not_authenticated` | Missing, expired or invalid access token |
| `403` | `permission_denied` | Authenticated but not allowed |
| `404` | `not_found` | Resource does not exist, or is not visible to you |
| `405` | `method_not_allowed` | HTTP method not supported on the route |
| `409` | `conflict` | Database integrity conflict (e.g. unique constraint) |
| `429` | `throttled` | Rate limit exceeded |

`details` is only present for validation errors.

---

## Filtering, search and pagination

### Patients

| Purpose | Query parameter | Example |
| --- | --- | --- |
| Filter | `gender`, `blood_group`, `is_active` | `?gender=female&blood_group=A+` |
| Search | `search` (name, email, phone) | `?search=ravi` |
| Order | `ordering` (`created_at`, `name`) | `?ordering=name` |

### Doctors

| Purpose | Query parameter | Example |
| --- | --- | --- |
| Filter | `specialization`, `is_available` | `?specialization=cardiology&is_available=true` |
| Search | `search` (name, email, phone, license number) | `?search=MCI-1001` |
| Order | `ordering` (`created_at`, `name`, `experience_years`, `consultation_fee`) | `?ordering=-consultation_fee` |

### All lists

```?page=2&page_size=50
```

`page_size` is capped at 100. Prefix `ordering` with `-` for descending order.

---

## Permissions model

| Resource | Read | Write |
| --- | --- | --- |
| Patients | Authenticated users see **only their own** patient records | Creator or staff |
| Doctors | Any authenticated user sees the **shared directory** | Creator or staff |
| Mappings | Authenticated users see assignments involving their patients, their doctors, or ones they created | Any participant in the assignment, or staff |

Additional rules:

- Every endpoint except `register`, `login` and `refresh` requires a valid access token.
- Deactivated accounts cannot authenticate.
- Patient records belonging to another user return `404` rather than `403`, so the API does not confirm that the record exists.
- Register and login are rate-limited via `ScopedRateThrottle`.

---

## Running tests

```bash
python manage.py test
```

The suite contains **80 tests** spread across the five apps and covers:

- registration, login, token refresh, password change, and user-enumeration resistance
- ownership enforcement on every CRUD operation for patients and doctors
- mapping creation, duplicate rejection, cross-user rejection and cascade behaviour
- the error envelope for `400`, `401` and `404` responses
- pagination, filtering and search

Run a single app or test:

```bash
python manage.py test patients
python manage.py test mappings.tests.MappingAPITests.test_delete_removes_assignment
```

Tests create a temporary `test_<POSTGRES_DB>` database and roll it back afterwards; your development data is never touched.

---

## Trying it with cURL

```bash
BASE=http://127.0.0.1:8000

# 1. Register (returns tokens)
curl -X POST $BASE/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Asha Mehta","email":"asha@example.com","password":"Str0ng-Pass!23","password_confirm":"Str0ng-Pass!23"}'

# 2. Log in
curl -X POST $BASE/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"asha@example.com","password":"Str0ng-Pass!23"}'

TOKEN=<paste access token>

# 3. Create a patient
curl -X POST $BASE/api/patients/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"Ravi Kumar","email":"ravi@example.com","phone":"+919876543210","date_of_birth":"1990-05-20","gender":"male","blood_group":"O+"}'

# 4. List patients
curl "$BASE/api/patients/?gender=male" -H "Authorization: Bearer $TOKEN"

# 5. Create a doctor
curl -X POST $BASE/api/doctors/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"Kavita Iyer","email":"kavita@example.com","phone":"+919812345678","specialization":"cardiology","license_number":"MCI-1001","experience_years":12}'

# 6. Assign the doctor to the patient
curl -X POST $BASE/api/mappings/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"patient_id":1,"doctor_id":1,"notes":"Follow-up in two weeks"}'

# 7. Doctors assigned to patient 1
curl "$BASE/api/mappings/1/" -H "Authorization: Bearer $TOKEN"

# 8. Current user
curl $BASE/api/auth/me/ -H "Authorization: Bearer $TOKEN"
```

---

## Postman setup

1. Import `Healthcare Backend.postman_collection.json` if present in the repository root, or create a collection manually.
2. Add a collection-level variable `baseUrl` = `http://127.0.0.1:8000` and `token` = empty.
3. **Register** — `POST {{baseUrl}}/api/auth/register/` with a JSON body as shown above.
4. In the **Tests** tab of the register/login request, capture the token:

   ```js
   pm.environment.set("token", pm.response.json().data.tokens.access);
   ```

5. For every other request, set the auth header to `{{token}}`.
6. To refresh an expired access token, call `POST {{baseUrl}}/api/auth/refresh/` with `{"refresh": "{{refreshToken}}"}` and update `token`.

---

## Design notes

**Custom user model.** `users.User` derives from `AbstractBaseUser` with email as `USERNAME_FIELD`. Passwords are hashed by Django's PBKDF2 hasher and are never returned by the API.

**Patient ownership.** Patient records are scoped to their creator in `get_queryset()`, which means the filtering happens in the database rather than in Python — no rows outside the caller's scope are ever loaded.

**Doctor directory.** Doctors are shared across users (any authenticated user may browse and assign them), but only the creator or a staff member may edit or delete a doctor.

**Assignment integrity.** Duplicate assignments are rejected by the serializer for a friendly message and blocked by a `UNIQUE` constraint as a hard guarantee. Deleting a patient or doctor cascades to their assignments.

**Query efficiency.** List endpoints use `select_related` for foreign keys and `prefetch_related` for mappings, so rendering a page of patients with their assigned doctors stays at a constant number of queries.

**Error contract.** A single exception handler normalises DRF's varied error payloads — including Django's `ValidationError` and `IntegrityError` — into one predictable envelope, so clients never have to branch on response shape.

**Security defaults.** Secrets come from the environment, `DEBUG` drives secure-cookie defaults, CORS is opt-in, login throttling limits credential stuffing, and 404-instead-of-403 responses avoid leaking the existence of other users' records.