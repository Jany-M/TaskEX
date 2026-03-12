import json

from PySide6.QtCore import QRunnable, Signal, QObject

from db.db_setup import get_session
from db.models import ProfileData


class ProfileLoadWorkerSignals(QObject):
    profile_loaded = Signal(int, dict)
    error = Signal(str)

    def __init__(self):
        super().__init__()

class ProfileLoadWorker(QRunnable):
    """
    Worker for loading profile data using QThreadPool.
    """
    def __init__(self, profile_id):
        super().__init__()
        self.profile_id = profile_id
        self.signals = ProfileLoadWorkerSignals()

    def run(self):
        """
        Perform the database fetch operation.
        """
        session = None
        try:
            session = get_session()
            profile_data = (
                session.query(ProfileData)
                .filter_by(profile_id=self.profile_id)
                .order_by(ProfileData.id.desc())
                .first()
            )
            # ProfileData.settings is a JSON column: SQLAlchemy may return dict (native)
            # while legacy rows may still be plain JSON strings.
            raw_settings = profile_data.settings if profile_data else {}
            settings = raw_settings
            # Handle legacy double-encoded JSON strings.
            for _ in range(2):
                if isinstance(settings, str):
                    settings = json.loads(settings) if settings else {}
                else:
                    break
            if not isinstance(settings, dict):
                settings = {}
            # Emit the signal with the loaded data
            # print(f"Emitting profile_loaded signal with settings: {settings}")
            self.signals.profile_loaded.emit(self.profile_id, settings)
        except Exception as e:
            error_message = f"Error loading profile data: {e}"
            print(error_message)
            self.signals.error.emit(error_message)
        finally:
            if session is not None:
                session.close()
