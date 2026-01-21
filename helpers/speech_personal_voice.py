from __future__ import annotations

import json
import logging
import os
import time
from contextlib import ExitStack
from dataclasses import asdict, dataclass, field
from datetime import datetime
from html import escape as xml_escape
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _mask_secret(value: str, *, show_last: int = 4) -> str:
    stripped = (value or "").strip()
    if not stripped:
        return ""
    if len(stripped) <= show_last:
        return "*" * len(stripped)
    return "*" * (len(stripped) - show_last) + stripped[-show_last:]


def _guess_audio_content_type(path: Path) -> str:
    ext = path.suffix.lower().lstrip(".")
    if ext == "wav":
        return "audio/wav"
    if ext in {"mp3", "mpeg"}:
        # Many browsers report MP3 as audio/mpeg.
        return "audio/mpeg"
    # Fall back to a reasonable default; the API may reject unknown types.
    return "application/octet-stream"


DEFAULT_CONFIG_PATH = Path(".conf") / "personal_voice_config.json"
DEFAULT_OUTPUT_WAV_PATH = Path("outputs") / "temp" / "personal_voice_output.wav"

CUSTOM_VOICE_API_VERSION = "2024-02-01-preview"


@dataclass(slots=True)
class SpeakerProfile:
    """Represents a Personal Voice speaker profile."""

    id: str
    name: str
    speaker_profile_id: str
    creation_date: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> SpeakerProfile:
        return SpeakerProfile(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            speaker_profile_id=str(data.get("speaker_profile_id", "")),
            creation_date=str(data.get("creation_date", "")),
        )


@dataclass(slots=True)
class PersonalVoiceConfig:
    """Configuration required to synthesize with Azure Speech Personal Voice.

    Notes:
        - `profiles` contains a list of SpeakerProfile objects.
        - `selected_profile_id` determines which profile is currently active.
        - `voice_name` is the base model voice name used in SSML (e.g., 'DragonLatestNeural').
          Azure will apply the Personal Voice embedding via the selected profile's speaker_profile_id.
    """

    speech_key: str = ""
    speech_region: str = ""
    voice_name: str = "DragonLatestNeural"
    language: str = "en-US"

    # Profile management
    profiles: list[SpeakerProfile] = field(default_factory=list)
    selected_profile_id: str = ""

    # Optional fields used when creating Personal Voice via the Custom Voice API.
    custom_voice_api_version: str = CUSTOM_VOICE_API_VERSION
    personal_voice_project_id: str = ""
    personal_voice_consent_id: str = ""
    personal_voice_id: str = ""
    personal_voice_consent_locale: str = "en-US"
    personal_voice_voice_talent_name: str = ""
    personal_voice_company_name: str = ""

    def validate_for_synthesis(self) -> None:
        missing: list[str] = []
        if not self.speech_key.strip():
            missing.append("speech_key")
        if not self.speech_region.strip():
            missing.append("speech_region")
        if not self.selected_profile_id.strip():
            missing.append("selected_profile_id (no profile selected)")
        elif not self.get_selected_profile():
            missing.append("selected_profile_id (profile not found)")
        if not self.voice_name.strip():
            missing.append("voice_name")
        if not self.language.strip():
            missing.append("language")
        if missing:
            raise ValueError(f"Missing required config values: {', '.join(missing)}")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        # Convert SpeakerProfile objects to dicts
        data["profiles"] = [profile.to_dict() for profile in self.profiles]
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> PersonalVoiceConfig:
        # Handle migration from old format (speaker_profile_id as top-level field)
        profiles_data = data.get("profiles", [])
        profiles = [SpeakerProfile.from_dict(p) for p in profiles_data] if profiles_data else []

        # Migrate old format if needed
        if not profiles and data.get("speaker_profile_id"):
            today = datetime.now().strftime("%Y-%m-%d")
            profile_id = f"profile_{today.replace('-', '_')}"
            profiles = [
                SpeakerProfile(
                    id=profile_id,
                    name="Migrated Profile",
                    speaker_profile_id=str(data.get("speaker_profile_id", "")),
                    creation_date=today,
                )
            ]

        return PersonalVoiceConfig(
            speech_key=str(data.get("speech_key", "")),
            speech_region=str(data.get("speech_region", "")),
            voice_name=str(data.get("voice_name", "DragonLatestNeural")),
            language=str(data.get("language", "en-US")),
            profiles=profiles,
            selected_profile_id=str(
                data.get("selected_profile_id", profiles[0].id if profiles else "")
            ),
            custom_voice_api_version=str(
                data.get("custom_voice_api_version", CUSTOM_VOICE_API_VERSION)
            ),
            personal_voice_project_id=str(data.get("personal_voice_project_id", "")),
            personal_voice_consent_id=str(data.get("personal_voice_consent_id", "")),
            personal_voice_id=str(data.get("personal_voice_id", "")),
            personal_voice_consent_locale=str(data.get("personal_voice_consent_locale", "en-US")),
            personal_voice_voice_talent_name=str(data.get("personal_voice_voice_talent_name", "")),
            personal_voice_company_name=str(data.get("personal_voice_company_name", "")),
        )

    def get_selected_profile(self) -> SpeakerProfile | None:
        """Get the currently selected speaker profile."""
        if not self.selected_profile_id:
            return None
        for profile in self.profiles:
            if profile.id == self.selected_profile_id:
                return profile
        return None

    def add_profile(self, name: str, speaker_profile_id: str) -> SpeakerProfile:
        """Add a new speaker profile."""
        today = datetime.now().strftime("%Y-%m-%d")
        profile_id = f"profile_{today.replace('-', '_')}_{len(self.profiles) + 1}"

        profile = SpeakerProfile(
            id=profile_id,
            name=name or f"Profile {today}",
            speaker_profile_id=speaker_profile_id,
            creation_date=today,
        )
        self.profiles.append(profile)
        # Auto-select the newly created profile
        self.selected_profile_id = profile.id
        return profile

    def get_profile_choices(self) -> list[tuple[str, str]]:
        """Get list of (display_name, profile_id) tuples for UI selection."""
        return [(f"{p.name} ({p.creation_date})", p.id) for p in self.profiles]


