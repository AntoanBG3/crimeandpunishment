import blessed

try:
    term = blessed.Terminal()
    print("blessed library imported and Terminal() instantiated successfully.")
except Exception as e:
    print(f"blessed library imported, but Terminal() instantiation failed: {e}")
