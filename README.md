# Stock Price Alert System Using Google Cloud Pub/Sub.

![System Architecture]()  
*Real-time stock price monitoring and alert system*

## 📌 Overview
A real-time stock price monitoring system that leverages Google Cloud Pub/Sub for scalable, decoupled event processing to trigger reliable email alerts when user-defined thresholds are crossed.

## ✨ Key Features
- **Real-time price monitoring** from multiple data sources
- **Dynamic threshold-based alerts** (email/SMS/webhook)
- **Event-driven architecture** with Google Cloud Pub/Sub
- **User-specific watchlists** with custom alert rules
- **Historical trend analysis** with basic visualizations

## 🛠️ Technology Stack
![Google Cloud Pub/Sub](https://img.shields.io/badge/Google_Cloud_Pub/Sub-4285F4?style=for-the-badge&logo=google-cloud&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-07405E?style=for-the-badge&logo=sqlite&logoColor=white)

## 🧠 Architectural Decision: Why Pub/Sub?

### Key Benefits of Pub/Sub in This Project:
1. **Real-time Processing**:
   - Handles high-frequency stock tick updates (100+ ms latency)
   - Automatic scaling during market volatility spikes

2. **Decoupled Architecture**:
   - Data collectors → Pub/Sub → Alert processors → Notification services
   - Each component can scale independently

3. **Managed Service Advantages**:
   - No server maintenance (vs self-hosted Kafka)
   - Built-in redundancy and 99.95% SLA
   - Seamless integration with other GCP services (Cloud Functions, BigQuery)

4. **Cost Efficiency**:
   - Pay-per-use model ideal for variable market hours
   - No upfront cluster provisioning costs

### Comparison with Apache Kafka:

| Feature               | Google Pub/Sub          | Apache Kafka             |
|-----------------------|-------------------------|--------------------------|
| **Deployment**        | Fully managed           | Self-hosted/VMs         |
| **Scalability**       | Automatic scaling       | Manual partition management |
| **Latency**           | ~100-500ms              | ~10-50ms (on-prem)       |
| **Throughput**        | ~1M msgs/sec per topic  | ~1M msgs/sec per cluster |
| **Pricing**          | $0.40 per million msgs  | Infrastructure costs     |
| **Best For**         | Cloud-native, event-driven apps | High-throughput, on-prem systems |

### When Kafka Might Be Better:
- If you need **exactly-once delivery** guarantees
- For **extremely low latency** requirements (<50ms)
- When you already have **Kafka expertise** in your team

## 📦 Installation
```bash
git clone https://github.com/gauthamkuckian/stock-price-alert-system.git
cd stock-price-alert-system

# Install dependencies
pip install -r requirements.txt

# Set up GCP credentials
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"

# Run the application
python app.py
