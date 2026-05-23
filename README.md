#  HelpNet

### Empowering Communities Through Technology

HelpNet is a modern full-stack community support and donation platform developed using **Flask, Socket.IO, and SQLite**. The platform is designed to bridge the gap between donors, NGOs, and individuals in need through a seamless, real-time, and interactive digital experience.

Built with a focus on accessibility, communication, and community engagement, HelpNet enables users to create requests, manage donations, communicate instantly, and track activities through dynamic dashboards.

---

# Key Features

##  Authentication System

* Secure user registration and login
* Role-based access for Donors and NGOs
* Session management using Flask

##  Real-Time Communication

* Live messaging system powered by Flask-SocketIO
* Instant notifications and updates
* Dynamic chat interface for user interaction

##  Donation Management

* Create and manage donations
* Request essential items from NGOs
* Track donation and fulfillment status

##  Interactive Dashboard

* Personalized dashboards for users
* Real-time activity tracking
* Request and donation analytics

##  File Upload Support

* Upload donation-related images
* Organized media handling using Flask uploads

##  Modern User Interface

* Responsive frontend design
* Glassmorphism-inspired UI
* Interactive cards and smooth user experience

---

# Tech Stack

## Backend

* Python
* Flask
* Flask-SocketIO
* SQLite

## Frontend

* HTML5
* CSS3
* Jinja2 Templates

## Deployment & Tools

* Git
* GitHub
* Render

---

#  Project Structure

```bash id="r5n3zx"
HelpNet/
│
├── app.py
├── requirements.txt
├── database.db
│
├── static/
│   ├── dashboard.css
│   ├── style.css
│   ├── uploads/
│   └── images/
│
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── login.html
│   ├── register.html
│   ├── donate.html
│   ├── create_request.html
│   ├── view_requests.html
│   ├── view_donations.html
│   └── chat_full.html
│
└── README.md
```

---

# 🚀 Installation Guide

## Clone Repository

```bash id="l1v9qp"
git clone https://github.com/db036703-eng/HelpNet.git
cd HelpNet
```

## Create Virtual Environment

```bash id="q3x7tm"
python -m venv venv
```

## Activate Environment

### Windows

```bash id="n8k2wr"
venv\Scripts\activate
```

### Linux / macOS

```bash id="u4m5zx"
source venv/bin/activate
```

## Install Dependencies

```bash id="j9p1vk"
pip install -r requirements.txt
```

## Run Application

```bash id="c2x8mn"
python app.py
```

---

#  Live Demo

🔗 https://helpnet-gwx3.onrender.com

---

# 📈 Future Enhancements

* AI-powered support recommendations
* Email verification system
* Secure password hashing
* Admin management dashboard
* Payment gateway integration
* Cloud database migration
* Mobile responsive enhancements
* Advanced analytics dashboard

---

#  Author

## Dharshini B

**B.E Computer Science Engineering (Cyber Security)**
First Year Student

🔗 GitHub: https://github.com/db036703-eng

---

#  License

This project is created for educational, learning, and portfolio purposes.
