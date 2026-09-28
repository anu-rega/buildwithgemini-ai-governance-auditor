# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import datetime
import json
import os
import urllib.parse
import urllib.request
import uuid
from zoneinfo import ZoneInfo

import vertexai
from dotenv import load_dotenv
from google import genai
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.memory.memory_entry import MemoryEntry
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.cloud import firestore, storage
from google.genai import types
from vertexai.preview import reasoning_engines

load_dotenv()

PROJECT_ID = "qwiklabs-gcp-03-aee88193e5fb"
COLLECTION_NAME = "agents_estate"
BUCKET_NAME = "ai-governance-auditor-media-qwiklabs-gcp-03-aee88193e5fb"


async def generate_governance_badge_image(
    prompt: str,
    tool_context: ToolContext = None,
) -> str:
    """Generates a visual governance badge or security seal for an agent using gemini-3.1-flash-lite-image model in global location.

    Saves the image as a Playground UI artifact and uploads the image bytes directly to public Cloud Storage, returning the public HTTPS URL.

    Args:
        prompt: Description of the governance badge to generate (e.g. 'A futuristic AI governance badge showing security audit score A+').

    Returns:
        The public HTTPS GCS URL of the generated image (https://storage.googleapis.com/<bucket>/<object>).
    """
    try:
        client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
        response = await client.aio.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
        )

        if not response.candidates or not response.candidates[0].content.parts:
            return "Failed to generate image: No content returned from model."

        part = response.candidates[0].content.parts[0]
        if not hasattr(part, "inline_data") or not part.inline_data:
            return "Failed to generate image: Returned part does not contain image bytes."

        image_bytes = part.inline_data.data
        mime_type = getattr(part.inline_data, "mime_type", "image/png") or "image/png"

        filename = f"governance_badge_{uuid.uuid4().hex[:8]}.png"

        # (1) Save artifact for Playground UI panel
        if tool_context is not None:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # (2) Upload image bytes directly to public GCS bucket
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
        return public_url
    except Exception as e:
        return f"Error generating or uploading governance image: {e}"


async def generate_governance_video(
    prompt: str,
    tool_context: ToolContext = None,
) -> str:
    """Generates a short governance or security audit video for an item in NovaSmart's agent domain using Google's Omni model (gemini-omni-flash-preview) in global location.

    Saves the video as a Playground UI artifact and uploads the video bytes directly to public Cloud Storage, returning the public HTTPS URL.

    Args:
        prompt: Description of the governance video to generate (e.g. 'A short video animation showing AI security audit scanner scanning agent estate').

    Returns:
        The public HTTPS GCS URL of the generated video (https://storage.googleapis.com/<bucket>/<object>).
    """
    try:
        client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
        response = await client.aio.interactions.create(
            model="gemini-omni-flash-preview",
            input=prompt,
        )

        out_video = getattr(response, "output_video", None)
        if not out_video:
            return "Failed to generate video: No output_video returned from Omni model interaction."

        raw_data = getattr(out_video, "data", None)
        if raw_data is None and hasattr(out_video, "model_dump"):
            raw_data = out_video.model_dump().get("data")

        if not raw_data:
            return "Failed to generate video: Video data is empty or missing."

        if isinstance(raw_data, str):
            video_bytes = base64.b64decode(raw_data)
        elif isinstance(raw_data, bytes):
            video_bytes = raw_data
        else:
            return "Failed to generate video: Video data format is invalid."

        mime_type = getattr(out_video, "mime_type", "video/mp4") or "video/mp4"
        ext = ".mp4" if "mp4" in mime_type else ".webm"
        filename = f"governance_video_{uuid.uuid4().hex[:8]}{ext}"

        # (1) Save artifact so it shows up in Playground's Artifacts panel
        if tool_context is not None:
            artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
            await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # (2) Upload video bytes directly to public GCS bucket
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
        return public_url
    except Exception as e:
        return f"Error generating or uploading governance video: {e}"


async def save_memory(
    memory_text: str,
    tool_context: ToolContext = None,
) -> str:
    """Saves a fact, user preference, health restriction, or allergy directly into the persistent Memory Bank.

    Args:
        memory_text: Statement, preference, or allergy to store in Memory Bank e.g. 'User is severely allergic to peanuts and shellfish.'

    Returns:
        Confirmation message that the memory entry was stored.
    """
    if tool_context is None:
        return "Memory service context is unavailable."
    try:
        cnt = types.Content(
            parts=[types.Part.from_text(text=memory_text.strip())],
            role="user",
        )
        await tool_context.add_memory(memories=[MemoryEntry(content=cnt)])
        return f"Successfully saved memory to Memory Bank: '{memory_text}'"
    except Exception as e:
        return f"Failed to save memory to Memory Bank: {e}"


