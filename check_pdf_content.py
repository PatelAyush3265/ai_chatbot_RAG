"""Quick script to check what content is in the PDF"""
from document_processor import DocumentProcessor

dp = DocumentProcessor()
chunks = dp.process_pdf('linmod.pdf')

print("\n" + "="*80)
print("SAMPLE CHUNKS FROM PDF")
print("="*80 + "\n")

# Show chunks at different positions
for i in [0, 10, 20, 30, 40, 50, 60, 70]:
    if i < len(chunks):
        print(f"Chunk {i}:")
        print(chunks[i]['text'][:400])
        print("\n" + "-"*80 + "\n")

print(f"\nTotal chunks: {len(chunks)}")
