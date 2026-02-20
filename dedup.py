import lancedb
import pyarrow as pa

db = lancedb.connect('engram_data/lance_store/lancedb')
t = db.open_table('memories')
df = t.to_pandas()
print(f"Before: {len(df)} memories")

# Keep first occurrence of each unique content
deduped = df.drop_duplicates(subset=['content'], keep='first')
print(f"After dedup: {len(deduped)} unique memories ({len(df) - len(deduped)} removed)")

if len(deduped) < len(df):
    # Drop and recreate table with deduped data
    db.drop_table('memories')
    table = db.create_table('memories', data=deduped)
    print(f"Table recreated: {table.count_rows()} rows")
