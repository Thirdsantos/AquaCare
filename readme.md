# AquaCare: Smart Aquarium Monitoring System

AquaCare is a smart aquarium monitoring system that tracks and manages key environmental parameters — including **pH**, **temperature**, and **turbidity** — to ensure a healthy aquatic environment.

The system features a **Flask-based backend** that receives sensor data from ESP32, stores logs in **Firebase Realtime Database**, sends alerts through **Firebase Cloud Messaging (FCM)**, and includes AI chatbot support to answer user queries. It also calculates **hourly and daily analytics** to help users monitor trends over time.

---

## 🚀 Features

- 📡 **Sensor Data Handling**  
  Accepts real-time data from aquarium sensors via API endpoints.

- ⚠️ **Threshold Monitoring & Alerts**  
  Automatically checks if sensor values exceed critical levels and sends FCM push notifications.

- 📊 **Hourly and Daily Analytics**  
  Calculates and stores aggregated data (pH, temperature, turbidity) per hour and per day.

- 🤖 **AI Chatbot**  
  Users can interact with an AI chatbot to ask questions about current or historical aquarium status.

- 🔄 **Firebase Realtime Database Integration**  
  Stores sensor logs and analytics with real-time data retrieval support.

---

## 🛠️ Technologies Used

- **Python** – Backend language  
- **Flask** – REST API framework  
- **Firebase Realtime Database** – Cloud-based JSON database  
- **Firebase Cloud Messaging (FCM)** – Real-time push notification system  

---


