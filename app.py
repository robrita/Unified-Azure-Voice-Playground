"""Azure Speech Personal Voice playground.

This page lets a user:
- Store Speech credentials + Personal Voice speaker profile id locally
- Enter text and synthesize audio using their already-created Personal Voice

It can also create a Personal Voice (speakerProfileId) using the Custom Voice API.
"""

import logging
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

sys.path.append("..")

from helpers.speech_personal_voice import (
    CUSTOM_VOICE_API_VERSION,
    DEFAULT_CONFIG_PATH,
    DEFAULT_OUTPUT_WAV_PATH,
    PersonalVoiceConfig,
    custom_voice_create_project,
    custom_voice_post_consent_from_file,
    custom_voice_post_personal_voice_from_files,
    custom_voice_wait_for_operation,
    load_personal_voice_config,
    save_personal_voice_config,
    synthesize_personal_voice_to_wave_file,
)
from helpers.utils import render_sidebar

load_dotenv()


logger = logging.getLogger(__name__)


def _initialize_state() -> None:
    if "pv_config" not in st.session_state:
        st.session_state.pv_config = load_personal_voice_config().to_dict()

    # Ensure widget keys exist early so the "Create" section (rendered above the
    # configuration section) can still access Speech credentials.
    cfg_dict = st.session_state.pv_config
    if "pv_speech_region" not in st.session_state:
        st.session_state.pv_speech_region = str(cfg_dict.get("speech_region", ""))
    if "pv_speech_key" not in st.session_state:
        st.session_state.pv_speech_key = str(cfg_dict.get("speech_key", ""))
    if "pv_voice_name" not in st.session_state:
        st.session_state.pv_voice_name = str(cfg_dict.get("voice_name", "DragonLatestNeural"))
    if "pv_language" not in st.session_state:
        st.session_state.pv_language = str(cfg_dict.get("language", "en-US"))
    if "pv_selected_profile_id" not in st.session_state:
        st.session_state.pv_selected_profile_id = str(cfg_dict.get("selected_profile_id", ""))

    if "pv_text" not in st.session_state:
        st.session_state.pv_text = "Hello! This is a Personal Voice synthesis test."

    if "pv_last_result" not in st.session_state:
        st.session_state.pv_last_result = None

    if "pv_create_last_result" not in st.session_state:
        st.session_state.pv_create_last_result = None

    # Create-flow widgets (use explicit keys + session_state so values persist
    # even if the user doesn't click 'Save Config').
    if "pv_create_project_id" not in st.session_state:
        st.session_state.pv_create_project_id = str(cfg_dict.get("personal_voice_project_id", ""))
    if "pv_create_consent_id" not in st.session_state:
        st.session_state.pv_create_consent_id = str(cfg_dict.get("personal_voice_consent_id", ""))
    if "pv_create_personal_voice_id" not in st.session_state:
        st.session_state.pv_create_personal_voice_id = str(cfg_dict.get("personal_voice_id", ""))
    if "pv_create_consent_locale" not in st.session_state:
        st.session_state.pv_create_consent_locale = str(
            cfg_dict.get("personal_voice_consent_locale", "en-US")
        )
    if "pv_create_voice_talent_name" not in st.session_state:
        st.session_state.pv_create_voice_talent_name = str(
            cfg_dict.get("personal_voice_voice_talent_name", "")
        )
    if "pv_create_company_name" not in st.session_state:
        st.session_state.pv_create_company_name = str(
            cfg_dict.get("personal_voice_company_name", "")
        )
    if "pv_create_api_version" not in st.session_state:
        st.session_state.pv_create_api_version = str(
            cfg_dict.get("custom_voice_api_version", CUSTOM_VOICE_API_VERSION)
        )


def _get_config_from_state():
    data = st.session_state.get("pv_config", {})
    if not isinstance(data, dict):
        data = {}
    return PersonalVoiceConfig.from_dict(data)


def _persist_config_to_state(cfg: PersonalVoiceConfig) -> None:
    st.session_state.pv_config = cfg.to_dict()


def _build_personal_voice_config(**kwargs):
    allowed = getattr(PersonalVoiceConfig, "__dataclass_fields__", {})
    safe_kwargs = {k: v for k, v in kwargs.items() if k in allowed}
    return PersonalVoiceConfig(**safe_kwargs)


