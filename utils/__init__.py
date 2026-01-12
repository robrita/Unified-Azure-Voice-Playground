import logging

import streamlit as st

# Configure logging
logger = logging.getLogger(__name__)

# Valid service names - must match app.py
VALID_SERVICE_NAMES = {
    "ADI-Template",
    "ADI-Neural",
    "Content-Understanding",
    "Mistral-Doc-AI",
    "GPT-4.1-Vision",
    "GPT-5-Vision",
}


def render_sidebar():
    """
    Render the common sidebar navigation for all pages in the Document Processing application.
    This function should be called on every page to maintain consistent navigation.
    """
    # Configure page
    st.set_page_config(
        page_title="Document Processing Dashboard",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.logo(
        "https://devblogs.microsoft.com/foundry/wp-content/uploads/sites/89/2025/03/ai-foundry.png",
        link="https://ai.azure.com/",
    )

    # Loading the CSS
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    with st.sidebar:
        with st.container(border=True):
            st.page_link("app.py", label="Personal Voice", icon="🎤")
            st.page_link("pages/pg3_Pricing.py", label="Pricing", icon="💰")

        st.image(
            "https://miro.medium.com/1*zBt3FbYHV2-CWcBnkYoQRA.png",
        )
        st.write("Powered by Azure AI Foundry.")


def keep_state(state_object, state_name):
    """
    Keep the Streamlit session state alive across page navigations.
    This is useful to maintain stateful data like uploaded files or user inputs.
    """
    if state_object:
        st.session_state[state_name] = state_object
    elif state_name in st.session_state:
        return True
    return False


def clean_temp_extraction_files() -> None:
    """
    Clean up all JSON files in the outputs/temp/ directory.
    This should be called before starting a new extraction batch.
    """
    from pathlib import Path

    temp_dir = Path("outputs/temp")

    try:
        if temp_dir.exists():
            json_files = list(temp_dir.glob("*.json"))
            for json_file in json_files:
                json_file.unlink()
                logger.debug(f"Deleted temp file: {json_file}")

            logger.info(f"Cleaned {len(json_files)} temp extraction file(s)")
        else:
            logger.debug("Temp directory does not exist, nothing to clean")

    except Exception as e:
        logger.error(f"Error cleaning temp files: {str(e)}", exc_info=True)
        st.warning(f"Failed to clean temp files: {str(e)}")


def save_extraction_to_json(
    file_name: str,
    service_name: str,
    pages_count: int,
    fields: dict,
    overall_confidence: float = None,
    processing_time: float = None,
) -> None:
    """
    Save extraction results to individual JSON file in outputs/temp/ directory.
    File naming: outputs/temp/<file_name>-<service_name>.json

    Args:
        file_name: Name of the processed file
        service_name: Name of the extraction service used
        pages_count: Number of pages in the document
        fields: Dictionary of extracted fields with confidence scores and content
        overall_confidence: Overall document confidence score (if None, defaults to 0.0)
        processing_time: Time taken to process the file in seconds (if None, defaults to 0.0)

    Raises:
        ValueError: If service_name is not in VALID_SERVICE_NAMES
    """
    import json
    from pathlib import Path

    # Validate service name
    if service_name not in VALID_SERVICE_NAMES:
        error_msg = (
            f"Invalid service name '{service_name}'. "
            f"Allowed: {', '.join(sorted(VALID_SERVICE_NAMES))}"
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info(
        f"Saving extraction results: file={file_name}, service={service_name}, "
        f"fields_count={len(fields) if fields else 0}"
    )

    try:
        # Ensure temp directory exists
        temp_dir = Path("outputs/temp")
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Build fields array with name, value, and confidence
        fields_array = []

        for field_name, field_data in fields.items():
            # Extract value from content (or fallback to value or empty string)
            value = field_data.get("content", field_data.get("value", ""))
            confidence = field_data.get("confidence", 0.0)

            fields_array.append(
                {"name": field_name, "value": value, "confidence": round(confidence, 3)}
            )

        # Use provided overall_confidence or default to 0.0
        document_confidence = (
            round(overall_confidence, 3) if overall_confidence is not None else 0.0
        )

        # Use provided processing_time or default to 0.0
        proc_time = round(processing_time, 3) if processing_time is not None else 0.0

        # Create result entry
        result_data = {
            "file_name": file_name,
            "service_name": service_name,
            "pages_count": pages_count,
            "document_confidence": document_confidence,
            "processing_time": proc_time,
            "fields": fields_array,
        }

        # Create filename: outputs/temp/<file_name>-<service_name>.json
        # Sanitize file_name to remove any path separators
        safe_file_name = Path(file_name).name
        temp_file_path = temp_dir / f"{safe_file_name}-{service_name}.json"

        # Save to temp file
        with open(temp_file_path, "w", encoding="utf-8") as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved temp result: {temp_file_path}")

    except Exception as e:
        logger.error(f"JSON save error: {file_name} | {service_name} | {str(e)}", exc_info=True)
        st.warning(f"Failed to save results to JSON: {str(e)}")
        print(f"Error details: {e}")


def consolidate_temp_extractions(
    output_file: str = "outputs/extract_results.json",
) -> int:
    """
    Consolidate all temporary extraction files from outputs/temp/ into the main results file.
    This function reads all JSON files from outputs/temp/, merges them with existing results
    (avoiding duplicates based on file_name + service_name), and saves to the output file.

    Args:
        output_file: Path to the consolidated results file (default: outputs/extract_results.json)

    Returns:
        Number of results consolidated

    Raises:
        Exception: If consolidation fails
    """
    import json
    from pathlib import Path

    try:
        temp_dir = Path("outputs/temp")
        output_path = Path(output_file)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing results or create new structure
        if output_path.exists():
            with open(output_path, encoding="utf-8") as f:
                consolidated_data = json.load(f)
            logger.debug(f"Loaded existing consolidated file: {output_file}")
        else:
            consolidated_data = {"results": []}
            logger.debug(f"Creating new consolidated file: {output_file}")

        # Read all temp JSON files
        temp_files = list(temp_dir.glob("*.json"))
        logger.info(f"Found {len(temp_files)} temp file(s) to consolidate")

        consolidated_count = 0

        for temp_file in temp_files:
            try:
                with open(temp_file, encoding="utf-8") as f:
                    temp_data = json.load(f)

                # Extract file_name and service_name for duplicate checking
                file_name = temp_data.get("file_name")
                service_name = temp_data.get("service_name")

                if not file_name or not service_name:
                    logger.warning(f"Skipping invalid temp file: {temp_file}")
                    continue

                # Find existing entry with same file_name and service_name
                existing_index = None
                for idx, result in enumerate(consolidated_data["results"]):
                    if (
                        result.get("file_name") == file_name
                        and result.get("service_name") == service_name
                    ):
                        existing_index = idx
                        break

                if existing_index is not None:
                    # Update existing entry
                    consolidated_data["results"][existing_index] = temp_data
                    logger.debug(f"Updated existing entry: {file_name} | {service_name}")
                else:
                    # Append new entry
                    consolidated_data["results"].append(temp_data)
                    logger.debug(f"Added new entry: {file_name} | {service_name}")

                consolidated_count += 1

            except Exception as e:
                logger.error(f"Error reading temp file {temp_file}: {str(e)}", exc_info=True)
                continue

        # Save consolidated results
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(consolidated_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Consolidated {consolidated_count} result(s) into {output_file}")

        return consolidated_count

    except Exception as e:
        logger.error(f"Consolidation error: {str(e)}", exc_info=True)
        st.warning(f"Failed to consolidate results: {str(e)}")
        raise


def delete_temp_extraction_files() -> int:
    """
    Delete all temporary extraction JSON files from outputs/temp/ directory.
    This should be called after successful consolidation.

    Returns:
        Number of files deleted
    """
    from pathlib import Path

    try:
        temp_dir = Path("outputs/temp")

        if not temp_dir.exists():
            logger.debug("Temp directory does not exist, nothing to delete")
            return 0

        json_files = list(temp_dir.glob("*.json"))
        deleted_count = 0

        for json_file in json_files:
            try:
                json_file.unlink()
                logger.debug(f"Deleted temp file: {json_file}")
                deleted_count += 1
            except Exception as e:
                logger.error(f"Error deleting {json_file}: {str(e)}", exc_info=True)

        logger.info(f"Deleted {deleted_count} temp extraction file(s)")

        return deleted_count

    except Exception as e:
        logger.error(f"Error deleting temp files: {str(e)}", exc_info=True)
        return 0
