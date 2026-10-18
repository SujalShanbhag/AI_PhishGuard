# VERITAS AI — REST API Documentation

Base URL: `http://localhost:8000`  
Interactive OpenAPI UI: `http://localhost:8000/docs`

---

## 1. Authentication Endpoints

### `POST /api/auth/register`
Creates a new forensic analyst account.
- **Request Body (JSON):**
  - `email` (string, required)
  - `password` (string, min 8 chars, required)
  - `full_name` (string, optional)
- **Response:** `200 OK` with access token and user metadata.

### `POST /api/auth/login`
Authenticates user and returns JWT bearer token and sets session cookie.
- **Request Body (JSON):** `email`, `password`
- **Response:** `200 OK` with access token.

### `GET /api/auth/me`
Retrieves authenticated user profile. Requires Bearer Token.

### `PUT /api/auth/retention`
Updates data retention duration in days (7, 30, 90).

### `DELETE /api/auth/me`
Permanently purges user account and all associated forensic data.

---

## 2. Health & Capabilities

### `GET /api/health`
System liveness check.

### `GET /api/capabilities`
Returns state of loaded models, PyTorch device (CUDA/CPU), face detection backend, and core disclaimers.

---

## 3. Media Analysis Endpoints

### `POST /api/analysis/image`
Multipart form upload of an image file (JPG, PNG, WEBP).
- **Form Data:** `file`
- **Response:** Immediate analysis result including assessment, scores, face detection, and Grad-CAM link.

### `POST /api/analysis/video`
Multipart form upload of video file (MP4, MOV, AVI).
- **Form Data:** `file`
- **Response:** `status: "PROCESSING"` with background tracking ID.

### `GET /api/analysis/{analysis_id}`
Retrieves analysis metadata, progress, and current state.

### `GET /api/analysis/{analysis_id}/frames`
Retrieves sampled video frame results.

### `GET /api/analysis/{analysis_id}/evidence/{evidence_type}`
Securely serves face crop (`face`), Grad-CAM heatmap (`gradcam`), or sampled frame (`frame_X_face`).

### `GET /api/analysis/history`
Lists user's previous analyses with optional query filters (`media_type`, `assessment`).

---

## 4. Identity Likeness Protection

### `POST /api/identity/profile`
Registers consented reference photo.
- **Form Data:** `file` (image), `consent` (boolean=true), `full_name` (optional).

### `GET /api/identity/profile`
Checks status of user's active reference profile.

### `DELETE /api/identity/profile`
Purges reference photo and facial embedding vector.

### `POST /api/identity/compare`
Compares reference profile against target analysis.
- **Request Body (JSON):** `analysis_id`, `threshold` (float 0.5–0.95).

---

## 5. Forensic Reports

### `POST /api/reports/{analysis_id}/generate`
Compiles downloadable forensic PDF report.

### `GET /api/reports/{report_id}/download`
Downloads formal PDF case report.

### `GET /api/reports/{report_id}?format=json`
Exports machine-readable forensic JSON telemetry.
