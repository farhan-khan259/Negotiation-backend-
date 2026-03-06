import re

# Read the original file
with open('app/api/v1/files.py', 'r') as f:
    content = f.read()

# Replace the vector store ingestion section
pattern = r'    # 5\. Ingest into Vector Store.*?return file_record'
replacement = '''    # 5. Vector Store ingestion temporarily disabled
    # TODO: Fix PGVector table initialization before enabling
    # if text_content:
    #     try:
    #         await ingest_text(text=text_content, metadata={...})
    #     except Exception as e:
    #         print(f"Vector ingestion failed: {e}")
    
    return file_record'''

content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Write back
with open('app/api/v1/files.py', 'w') as f:
    f.write(content)

print("Fixed files.py - vector store ingestion disabled")
