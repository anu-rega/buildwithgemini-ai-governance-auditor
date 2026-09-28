"""Seed script for initializing the Firestore `agents_estate` collection.

Hardcoded Project ID: qwiklabs-gcp-03-aee88193e5fb
"""

from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-03-aee88193e5fb"
COLLECTION_NAME = "agents_estate"

SEED_DATA = [
    {
        "agent_id": "agent-001",
        "display_name": "Price Match Concierge",
        "owner_team": "Retail Engineering",
        "service_account": "pma-sa@qwiklabs-gcp-03-aee88193e5fb.iam.gserviceaccount.com",
        "status": "REGISTERED",
        "risk_level": "LOW",
        "permissions": ["roles/aiplatform.user", "roles/storage.objectViewer"],
        "data_classification": "Internal",
        "last_audit": "2026-09-27",
    },
    {
        "agent_id": "agent-002",
        "display_name": "Shadow Customer Copilot",
        "owner_team": "Marketing Shadow IT",
        "service_account": "novasmart-customer-sa@qwiklabs-gcp-03-aee88193e5fb.iam.gserviceaccount.com",
        "status": "UNSANCTIONED",
        "risk_level": "CRITICAL",
        "permissions": ["roles/owner", "roles/bigquery.admin", "roles/storage.admin"],
        "data_classification": "PII_Confidential",
        "last_audit": "2026-09-28",
    },
    {
        "agent_id": "agent-003",
        "display_name": "Financial Reporting Bot",
        "owner_team": "Finance Ops",
        "service_account": "finops-sa@qwiklabs-gcp-03-aee88193e5fb.iam.gserviceaccount.com",
        "status": "REVIEW_REQUIRED",
        "risk_level": "HIGH",
        "permissions": ["roles/bigquery.admin", "roles/secretmanager.admin"],
        "data_classification": "Restricted_Financial",
        "last_audit": "2026-09-25",
    },
]


def seed_firestore():
    print(f"Connecting to Firestore for project: {PROJECT_ID}")
    db = firestore.Client(project=PROJECT_ID)
    collection_ref = db.collection(COLLECTION_NAME)

    for item in SEED_DATA:
        doc_ref = collection_ref.document(item["agent_id"])
        doc_ref.set(item)
        print(f"Seeded document '{item['agent_id']}' -> {item['display_name']} ({item['status']})")

    print(f"✅ Successfully seeded {len(SEED_DATA)} items into '{COLLECTION_NAME}'.")


if __name__ == "__main__":
    seed_firestore()
