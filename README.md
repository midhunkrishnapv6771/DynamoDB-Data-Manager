# Excel/CSV to DynamoDB Data Manager

A robust, full-stack Python web application that parses uploaded Excel or CSV files, stores the records in a non-relational AWS DynamoDB table, and retrieves/displays the records dynamically in a search-friendly web interface.

---

## 📐 System Architecture & Workflow

```text
             Browser (HTML)
                  │
      ┌───────────┴───────────┐
      │                       │
 Upload Excel            Retrieve Button
      │                       │
      ▼                       ▼
         Flask (Python Backend)
                  │
      ┌───────────┴───────────┐
      │                       │
   Pandas                boto3
(Read Excel)        (AWS SDK for Python)
      │                       │
      └───────────┬───────────┘
                  ▼
            AWS DynamoDB
```

### 🔁 Data Flow Sequence:
1. **User Action:** The user selects a CSV or Excel file on the web interface and clicks **Upload**.
2. **File Processing (Pandas):** The Flask backend receives the file. Pandas parses the rows and maps columns dynamically.
3. **Database Insertion (boto3):** Using the AWS SDK, the backend connects to DynamoDB and auto-creates the table if it doesn't already exist. The records are written efficiently in batches.
4. **Data Retrieval:** When the user clicks **Retrieve from AWS**, Flask runs a scan query on the DynamoDB table.
5. **Interactive UI Display:** The retrieved data is returned to the frontend and rendered in an interactive, searchable data table with modern dark aesthetics.

---

## 🛠️ Features Included
- **AWS DynamoDB Integration:** Auto-provisioning table configuration with a dynamic primary key per uploaded dataset.
- **Robust Parsing (Pandas):** Support for both `.csv` and `.xlsx` files with dynamic column mapping.
- **Smart Data Conversion:** Sanitizes empty fields and converts numeric decimals automatically to meet strict DynamoDB schemas.
- **Interactive UI:** Smooth drag-and-drop file upload, instant client-side search, status spinners, and styled rating/tier badges.
- **Secure Credentials:** Keeps AWS credentials secret using an external environment (`.env`) loader.

---

## 🚀 How to Run Locally

### 1. Configure Credentials
Copy `.env.example` to a new file named `.env` and fill in your AWS IAM access keys:
```ini
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_access_key_here
AWS_REGION=ap-south-1
```

### 2. Set Up Virtual Environment & Install Dependencies
```bash
# Create venv
python -m venv venv

# Activate venv (Windows)
.\venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 3. Run the Application
```bash
python app.py
```
Open **`http://127.0.0.1:5000`** in your browser.
