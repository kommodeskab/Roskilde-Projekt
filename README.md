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

## How to set up Raspberry Pi
Install dependecies:
```bash
sudo apt update
sudo apt install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev git
```

Install PyEnv:
```bash
curl https://pyenv.run | bash
```

Make sure following dependency is installed:
```bash
sudo apt-get install libffi-dev
```

Open `bashrc` and add some important stuff:
```bash
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"
```
Save by pressing `Ctrl+0` and then `Enter`. Exit by pressing `Ctrl+X`.

Install and activate a (newer) version of Python, preferably `3.11`.
```bash
pyenv install 3.11
pyenv global 3.11
pyenv --version
```
This should print `3.11.9` as the currently installed python version. 

Clone this repository and step into the project:
```bash
git clone https://github.com/kommodeskab/Roskilde-Projekt.git
cd Roskilde-Projekt
```

Make a new virtual environment and install the dependecies:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Setting up git
Make sure `git` is installed:
```bash
sudo apt install git
```
Generate a new ssh-key on the raspberry:
```
ssh-keygen -t ed25519 -C "your_email@example.com"
```
Add your SSH key to the ssh-agent 
```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```
Here, you can see the ssh-key:
```bash
cat ~/.ssh/id_ed25519.pub
```
Ideally, copy this file to your laptop using the below code (see under 'Communicating with Raspberry Pi).
```bash
scp <device name>@<device ip address>:~/.ssh/id_ed25519 .
```

### Communicating with Raspberry Pi
To copy files from the Raspberry Pi to your laptop, write:
```bash
scp <device name>@<device ip address>:<path to file>
```
Where device name is the name of the Raspberry and device ip is the ip of the Raspberry.