def main() -> None:
    render_sidebar()

    st.title("🎤 Azure Personal Voice Playground")
    st.markdown(
        """
    <div style="text-align: center; margin-bottom: 2rem;">
        <p style="font-size: 1.1rem; color: var(--text-secondary);">
            Configure Azure Speech Personal Voice and synthesize text to audio.
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    _initialize_state()

    col_left, col_right = st.columns([1, 1.2], gap="large")

    with col_left:
        st.subheader("0️⃣ Configuration")

        with st.container(border=True):
            st.caption(
                "Credentials are saved locally to: "
                f"`{DEFAULT_CONFIG_PATH.as_posix()}` (gitignored)."
            )
            cfg_dict = st.session_state.pv_config

            st.text_input(
                "Speech region",
                value=str(cfg_dict.get("speech_region", "")),
                placeholder="e.g., eastus",
                help="Azure Speech resource region (same as your Speech resource).",
                key="pv_speech_region",
            )

            st.text_input(
                "Speech key",
                value=str(cfg_dict.get("speech_key", "")),
                placeholder="Your Speech subscription key",
                type="password",
                help="Stored locally in .conf/personal_voice_config.json.",
                key="pv_speech_key",
            )

            st.text_input(
                "Base voice name",
                value=str(cfg_dict.get("voice_name", "DragonLatestNeural")),
                placeholder="DragonLatestNeural",
                help="Voice name used in SSML <voice name='...'>.",
                key="pv_voice_name",
            )

            st.text_input(
                "Language",
                value=str(cfg_dict.get("language", "en-US")),
                placeholder="en-US",
                help="SSML language (xml:lang).",
                key="pv_language",
            )

            btn_col1, btn_col2 = st.columns(2, gap="medium")
            with btn_col1:
                if st.button("💾 Save Config", width="stretch"):
                    cfg = _get_config_from_state()
                    cfg.speech_region = str(st.session_state.get("pv_speech_region", ""))
                    cfg.speech_key = str(st.session_state.get("pv_speech_key", ""))
                    cfg.voice_name = str(st.session_state.get("pv_voice_name", ""))
                    cfg.language = str(st.session_state.get("pv_language", ""))
                    save_personal_voice_config(cfg)
                    _persist_config_to_state(cfg)
                    st.success("✅ Config saved to disk")

            with btn_col2:
                if st.button("🔄 Reload From Disk", width="stretch"):
                    reloaded_cfg = load_personal_voice_config()
                    _persist_config_to_state(reloaded_cfg)
                    st.success("✅ Config reloaded from disk")
                    st.rerun()

        st.subheader("1️⃣ Create Personal Voice")

        with st.container(border=True):
            st.caption(
                "Creates a Personal Voice speaker profile id via the Custom Voice API. "
                "This feature is not available in Speech Playground."
            )

            project_id = st.text_input(
                "Project id",
                placeholder="e.g., personal-voice-project-1",
                help="Custom Voice project id (kind=PersonalVoice).",
                key="pv_create_project_id",
            )

            consent_id = st.text_input(
                "Consent id",
                placeholder="e.g., personal-voice-consent-1",
                help="Consent id for the recorded verbal statement audio.",
                key="pv_create_consent_id",
            )

            personal_voice_id = st.text_input(
                "Personal voice id",
                placeholder="e.g., personal-voice-1",
                help="Personal voice id that you choose (speakerProfileId is generated).",
                key="pv_create_personal_voice_id",
            )

            consent_locale = st.text_input(
                "Consent locale",
                placeholder="en-US",
                help="Locale of the consent statement audio (BCP-47).",
                key="pv_create_consent_locale",
            )

            voice_talent_name = st.text_input(
                "Voice talent name",
                placeholder="First Last",
                help="Must match the name spoken in the consent audio.",
                key="pv_create_voice_talent_name",
            )

            company_name = st.text_input(
                "Company name",
                placeholder="Contoso",
                help="Must match the company name spoken in the consent audio.",
                key="pv_create_company_name",
            )

            api_version = st.text_input(
                "Custom Voice API version",
                help="Defaults to the documented preview version.",
                key="pv_create_api_version",
            )

            consent_audio = st.file_uploader(
                "Consent audio (wav/mp3)",
                type=["wav", "mp3"],
                help="Recorded verbal consent statement audio.",
                key="pv_consent_audio",
            )

            prompt_audios = st.file_uploader(
                "Prompt audio (5-90s, wav/mp3) — you can upload multiple",
                type=["wav", "mp3"],
                accept_multiple_files=True,
                help="Clean prompt audio from the same speaker.",
                key="pv_prompt_audios",
            )

            speech_region_now = str(st.session_state.get("pv_speech_region", "")).strip()
            speech_key_now = str(st.session_state.get("pv_speech_key", "")).strip()
            missing_speech_creds = not speech_region_now or not speech_key_now
            if missing_speech_creds:
                st.info(
                    "Set `Speech region` + `Speech key` in **0️⃣ Configuration** before creating a "
                    "Personal Voice. You can also set env vars `AZURE_SPEECH_REGION` and "
                    "`AZURE_SPEECH_KEY` in your `.env` file."
                )

            create_col1, create_col2 = st.columns(2, gap="medium")
            with create_col1:
                create_all = st.button(
                    "🧪 Create (Project + Consent + Voice)",
                    width="stretch",
                    disabled=missing_speech_creds,
                )
            with create_col2:
                if st.button("🧹 Clear Create Result", width="stretch"):
                    st.session_state.pv_create_last_result = None
                    st.rerun()

            if create_all:
                # Read from session_state to ensure we're using the persisted widget values.
                project_id = str(st.session_state.get("pv_create_project_id", project_id))
                consent_id = str(st.session_state.get("pv_create_consent_id", consent_id))
                personal_voice_id = str(
                    st.session_state.get("pv_create_personal_voice_id", personal_voice_id)
                )
                consent_locale = str(
                    st.session_state.get("pv_create_consent_locale", consent_locale)
                )
                voice_talent_name = str(
                    st.session_state.get("pv_create_voice_talent_name", voice_talent_name)
                )
                company_name = str(st.session_state.get("pv_create_company_name", company_name))
                api_version = str(st.session_state.get("pv_create_api_version", api_version))

                cfg = _get_config_from_state()
                cfg.custom_voice_api_version = api_version
                cfg.personal_voice_project_id = project_id
                cfg.personal_voice_consent_id = consent_id
                cfg.personal_voice_id = personal_voice_id
                cfg.personal_voice_consent_locale = consent_locale
                cfg.personal_voice_voice_talent_name = voice_talent_name
                cfg.personal_voice_company_name = company_name

                # Pull Speech creds from the config widgets (even if user didn't hit Save).
                cfg.speech_region = str(st.session_state.get("pv_speech_region", cfg.speech_region))
                cfg.speech_key = str(st.session_state.get("pv_speech_key", cfg.speech_key))
                _persist_config_to_state(cfg)

                if not cfg.speech_key.strip() or not cfg.speech_region.strip():
                    st.error("❌ Missing Speech key or region.")
                    return

                required_fields = {
                    "Project id": project_id,
                    "Consent id": consent_id,
                    "Personal voice id": personal_voice_id,
                    "Consent locale": consent_locale,
                    "Voice talent name": voice_talent_name,
                    "Company name": company_name,
                }
                missing = [
                    name for name, value in required_fields.items() if not str(value).strip()
                ]
                if missing:
                    st.error(f"❌ Missing required field(s): {', '.join(missing)}")
                    return

                if consent_audio is None:
                    st.error("❌ Consent audio file is required.")
                    return

                if not prompt_audios:
                    st.error("❌ At least one prompt audio file is required.")
                    return

                temp_dir = Path("outputs") / "temp" / "personal_voice_create"
                temp_dir.mkdir(parents=True, exist_ok=True)

                def _uploaded_ext(uploaded):
                    """Get file extension from uploaded file."""
                    if hasattr(uploaded, "name"):
                        return uploaded.name.split(".")[-1].lower()
                    return "wav"

                consent_path = temp_dir / f"personal_voice_consent.{_uploaded_ext(consent_audio)}"
                consent_path.write_bytes(consent_audio.getvalue())

                prompt_paths = []
                for idx, up in enumerate(prompt_audios, start=1):
                    prompt_path = temp_dir / f"prompt_{idx}.{_uploaded_ext(up)}"
                    prompt_path.write_bytes(up.getvalue())
                    prompt_paths.append(prompt_path)

                with st.spinner("Creating project..."):
                    project_result = custom_voice_create_project(
                        config=cfg,
                        project_id=project_id,
                    )
                if not project_result.get("ok"):
                    st.error(
                        f"❌ Project creation failed: {project_result.get('error', 'Unknown')}"
                    )
                    st.session_state.pv_create_last_result = project_result
                    return

                with st.spinner("Uploading consent..."):
                    consent_result = custom_voice_post_consent_from_file(
                        config=cfg,
                        consent_id=consent_id,
                        project_id=project_id,
                        voice_talent_name=voice_talent_name,
                        company_name=company_name,
                        locale=consent_locale,
                        consent_audio_path=consent_path,
                    )
                if not consent_result.get("ok"):
                    st.error(f"❌ Consent upload failed: {consent_result.get('error', 'Unknown')}")
                    st.session_state.pv_create_last_result = consent_result
                    return

                with st.spinner("Creating Personal Voice..."):
                    pv_result = custom_voice_post_personal_voice_from_files(
                        config=cfg,
                        personal_voice_id=personal_voice_id,
                        project_id=project_id,
                        consent_id=consent_id,
                        prompt_audio_paths=prompt_paths,
                    )

                if pv_result.get("ok"):
                    speaker_profile_id = pv_result.get("speaker_profile_id", "")
                    operation_id = pv_result.get("operation_id", "")

                    with st.spinner("Waiting for operation to complete..."):
                        wait_result = custom_voice_wait_for_operation(
                            config=cfg,
                            operation_id=operation_id,
                        )

                    if wait_result.get("ok"):
                        st.success(
                            f"✅ Personal Voice created! Speaker Profile ID: {speaker_profile_id}"
                        )

                        # Add profile with automatic naming
                        profile_name = voice_talent_name or f"Profile {personal_voice_id}"
                        cfg.add_profile(name=profile_name, speaker_profile_id=speaker_profile_id)

                        # Save all creation info to config JSON
                        cfg.custom_voice_api_version = api_version
                        cfg.personal_voice_project_id = project_id
                        cfg.personal_voice_consent_id = consent_id
                        cfg.personal_voice_id = personal_voice_id
                        cfg.personal_voice_consent_locale = consent_locale
                        cfg.personal_voice_voice_talent_name = voice_talent_name
                        cfg.personal_voice_company_name = company_name

                        # Persist to state and save to disk
                        _persist_config_to_state(cfg)
                        save_personal_voice_config(cfg)

                        st.success(
                            f"✅ Profile '{profile_name}' saved to {DEFAULT_CONFIG_PATH.as_posix()}"
                        )
                        st.session_state.pv_create_last_result = {
                            "ok": True,
                            "speaker_profile_id": speaker_profile_id,
                            "profile_name": profile_name,
                        }
                    else:
                        st.error(f"❌ Operation wait failed: {wait_result.get('error', 'Unknown')}")
                        st.session_state.pv_create_last_result = wait_result
                else:
                    st.error(
                        f"❌ Personal Voice creation failed: {pv_result.get('error', 'Unknown')}"
                    )
                    st.session_state.pv_create_last_result = pv_result

            create_result = st.session_state.pv_create_last_result
            if isinstance(create_result, dict):
                with st.expander("📋 Create Result Details", expanded=False):
                    st.json(create_result)

    with col_right:
        st.subheader("2️⃣ Synthesize Text")

        with st.container(border=True):
            # Profile selector
            cfg = _get_config_from_state()
            profile_choices = cfg.get_profile_choices()

            if not profile_choices:
                st.warning(
                    "⚠️ No speaker profiles found. Create a Personal Voice first in section 1️⃣."
                )
            else:
                # Build options dict for selectbox
                profile_options = dict(profile_choices)

                # Find current selection
                current_profile_id = st.session_state.get(
                    "pv_selected_profile_id", cfg.selected_profile_id
                )
                current_index = 0
                for idx, (_display, pid) in enumerate(profile_choices):
                    if pid == current_profile_id:
                        current_index = idx
                        break

                selected_display = st.selectbox(
                    "Speaker Profile",
                    options=list(profile_options.keys()),
                    index=current_index,
                    help="Select which Personal Voice profile to use for synthesis.",
                    key="pv_profile_selector",
                )

                # Update selected profile ID in session state
                if selected_display:
                    st.session_state.pv_selected_profile_id = profile_options[selected_display]
                    cfg.selected_profile_id = profile_options[selected_display]
                    _persist_config_to_state(cfg)

            st.session_state.pv_text = st.text_area(
                "Text to synthesize",
                value=st.session_state.pv_text,
                height=160,
                placeholder="Type something to speak...",
            )

            enable_word_boundary_events = st.toggle(
                "Capture word boundary events (debug)",
                value=False,
                help="Collect word boundary events if the selected voice supports it.",
            )

            log_ssml_to_console = st.toggle(
                "Log SSML to console (debug)",
                value=False,
                help="Writes the generated SSML to the server console for easier debugging.",
            )

            output_path = st.text_input(
                "Output WAV path",
                value=DEFAULT_OUTPUT_WAV_PATH.as_posix(),
                help="Local output file path. Keep it under outputs/temp/ to avoid clutter.",
            )

            synth_col1, synth_col2 = st.columns([1, 1], gap="medium")
            with synth_col1:
                do_synthesize = st.button("🔊 Synthesize", width="stretch")
            with synth_col2:
                if st.button("🧹 Clear Result", width="stretch"):
                    st.session_state.pv_last_result = None
                    st.rerun()

            if do_synthesize:
                # Collect all config from session state
                cfg = _get_config_from_state()
                cfg.speech_region = str(st.session_state.get("pv_speech_region", ""))
                cfg.speech_key = str(st.session_state.get("pv_speech_key", ""))
                cfg.voice_name = str(st.session_state.get("pv_voice_name", ""))
                cfg.language = str(st.session_state.get("pv_language", ""))
                cfg.selected_profile_id = str(
                    st.session_state.get("pv_selected_profile_id", cfg.selected_profile_id)
                )

                if not cfg.speech_key.strip() or not cfg.speech_region.strip():
                    st.error("❌ Missing Speech key or region.")
                    return

                selected_profile = cfg.get_selected_profile()
                if not selected_profile:
                    st.error("❌ No speaker profile selected or profile not found.")
                    return

                with st.spinner("🎤 Synthesizing audio..."):
                    result = synthesize_personal_voice_to_wave_file(
                        text=st.session_state.pv_text,
                        config=cfg,
                        output_file_path=Path(output_path),
                        enable_word_boundary_events=enable_word_boundary_events,
                        log_ssml_to_console=log_ssml_to_console,
                    )

                st.session_state.pv_last_result = result

        result = st.session_state.pv_last_result
        if isinstance(result, dict):
            if result.get("ok"):
                st.success("✅ Audio synthesized successfully!")
                audio_file = result.get("output_file_path")
                if audio_file and Path(audio_file).exists():
                    st.audio(audio_file, format="audio/wav")
                    st.caption(f"💾 Saved to: `{audio_file}`")

                # Show processing info
                if result.get("processing_info"):
                    with st.expander("📊 Processing Details", expanded=False):
                        st.json(result.get("processing_info"))

            else:
                st.error(f"❌ Synthesis failed: {result.get('error', 'Unknown error')}")
                if result.get("details"):
                    with st.expander("📋 Error Details", expanded=False):
                        st.json(result.get("details"))

    st.markdown("---")
    st.subheader("💡 Notes")
    st.info(
        """
- Creating Personal Voice requires explicit user consent and uses the Custom Voice API.
- You still use the generated `speakerProfileId` for synthesis (via `mstts:ttsembedding`).
- If you see an SDK import error, install `azure-cognitiveservices-speech` (see pyproject.toml).
- The saved config contains secrets — keep it local and do not commit it.
"""
    )


if __name__ == "__main__":
    main()
