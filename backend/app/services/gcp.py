import os
import time
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)


class GCPServiceBridge:
    """
    Production bridge to live Google Cloud services.
    
    Architecture:
    - Cloud Logging: Native stream for operational observability.
    - Firebase Admin: Token verification for administrative security.
    - Firestore: Real-time NoSQL state for live client updates (Throttled).
    - BigQuery: Analytical data warehouse for post-match crowd science (Async).
    - Vertex AI: Generative reasoning using Gemini 1.5 Flash.
    """

    def __init__(self):
        # Master toggle from settings. If USE_REAL_GCP is False, all methods
        # fall back to safe local mocks.
        self.use_mock = not settings.USE_REAL_GCP
        
        self._firestore_client = None
        self._bigquery_client = None
        self._firebase_initialized = False
        self._vertex_initialized = False
        
        self._last_firestore_write: float = 0.0

        # Operational: Logs should always go to Cloud Logging if it exists
        self._setup_cloud_logging()

        if not self.use_mock:
            self._setup_firebase()
            self._setup_firestore()
            self._setup_vertex_ai()
            self._setup_bigquery()

    # ── Setup Methods ──────────────────────────────────────────────────────

    def _setup_cloud_logging(self):
        try:
            import google.cloud.logging
            client = google.cloud.logging.Client(project=settings.GCP_PROJECT_ID)
            client.setup_logging()
            logger.info("GCP Cloud Logging active. Project: %s", settings.GCP_PROJECT_ID)
        except Exception as exc:
            logging.basicConfig(level=logging.INFO)
            logger.info("Cloud Logging fallback to stdout (Local). Reason: %s", exc)

    def _setup_firebase(self):
        try:
            import firebase_admin
            if not firebase_admin._apps:
                firebase_admin.initialize_app()
                self._firebase_initialized = True
                logger.info("Firebase Admin initialized successfully.")
        except Exception as exc:
            logger.warning("Firebase Admin initialization skipped: %s", exc)

    def _setup_firestore(self):
        try:
            from google.cloud import firestore
            self._firestore_client = firestore.Client(project=settings.GCP_PROJECT_ID)
            logger.info("Firestore client initialized. Project: %s", settings.GCP_PROJECT_ID)
        except Exception as exc:
            logger.warning("Firestore connection failed: %s", exc)

    def _setup_vertex_ai(self):
        try:
            import vertexai
            vertexai.init(project=settings.GCP_PROJECT_ID, location=settings.GCP_REGION)
            self._vertex_initialized = True
            logger.info("Vertex AI (Gemini) active in region: %s", settings.GCP_REGION)
        except Exception as exc:
            logger.warning("Vertex AI initialization failed: %s", exc)

    def _setup_bigquery(self):
        """
        Initializes the BigQuery client for analytical data streaming.
        Attempts to create the destination dataset if it does not exist.
        """
        try:
            from google.cloud import bigquery
            self._bigquery_client = bigquery.Client(project=settings.GCP_PROJECT_ID)
            
            # Ensure dataset exists (Idempotent)
            dataset_id = f"{settings.GCP_PROJECT_ID}.{settings.BIGQUERY_DATASET}"
            self._bigquery_client.create_dataset(dataset_id, exists_ok=True)
            logger.info("BigQuery client active. Target: %s", dataset_id)
        except Exception as exc:
            logger.warning("BigQuery initialization failed: %s", exc)

    # ── Security ───────────────────────────────────────────────────────────

    def verify_token(self, token: str) -> bool:
        if self.use_mock:
            return token == "mock-admin-token-123"
        try:
            import firebase_admin.auth
            decoded = firebase_admin.auth.verify_id_token(token)
            return True
        except Exception:
            return False

    # ── Real-Time Telemetry (Firestore) ───────────────────────────────────

    def publish_telemetry(self, event_type: str, data: dict):
        """Publishes live state with write throttling for cost efficiency."""
        if self.use_mock or not self._firestore_client:
            return

        now = time.monotonic()
        if now - self._last_firestore_write < settings.FIRESTORE_THROTTLE_SECONDS:
            return

        try:
            doc_ref = self._firestore_client.collection("venue_telemetry").document()
            doc_ref.set({"event_type": event_type, "timestamp": datetime.utcnow(), **data})
            self._last_firestore_write = now
        except Exception as exc:
            logger.error("Firestore publish failed: %s", exc)

    # ── Analytical Intelligence (BigQuery) ────────────────────────────────

    async def log_telemetry_batch(self, telemetry_snapshot: Dict[str, Any]):
        """
        Streams a telemetry snapshot to BigQuery for historical analysis.
        Designed to be called as a FastAPI Background Task.
        """
        if self.use_mock or not self._bigquery_client:
            return

        try:
            table_id = f"{settings.GCP_PROJECT_ID}.{settings.BIGQUERY_DATASET}.{settings.BIGQUERY_TABLE}"
            
            # Prepare row for BQ schema
            row = {
                "timestamp": datetime.utcnow().isoformat(),
                "attendance": telemetry_snapshot.get("attendance"),
                "mass_exodus": telemetry_snapshot.get("mass_exodus"),
                "weather": telemetry_snapshot.get("weather"),
                "heatmap_json": json.dumps(telemetry_snapshot.get("heatmap", []))
            }
            
            errors = self._bigquery_client.insert_rows_json(table_id, [row])
            if errors:
                logger.error("BigQuery streaming errors: %s", errors)
            else:
                logger.debug("Telemetry snapshot streamed to BigQuery.")
        except Exception as exc:
            logger.error("BigQuery log failed: %s", exc)

    # ── Generative Reasoning (Vertex AI) ──────────────────────────────────

    def get_ai_route_insight(
        self,
        start: str,
        end: str,
        weather: str,
        avg_density: float,
        emergency: bool,
    ) -> Optional[str]:
        if not self._vertex_initialized:
            return None

        try:
            from vertexai.generative_models import GenerativeModel
            model = GenerativeModel("gemini-1.5-flash")
            
            prompt = (
                f"Attendee route: {start} to {end}. Weather: {weather}. "
                f"Crowd Density: {avg_density:.1f}/3.0. Emergency: {emergency}. "
                "Provide ONE very short, friendly, hyper-personalized safety tip "
                "for this specific journey. No emojis."
            )
            
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception:
            return None

import json
gcp_services = GCPServiceBridge()
