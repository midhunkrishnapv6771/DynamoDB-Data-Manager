import os
import boto3
import pandas as pd
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from decimal import Decimal
import json

load_dotenv()

app = Flask(__name__)

# ── d1/d2/d3 Column Mapping (as required by recruiter) ────────────────────────
# d1 = Business Name (Partition Key), d2 = Phone, d3 = Rating
D1_COL = "BusinessName"   # d1 — primary identifier
D2_COL = "Phone"          # d2 — contact
D3_COL = "Rating"         # d3 — numeric value field

# ── AWS DynamoDB setup ─────────────────────────────────────────────────────────
AWS_REGION       = os.getenv("AWS_REGION", "ap-south-1")
ACCESS_KEY       = os.getenv("AWS_ACCESS_KEY_ID")
SECRET_KEY       = os.getenv("AWS_SECRET_ACCESS_KEY")
TABLE_NAME       = "intership"          # table name exactly as given in task

dynamodb = boto3.resource(
    "dynamodb",
    region_name=AWS_REGION,
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
)

# ── Helper: create table if it doesn't exist ───────────────────────────────────
def get_or_create_table():
    """Create the 'intership' DynamoDB table with BusinessName as PK."""
    client = boto3.client(
        "dynamodb",
        region_name=AWS_REGION,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
    )
    existing = [t for t in client.list_tables()["TableNames"] if t == TABLE_NAME]
    if existing:
        return dynamodb.Table(TABLE_NAME)

    table = dynamodb.create_table(
        TableName=TABLE_NAME,
        KeySchema=[
            {"AttributeName": "BusinessName", "KeyType": "HASH"},  # Partition key
        ],
        AttributeDefinitions=[
            {"AttributeName": "BusinessName", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",   # On-demand (no provisioned capacity needed)
    )
    table.wait_until_exists()
    return table


# ── Helper: sanitise values for DynamoDB (no empty strings, Decimal for floats)─
def sanitise(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    if isinstance(val, float):
        return Decimal(str(val))
    return str(val).strip() or "N/A"


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    """Accept a CSV/Excel file, parse it with pandas, insert rows into DynamoDB."""
    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file part in request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "message": "No file selected"}), 400

    filename = file.filename.lower()
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(file)
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file)
        else:
            return jsonify({"success": False, "message": "Unsupported file type. Use CSV or Excel."}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to read file: {str(e)}"}), 500

    # Clean column headers
    df.columns = [str(col).strip() for col in df.columns]

    # Find the primary key column (d1)
    # If the recruiter's sheet literally has a column named "d1" or "BusinessName", use it.
    # Otherwise, map the very first column as d1.
    cols = list(df.columns)
    
    # We will standardise the key columns to d1, d2, d3
    # so that the DB entries always have consistent fields for the UI
    d1_source = next((c for c in cols if c.lower() == 'd1' or c.lower() == 'businessname'), cols[0])
    d2_source = next((c for c in cols if c.lower() == 'd2' or c.lower() == 'phone'), cols[1] if len(cols) > 1 else None)
    d3_source = next((c for c in cols if c.lower() == 'd3' or c.lower() == 'rating'), cols[2] if len(cols) > 2 else None)

    # Rename them in the dataframe so they map to DynamoDB partition keys consistently
    rename_map = {d1_source: "BusinessName"}  # BusinessName is the PK in our table schema
    df.rename(columns=rename_map, inplace=True)

    # Create explicit aliases for d1, d2, d3
    df["d1"] = df["BusinessName"]
    if d2_source:
        df["d2"] = df[d2_source]
    else:
        df["d2"] = "N/A"

    if d3_source:
        df["d3"] = df[d3_source]
    else:
        df["d3"] = "N/A"

    # Make column names DynamoDB-friendly (no spaces or special chars)
    df.columns = [
        str(col).replace(" ", "").replace("/", "").replace("(", "").replace(")", "")
        for col in df.columns
    ]

    pk_col = "BusinessName"
    table = get_or_create_table()

    inserted = 0
    failed   = 0
    errors   = []

    with table.batch_writer() as batch:
        for _, row in df.iterrows():
            item = {col: sanitise(row[col]) for col in df.columns}
            # Skip rows where PK is empty / N/A
            if not item.get(pk_col) or item[pk_col] == "N/A":
                failed += 1
                continue
            try:
                batch.put_item(Item=item)
                inserted += 1
            except Exception as e:
                failed += 1
                errors.append(str(e))

    return jsonify({
        "success": True,
        "message": f"Upload complete: {inserted} rows inserted, {failed} skipped/failed.",
        "inserted": inserted,
        "failed": failed,
        "errors": errors[:5],
    })


@app.route("/retrieve", methods=["GET"])
def retrieve():
    """Scan all items from DynamoDB 'intership' table and return as JSON."""
    try:
        table = get_or_create_table()
        response = table.scan()
        items = response.get("Items", [])

        # Handle DynamoDB pagination (scan returns max 1 MB per call)
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))

        # Convert Decimal → float for JSON serialisation
        def decimal_fix(obj):
            if isinstance(obj, list):
                return [decimal_fix(i) for i in obj]
            if isinstance(obj, dict):
                return {k: decimal_fix(v) for k, v in obj.items()}
            if isinstance(obj, Decimal):
                return float(obj)
            return obj

        items = decimal_fix(items)
        return jsonify({"success": True, "count": len(items), "data": items})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
