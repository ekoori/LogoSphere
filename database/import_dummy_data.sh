#!/bin/bash

# Path to the flag file
FLAG_FILE="/scripts/.data_imported"

# Check if the flag file exists
if [ -f "$FLAG_FILE" ]; then
  echo "Data already imported. Skipping schema and data import."
  exit 0
fi


# Wait for Cassandra to be ready
echo "Waiting for Cassandra to be ready..."
until cqlsh --cqlversion=3.4.7 -e "DESCRIBE KEYSPACES;" > /dev/null 2>&1; do
  sleep 5
  done
  echo "Cassandra is ready!"

  # Apply the schema
  echo "Applying schema..."
  cqlsh --cqlversion=3.4.7 -f /scripts/schema.cql

  # Import data
  echo "Starting data import..."
  for file in /dummy_data/*.csv; do
    table_name=$(basename "$file" .csv)  # Extract table name from filename
      echo "Importing $file into $table_name..."
        cqlsh --cqlversion=3.4.7 -e "USE logosphere; COPY $table_name FROM '$file' WITH HEADER = TRUE;"
        done

        echo "Data import completed."

# Create the flag file
touch "$FLAG_FILE"

exit 0