def get_maps_api_key() -> str:
    load_dotenv()
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_MAPS_API_KEY environment variable is not set in .env")
    return api_key


def geocode_address(address: str) -> str:
    """Converts a street address or location name into geographic coordinates (latitude and longitude) using Google Maps Geocoding API.

    Args:
        address: Street address or city name e.g. '1600 Amphitheatre Pkwy, Mountain View, CA' or 'San Francisco, CA'.

    Returns:
        Formatted address, latitude, and longitude.
    """
    try:
        key = get_maps_api_key()
        query = urllib.parse.quote_plus(address.strip())
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={query}&key={key}"

        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") != "OK" or not data.get("results"):
                return f"Geocoding failed for address '{address}': {data.get('status')}"

            res = data["results"][0]
            fmt_address = res.get("formatted_address")
            location = res["geometry"]["location"]
            return str({
                "formatted_address": fmt_address,
                "latitude": location["lat"],
                "longitude": location["lng"],
            })
    except Exception as e:
        return f"Error executing Geocoding API: {e}"


def search_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "restaurant",
    radius_meters: float = 1000.0,
) -> str:
    """Finds nearby places of a given type around a latitude/longitude coordinate using Google Places API (New).

    Args:
        latitude: Latitude coordinate e.g. 37.7749.
        longitude: Longitude coordinate e.g. -122.4194.
        place_type: Type of place to search for e.g. 'restaurant', 'cafe', 'bank', 'store', 'hospital'.
        radius_meters: Search radius in meters (default 1000.0).

    Returns:
        List of nearby places with key fields (name, address, location).
    """
    try:
        key = get_maps_api_key()
        url = "https://places.googleapis.com/v1/places:searchNearby"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
        }
        body = {
            "includedTypes": [place_type.strip().lower()],
            "maxResultCount": 5,
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": latitude, "longitude": longitude},
                    "radius": float(radius_meters),
                }
            },
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
        )

        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            places = data.get("places", [])
            if not places:
                return f"No nearby places of type '{place_type}' found around ({latitude}, {longitude})."

            results = []
            for p in places:
                display_name = p.get("displayName", {}).get("text", "Unknown")
                fmt_address = p.get("formattedAddress", "N/A")
                loc = p.get("location", {})
                results.append({
                    "name": display_name,
                    "address": fmt_address,
                    "location": loc,
                })
            return str(results)
    except Exception as e:
        return f"Error executing Places API (New): {e}"


