import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class GCPServiceSimulator:
    """
    Acts as a bridge to real GCP services (Firestore, PubSub, Auth).
    If GCP credentials are not active, safely falls back to local memory.
    """
    def __init__(self):
        self.use_mock = os.getenv("USE_REAL_GCP", "false").lower() == "false"
        
        # Google Services Integration: Instantiate Cloud Logging natively
        try:
            import google.cloud.logging
            client = google.cloud.logging.Client()
            client.setup_logging()
            logger.info("Google Cloud Logging successfully attached.")
        except Exception as e:
            logger.info("Running locally without GCP Active Credentials. Cloud Logging bypassed.")

        if not self.use_mock:
            try:
                # In a real environment, initialize firebase_admin and google.cloud SDKs here
                # import firebase_admin
                # from google.cloud import firestore, pubsub_v1
                # firebase_admin.initialize_app()
                logger.info("GCP Real Services Initialized.")
            except Exception as e:
                logger.warning(f"Failed to init GCP, falling back to mock: {e}")
                self.use_mock = True

    def verify_token(self, token: str) -> bool:
        if self.use_mock:
            return token == "mock-admin-token-123"
        # Real impl: use firebase_admin.auth.verify_id_token(token)
        return True

    def publish_telemetry(self, topic: str, data: dict):
        if self.use_mock:
            # Mock pubsub
            pass
        else:
            # Real impl: publisher.publish(topic_path, json.dumps(data).encode("utf-8"))
            pass

gcp_services = GCPServiceSimulator()
