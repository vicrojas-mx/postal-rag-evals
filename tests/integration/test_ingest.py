import os
import pytest
from ingest.ingest import build_sections

@pytest.fixture(scope="module")
def sections():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(current_dir, "../../data", "po-209_-_2023.pdf")
    return build_sections(pdf_path)

def test_pipeline_returns_319_sections(sections):
    assert len(sections) == 319, "Expected 319 sections after cleaning sections and filtering front matter"



