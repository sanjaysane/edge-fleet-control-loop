# MVP: telemetry directly via control plane's /telemetry -> lake.
# At scale replace this with Kafka/Kinesis consumer writing parquet to S3.
print("Ingestor is standing by (using control_plane ingest for MVP). See data/lake/")
