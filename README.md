# Roskilde-Projekt

## About This Repository

This repository was created by **Andreas Bagge** ([s214630@dtu.dk](mailto:s214630@dtu.dk)) and **Christian Bjerregaard** ([s224389@dtu.dk](mailto:s224389@dtu.dk)) as part of a project for Roskilde Festival.

Our project focuses on **crowd counting** at the festival, aiming to provide valuable insights into attendee movement and density.

---

> **Ownership:**
> This work is the intellectual property of Andreas Bagge and Christian Bjerregaard.

---

## Getting Started

### Prerequisites
- **Python 3.11.9** (recommended)
- [pip](https://pip.pypa.io/en/stable/)

### 1. Create a Virtual Environment

**Windows:**
```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

**Linux/macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Additional Notes
- Make sure you have access to the required Google Sheets credentials (`excel_key.json`).
- To run the dashboard, use:
  ```bash
  streamlit run website.py
  ```
---