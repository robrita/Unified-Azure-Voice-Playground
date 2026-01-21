"""
Unit tests for utils.py module.

Tests the utility functions including save_extraction_to_json,
keep_state, and render_sidebar.
"""

import json
from unittest.mock import mock_open, patch


class TestSaveExtractionToJson:
    """Test suite for save_extraction_to_json function."""

    def test_save_extraction_creates_temp_file(self, tmp_path, monkeypatch):
        """Test saving extraction results creates temp JSON file."""
        from helpers.utils import save_extraction_to_json

        # Change to temp directory so outputs/temp will be created there
        monkeypatch.chdir(tmp_path)

        fields = {
            "tin": {"content": "123-456-789-00000", "confidence": 0.98},
            "taxpayerName": {"content": "Sample Corp", "confidence": 0.96},
        }

        save_extraction_to_json(
            file_name="test_file.png",
            service_name="ADI-Template",
            pages_count=1,
            fields=fields,
            overall_confidence=0.95,
            processing_time=2.5,
        )

        # Verify temp file was created
        temp_file = tmp_path / "outputs" / "temp" / "test_file.png-ADI-Template.json"
        assert temp_file.exists()

        # Verify content structure
        with open(temp_file, encoding="utf-8") as f:
            data = json.load(f)

        assert data["file_name"] == "test_file.png"
        assert data["service_name"] == "ADI-Template"
        assert data["pages_count"] == 1
        assert data["document_confidence"] == 0.95
        assert data["processing_time"] == 2.5

    def test_save_extraction_rounds_confidence_to_three_decimals(self, tmp_path, monkeypatch):
        """Test confidence scores are rounded to 3 decimal places."""
        from helpers.utils import save_extraction_to_json

        monkeypatch.chdir(tmp_path)

        fields = {
            "tin": {"content": "123-456-789-00000", "confidence": 0.987654321},
            "taxpayerName": {"content": "Sample Corp", "confidence": 0.123456789},
        }

        save_extraction_to_json(
            file_name="test_file.png",
            service_name="ADI-Template",
            pages_count=1,
            fields=fields,
            overall_confidence=0.956789,
            processing_time=2.567891,
        )

        temp_file = tmp_path / "outputs" / "temp" / "test_file.png-ADI-Template.json"
        with open(temp_file, encoding="utf-8") as f:
            data = json.load(f)

        # Check overall confidence rounded
        assert data["document_confidence"] == 0.957

        # Check processing time rounded
        assert data["processing_time"] == 2.568

        # Check field confidences rounded
        field_confidences = {field["name"]: field["confidence"] for field in data["fields"]}
        assert field_confidences["tin"] == 0.988
        assert field_confidences["taxpayerName"] == 0.123

    def test_save_extraction_with_none_confidence_defaults_to_zero(self, tmp_path, monkeypatch):
        """Test None confidence values default to 0.0."""
        from helpers.utils import save_extraction_to_json

        monkeypatch.chdir(tmp_path)

        fields = {"tin": {"content": "123-456-789-00000", "confidence": 0.98}}

        save_extraction_to_json(
            file_name="test_file.png",
            service_name="ADI-Template",
            pages_count=1,
            fields=fields,
            overall_confidence=None,
            processing_time=None,
        )

        temp_file = tmp_path / "outputs" / "temp" / "test_file.png-ADI-Template.json"
        with open(temp_file, encoding="utf-8") as f:
            data = json.load(f)

        assert data["document_confidence"] == 0.0
        assert data["processing_time"] == 0.0

    def test_save_extraction_handles_fields_with_value_key(self, tmp_path, monkeypatch):
        """Test extraction handles fields using 'value' instead of 'content'."""
        from helpers.utils import save_extraction_to_json

        monkeypatch.chdir(tmp_path)

        # Use 'value' key instead of 'content'
        fields = {
            "tin": {"value": "123-456-789-00000", "confidence": 0.98},
            "taxpayerName": {"value": "Sample Corp", "confidence": 0.96},
        }

        save_extraction_to_json(
            file_name="test_file.png",
            service_name="ADI-Template",
            pages_count=1,
            fields=fields,
            overall_confidence=0.95,
            processing_time=2.5,
        )

        temp_file = tmp_path / "outputs" / "temp" / "test_file.png-ADI-Template.json"
        with open(temp_file, encoding="utf-8") as f:
            data = json.load(f)

        # Verify values were extracted correctly
        field_values = {field["name"]: field["value"] for field in data["fields"]}
        assert field_values["tin"] == "123-456-789-00000"
        assert field_values["taxpayerName"] == "Sample Corp"

    def test_save_extraction_handles_missing_confidence_in_fields(self, tmp_path, monkeypatch):
        """Test extraction handles fields without confidence key."""
        from helpers.utils import save_extraction_to_json

        monkeypatch.chdir(tmp_path)

        # Fields without confidence
        fields = {
            "tin": {"content": "123-456-789-00000"},
            "taxpayerName": {"content": "Sample Corp"},
        }

        save_extraction_to_json(
            file_name="test_file.png",
            service_name="ADI-Template",
            pages_count=1,
            fields=fields,
            overall_confidence=0.95,
            processing_time=2.5,
        )

        temp_file = tmp_path / "outputs" / "temp" / "test_file.png-ADI-Template.json"
        with open(temp_file, encoding="utf-8") as f:
            data = json.load(f)

        # Verify confidence defaults to 0.0
        for field in data["fields"]:
            assert field["confidence"] == 0.0

    def test_save_extraction_creates_directory_if_not_exists(self, tmp_path, monkeypatch):
        """Test extraction creates temp directory if it doesn't exist."""
        from helpers.utils import save_extraction_to_json

        monkeypatch.chdir(tmp_path)

        fields = {"tin": {"content": "123-456-789-00000", "confidence": 0.98}}

        save_extraction_to_json(
            file_name="test_file.png",
            service_name="ADI-Template",
            pages_count=1,
            fields=fields,
            overall_confidence=0.95,
            processing_time=2.5,
        )

        # Verify directory and file were created
        temp_dir = tmp_path / "outputs" / "temp"
        assert temp_dir.exists()
        temp_file = temp_dir / "test_file.png-ADI-Template.json"
        assert temp_file.exists()

    @patch("streamlit.warning")
    def test_save_extraction_handles_json_write_error(self, mock_warning):
        """Test extraction handles errors when writing JSON file."""
        from helpers.utils import save_extraction_to_json

        fields = {"tin": {"content": "123-456-789-00000", "confidence": 0.98}}

        # Mock the open function to raise an exception
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            save_extraction_to_json(
                file_name="test_file.png",
                service_name="ADI-Template",
                pages_count=1,
                fields=fields,
                overall_confidence=0.95,
                processing_time=2.5,
            )

        # Verify warning was called
        mock_warning.assert_called_once()
        assert "Failed to save results to JSON" in mock_warning.call_args[0][0]


