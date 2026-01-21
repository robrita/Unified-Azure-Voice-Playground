import json
import logging
import os
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

try:  # Optional dependency
    import azure.cognitiveservices.speech as speechsdk
except Exception:  # pragma: no cover
    speechsdk = None

import sys

sys.path.append("..")
from helpers.utils import render_sidebar

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_VOICES_PATH = Path("inputs") / "voice_gallery_voices.json"
TEMP_AUDIO_PATH = Path("outputs") / "temp" / "voice_gallery_preview.wav"


@st.cache_data
def load_voices(path: str = str(DEFAULT_VOICES_PATH)) -> list[dict[str, Any]]:
    """Load voices from JSON file. Uses st.cache_data for Streamlit-aware caching."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, list):
            logger.warning("Voice data is not a list. Path=%s", path)
            return []
        logger.info("Loaded %d voices from %s", len(data), path)
        return data
    except FileNotFoundError:
        logger.error("Voice data file not found: %s", path)
        return []
    except Exception as exc:  # pragma: no cover
        logger.exception("Failed to load voice data: %s", exc)
        return []


def apply_filters(
    df: pd.DataFrame,
    search_query: str = "",
    locale_filter: list[str] | None = None,
    gender_filter: list[str] | None = None,
    age_filter: list[str] | None = None,
) -> pd.DataFrame:
    filtered = df.copy()
    if search_query:
        q = search_query.lower()
        filtered = filtered[
            filtered["Voice Name"].str.lower().str.contains(q)
            | filtered["Description"].str.lower().str.contains(q)
        ]
    if locale_filter:
        filtered = filtered[filtered["Locale"].isin(locale_filter)]
    if gender_filter:
        filtered = filtered[filtered["Gender"].isin(gender_filter)]
    if age_filter:
        filtered = filtered[filtered["Age Group"].isin(age_filter)]
    return filtered


def build_ssml(
    voice_name: str, locale: str, text: str, pitch: float, rate: float, volume: float
) -> str:
    """Build SSML with proper namespaces for HD voices."""
    rate_pct = (rate - 1.0) * 100
    pitch_st = (pitch - 1.0) * 10
    volume_db = (volume - 1.0) * 10
    return f"""<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='https://www.w3.org/2001/mstts' xml:lang='{locale}'>
  <voice name='{voice_name}'>
    <prosody rate='{rate_pct:+.0f}%' pitch='{pitch_st:+.0f}st' volume='{volume_db:+.0f}dB'>
      {text}
    </prosody>
  </voice>
