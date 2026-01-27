"""Quick test script for Speech SDK authentication with Azure Identity."""

import os
import re

from dotenv import load_dotenv

load_dotenv()

region = os.environ.get("AZURE_SPEECH_REGION", "")
endpoint = os.environ.get("AZURE_SPEECH_ENDPOINT", "")
# For multi-service resources, you may need the resource ID
resource_id = os.environ.get("AZURE_SPEECH_RESOURCE_ID", "")

print(f"Region: {region}")
print(f"Endpoint: {endpoint}")
print(f"Resource ID: {resource_id or '(not set)'}")

# Test with Azure Identity (DefaultAzureCredential)
try:
    import azure.cognitiveservices.speech as speechsdk
    from azure.identity import DefaultAzureCredential

    # Get token using DefaultAzureCredential
    print("\nGetting token via DefaultAzureCredential...")
    credential = DefaultAzureCredential()
    token = credential.get_token("https://cognitiveservices.azure.com/.default")
    print(f"Token obtained! Length: {len(token.token)}")

    # For multi-service Cognitive Services with AAD auth,
    # we need to use the aad# format: "aad#<resource-id>#<access-token>"
    # If resource_id is not provided, try to construct it from endpoint

    if not resource_id:
        # Try to extract resource name from endpoint
        match = re.search(r"https://([^.]+)\.cognitiveservices", endpoint)
        if match:
            resource_name = match.group(1)
            print(f"\nExtracted resource name: {resource_name}")
            print("To use AAD auth with multi-service resources, set AZURE_SPEECH_RESOURCE_ID")
            print(
                "Format: /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.CognitiveServices/accounts/{name}"
            )

    # Test with standard approach first
    print("\n--- Test 1: Standard auth_token + region ---")
    config1 = speechsdk.SpeechConfig(auth_token=token.token, region=region)
    config1.speech_synthesis_voice_name = "en-US-JennyNeural"
    synth1 = speechsdk.SpeechSynthesizer(speech_config=config1, audio_config=None)
    result1 = synth1.speak_text_async("test").get()
    print(f"Result: {result1.reason}")
    if result1.reason == speechsdk.ResultReason.Canceled:
        details = result1.cancellation_details
        print(f"Error: {details.error_details}")
    elif result1.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print("SUCCESS!")
        exit(0)

    # Test with aad# format if resource_id is available
    if resource_id:
        print("\n--- Test 2: AAD token with resource ID ---")
        aad_token = f"aad#{resource_id}#{token.token}"
        config2 = speechsdk.SpeechConfig(auth_token=aad_token, region=region)
        config2.speech_synthesis_voice_name = "en-US-JennyNeural"
        synth2 = speechsdk.SpeechSynthesizer(speech_config=config2, audio_config=None)
        result2 = synth2.speak_text_async("test").get()
        print(f"Result: {result2.reason}")
        if result2.reason == speechsdk.ResultReason.Canceled:
            details = result2.cancellation_details
            print(f"Error: {details.error_details}")
        elif result2.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            print("SUCCESS!")
            exit(0)

    print("\n" + "=" * 60)
    print("TROUBLESHOOTING STEPS:")
    print("=" * 60)
    print("1. Verify region: Run in Azure Portal Cloud Shell:")
    print(
        "   az cognitiveservices account show --name r0bsea-resource --resource-group <your-rg> --query location"
    )
    print("")
    print(
        "2. Check RBAC role: Ensure you have 'Cognitive Services Speech User' or 'Cognitive Services User'"
    )
    print("")
    print("3. For multi-service resources, add to .env:")
    print(
        "   AZURE_SPEECH_RESOURCE_ID=/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.CognitiveServices/accounts/r0bsea-resource"
    )

except ImportError as e:
    print(f"Missing dependency: {e}")
except Exception as e:
    print(f"Error: {e}")