def check_package_vulnerabilities(package_name: str, version: str = "") -> str:
    """Queries the OSV.dev public vulnerability database for known security advisories (CVEs) affecting Python libraries used by agents.

    Args:
        package_name: Name of the PyPI package to check (e.g. 'urllib3', 'requests', 'langchain', 'transformers').
        version: Optional version string of the package (e.g. '1.26.4').

    Returns:
        A list of known CVE/GHSA vulnerabilities and summaries affecting the package.
    """
    url = "https://api.osv.dev/v1/query"
    payload = {"package": {"name": package_name.strip().lower(), "ecosystem": "PyPI"}}
    if version:
        payload["version"] = version.strip()

    headers = {"Content-Type": "application/json"}
    api_key = os.environ.get("OSV_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            vulns = data.get("vulns", [])
            if not vulns:
                ver_str = f" v{version}" if version else ""
                return f"No known security vulnerabilities found for package '{package_name}'{ver_str}."

            results = []
            for v in vulns[:5]:
                results.append({
                    "id": v.get("id", "Unknown"),
                    "aliases": ", ".join(v.get("aliases", [])),
                    "summary": v.get("summary", v.get("details", ""))[:120],
                })
            return str(results)
    except Exception as e:
        return f"Failed to fetch vulnerability data for '{package_name}': {e}"


def discover_vertex_reasoning_engines() -> str:
    """Queries Vertex AI Reasoning Engines API in us-central1 to discover live deployed agents in GCP.

    Returns:
        A formatted list of live deployed Reasoning Engine resources with display names and resource IDs.
    """
    vertexai.init(project=PROJECT_ID, location="us-central1")
    engines = reasoning_engines.ReasoningEngine.list()
    if not engines:
        return "No live Reasoning Engine agents found in us-central1."

    live_agents = [
        {
            "display_name": getattr(e, "display_name", "Unknown"),
            "resource_name": getattr(e, "resource_name", str(e)),
            "create_time": str(getattr(e, "create_time", "")),
        }
        for e in engines
    ]
    return str(live_agents)


def get_agent_estate(status_filter: str = "") -> str:
    """Retrieves the list of AI agents in the enterprise estate from Firestore.

    Args:
        status_filter: Optional filter by status e.g. 'REGISTERED', 'UNSANCTIONED', 'REVIEW_REQUIRED'.

    Returns:
        A formatted list of agent metadata dictionaries.
    """
    db = firestore.Client(project=PROJECT_ID)
    collection_ref = db.collection(COLLECTION_NAME)

    if status_filter:
        query = collection_ref.where("status", "==", status_filter.upper())
        docs = query.stream()
    else:
        docs = collection_ref.stream()

    results = [doc.to_dict() for doc in docs]
    if not results:
        return f"No agents found matching status filter: '{status_filter}'" if status_filter else "No agents found in estate."
    return str(results)


def audit_agent_details(agent_id: str) -> str:
    """Audits and fetches complete security details for a specific agent by agent_id.

    Args:
        agent_id: Unique ID of the agent to audit e.g. 'agent-001', 'agent-002'.

    Returns:
        Detailed agent governance record or an error message if not found.
    """
    db = firestore.Client(project=PROJECT_ID)
    doc_ref = db.collection(COLLECTION_NAME).document(agent_id)
    doc = doc_ref.get()

    if not doc.exists:
        return f"Agent ID '{agent_id}' not found in governance database."
    return str(doc.to_dict())


def register_or_update_agent(
    agent_id: str,
    display_name: str,
    owner_team: str,
    service_account: str,
    status: str,
    risk_level: str,
    permissions: str,
) -> str:
    """Registers a new agent or updates an existing agent's security record in Firestore.

    Args:
        agent_id: Unique identifier for the agent e.g. 'agent-004'.
        display_name: Human-readable name of the agent.
        owner_team: Team responsible for operating the agent.
        service_account: Service account email tied to the agent.
        status: Governance status e.g. 'REGISTERED', 'UNSANCTIONED', 'REVIEW_REQUIRED'.
        risk_level: Assessed risk level e.g. 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'.
        permissions: Comma-separated list of IAM roles or permissions.

    Returns:
        Status message confirming record creation/update.
    """
    db = firestore.Client(project=PROJECT_ID)
    doc_ref = db.collection(COLLECTION_NAME).document(agent_id)

    perm_list = [p.strip() for p in permissions.split(",") if p.strip()]
    record = {
        "agent_id": agent_id,
        "display_name": display_name,
        "owner_team": owner_team,
        "service_account": service_account,
        "status": status.upper(),
        "risk_level": risk_level.upper(),
        "permissions": perm_list,
        "last_audit": datetime.date.today().isoformat(),
    }
    doc_ref.set(record)
    return f"Successfully updated agent governance record for '{agent_id}' ({display_name})."


from pathlib import Path
from google.adk.code_executors import AgentEngineSandboxCodeExecutor

DEPLOYMENT_METADATA_FILE = Path(__file__).parent.parent / "deployment_metadata.json"
AGENT_ENGINE_RESOURCE_NAME = "projects/231506936805/locations/us-central1/reasoningEngines/5827652970015096832"
if DEPLOYMENT_METADATA_FILE.exists():
    try:
        with open(DEPLOYMENT_METADATA_FILE) as f:
            data = json.load(f)
            AGENT_ENGINE_RESOURCE_NAME = data.get("remote_agent_runtime_id", AGENT_ENGINE_RESOURCE_NAME)
    except Exception:
        pass

code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=AGENT_ENGINE_RESOURCE_NAME,
)

from google.adk.memory import VertexAiMemoryBankService
from google.adk.tools import load_memory, preload_memory
from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from .a2ui_utils import a2ui_callback

MEMORY_ENGINE_ID = AGENT_ENGINE_RESOURCE_NAME.split("/")[-1]
memory_service = VertexAiMemoryBankService(
    project=PROJECT_ID,
    location="us-central1",
    agent_engine_id=MEMORY_ENGINE_ID,
)

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are the AI Governance & Shadow Agent Auditor for NovaSmart's Google Cloud estate. "
        "Your role is to help security leaders discover unsanctioned shadow agents, audit over-privileged service accounts, "
        "check package security vulnerabilities, geocode addresses, find nearby places, generate security governance badges using AI, "
        "generate short governance videos using Google's Omni model (gemini-omni-flash-preview), "
        "execute sandboxed Python code safely, and access/retrieve persistent memories from the Memory Bank. "
        "Always remember and track user preferences, personal details, health/dietary restrictions, and specifically ALL user allergies "
        "(food, chemical, environmental, or medical). Whenever the user mentions any allergy or preference, immediately call `save_memory` to store it in Memory Bank, "
        "and always use `load_memory` or `preload_memory` to recall user allergies before offering suggestions or recommendations."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=code_executor,
    instruction=instruction,
    after_model_callback=a2ui_callback,
    tools=[
        generate_governance_badge_image,
        generate_governance_video,
        geocode_address,
        search_nearby_places,
        check_package_vulnerabilities,
        discover_vertex_reasoning_engines,
        get_agent_estate,
        audit_agent_details,
        register_or_update_agent,
        load_memory,
        preload_memory,
        save_memory,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)







