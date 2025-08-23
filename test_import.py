
import sys
print(f"Python Executable: {sys.executable}")
print(f"Python Version: {sys.version}")
print(f"System Path: {sys.path}")
try:
    import solana
    import solders
    import spl.token
    print("SUCCESS: All libraries imported successfully.")
except ImportError as e:
    print(f"ERROR: Failed to import libraries.")
    print(e)
except Exception as e:
    print(f"An unexpected error occurred: {e}")
