"""Tests for document upload validation and security."""

import pytest
from app.api.routes.documents import _sanitize_filename, _detect_content_type


class TestSanitizeFilename:
    def test_strips_directory_components(self):
        assert _sanitize_filename("../../etc/passwd") == "etc_passwd"

    def test_strips_backslash_paths(self):
        assert _sanitize_filename("C:\\Users\\evil\\file.pdf") == "file.pdf"

    def test_removes_null_bytes(self):
        assert _sanitize_filename("file\x00.pdf") == "file.pdf"

    def test_removes_special_characters(self):
        assert _sanitize_filename("file<script>.pdf") == "file_script_.pdf"

    def test_limits_length(self):
        long_name = "a" * 300 + ".pdf"
        result = _sanitize_filename(long_name)
        assert len(result) <= 255

    def test_empty_filename_returns_unnamed(self):
        assert _sanitize_filename("") == "unnamed"
        assert _sanitize_filename("...") == "unnamed"

    def test_normal_filename_passes_through(self):
        assert _sanitize_filename("lecture-notes.pdf") == "lecture-notes.pdf"

    def test_spaces_and_underscores_collapsed(self):
        assert _sanitize_filename("my   file___name.pdf") == "my_file_name.pdf"


class TestDetectContentType:
    def test_detects_pdf(self):
        assert _detect_content_type(b"%PDF-1.4 ...") == "application/pdf"

    def test_detects_docx(self):
        # DOCX files start with PK zip header
        assert _detect_content_type(b"PK\x03\x04 ...") == (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    def test_utf8_text_returns_none(self):
        # Text files should return None (trust client header)
        assert _detect_content_type(b"Hello, this is plain text") is None

    def test_unknown_binary_returns_none(self):
        assert _detect_content_type(b"\xff\xfe\x00\x01 random bytes") is None