class TestConsolidateTempExtractions:
    """Test suite for consolidate_temp_extractions function."""

    def test_consolidate_creates_new_results_file(self, tmp_path, monkeypatch):
        """Test consolidation creates new results file when none exists."""
        from helpers.utils import consolidate_temp_extractions

        monkeypatch.chdir(tmp_path)

        # Create temp directory with test files
        temp_dir = tmp_path / "outputs" / "temp"
        temp_dir.mkdir(parents=True)
        output_file = tmp_path / "outputs" / "results.json"

        # Create temp files
        temp_file1 = temp_dir / "file1.pdf-ADI-Template.json"
        temp_file1.write_text(
            json.dumps(
                {
                    "file_name": "file1.pdf",
                    "service_name": "ADI-Template",
                    "pages_count": 1,
                    "document_confidence": 0.95,
                    "processing_time": 2.5,
                    "fields": [],
                }
            )
        )

        count = consolidate_temp_extractions("outputs/results.json")

        assert count == 1
        assert output_file.exists()

        with open(output_file) as f:
            data = json.load(f)

        assert len(data["results"]) == 1
        assert data["results"][0]["file_name"] == "file1.pdf"

    def test_consolidate_appends_to_existing_file(self, tmp_path, monkeypatch):
        """Test consolidation appends to existing results."""
        from helpers.utils import consolidate_temp_extractions

        monkeypatch.chdir(tmp_path)

        temp_dir = tmp_path / "outputs" / "temp"
        temp_dir.mkdir(parents=True)
        output_file = tmp_path / "outputs" / "results.json"

        # Create existing results file
        existing_data = {
            "results": [
                {
                    "file_name": "existing.pdf",
                    "service_name": "ADI-Neural",
                    "pages_count": 1,
                    "document_confidence": 0.90,
                    "processing_time": 1.5,
                    "fields": [],
                }
            ]
        }
        output_file.write_text(json.dumps(existing_data))

        # Create temp file
        temp_file = temp_dir / "new.pdf-ADI-Template.json"
        temp_file.write_text(
            json.dumps(
                {
                    "file_name": "new.pdf",
                    "service_name": "ADI-Template",
                    "pages_count": 1,
                    "document_confidence": 0.95,
                    "processing_time": 2.5,
                    "fields": [],
                }
            )
        )

        count = consolidate_temp_extractions("outputs/results.json")

        assert count == 1

        with open(output_file) as f:
            data = json.load(f)

        assert len(data["results"]) == 2


