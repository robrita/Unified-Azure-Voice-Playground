import sys

import streamlit as st
from dotenv import load_dotenv

sys.path.append("..")
from helpers.utils import render_sidebar

# Load environment variables
load_dotenv()


def main():
    # Render shared sidebar navigation
    render_sidebar()

    # Page Title
    st.title("💰 Azure Speech Service Pricing")
    st.markdown(
        """
    <div style="text-align: center; margin-bottom: 2rem;">
        <p style="font-size: 1.2rem; color: var(--text-secondary);">
            Official pricing information for Azure AI Speech Service features
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Create three columns for the pricing cards
    col1, col2, col3 = st.columns(3, gap="large")

    # Neural Text-to-Speech Card
    with col1.container(key="container1"):
        st.subheader("Neural Text-to-Speech")
        st.markdown("""
        High-quality neural voices with natural-sounding speech synthesis for various scenarios.
        """)

        st.markdown("#### Features")
        st.markdown("""
        - 400+ neural voices
        - 140+ languages/locales
        - SSML customization
        - Prosody controls
        """)

        st.link_button(
            "View Pricing →",
            "https://azure.microsoft.com/en-us/pricing/details/cognitive-services/speech-services/",
            width="stretch",
        )

    # Personal Voice Card
    with col2.container(key="container2"):
        st.subheader("Personal Voice")
        st.markdown("""
        Create custom neural voices using your own voice samples for personalized text-to-speech experiences.
        """)

        st.markdown("#### Features")
        st.markdown("""
        - Custom voice creation
        - Personal voice cloning
        - Speaker profile management
        - Consent verification
        """)

        st.link_button(
            "View Pricing →",
            "https://azure.microsoft.com/en-us/pricing/details/cognitive-services/speech-services/",
            width="stretch",
        )

    # Custom Neural Voice Card
    with col3.container(key="container3"):
        st.subheader("Custom Neural Voice")
        st.markdown("""
        Professional-grade custom voice models trained on extensive audio datasets for brand-specific voices.
        """)

        st.markdown("#### Features")
        st.markdown("""
        - Enterprise voice training
        - Multi-style voices
        - Emotion & expressiveness
        - Advanced customization
        """)

        st.link_button(
            "View Pricing →",
            "https://azure.microsoft.com/en-us/pricing/details/cognitive-services/speech-services/",
            width="stretch",
        )

    # Additional Information Section
    st.markdown("---")
    st.subheader("📊 Speech Service Comparison")

    col_left, col_right = st.columns(2)

    with col_left:
        st.info("""
        **Neural TTS** is ideal for:
        - Standard voice applications
        - Quick implementation
        - Wide language support
        - Cost-effective at scale
        """)

    with col_right:
        st.info("""
        **Personal/Custom Voice** excels at:
        - Brand voice identity
        - Unique voice requirements
        - Personalized experiences
        - Professional applications
        """)

    # Footer with helpful links
    st.markdown("---")
    st.markdown(
        """
    <div style="text-align: center; margin-top: 2rem;">
        <p style="color: var(--text-secondary);">
            💡 <strong>Tip:</strong> Start with free tier (0.5M characters/month) to test Personal Voice<br>
            📚 Learn more: <a href="https://azure.microsoft.com/en-us/pricing/calculator/" target="_blank">Azure Pricing Calculator</a> |
            <a href="https://learn.microsoft.com/azure/ai-services/speech-service/personal-voice-overview" target="_blank">Personal Voice Documentation</a>
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
