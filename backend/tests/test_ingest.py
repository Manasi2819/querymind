import pytest
from services.ingest_service import ingest_file
import os

def test_ingestion_pipeline(tmp_path, mocker):
    # Create fake text file
    test_file = tmp_path / "sample.txt"
    test_file.write_text("QueryMind is an independent, enterprise-grade chatbot module.")
    
    # Mock chroma DB embed logic so it doesn't fail trying to reach localhost:8001
    mocker.patch('services.ingest_service.delete_collection')
    mocker.patch('services.ingest_service.add_documents', return_value=1)
    
    result = ingest_file(str(test_file), "test_tenant", "document")
    
    assert result["status"] == "done"
    assert result["chunks"] == 1
