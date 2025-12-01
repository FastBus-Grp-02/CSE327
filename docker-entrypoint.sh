#!/bin/sh
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting FastBus Application...${NC}"

# Wait for database to be ready with timeout
echo -e "${YELLOW}Waiting for database to be ready...${NC}"
RETRIES=30
RETRY_COUNT=0

while ! pg_isready -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "${DB_USER:-postgres}" > /dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $RETRIES ]; then
        echo -e "${RED}Database is not available after ${RETRIES} attempts. Exiting.${NC}"
        exit 1
    fi
    echo -e "${YELLOW}Database is unavailable - waiting (attempt $RETRY_COUNT/$RETRIES)${NC}"
    sleep 2
done

echo -e "${GREEN}Database is ready!${NC}"

# Run database migrations
echo -e "${YELLOW}Running database migrations...${NC}"
if flask db upgrade; then
    echo -e "${GREEN}Database migrations completed successfully${NC}"
else
    echo -e "${RED}Database migration failed${NC}"
    exit 1
fi

# Check if database needs seeding (optional)
if [ "$SEED_DATABASE" = "true" ]; then
    echo -e "${YELLOW}Seeding database with sample data...${NC}"
    if python seed_db.py; then
        echo -e "${GREEN}Database seeding completed${NC}"
    else
        echo -e "${YELLOW}Warning: Database seeding failed (continuing anyway)${NC}"
    fi
fi

echo -e "${GREEN}Application startup complete!${NC}"
echo -e "${GREEN}Starting application server...${NC}"

# Execute the main command
exec "$@"

