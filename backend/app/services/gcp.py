import os
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Google Services Integration: Project and region constants
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "promptwars-1-493418")
GCP_REGION = os.getenv("GCP_REGION", "us-central1")


class GCPServiceBridge:
    """
    Production bridge to live Google Cloud services:

    - Cloud Logging:  Streams all backend logs to GCP Log Explorer.
    - Firebase Admin: Validates admin auth tokens via Firebase Auth.
    - Firestore:      Persists real-time venue telemetry with write throttling.
    - Vertex AI:      Generates empathetic, context-aware route insights via Gemini.

    Falls back safely to local mock mode when GCP credentials are unavailable
    (e.g., during local development without ADC configured).
    """

    # Throttle Firestore writes: only publish if last write was >5 seconds ago.
    # Prevents excessive GCP write operations during high-frequency SSE ticks.
    _FIRESTORE_THROTTLE_SECONDS = 5.0

    def __init__(self):
        self.use_mock = os.getenv("USE_REAL_GCP", "false").lower() != "true"
        self._firestore_client = None
        self._firebase_initialized = False
        self._vertex_initialized = False
        self._last_firestore_write: float = 0.0

        # Step 1: Attach Cloud Logging — always attempt even in mock mode.
        self._setup_cloud_logging()

        # Step 2: Activate Firebase, Firestore and Vertex AI for live services.
        if not self.use_mock:
            self._setup_firebase()
            self._setup_firestore()
            self._setup_vertex_ai()

    # ── Setup Methods ──────────────────────────────────────────────────────

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
            logger.info("Cloud Logging unavailable (running locally). Reason: %s", exc)

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
        and sharing state durably across stateless Cloud Run instances.
        """
        try:
            from google.cloud import firestore
            self._firestore_client = firestore.Client(project=GCP_PROJECT_ID)
            logger.info("Firestore client connected. Project: %s", GCP_PROJECT_ID)
        except Exception as exc:
            logger.warning("Firestore init failed, telemetry will not persist: %s", exc)

    def _setup_vertex_ai(self):
        """
        Initializes the Vertex AI SDK pointing to the Gemini 1.5 Flash model.
        Used to generate context-aware, empathetic route insight text based on
        live venue telemetry (crowd density, weather, emergency state).
        """
        try:
            import vertexai
            vertexai.init(project=GCP_PROJECT_ID, location=GCP_REGION)
            self._vertex_initialized = True
            logger.info(
                "Vertex AI (Gemini) initialized. Project: %s | Region: %s",
                GCP_PROJECT_ID, GCP_REGION
            )
        except Exception as exc:
            logger.warning("Vertex AI init failed, will use static reasoning. Reason: %s", exc)

    # ── Public Methods ─────────────────────────────────────────────────────

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
        Publishes a telemetry event to Google Cloud Firestore with write throttling.

        Writes are throttled to at most once per _FIRESTORE_THROTTLE_SECONDS interval
        to prevent excessive GCP writes during high-frequency SSE ticks. This
        significantly reduces billing cost and improves Cloud Run throughput.

        Args:
            event_type: Label for the kind of event (e.g. 'congestion_update').
            data: Dictionary of event payload fields to persist.
        """
        if self.use_mock or self._firestore_client is None:
            logger.debug("Mock telemetry event: %s | data: %s", event_type, data)
            return

        now = time.monotonic()
        if now - self._last_firestore_write < self._FIRESTORE_THROTTLE_SECONDS:
            logger.debug("Firestore write throttled for event: %s", event_type)
            return

        try:
            doc_ref = self._firestore_client.collection("venue_telemetry").document()
            payload = {"event_type": event_type, **data}
            doc_ref.set(payload)
            self._last_firestore_write = now
            logger.info("Telemetry published to Firestore: %s", event_type)
        except Exception as exc:
            logger.error("Firestore publish failed: %s", exc)

    def get_ai_route_insight(
        self,
        start: str,
        end: str,
        weather: str,
        avg_density: float,
        emergency: bool,
    ) -> Optional[str]:
        """
        Uses Google Vertex AI (Gemini 1.5 Flash) to generate a short, empathetic
        route insight tailored to current venue conditions.

        The response is a 1-2 sentence human-readable tip that supplements the
        static routing reasoning, adding context-aware safety and comfort advice.

        Args:
            start:       Departure node label (e.g. 'entrance_north').
            end:         Destination node label (e.g. 'food_court_1').
            weather:     Current weather state ('clear' or 'rain').
            avg_density: Average crowd density multiplier along the path (1.0–3.0).
            emergency:   True if emergency/exodus mode is active.

        Returns:
            A 1-2 sentence string from Gemini, or None if the call fails.
        """
        if not self._vertex_initialized:
            return None

        try:
            from vertexai.generative_models import GenerativeModel

            weather_ctx = "it is currently raining" if weather == "rain" else "weather is clear"
            crowd_ctx = (
                "the venue is extremely crowded" if avg_density > 2.0
                else "the venue has moderate crowd levels" if avg_density > 1.4
                else "the venue has light crowd levels"
            )
            emergency_ctx = " An emergency evacuation is in progress." if emergency else ""

            prompt = (
                f"You are a friendly AI assistant helping a sports venue attendee navigate safely. "
                f"The attendee is walking from {start.replace('_', ' ')} to {end.replace('_', ' ')}. "
                f"Currently, {weather_ctx} and {crowd_ctx}.{emergency_ctx} "
                f"Give ONE short (max 25 words), warm, helpful safety tip for this journey. "
                f"Do not use markdown, bullet points, or emojis."
            )

            model = GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            tip = response.text.strip()
            logger.info("Vertex AI route insight generated (%d chars).", len(tip))
            return tip
        except Exception as exc:
            logger.warning("Vertex AI insight generation failed: %s", exc)
            return None


# Global singleton — shared across all FastAPI request handlers.
# On Cloud Run with multiple instances, state is anchored in Firestore.
gcp_services = GCPServiceBridge()