</speak>"""


def synthesize_speech(
    voice_name: str, text: str, endpoint: str, key: str, output_path: Path
) -> dict[str, Any]:
    """Synthesize speech using Azure Speech SDK with endpoint URL."""
    if speechsdk is None:
        return {"ok": False, "error": "azure-cognitiveservices-speech not installed"}

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        speech_config = speechsdk.SpeechConfig(subscription=key, endpoint=endpoint)
        speech_config.speech_synthesis_voice_name = voice_name
        audio_config = speechsdk.audio.AudioOutputConfig(filename=str(output_path))
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config, audio_config=audio_config
        )
        result = synthesizer.speak_text_async(text).get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            logger.info("Speech synthesized successfully to %s", output_path)
            return {"ok": True, "output_file_path": str(output_path)}
        if result.reason == speechsdk.ResultReason.Canceled:
            details = result.cancellation_details
            error_details = getattr(details, "error_details", "") or ""
            error_msg = error_details if error_details else str(details.reason)
            logger.warning("Synthesis canceled: %s - %s", details.reason, error_details)
            return {
                "ok": False,
                "error": error_msg,
                "reason": str(details.reason),
            }
        logger.warning("Synthesis failed: %s", result.reason)
        return {"ok": False, "error": str(result.reason)}
    except Exception as exc:  # pragma: no cover
        logger.exception("Synthesis failed with exception: %s", exc)
        return {"ok": False, "error": str(exc)}


def main() -> None:
    logger.info("Rendering Voice Gallery page")
    render_sidebar()

    st.title("🎙️ Azure Voice Gallery")
    st.markdown(
        """
    <div style="text-align: center; margin-bottom: 2rem;">
        <p style="font-size: 1.1rem; color: var(--text-secondary);">
            Browse Azure Dragon HD Omni voices, filter by locale & gender, tune prosody, and generate SSML.
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    voices_data = load_voices()
    if not voices_data:
        st.error("No voice data available. Check inputs/voice_gallery_voices.json.")
        logger.error("No voice data available to render page")
        return

    df = pd.DataFrame(voices_data)

    col_left, col_right = st.columns([1.1, 1], gap="large")

    with col_left:
        st.subheader("1️⃣ Filter Voices")
        with st.container(border=True):
            search_query = st.text_input(
                "Search",
                placeholder="Voice name or description",
                help="Case-insensitive search across voice name and description.",
            )
            locale_options = sorted(df["Locale"].unique())
            gender_options = sorted(df["Gender"].unique())
            age_options = sorted(df["Age Group"].unique())

            locale_filter = st.multiselect("Locale", options=locale_options, default=[])
            gender_filter = st.multiselect("Gender", options=gender_options, default=[])
            age_filter = st.multiselect("Age Group", options=age_options, default=[])

            filtered = apply_filters(
                df,
                search_query=search_query,
                locale_filter=locale_filter,
                gender_filter=gender_filter,
                age_filter=age_filter,
            )
            st.caption(f"{len(filtered)} voice(s) match your filters")
            logger.debug(
                "Filters applied: search=%s locale=%s gender=%s age=%s matches=%d",
                search_query,
                locale_filter,
                gender_filter,
                age_filter,
                len(filtered),
            )
            st.dataframe(
                filtered[["Voice Name", "Locale", "Gender", "Age Group", "Description"]],
                height=320,
                use_container_width=True,
            )

        st.subheader("2️⃣ Select Voice")
        with st.container(border=True):
            options = (
                filtered["Voice Name"].tolist() if len(filtered) else df["Voice Name"].tolist()
            )
            if not options:
                st.warning("No voices available.")
            else:
                selected_voice_name = st.selectbox(
                    "Voice", options=options, index=0, help="Voice name for SSML <voice name=...>"
                )
                selected_voice = next(
                    v for v in voices_data if v["Voice Name"] == selected_voice_name
                )

                st.info(
                    f"**Locale:** {selected_voice['Locale']}\n\n"
                    f"**Gender:** {selected_voice['Gender']}\n\n"
                    f"**Age Group:** {selected_voice['Age Group']}\n\n"
                    f"**Description:** {selected_voice['Description']}"
                )

    with col_right:
        st.subheader("3️⃣ Voice Settings")
        with st.container(border=True):
            pitch = st.slider("Pitch", min_value=0.5, max_value=2.0, value=1.0, step=0.1)
            rate = st.slider("Rate", min_value=0.5, max_value=2.0, value=1.0, step=0.1)
            volume = st.slider("Volume", min_value=0.5, max_value=2.0, value=1.0, step=0.1)

            text = st.text_area(
                "Text to speak",
                value="Hello, welcome to Azure AI Foundry!",
                height=160,
                placeholder="Type something to speak...",
            )

            # Build SSML dynamically from current settings
            ssml = None
            if "selected_voice_name" in locals():
                selected_voice = next(
                    v for v in voices_data if v["Voice Name"] == selected_voice_name
                )
                ssml = build_ssml(
                    voice_name=selected_voice["Voice Name"],
                    locale=selected_voice["Locale"],
                    text=text,
                    pitch=pitch,
                    rate=rate,
                    volume=volume,
                )
                with st.expander("🔧 SSML Editor"):
                    st.code(ssml, language="xml")

        st.subheader("4️⃣ Voice Synthesis")
        with st.container(border=True):
            endpoint = os.environ.get("AZURE_SPEECH_ENDPOINT", "")
            key = os.environ.get("AZURE_SPEECH_KEY", "")
            if not endpoint or not key:
                st.info(
                    "Set AZURE_SPEECH_ENDPOINT and AZURE_SPEECH_KEY in your .env to enable synthesis."
                )
            elif speechsdk is None:
                st.warning("Install azure-cognitiveservices-speech to synthesize audio.")
            elif ssml is None:
                st.info("Select a voice to synthesize.")
            else:
                if st.button("🔊 Synthesize Voice", use_container_width=True):
                    with st.spinner("Synthesizing..."):
                        result = synthesize_speech(
                            voice_name=selected_voice_name,
                            text=text,
                            endpoint=endpoint,
                            key=key,
                            output_path=TEMP_AUDIO_PATH,
                        )
                    if result.get("ok"):
                        st.success("✅ Audio synthesized!")
                        st.audio(result.get("output_file_path"), format="audio/wav")
                    else:
                        st.error(f"❌ Synthesis failed: {result.get('error')}")
                        if result.get("reason"):
                            st.caption(f"Reason: {result.get('reason')}")

    st.markdown("---")
    st.subheader("💡 Notes")
    st.info(
        """
- Voices shown are Dragon HD Omni samples; expand this list with OpenAI / Azure voice catalogs.
- SSML uses <prosody> with rate (±%), pitch (±semitones), and volume (±dB).
- Expand the SSML Editor to view the generated markup based on your settings.
- Synthesis uses Speech SDK if env vars are set; otherwise copy SSML into Azure Speech Studio.
"""
    )


if __name__ == "__main__":
    main()
