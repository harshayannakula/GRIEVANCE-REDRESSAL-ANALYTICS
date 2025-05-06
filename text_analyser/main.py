import spacy
import spacy.cli
import re
import json
from spacy.matcher import PhraseMatcher
from google.cloud import storage

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

# Constants
BUCKET_NAME = "dataingestion_master"

# Keywords
ISSUE_KEYWORDS = [
    "pothole", "street light", "water leakage", "garbage", "sewage", "electric pole",
    "road damage", "power cut", "blocked drain", "tree fallen"
]
URGENCY_KEYWORDS = ["urgent", "immediately", "asap", "emergency", "it's been", "not working", "dangerous"]
DATE_PATTERNS = [
    r"since (last )?\w+", r"\b\w+day\b", r"\b\d{1,2}(st|nd|rd|th)?\s+\w+\b", r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"
]

def extract_features(text):
    doc = nlp(text)

    # Matcher setup
    issue_matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    urgency_matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    issue_matcher.add("ISSUE", [nlp(issue) for issue in ISSUE_KEYWORDS])
    urgency_matcher.add("URGENCY", [nlp(word) for word in URGENCY_KEYWORDS])

    matched_issues = list(set([doc[start:end].text.lower() for _, start, end in issue_matcher(doc)]))
    matched_urgency = list(set([doc[start:end].text.lower() for _, start, end in urgency_matcher(doc)]))

    locations = list(set([ent.text for ent in doc.ents if ent.label_ in ("GPE", "LOC", "FAC")]))
    near_locations = re.findall(r'near\s+([A-Z][\w\s]+)', text, re.IGNORECASE)
    locations.extend(near_locations)
    locations = list(set(locations))

    matched_dates = []
    for pattern in DATE_PATTERNS:
        matched_dates.extend(re.findall(pattern, text, re.IGNORECASE))
    matched_dates = list(set(matched_dates))

    people = list(set([ent.text for ent in doc.ents if ent.label_ == "PERSON"]))

    return {
        "Location": locations,
        "Issue Type": matched_issues,
        "Urgency": matched_urgency,
        "Date": matched_dates,
        "Person": people
    }

def analyze_text(event, context):
    file_name = event['name']  # e.g., testcase1/complaint.txt
    print(f"📄 Processing file: {file_name}")

    if not file_name.endswith("complaint.txt"):
        print("⛔ Not a complaint.txt file, skipping.")
        return

    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(file_name)

    if not blob.exists():
        print(f"⚠️ Blob {file_name} not found.")
        return

    # Read complaint
    text = blob.download_as_text()

    # Extract features
    extracted = extract_features(text)

    # Generate output path in the *same folder* as the complaint.txt
    base_path = "/".join(file_name.split("/")[:-1])
    output_path = f"{base_path}/complaint_extract.json"

    # Save output
    output_blob = bucket.blob(output_path)
    output_blob.upload_from_string(
        data=json.dumps(extracted, indent=2),
        content_type="application/json"
    )

    print(f"✅ Extracted features saved to: {output_path}")
