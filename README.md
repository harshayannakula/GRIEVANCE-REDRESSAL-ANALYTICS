Introduction
This project aims to design a Citizen Grievance Redressal System on Google Cloud
Platform (GCP) to automate the process of submitting, analyzing, storing, and visualizing
citizen complaints.
Even someone with zero cloud knowledge can understand this document because it explains
each service, why it was chosen, and how they work together.
What is the Goal?
Allow citizens to submit complaints (text + image) through a web app.
• Text: Complaint description.
• Image: Photo evidence (pothole, garbage, broken sign, etc.)
Automatically process the complaints:
• Analyze text to extract issue type.
• Analyze images to classify problems.
• Store everything securely.
• Visualize the data for authorities to take action.
GCP Services Used and Their Role
1. Cloud Storage
• What it is: A storage space on the cloud, like Google Drive but for programs.
• How we use it: Store the uploaded images, complaint texts, and processed data.
2. API Gateway
• What it is: A managed entrance where we safely send data into GCP.
• How we use it: Receives complaint data from the web app and sends it to a Cloud
Function securely.
3. Cloud Functions
• What it is: Small pieces of code that run only when needed.
• How we use it: Processes incoming complaint data:
o Saves text and image into Cloud Storage.
o Sends text to analysis.
o Sends images to analysis.
There are two important Cloud Functions:
• Function 1 (Submission Processing): Handles incoming complaint and saves it.
• Function 2 (Storage to BigQuery Loader): Watches for new files, parses the data,
and pushes it into a database.
4. Natural Language API
• What it is: A tool that reads and understands human language.
• How we use it: Reads complaint description and detects "issue type" (e.g., "garbage",
"pothole").
5. Roboflow API
• What it is: A third-party tool to classify images.
• How we use it: Analyzes submitted images to recognize potholes, garbage dumps,
collapsed trees, etc.
6. BigQuery
• What it is: A large, powerful database designed for big data and fast analysis.
• How we use it: Store all complaints in a structured way:
o Complaint ID
o User ID
o Issue Type
o Location
o Status
o Timestamp
o Department assigned
7. Looker Studio
• What it is: A tool for making reports and dashboards.
• How we use it: Create live dashboards showing:
o How many complaints submitted
o What kind of issues are common
o Which departments have the most pending work
Complete Process Flow (Step-by-Step)
1. User submits complaint (text + image) via a web application (React frontend hosted
locally or on cloud).
2. API Gateway securely passes the complaint to a Cloud Function.
3. Cloud Function:
o Saves the text and image into Cloud Storage.
o Sends the text to Natural Language API to detect issue type.
o Sends the image to Roboflow API to identify visual issues.
4. Storage to BigQuery Cloud Function:
o Detects new data stored.
o Parses metadata, extracted results.
o Pushes structured complaint details into BigQuery.
5. Looker Studio connects to BigQuery:
o Creates live dashboards and reports.
o City officials can see real-time insights and track resolution progress.
Why Google Cloud Platform (GCP)?
• Managed services: No need to manage servers manually.
• Pay-as-you-go: Only pay when you use.
• Powerful AI services: Ready-to-use NLP API, serverless functions.
• Scalability: Can handle 10 users or 10 million users without redesign.
• Simple Integration: All services easily talk to each other.
• Global Network: Fast and reliable delivery anywhere in the world.
Summary Table
Step Service Used Purpose
Data submission API Gateway + Cloud
Safely receive and handle
Function
complaints
Storage Cloud Storage Store complaint text and images
Text Analysis Natural Language API Extract key information from
complaint
Image Analysis Roboflow API Detect visual issues
Structured Storage BigQuery Organize complaints into database
Visualization &
Reporting Looker Studio Live dashboards for monitoring
Final Notes
This project is:
• Automated: Minimal manual work.
• Real-Time: Data flows continuously.
• Scalable: Designed to grow easily.
• Cost-efficient: No over-provisioning.
• Secure: Data remains private and safe.
This approach solves the real-world problem of slow, paper-based grievance systems and
speeds up responses dramatically using smart cloud services.







