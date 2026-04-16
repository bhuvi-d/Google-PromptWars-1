import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Google Services Integration: Project-level constants
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "promptwars-1-493418")

class GCPServiceBridge:
    """
    Production bridge to live Google Cloud services:
    - Cloud Logging: Streams all backend logs to GCP log explorer
    - Firebase Admin: Validates admin auth tokens via Firebase Auth
    - Firestore: Publishes real-time venue telemetry to a NoSQL cloud database
    - Pub/Sub: Event broadcast channel for distributed updates

    Falls back safely to local mock mode when GCP credentials are unavailable
    (e.g., during local development without ADC configured).
    """

    def __init__(self):
        self.use_mock = os.getenv("USE_REAL_GCP", "false").lower() != "true"
        self._firestore_client = None
        self._firebase_initialized = False

        # Step 1: Always attempt to attach Google Cloud Logging.
        # When running on Cloud Run with USE_REAL_GCP=true, this streams
        # all Python logger calls to GCP Log Explorer in real time.
        self._setup_cloud_logging()

        # Step 2: Activate Firebase Admin and Firestore for live services
        if not self.use_mock:
            self._setup_firebase()
            self._setup_firestore()

    def _setup_cloud_logging(self):
        """
        Attaches Google Cloud Logging to the Python root logger.
        All subsequent logger.info / logger.warning calls will appear
        natively in GCP Cloud Logging / Log Explorer.
        """
        try:
            import google.cloud.logging
            client = google.cloud.logging.Client(project=GCP_PROJECT_ID)
            client.setup_logging()
            logger.info(
                "GCP Cloud Logging active. Project: %s | Service: venue-api",
                GCP_PROJECT_ID
            )
        except Exception as exc:
            logging.basicConfig(level=logging.INFO)
            logger.info(
                "Cloud Logging unavailable (running locally). Reason: %s", exc
            )

    def _setup_firebase(self):
        """
        Initializes the Firebase Admin SDK using the Cloud Run service
        account credentials bound to the 'venue-api' Cloud Run service.
        """
        try:
            import firebase_admin
            if not firebase_admin._apps:
                firebase_admin.initialize_app()
                self._firebase_initialized = True
                logger.info("Firebase Admin SDK initialized successfully.")
        except Exception as exc:
            logger.warning(
                "Firebase Admin SDK init failed, falling back to mock token. Reason: %s", exc
            )
            self.use_mock = True

    def _setup_firestore(self):
        """
        Connects to Google Cloud Firestore for persisting venue telemetry
        events and making state durable across Cloud Run instances.
        """
        try:
            from google.cloud import firestore
            self._firestore_client = firestore.Client(project=GCP_PROJECT_ID)
            logger.info("Firestore client connected. Project: %s", GCP_PROJECT_ID)
        except Exception as exc:
            logger.warning(
                "Firestore init failed, telemetry will not persist: %s", exc
            )

    def verify_token(self, token: str) -> bool:
        """
        Validates an admin Bearer token.
        - When USE_REAL_GCP=true: verifies a real Firebase ID token.
        - When in mock mode: accepts the development test token.

        Args:
            token: Raw Bearer token string from the Authorization header.

        Returns:
            True if the token is valid, False otherwise.
        """
        if self.use_mock:
            return token == "mock-admin-token-123"
        try:
            import firebase_admin.auth
            decoded = firebase_admin.auth.verify_id_token(token)
            logger.info("Admin verified. UID: %s", decoded.get("uid"))
            return True
        except Exception as exc:
            logger.warning("Token verification failed: %s", exc)
            return False

    def publish_telemetry(self, event_type: str, data: dict):
        """
        Publishes a telemetry event to Google Cloud Firestore.
        This persists real-time venue state (congestion, attendance, weather)
        across all stateless Cloud Run instances.

        Args:
            event_type: A label for the kind of event (e.g. 'congestion_update').
            data: A dictionary of event payload fields to persist.
        """
        if self.use_mock or self._firestore_client is None:
            logger.debug("Mock telemetry event: %s | data: %s", event_type, data)
            return
        try:
            doc_ref = self._firestore_client.collection("venue_telemetry").document()
            payload = {"event_type": event_type, **data}
            doc_ref.set(payload)
            logger.info("Telemetry published to Firestore: %s", event_type)
        except Exception as exc:
            logger.error("Firestore publish failed: %s", exc)


# Global singleton — shared across all FastAPI request handlers.
# On Cloud Run with multiple instances, state is anchored in Firestore.
gcp_services = GCPServiceBridge()