def _custom_voice_endpoint(region: str) -> str:
    # Docs use: https://{region}.api.cognitive.microsoft.com/customvoice/...
    return f"https://{region}.api.cognitive.microsoft.com"


def _import_requests():
    try:
        import requests  # type: ignore

        return requests
    except Exception:
        return None


def _coerce_response_body(body: Any) -> dict[str, Any] | list[Any]:
    # Streamlit's st.json renders dict/list well, but passing a plain string
    # triggers a JSON parse attempt in the UI. Coerce primitives to a dict.
    if isinstance(body, (dict, list)):
        return body
    if body is None:
        return {"raw": ""}
    return {"raw": str(body)}


def _parse_operation_id(operation_location: str | None, operation_id: str | None) -> str | None:
    if operation_id:
        return operation_id
    if not operation_location:
        return None

    parsed = urlparse(operation_location)
    # /customvoice/operations/{id}
    parts = [p for p in parsed.path.split("/") if p]
    if "operations" in parts:
        idx = parts.index("operations")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return None


def custom_voice_create_project(
    *,
    config: PersonalVoiceConfig,
    project_id: str,
    description: str = "",
    display_name: str = "",
    http=None,
) -> dict[str, Any]:
    """Create a Personal Voice project via the Custom Voice REST API."""

    try:
        if not config.speech_key.strip() or not config.speech_region.strip():
            return {"ok": False, "error": "Missing speech_key or speech_region."}

        api_version = (config.custom_voice_api_version or CUSTOM_VOICE_API_VERSION).strip()
        if not project_id.strip():
            return {"ok": False, "error": "Project id is required."}

        requests_mod = http or _import_requests()
        if requests_mod is None:
            return {
                "ok": False,
                "error": "Missing dependency 'requests'.",
                "hint": "Add 'requests' to pyproject.toml dependencies and reinstall.",
            }

        endpoint = _custom_voice_endpoint(config.speech_region)
        url = f"{endpoint}/customvoice/projects/{project_id}"
        params = {"api-version": api_version}
        headers = {
            "Ocp-Apim-Subscription-Key": config.speech_key,
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {"kind": "PersonalVoice"}
        if description.strip():
            payload["description"] = description.strip()
        if display_name.strip():
            payload["displayName"] = display_name.strip()

        resp = requests_mod.put(url, params=params, headers=headers, json=payload, timeout=60)
        try:
            body = _coerce_response_body(resp.json())
        except Exception:
            body = {"raw": resp.text}

        if resp.status_code not in {200, 201}:
            return {
                "ok": False,
                "status_code": resp.status_code,
                "error": "Project create failed.",
                "response": body,
            }

        return {"ok": True, "project": body, "status_code": resp.status_code}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def custom_voice_post_consent_from_file(
    *,
    config: PersonalVoiceConfig,
    consent_id: str,
    project_id: str,
    voice_talent_name: str,
    company_name: str,
    locale: str,
    consent_audio_path: Path,
    description: str = "",
    http=None,
) -> dict[str, Any]:
    """Upload consent audio for Personal Voice (multipart/form-data)."""

    try:
        if not config.speech_key.strip() or not config.speech_region.strip():
            return {"ok": False, "error": "Missing speech_key or speech_region."}

        api_version = (config.custom_voice_api_version or CUSTOM_VOICE_API_VERSION).strip()
        if not consent_id.strip():
            return {"ok": False, "error": "Consent id is required."}
        if not project_id.strip():
            return {"ok": False, "error": "Project id is required."}
        if not voice_talent_name.strip():
            return {"ok": False, "error": "Voice talent name is required."}
        if not company_name.strip():
            return {"ok": False, "error": "Company name is required."}
        if not locale.strip():
            return {"ok": False, "error": "Locale is required."}
        if not consent_audio_path.exists():
            return {
                "ok": False,
                "error": f"Consent audio file not found: {consent_audio_path.as_posix()}",
            }

        requests_mod = http or _import_requests()
        if requests_mod is None:
            return {
                "ok": False,
                "error": "Missing dependency 'requests'.",
                "hint": "Add 'requests' to pyproject.toml dependencies and reinstall.",
            }

        endpoint = _custom_voice_endpoint(config.speech_region)
        url = f"{endpoint}/customvoice/consents/{consent_id}"
        params = {"api-version": api_version}
        headers = {"Ocp-Apim-Subscription-Key": config.speech_key}

        data: dict[str, str] = {
            "projectId": project_id,
            "voiceTalentName": voice_talent_name,
            "companyName": company_name,
            "locale": locale,
        }
        if description.strip():
            data["description"] = description.strip()

        with consent_audio_path.open("rb") as f:
            files = {
                "audiodata": (
                    consent_audio_path.name,
                    f,
                    _guess_audio_content_type(consent_audio_path),
                )
            }
            resp = requests_mod.post(
                url, params=params, headers=headers, data=data, files=files, timeout=120
            )

        operation_location = resp.headers.get("Operation-Location")
        operation_id = resp.headers.get("Operation-Id")
        parsed_operation_id = _parse_operation_id(operation_location, operation_id)

        try:
            body = _coerce_response_body(resp.json())
        except Exception:
            body = {"raw": resp.text}

        # Consent IDs are user-provided. If the id already exists, treat this as
        # an idempotent success by fetching the existing resource.
        if resp.status_code == 409:
            existing = custom_voice_get_consent(
                config=config, consent_id=consent_id, http=requests_mod
            )
            if existing.get("ok"):
                existing["note"] = "Consent already exists; using existing consent resource."
                return existing

        if resp.status_code not in {200, 201}:
            return {
                "ok": False,
                "status_code": resp.status_code,
                "error": "Consent upload failed.",
                "response": body,
                "operation_location": operation_location,
                "operation_id": parsed_operation_id,
            }

        return {
            "ok": True,
            "consent": body,
            "status_code": resp.status_code,
            "operation_location": operation_location,
            "operation_id": parsed_operation_id,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def custom_voice_get_consent(
    *,
    config: PersonalVoiceConfig,
    consent_id: str,
    http=None,
) -> dict[str, Any]:
    """Fetch a consent resource by id."""

    try:
        if not config.speech_key.strip() or not config.speech_region.strip():
            return {"ok": False, "error": "Missing speech_key or speech_region."}
        if not consent_id.strip():
            return {"ok": False, "error": "Consent id is required."}

        api_version = (config.custom_voice_api_version or CUSTOM_VOICE_API_VERSION).strip()
        requests_mod = http or _import_requests()
        if requests_mod is None:
            return {
                "ok": False,
                "error": "Missing dependency 'requests'.",
                "hint": "Add 'requests' to pyproject.toml dependencies and reinstall.",
            }

        endpoint = _custom_voice_endpoint(config.speech_region)
        url = f"{endpoint}/customvoice/consents/{consent_id}"
        params = {"api-version": api_version}
        headers = {"Ocp-Apim-Subscription-Key": config.speech_key}

        resp = requests_mod.get(url, params=params, headers=headers, timeout=60)
        try:
            body = _coerce_response_body(resp.json())
        except Exception:
            body = {"raw": resp.text}

        if resp.status_code != 200:
            return {
                "ok": False,
                "status_code": resp.status_code,
                "error": "Get consent failed.",
                "response": body,
            }

        return {"ok": True, "consent": body, "status_code": resp.status_code}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def custom_voice_post_personal_voice_from_files(
    *,
    config: PersonalVoiceConfig,
    personal_voice_id: str,
    project_id: str,
    consent_id: str,
    prompt_audio_paths: list[Path],
    description: str = "",
    http=None,
) -> dict[str, Any]:
    """Create Personal Voice and return speakerProfileId (multipart/form-data)."""

    try:
        if not config.speech_key.strip() or not config.speech_region.strip():
            return {"ok": False, "error": "Missing speech_key or speech_region."}

        api_version = (config.custom_voice_api_version or CUSTOM_VOICE_API_VERSION).strip()
        if not personal_voice_id.strip():
            return {"ok": False, "error": "Personal voice id is required."}
        if not project_id.strip():
            return {"ok": False, "error": "Project id is required."}
        if not consent_id.strip():
            return {"ok": False, "error": "Consent id is required."}
        if not prompt_audio_paths:
            return {"ok": False, "error": "At least one prompt audio file is required."}

        for p in prompt_audio_paths:
            if not p.exists():
                return {"ok": False, "error": f"Prompt audio file not found: {p.as_posix()}"}

        requests_mod = http or _import_requests()
        if requests_mod is None:
            return {
                "ok": False,
                "error": "Missing dependency 'requests'.",
                "hint": "Add 'requests' to pyproject.toml dependencies and reinstall.",
            }

        endpoint = _custom_voice_endpoint(config.speech_region)
        url = f"{endpoint}/customvoice/personalvoices/{personal_voice_id}"
        params = {"api-version": api_version}
        headers = {"Ocp-Apim-Subscription-Key": config.speech_key}

        data: dict[str, str] = {
            "projectId": project_id,
            "consentId": consent_id,
        }
        if description.strip():
            data["description"] = description.strip()

        # Multiple 'audiodata' parts in a single multipart request.
        with ExitStack() as stack:
            file_tuples = []
            for p in prompt_audio_paths:
                f = stack.enter_context(p.open("rb"))
                file_tuples.append(("audiodata", (p.name, f, _guess_audio_content_type(p))))

            resp = requests_mod.post(
                url,
                params=params,
                headers=headers,
                data=data,
                files=file_tuples,
                timeout=300,
            )

        operation_location = resp.headers.get("Operation-Location")
        operation_id = resp.headers.get("Operation-Id")
        parsed_operation_id = _parse_operation_id(operation_location, operation_id)

        try:
            body = _coerce_response_body(resp.json())
        except Exception:
            body = {"raw": resp.text}

        if resp.status_code not in {200, 201}:
            return {
                "ok": False,
                "status_code": resp.status_code,
                "error": "Personal voice creation failed.",
                "response": body,
                "operation_location": operation_location,
                "operation_id": parsed_operation_id,
            }

        speaker_profile_id = None
        if isinstance(body, dict):
            speaker_profile_id = body.get("speakerProfileId")

        return {
            "ok": True,
            "personal_voice": body,
            "speaker_profile_id": speaker_profile_id,
            "status_code": resp.status_code,
            "operation_location": operation_location,
            "operation_id": parsed_operation_id,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def custom_voice_get_operation(
    *,
    config: PersonalVoiceConfig,
    operation_id: str,
    http=None,
) -> dict[str, Any]:
    """Fetch Custom Voice operation status."""

    try:
        if not config.speech_key.strip() or not config.speech_region.strip():
            return {"ok": False, "error": "Missing speech_key or speech_region."}
        if not operation_id.strip():
            return {"ok": False, "error": "Operation id is required."}

        api_version = (config.custom_voice_api_version or CUSTOM_VOICE_API_VERSION).strip()
        requests_mod = http or _import_requests()
        if requests_mod is None:
            return {
                "ok": False,
                "error": "Missing dependency 'requests'.",
                "hint": "Add 'requests' to pyproject.toml dependencies and reinstall.",
            }

        endpoint = _custom_voice_endpoint(config.speech_region)
        url = f"{endpoint}/customvoice/operations/{operation_id}"
        params = {"api-version": api_version}
        headers = {"Ocp-Apim-Subscription-Key": config.speech_key}

        resp = requests_mod.get(url, params=params, headers=headers, timeout=60)
        try:
            body = _coerce_response_body(resp.json())
        except Exception:
            body = {"raw": resp.text}

        if resp.status_code != 200:
            return {
                "ok": False,
                "status_code": resp.status_code,
                "error": "Get operation failed.",
                "response": body,
            }

        return {"ok": True, "operation": body, "status_code": resp.status_code}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def custom_voice_get_personal_voice(
    *,
    config: PersonalVoiceConfig,
    personal_voice_id: str,
    http=None,
) -> dict[str, Any]:
    """Fetch a Personal Voice resource (includes speakerProfileId once ready)."""

    try:
        if not config.speech_key.strip() or not config.speech_region.strip():
            return {"ok": False, "error": "Missing speech_key or speech_region."}
        if not personal_voice_id.strip():
            return {"ok": False, "error": "Personal voice id is required."}

        api_version = (config.custom_voice_api_version or CUSTOM_VOICE_API_VERSION).strip()
        requests_mod = http or _import_requests()
        if requests_mod is None:
            return {
                "ok": False,
                "error": "Missing dependency 'requests'.",
                "hint": "Add 'requests' to pyproject.toml dependencies and reinstall.",
            }

        endpoint = _custom_voice_endpoint(config.speech_region)
        url = f"{endpoint}/customvoice/personalvoices/{personal_voice_id}"
        params = {"api-version": api_version}
        headers = {"Ocp-Apim-Subscription-Key": config.speech_key}

        resp = requests_mod.get(url, params=params, headers=headers, timeout=60)
        try:
            body = _coerce_response_body(resp.json())
        except Exception:
            body = {"raw": resp.text}

        if resp.status_code != 200:
            return {
                "ok": False,
                "status_code": resp.status_code,
                "error": "Get personal voice failed.",
                "response": body,
            }

        speaker_profile_id = None
        if isinstance(body, dict):
            speaker_profile_id = body.get("speakerProfileId")

        return {
            "ok": True,
            "personal_voice": body,
            "speaker_profile_id": speaker_profile_id,
            "status_code": resp.status_code,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def custom_voice_wait_for_operation(
    *,
    config: PersonalVoiceConfig,
    operation_id: str,
    timeout_s: int = 300,
    poll_interval_s: float = 2.0,
    http=None,
) -> dict[str, Any]:
    """Poll a Custom Voice operation until terminal state."""

    started = time.time()
    while True:
        if time.time() - started > timeout_s:
            return {
                "ok": False,
                "error": "Timed out waiting for operation.",
                "operation_id": operation_id,
            }

        result = custom_voice_get_operation(config=config, operation_id=operation_id, http=http)
        if not result.get("ok"):
            return result

        op = result.get("operation")
        status = None
        if isinstance(op, dict):
            status = op.get("status")
        if status in {"Succeeded", "Failed"}:
            return {"ok": True, "operation": op, "status": status, "operation_id": operation_id}

        time.sleep(poll_interval_s)


def load_personal_voice_config(path: Path = DEFAULT_CONFIG_PATH) -> PersonalVoiceConfig:
    def _first_env(*names: str) -> str:
        for name in names:
            value = os.environ.get(name, "")
            if value and value.strip():
                return value.strip()
        return ""

    def _apply_env_defaults(cfg: PersonalVoiceConfig) -> PersonalVoiceConfig:
        # Keep file config as the primary source; only fill missing fields.
        if not cfg.speech_key.strip():
            cfg.speech_key = _first_env("AZURE_SPEECH_KEY", "SPEECH_KEY")
        if not cfg.speech_region.strip():
            cfg.speech_region = _first_env("AZURE_SPEECH_REGION", "SPEECH_REGION")
        return cfg

    if not path.exists():
        return _apply_env_defaults(PersonalVoiceConfig())

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        return _apply_env_defaults(PersonalVoiceConfig())

    return _apply_env_defaults(PersonalVoiceConfig.from_dict(data))


def save_personal_voice_config(
    config: PersonalVoiceConfig, path: Path = DEFAULT_CONFIG_PATH
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)


def build_personal_voice_ssml(
    *,
    text: str,
    speaker_profile_id: str,
    voice_name: str,
    language: str,
) -> str:
    """Build SSML for Personal Voice synthesis.

    The `mstts:ttsembedding` tag is what applies the Personal Voice speaker profile.
    """

    safe_text = xml_escape(text)
    safe_profile = xml_escape(speaker_profile_id)
    safe_voice = xml_escape(voice_name)
    safe_lang = xml_escape(language)

    inner = f"<lang xml:lang='{safe_lang}'>{safe_text}</lang>"

    # Keep this in a predictable, SDK-friendly format.
    return (
        "<speak version='1.0' "
        "xmlns='http://www.w3.org/2001/10/synthesis' "
        f"xml:lang='{safe_lang}' "
        "xmlns:mstts='http://www.w3.org/2001/mstts'>"
        f"<voice name='{safe_voice}'>"
        f"<mstts:ttsembedding speakerProfileId='{safe_profile}'>"
        f"{inner}"
        "</mstts:ttsembedding>"
        "</voice>"
        "</speak>"
    )


def _import_speechsdk():
    try:
        import azure.cognitiveservices.speech as speechsdk  # type: ignore

        return speechsdk
    except Exception:
        return None


def synthesize_personal_voice_to_wave_file(
    *,
    text: str,
    config: PersonalVoiceConfig,
    output_file_path: Path = DEFAULT_OUTPUT_WAV_PATH,
    enable_word_boundary_events: bool = False,
    log_ssml_to_console: bool = False,
    speechsdk=None,
) -> dict[str, Any]:
    """Synthesize text to a WAV file using Personal Voice.

    Returns a dict (never raises for SDK failures) shaped for easy UI consumption.
    """

    try:
        config.validate_for_synthesis()
        if not text.strip():
            return {"ok": False, "error": "Text is empty."}

        selected_profile = config.get_selected_profile()
        if not selected_profile:
            return {"ok": False, "error": "No speaker profile selected."}

        logger.info(
            "Personal Voice synth start | region=%s voice=%s lang=%s speaker_profile_id=%s output=%s key=%s",
            config.speech_region,
            config.voice_name,
            config.language,
            selected_profile.speaker_profile_id,
            output_file_path.as_posix(),
            _mask_secret(config.speech_key),
        )

        sdk = speechsdk or _import_speechsdk()
        if sdk is None:
            return {
                "ok": False,
                "error": "Azure Speech SDK is not installed.",
                "hint": "Add dependency 'azure-cognitiveservices-speech' and restart the app.",
            }

        output_file_path.parent.mkdir(parents=True, exist_ok=True)

        speech_config = sdk.SpeechConfig(
            subscription=config.speech_key, region=config.speech_region
        )
        speech_config.set_speech_synthesis_output_format(
            sdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm
        )

        logger.info("Personal Voice output format set: Riff24Khz16BitMonoPcm")

        file_config = sdk.audio.AudioOutputConfig(filename=str(output_file_path))
        synthesizer = sdk.SpeechSynthesizer(speech_config=speech_config, audio_config=file_config)

        word_boundaries: list[dict[str, Any]] = []
        if enable_word_boundary_events:

            def _on_word_boundary(evt):
                word_boundaries.append(
                    {
                        "text": getattr(evt, "text", ""),
                        "audio_offset_ms": getattr(evt, "audio_offset", 0) / 10000,
                        "duration_ms": getattr(evt, "duration", 0) / 10000,
                    }
                )

            synthesizer.synthesis_word_boundary.connect(_on_word_boundary)

        ssml = build_personal_voice_ssml(
            text=text,
            speaker_profile_id=selected_profile.speaker_profile_id,
            voice_name=config.voice_name,
            language=config.language,
        )

        if log_ssml_to_console:
            logger.info("Personal Voice SSML:\n%s", ssml)

        result = synthesizer.speak_ssml_async(ssml).get()

        if result.reason == sdk.ResultReason.SynthesizingAudioCompleted:
            logger.info(
                "Personal Voice synth completed | result_id=%s output=%s",
                getattr(result, "result_id", None),
                output_file_path.as_posix(),
            )
            return {
                "ok": True,
                "output_file_path": str(output_file_path),
                "result_id": getattr(result, "result_id", None),
                "word_boundaries": word_boundaries,
                "ssml": ssml if log_ssml_to_console else None,
            }

        if result.reason == sdk.ResultReason.Canceled:
            details = getattr(result, "cancellation_details", None)
            logger.error(
                "Personal Voice synth canceled | result_id=%s reason=%s details=%s",
                getattr(result, "result_id", None),
                getattr(details, "reason", None),
                getattr(details, "error_details", None),
            )
            return {
                "ok": False,
                "error": "Speech synthesis canceled.",
                "cancellation_reason": getattr(details, "reason", None),
                "error_details": getattr(details, "error_details", None),
                "result_id": getattr(result, "result_id", None),
                "ssml": ssml if log_ssml_to_console else None,
            }

        logger.error(
            "Personal Voice synth unexpected reason | reason=%s result_id=%s",
            getattr(result, "reason", None),
            getattr(result, "result_id", None),
        )
        return {
            "ok": False,
            "error": f"Unexpected synthesis result reason: {getattr(result, 'reason', None)}",
            "result_id": getattr(result, "result_id", None),
            "ssml": ssml if log_ssml_to_console else None,
        }

    except Exception as e:
        logger.exception("Personal Voice synth failed")
        return {"ok": False, "error": str(e)}
