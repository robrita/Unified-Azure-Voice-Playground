import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from utils.speech_personal_voice import (
    PersonalVoiceConfig,
    build_personal_voice_ssml,
    custom_voice_create_project,
    custom_voice_get_consent,
    custom_voice_get_operation,
    custom_voice_get_personal_voice,
    custom_voice_post_consent_from_file,
    custom_voice_post_personal_voice_from_files,
    load_personal_voice_config,
    save_personal_voice_config,
    synthesize_personal_voice_to_wave_file,
)


class _FakeSignal:
    def __init__(self):
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, evt):
        for cb in self._callbacks:
            cb(evt)


class _FakeCancellationDetails:
    def __init__(self, reason="Error", error_details="boom"):
        self.reason = reason
        self.error_details = error_details


class _FakeResult:
    def __init__(self, reason, result_id="rid-123", cancellation_details=None):
        self.reason = reason
        self.result_id = result_id
        self.cancellation_details = cancellation_details


class _FakeFuture:
    def __init__(self, get_result):
        self._get_result = get_result

    def get(self):
        return self._get_result()


class _FakeSpeechSDK:
    class SpeechSynthesisOutputFormat:
        Riff24Khz16BitMonoPcm = object()

    class ResultReason:
        SynthesizingAudioCompleted = "done"
        Canceled = "canceled"

    class SpeechConfig:
        def __init__(self, subscription, region):
            self.subscription = subscription
            self.region = region
            self.output_format = None

        def set_speech_synthesis_output_format(self, output_format):
            self.output_format = output_format

    class AudioOutputConfig:
        def __init__(self, filename):
            self.filename = filename

    def __init__(self, *, next_reason="done"):
        self._next_reason = next_reason
        self.audio = SimpleNamespace(AudioOutputConfig=_FakeSpeechSDK.AudioOutputConfig)

    class SpeechSynthesizer:
        def __init__(self, *, speech_config, audio_config):
            self.speech_config = speech_config
            self.audio_config = audio_config
            self.synthesis_word_boundary = _FakeSignal()
            self._next_reason = getattr(speech_config, "_next_reason", "done")

        def speak_ssml_async(self, ssml):
            # Simulate word boundary events.
            evt = type(
                "Evt",
                (),
                {"text": "Hello", "audio_offset": 10000, "duration": 20000},
            )
            self.synthesis_word_boundary.emit(evt)

            def _make_result():
                if self._next_reason == _FakeSpeechSDK.ResultReason.Canceled:
                    return _FakeResult(
                        _FakeSpeechSDK.ResultReason.Canceled,
                        cancellation_details=_FakeCancellationDetails(),
                    )

                # Write a minimal WAV header-ish payload so a file exists.
                Path(self.audio_config.filename).write_bytes(b"RIFF....WAVEfmt ")
                return _FakeResult(_FakeSpeechSDK.ResultReason.SynthesizingAudioCompleted)

            return _FakeFuture(_make_result)


class TestPersonalVoiceConfigPersistence:
    @pytest.mark.unit
    def test_save_and_load_roundtrip(self, tmp_path):
        from utils.speech_personal_voice import SpeakerProfile

        profile = SpeakerProfile(
            id="profile_1",
            name="Test Profile",
            speaker_profile_id="spid",
            creation_date="2026-01-12",
        )
        cfg = PersonalVoiceConfig(
            speech_key="k",
            speech_region="eastus",
            voice_name="DragonLatestNeural",
            language="en-US",
            profiles=[profile],
            selected_profile_id="profile_1",
        )

        path = tmp_path / ".conf" / "personal_voice_config.json"
        save_personal_voice_config(cfg, path)

        loaded = load_personal_voice_config(path)
        assert loaded.speech_key == "k"
        assert loaded.speech_region == "eastus"
        assert len(loaded.profiles) == 1
        assert loaded.profiles[0].speaker_profile_id == "spid"
        assert loaded.selected_profile_id == "profile_1"

        # Verify file contents are valid JSON dict.
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        assert data["speech_region"] == "eastus"
        assert "profiles" in data
        assert len(data["profiles"]) == 1


class TestPersonalVoiceSsml:
    @pytest.mark.unit
    def test_build_ssml_includes_profile_and_voice(self):
        ssml = build_personal_voice_ssml(
            text="Hello",
            speaker_profile_id="abc",
            voice_name="DragonLatestNeural",
            language="en-US",
        )

        assert "speakerProfileId='abc'" in ssml
        assert "<voice name='DragonLatestNeural'>" in ssml
        assert "<mstts:ttsembedding speakerProfileId='abc'>" in ssml

    @pytest.mark.unit
    def test_build_ssml_escapes_text(self):
        ssml = build_personal_voice_ssml(
            text='<hi>&"</hi>',
            speaker_profile_id="abc",
            voice_name="DragonLatestNeural",
            language="en-US",
        )

        assert "<hi>" not in ssml
        assert "&lt;hi&gt;" in ssml
        assert "&amp;" in ssml


