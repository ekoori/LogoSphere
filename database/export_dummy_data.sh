#!/bin/bash

# docker cp /home/dev1/TrustSphere/database/export_dummy_data.sh cassandra:/scripts/export_dummy_data.sh
# docker exec cassandra chmod +x /scripts/export_dummy_data.sh
# docker exec cassandra /scripts/export_dummy_data.sh


# Directory to store exported data
EXPORT_DIR="/dummy_data"
mkdir -p "$EXPORT_DIR"

# Export schema
echo "Exporting schema..."
cqlsh --cqlversion=3.4.7 -e "DESCRIBE SCHEMA;" > /scripts/schema.cql

# Export data from each table
echo "Starting data export..."
tables=$(cqlsh --cqlversion=3.4.7 -e "USE trustsphere; DESCRIBE TABLES;")
for table in $tables; do
  echo "Exporting $table to CSV..."
  cqlsh --cqlversion=3.4.7 -e "USE trustsphere; COPY $table TO '$EXPORT_DIR/$table.csv' WITH HEADER = TRUE;"
done

echo "Data export completed."

exit 0
