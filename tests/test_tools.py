import os
import pytest
from blinsky.tools.files import write_file, read_file, OUTPUT_DIR

def test_file_tools():
    filename = "test_run_file.txt"
    content = "Hello test suite!"
    
    # Write file
    msg = write_file(filename, content)
    assert "Wrote test_run_file.txt" in msg
    
    # Read file
    read_msg = read_file(filename)
    assert "[test_run_file.txt]" in read_msg
    assert content in read_msg

    # Cleanup
    path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(path):
        os.remove(path)