class TestPersonalVoiceSynthesis:
    @pytest.mark.unit
    def test_synthesize_success_writes_output(self, tmp_path):
        from utils.speech_personal_voice import SpeakerProfile

        profile = SpeakerProfile(
            id="profile_1",
            name="Test Profile",
            speaker_profile_id="spid",
            creation_date="2026-01-12",
        )
        cfg = PersonalVoiceConfig(
            speech_key="k",
            speech_region="eastus",
            profiles=[profile],
            selected_profile_id="profile_1",
        )

        output = tmp_path / "out.wav"
        fake_sdk = _FakeSpeechSDK(
            next_reason=_FakeSpeechSDK.ResultReason.SynthesizingAudioCompleted
        )

        # Inject the next reason into the SpeechConfig created inside the function.
        original_speech_config = fake_sdk.SpeechConfig

        def _speech_config(subscription, region):
            sc = original_speech_config(subscription, region)
            sc._next_reason = fake_sdk._next_reason
            return sc

        fake_sdk.SpeechConfig = _speech_config

        result = synthesize_personal_voice_to_wave_file(
            text="Hello",
            config=cfg,
            output_file_path=output,
            enable_word_boundary_events=True,
            speechsdk=fake_sdk,
        )

        assert result["ok"] is True
        assert output.exists()
        assert result.get("word_boundaries")

    @pytest.mark.unit
    def test_synthesize_canceled_returns_error(self, tmp_path):
        from utils.speech_personal_voice import SpeakerProfile

        profile = SpeakerProfile(
            id="profile_1",
            name="Test Profile",
            speaker_profile_id="spid",
            creation_date="2026-01-12",
        )
        cfg = PersonalVoiceConfig(
            speech_key="k",
            speech_region="eastus",
            profiles=[profile],
            selected_profile_id="profile_1",
        )

        output = tmp_path / "out.wav"
        fake_sdk = _FakeSpeechSDK(next_reason=_FakeSpeechSDK.ResultReason.Canceled)

        original_speech_config = fake_sdk.SpeechConfig

        def _speech_config(subscription, region):
            sc = original_speech_config(subscription, region)
            sc._next_reason = fake_sdk._next_reason
            return sc

        fake_sdk.SpeechConfig = _speech_config

        result = synthesize_personal_voice_to_wave_file(
            text="Hello",
            config=cfg,
            output_file_path=output,
            speechsdk=fake_sdk,
        )

        assert result["ok"] is False
        assert "canceled" in result.get("error", "").lower()

    @pytest.mark.unit
    def test_synthesize_missing_config_returns_error_dict(self, tmp_path):
        cfg = PersonalVoiceConfig()
        output = tmp_path / "out.wav"

        result = synthesize_personal_voice_to_wave_file(
            text="Hello",
            config=cfg,
            output_file_path=output,
            speechsdk=_FakeSpeechSDK(),
        )

        assert result["ok"] is False
        assert "Missing required config values" in result.get("error", "")


class _FakeResponse:
    def __init__(self, status_code: int, json_body=None, text: str = "", headers=None):
        self.status_code = status_code
        self._json_body = json_body
        self.text = text
        self.headers = headers or {}

    def json(self):
        if isinstance(self._json_body, Exception):
            raise self._json_body
        return self._json_body


class _FakeRequests:
    def __init__(self):
        self.calls = []
        self.next_consent_post_status_code = 201

    def put(self, url, params=None, headers=None, json=None, timeout=None):
        self.calls.append(("PUT", url, params, headers, json))
        return _FakeResponse(201, {"id": "p1", "kind": "PersonalVoice"})

    def post(self, url, params=None, headers=None, data=None, files=None, timeout=None):
        self.calls.append(("POST", url, params, headers, data, files))
        if "/consents/" in url:
            if self.next_consent_post_status_code == 409:
                return _FakeResponse(409, {"raw": "Resource Id already exists."})

            return _FakeResponse(
                201,
                {"id": "c1", "status": "NotStarted"},
                headers={
                    "Operation-Id": "op-consent-1",
                    "Operation-Location": "https://eastus.api.cognitive.microsoft.com/customvoice/operations/op-consent-1?api-version=2024-02-01-preview",
                },
            )
        return _FakeResponse(
            201,
            {
                "id": "pv1",
                "speakerProfileId": "spid-123",
                "status": "NotStarted",
            },
            headers={
                "Operation-Id": "op-pv-1",
                "Operation-Location": "https://eastus.api.cognitive.microsoft.com/customvoice/operations/op-pv-1?api-version=2024-02-01-preview",
            },
        )

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append(("GET", url, params, headers))
        if "/consents/" in url:
            return _FakeResponse(200, {"id": "c1", "status": "Succeeded"})
        if "/personalvoices/" in url:
            return _FakeResponse(
                200,
                {
                    "id": "pv1",
                    "speakerProfileId": "spid-123",
                    "status": "Succeeded",
                },
            )
        return _FakeResponse(200, {"id": "op-1", "status": "Succeeded"})