class TestCleanAndDeleteTempFiles:
    """Test suite for temp file cleanup functions."""

    def test_clean_temp_extraction_files(self, tmp_path, monkeypatch):
        """Test cleaning temp files before extraction."""
        from helpers.utils import clean_temp_extraction_files

        monkeypatch.chdir(tmp_path)

        temp_dir = tmp_path / "outputs" / "temp"
        temp_dir.mkdir(parents=True)

        # Create some temp files
        (temp_dir / "file1.json").write_text("{}")
        (temp_dir / "file2.json").write_text("{}")

        clean_temp_extraction_files()

        # Verify files are deleted
        assert not (temp_dir / "file1.json").exists()
        assert not (temp_dir / "file2.json").exists()

    def test_delete_temp_extraction_files(self, tmp_path, monkeypatch):
        """Test deleting temp files after consolidation."""
        from helpers.utils import delete_temp_extraction_files

        monkeypatch.chdir(tmp_path)

        temp_dir = tmp_path / "outputs" / "temp"
        temp_dir.mkdir(parents=True)

        # Create temp files
        (temp_dir / "file1.json").write_text("{}")
        (temp_dir / "file2.json").write_text("{}")

        count = delete_temp_extraction_files()

        assert count == 2
        assert not (temp_dir / "file1.json").exists()
        assert not (temp_dir / "file2.json").exists()

    @patch("streamlit.session_state", new_callable=dict)
    def test_keep_state_returns_true_when_key_exists(self, mock_session_state):
        """Test keep_state returns True when key already exists."""
        from helpers.utils import keep_state

        # Pre-populate session state
        mock_session_state["existing_key"] = "existing_value"

        result = keep_state(None, "existing_key")

        assert result is True
        assert mock_session_state["existing_key"] == "existing_value"

    @patch("streamlit.session_state", new_callable=dict)
    def test_keep_state_updates_existing_value(self, mock_session_state):
        """Test keep_state updates existing value when new value provided."""
        from helpers.utils import keep_state

        # Pre-populate session state
        mock_session_state["test_key"] = "old_value"

        result = keep_state("new_value", "test_key")

        assert mock_session_state["test_key"] == "new_value"
        assert result is False

    @patch("streamlit.session_state", new_callable=dict)
    def test_keep_state_handles_empty_string(self, mock_session_state):
        """Test keep_state treats empty string as falsy."""
        from helpers.utils import keep_state

        result = keep_state("", "test_key")

        assert "test_key" not in mock_session_state
        assert result is False

    @patch("streamlit.session_state", new_callable=dict)
    def test_keep_state_handles_zero(self, mock_session_state):
        """Test keep_state treats zero as falsy."""
        from helpers.utils import keep_state

        result = keep_state(0, "test_key")

        assert "test_key" not in mock_session_state
        assert result is False

    @patch("streamlit.session_state", new_callable=dict)
    def test_keep_state_handles_list(self, mock_session_state):
        """Test keep_state stores list values."""
        from helpers.utils import keep_state

        test_list = [1, 2, 3, 4, 5]
        result = keep_state(test_list, "list_key")

        assert mock_session_state["list_key"] == test_list
        assert result is False

    @patch("streamlit.session_state", new_callable=dict)
    def test_keep_state_handles_dict(self, mock_session_state):
        """Test keep_state stores dictionary values."""
        from helpers.utils import keep_state

        test_dict = {"key1": "value1", "key2": "value2"}
        result = keep_state(test_dict, "dict_key")

        assert mock_session_state["dict_key"] == test_dict
        assert result is False


class TestRenderSidebar:
    """Test suite for render_sidebar function."""

    @patch("streamlit.set_page_config")
    @patch("streamlit.logo")
    @patch("builtins.open", mock_open(read_data="body { color: red; }"))
    @patch("streamlit.markdown")
    @patch("streamlit.sidebar")
    def test_render_sidebar_configures_page(
        self, mock_sidebar, mock_markdown, mock_logo, mock_config
    ):
        """Test render_sidebar sets up page configuration."""
        from helpers.utils import render_sidebar

        render_sidebar()

        # Verify page config was called
        mock_config.assert_called_once_with(
            page_title="Document Processing Dashboard",
            page_icon="🚀",
            layout="wide",
            initial_sidebar_state="expanded",
        )

    @patch("streamlit.set_page_config")
    @patch("streamlit.logo")
    @patch("builtins.open", mock_open(read_data="body { color: red; }"))
    @patch("streamlit.markdown")
    @patch("streamlit.sidebar")
    def test_render_sidebar_loads_css(self, mock_sidebar, mock_markdown, mock_logo, mock_config):
        """Test render_sidebar loads CSS file."""
        from helpers.utils import render_sidebar

        render_sidebar()

        # Verify markdown was called with CSS
        assert mock_markdown.called
        call_args = mock_markdown.call_args[0][0]
        assert "<style>" in call_args
        assert "body { color: red; }" in call_args

    @patch("streamlit.set_page_config")
    @patch("streamlit.logo")
    @patch("builtins.open", mock_open(read_data=""))
    @patch("streamlit.markdown")
    @patch("streamlit.sidebar")
    def test_render_sidebar_sets_logo(self, mock_sidebar, mock_markdown, mock_logo, mock_config):
        """Test render_sidebar sets Azure AI logo."""
        from helpers.utils import render_sidebar

        render_sidebar()

        # Verify logo was called
        mock_logo.assert_called_once()
        assert "ai-foundry.png" in mock_logo.call_args[0][0]
        assert mock_logo.call_args[1]["link"] == "https://ai.azure.com/"
