# Cloud-Powered Citizen Grievance Redressal Analytics Using GCP

## 📌 Introduction

This project aims to design a **Citizen Grievance Redressal System** using **Google Cloud Platform (GCP)** that automates complaint submission, analysis, storage, and visualization. It allows citizens to report civic issues via a web interface, and leverages cloud services to streamline resolution.

> ✅ Designed to be easily understood—even by those without prior cloud knowledge.

---

## 🎯 Project Goal

Enable citizens to submit complaints using a web app:

- **Text**: Description of the issue
- **Image**: Visual proof (e.g., pothole, garbage)

Automate the processing:
- Extract issue type from text
- Identify problems from image
- Store data securely
- Visualize for authorities to act

---

## 🧠 GCP Services Used

| Service             | Purpose                                                                 |
|---------------------|-------------------------------------------------------------------------|
| **Cloud Storage**   | Store uploaded images and complaint text                                |
| **API Gateway**     | Secure entry point to GCP; receives complaints                          |
| **Cloud Functions** | Serverless functions to process and load complaints                     |
| **Natural Language API** | Extract issue type from complaint descriptions                   |
| **Roboflow API**    | Image classification (e.g., potholes, garbage, fallen trees)            |
| **BigQuery**        | Structured storage of complaints data                                   |
| **Looker Studio**   | Real-time dashboards for authorities                                    |

---

## 🔄 Workflow (Step-by-Step)

1. 🚀 User submits a complaint (text + image) via the React web app.
2. 🛡️ API Gateway securely forwards it to a **Cloud Function**.
3. ⚙️ Cloud Function:
   - Stores the data in **Cloud Storage**
   - Analyzes text using **Natural Language API**
   - Analyzes image using **Roboflow API**
4. 📦 A second **Cloud Function** watches for new files and:
   - Extracts relevant data
   - Pushes it to **BigQuery**
5. 📊 **Looker Studio** connects to BigQuery to create:
   - Live dashboards
   - Real-time performance reports

---

## 🌐 Why GCP?

- 🔧 Fully managed services
- 💵 Pay-as-you-go pricing
- 🤖 Powerful AI/ML APIs (NLP, Vision)
- 📈 Scalable for millions of users
- 🔗 Seamless integration between components
- 🌍 Fast global network

---

## 📋 Summary Table

| Step               | Service Used                         | Purpose                              |
|--------------------|--------------------------------------|--------------------------------------|
| Data Submission    | API Gateway + Cloud Functions        | Secure data intake                   |
| Storage            | Cloud Storage                        | Save images and text                 |
| Text Analysis      | Natural Language API                 | Detect issue category                |
| Image Analysis     | Roboflow API                         | Recognize visual issues              |
| Structured Storage | BigQuery                             | Organize complaint data              |
| Visualization      | Looker Studio                        | Live monitoring and reporting        |

---

## 🔐 Final Notes

This project is:
- ✅ **Automated** – minimal manual effort
- 🕐 **Real-Time** – instant data updates
- 📏 **Scalable** – handles growth efficiently
- 💸 **Cost-Effective** – optimized billing
- 🔒 **Secure** – privacy and safety assured

> This modern system replaces slow, manual paper-based processes and speeds up government responsiveness using smart cloud infrastructure.

---

## 🚧 Status

🟢 **In development** — actively being improved and refined.

## 📁 Project Folder

Ensure sensitive credentials like `.json` keys are **not pushed** to GitHub. Use `.gitignore` to exclude them and use `git filter-repo` to remove them from history if accidentally committed.

---

## 📬 Contact

For queries, contact **[Your Name]** at **[Your Email or GitHub Profile]**.
