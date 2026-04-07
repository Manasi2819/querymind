import sys
import os
from unittest.mock import MagicMock, patch

# Add the current directory to sys.path to import services
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.sql_rag_service import run_sql_rag_pipeline

def test_retry_logic():
    print("Testing retry logic...")
    
    # Mock dependencies
    with patch("services.sql_rag_service.retrieve_relevant_schema") as mock_retrieve, \
         patch("services.sql_rag_service.generate_sql") as mock_gen, \
         patch("services.sql_rag_service.execute_query") as mock_exec, \
         patch("services.sql_rag_service.generate_corrected_sql") as mock_correct, \
         patch("services.sql_rag_service.get_llm") as mock_llm:
        
        mock_retrieve.return_value = "Table inventory(item_name, price)"
        mock_gen.return_value = "SELECT item_name, MAX(price) FROM inventory"
        
        # Simulating first execution failure (only_full_group_by error)
        mock_exec.side_effect = [
            Exception("(1140, 'In aggregated query without GROUP BY...')"),
            ("SELECT item_name, price FROM inventory ORDER BY price DESC LIMIT 1", [{"item_name": "Keyboard", "price": 100}], None)
        ]
        
        mock_correct.return_value = "SELECT item_name, price FROM inventory ORDER BY price DESC LIMIT 1"
        
        mock_llm_inst = MagicMock()
        mock_llm_inst.invoke.return_value.content = "The item with the highest price is Keyboard ($100)."
        mock_llm.return_value = mock_llm_inst
        
        summary, sql, data = run_sql_rag_pipeline(
            question="which item has the highest price",
            tenant_id="test_tenant",
            db_url="mysql://user:pass@localhost/db"
        )
        
        print(f"Summary: {summary}")
        print(f"Final SQL: {sql}")
        print(f"Data: {data}")
        
        assert "Keyboard" in summary
        assert "ORDER BY price DESC LIMIT 1" in sql
        assert mock_exec.call_count == 2
        assert mock_correct.call_count == 1
        
        print("Retry logic test passed!")

if __name__ == "__main__":
    try:
        test_retry_logic()
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