class TestCustomVoicePersonalVoiceApi:
    @pytest.mark.unit
    def test_create_project_success(self):
        cfg = PersonalVoiceConfig(speech_key="k", speech_region="eastus")
        fake_http = _FakeRequests()

        result = custom_voice_create_project(
            config=cfg,
            project_id="p1",
            description="d",
            http=fake_http,
        )

        assert result["ok"] is True
        assert result["project"]["kind"] == "PersonalVoice"

    @pytest.mark.unit
    def test_post_consent_from_file_success(self, tmp_path):
        cfg = PersonalVoiceConfig(speech_key="k", speech_region="eastus")
        fake_http = _FakeRequests()

        consent_path = tmp_path / "consent.wav"
        consent_path.write_bytes(b"RIFF....WAVE")

        result = custom_voice_post_consent_from_file(
            config=cfg,
            consent_id="c1",
            project_id="p1",
            voice_talent_name="Jessica Smith",
            company_name="Contoso",
            locale="en-US",
            consent_audio_path=consent_path,
            http=fake_http,
        )

        assert result["ok"] is True
        assert result.get("operation_id") == "op-consent-1"

        # Verify we sent multipart with explicit audio content-type.
        method, url, params, headers, data, files = fake_http.calls[-1]
        assert method == "POST"
        assert "/consents/" in url
        assert isinstance(files, dict)
        assert "audiodata" in files
        filename, fileobj, content_type = files["audiodata"]
        assert filename.endswith(".wav")
        assert content_type == "audio/wav"

    @pytest.mark.unit
    def test_post_consent_from_file_conflict_uses_existing(self, tmp_path):
        cfg = PersonalVoiceConfig(speech_key="k", speech_region="eastus")
        fake_http = _FakeRequests()
        fake_http.next_consent_post_status_code = 409

        consent_path = tmp_path / "consent.wav"
        consent_path.write_bytes(b"RIFF....WAVE")

        result = custom_voice_post_consent_from_file(
            config=cfg,
            consent_id="c1",
            project_id="p1",
            voice_talent_name="Jessica Smith",
            company_name="Contoso",
            locale="en-US",
            consent_audio_path=consent_path,
            http=fake_http,
        )

        assert result["ok"] is True
        assert "consent" in result

        # And verify the direct GET helper works as expected.
        fetched = custom_voice_get_consent(config=cfg, consent_id="c1", http=fake_http)
        assert fetched["ok"] is True

    @pytest.mark.unit
    def test_create_personal_voice_from_files_returns_speaker_profile_id(self, tmp_path):
        cfg = PersonalVoiceConfig(speech_key="k", speech_region="eastus")
        fake_http = _FakeRequests()

        p1 = tmp_path / "p1.wav"
        p1.write_bytes(b"RIFF....WAVE")

        result = custom_voice_post_personal_voice_from_files(
            config=cfg,
            personal_voice_id="pv1",
            project_id="p1",
            consent_id="c1",
            prompt_audio_paths=[p1],
            http=fake_http,
        )

        assert result["ok"] is True
        assert result.get("speaker_profile_id") == "spid-123"
        assert result.get("operation_id") == "op-pv-1"

        # Verify we sent multipart with explicit audio content-type.
        method, url, params, headers, data, files = fake_http.calls[-1]
        assert method == "POST"
        assert "/personalvoices/" in url
        assert isinstance(files, list)
        assert files
        field_name, file_tuple = files[0]
        assert field_name == "audiodata"
        filename, fileobj, content_type = file_tuple
        assert filename.endswith(".wav")
        assert content_type == "audio/wav"

    @pytest.mark.unit
    def test_get_operation_success(self):
        cfg = PersonalVoiceConfig(speech_key="k", speech_region="eastus")
        fake_http = _FakeRequests()

        result = custom_voice_get_operation(config=cfg, operation_id="op-1", http=fake_http)
        assert result["ok"] is True
        assert result["operation"]["status"] == "Succeeded"

    @pytest.mark.unit
    def test_get_personal_voice_returns_speaker_profile_id(self):
        cfg = PersonalVoiceConfig(speech_key="k", speech_region="eastus")
        fake_http = _FakeRequests()

        result = custom_voice_get_personal_voice(
            config=cfg, personal_voice_id="pv1", http=fake_http
        )
        assert result["ok"] is True
        assert result.get("speaker_profile_id") == "spid-123"
