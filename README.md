
# 🧠 AdVision AI  

**Turning Billboard Views into Business Data**

## 📖 Project Overview
**AdVision AI** is a B2B solution that helps businesses measure the real impact of **offline advertising**.  
It uses **AI-powered facial recognition** to anonymously track how many people view outdoor billboards and for how long — without storing personal data.  

When a viewer visits a partner store, their anonymized token is matched automatically, turning **ad attention into measurable conversions** displayed on a **real-time analytics dashboard**.

---

## ⚙️ System Architecture
<img width="953" height="504" alt="Screenshot 2025-11-09 at 10 55 27 AM" src="https://github.com/user-attachments/assets/0cbae619-17a1-4a55-b41a-7c30be19bc75" />


### **Flow**
1. **Application (CCTV Role)** – Captures real-time video via native camera and detects people using the **AI Person Detection Model**.  
2. **AI Model Workers** – Process video frames for **Face Detection** and generate anonymized tokens.  
3. **Backend (FastAPI + RabbitMQ + PostgreSQL)** –  
   - Handles data flow between model workers, dashboard, and application.  
   - Stores anonymized event logs securely.  
4. **Dashboard (Web)** – Displays **views, dwell time, and conversions** through visual graphs and CMS insights.

---

## 🌟 Key Features
- 🧍‍♂️ **AI Face & Person Detection** — Detects billboard viewers anonymously.  
- 🔒 **Privacy-First Design** — Converts faces into tokens, no personal data stored.  
- 🪄 **Real-Time Analytics** — Tracks view count, duration, and store conversion.  
- 📊 **Dashboard Visualization** — View insights with charts and metrics.  
- ⚡ **Scalable Architecture** — Distributed AI workers + message queue (RabbitMQ).

---

## 🎥 Demo
👉 **Demo Video:** [Watch on YouTube]([https://youtu.be/your-demo-link-here](https://youtu.be/eaS1667Yei4?si=jKcpfbwmPLnxmx4c))

---

## 🧩 Tech Stack
**Frontend (Dashboard)**: React.js, Tailwind CSS  
**Backend**: FastAPI, RabbitMQ, PostgreSQL  
**AI Models**: OpenCV, Dlib, DeepFace  
**Mobile App (CCTV Role)**: Flutter / Native Camera  
**Deployment**: Docker, AWS EC2  

---

## 🚀 Future Roadmap
1. 🤖 AI Chatbot Consulting — Automated marketing insights.  
2. 📷 Advanced Vision System — High-accuracy camera for large outdoor spaces.  
3. 🧾 B2B SaaS Platform — Subscription-based analytics dashboard.  
4. 🌍 Cross-Industry Integration — F&B, tourism, and event marketing.

---

## 👥 Team
- **Ali** – AI/Backend Engineer (Facial Recognition, Data Matching)  
- **Kumush** – Full Stack Developer / PM (Web Dashboard, CMS)  
- **Seo** – Business Research & Presentation  
- **Mark** – Mobile App Developer (Camera Integration)

---

© 2025 AdVision AI. All rights reserved.
