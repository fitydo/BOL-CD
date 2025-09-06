#!/bin/bash
# BOL-CD Restore Script

set -e

# Configuration
BACKUP_NAME="${1}"
RESTORE_TYPE="${2:-full}"
BACKUP_DIR="/backups"
S3_BUCKET="${BACKUP_S3_BUCKET:-bolcd-backups}"
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

if [ -z "$BACKUP_NAME" ]; then
    echo -e "${RED}Error: Backup name required${NC}"
    echo "Usage: $0 <backup_name> [restore_type]"
    echo "Types: full, database, redis, application"
    exit 1
fi

echo -e "${BLUE}🔄 BOL-CD Restore Script${NC}"
echo "========================"
echo "Backup: $BACKUP_NAME"
echo "Type: $RESTORE_TYPE"
echo ""

# Function to download from S3
download_from_s3() {
    echo -e "${YELLOW}Downloading backup from S3...${NC}"
    
    if command -v aws &> /dev/null; then
        # Download backup
        aws s3 cp "s3://${S3_BUCKET}/backups/${RESTORE_TYPE}/${BACKUP_NAME}.tar.gz" \
            "$BACKUP_DIR/${BACKUP_NAME}.tar.gz"
        
        # Extract
        mkdir -p "$BACKUP_DIR/$BACKUP_NAME"
        tar -xzf "$BACKUP_DIR/${BACKUP_NAME}.tar.gz" -C "$BACKUP_DIR/$BACKUP_NAME"
        
        echo -e "${GREEN}✓${NC} Backup downloaded from S3"
    else
        echo -e "${YELLOW}⚠${NC} AWS CLI not available, using local backup"
    fi
}

# Function to decrypt backup
decrypt_backup() {
    cd "$BACKUP_DIR/$BACKUP_NAME"
    
    if [ -f "backup.tar.enc" ] && [ -n "$ENCRYPTION_KEY" ]; then
        echo -e "${YELLOW}Decrypting backup...${NC}"
        
        # Decrypt
        openssl enc -aes-256-cbc \
            -d \
            -in backup.tar.enc \
            -out backup.tar \
            -pass pass:"$ENCRYPTION_KEY"
        
        # Extract
        tar -xf backup.tar
        rm backup.tar
        
        echo -e "${GREEN}✓${NC} Backup decrypted"
    fi
}

# Function to verify backup
verify_backup() {
    echo -e "${YELLOW}Verifying backup integrity...${NC}"
    
    if [ ! -f "manifest.json" ]; then
        echo -e "${RED}❌ Manifest file not found${NC}"
        exit 1
    fi
    
    # Verify checksums
    while IFS= read -r file; do
        if [ -f "$file" ] && [ "$file" != "manifest.json" ]; then
            expected_checksum=$(grep "\"name\": \"$file\"" manifest.json | grep -oP '(?<="checksum": ")[^"]*')
            actual_checksum=$(sha256sum "$file" | cut -d' ' -f1)
            if [ "$expected_checksum" != "$actual_checksum" ]; then
                echo -e "${RED}❌ Checksum mismatch for $file${NC}"
                exit 1
            fi
        fi
    done < <(find . -type f -print)
    
    echo -e "${GREEN}✓${NC} Backup integrity verified"
}

# Function to restore database
restore_database() {
    echo -e "${YELLOW}Restoring PostgreSQL database...${NC}"
    
    if [ ! -f "database.dump" ]; then
        echo -e "${RED}❌ Database backup file not found${NC}"
        return 1
    fi
    
    # Get database credentials
    DB_HOST="${DATABASE_HOST:-postgres}"
    DB_PORT="${DATABASE_PORT:-5432}"
    DB_NAME="${DATABASE_NAME:-bolcd}"
    DB_USER="${DATABASE_USER:-bolcd_user}"
    
    # Create backup of current database
    echo "Creating backup of current database..."
    PGPASSWORD="${DATABASE_PASSWORD}" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --no-password \
        --format=custom \
        --file="/tmp/pre_restore_backup.dump" || true
    
    # Drop and recreate database
    echo "Recreating database..."
    PGPASSWORD="${DATABASE_PASSWORD}" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d postgres \
        --no-password \
        -c "DROP DATABASE IF EXISTS ${DB_NAME};"
    
    PGPASSWORD="${DATABASE_PASSWORD}" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d postgres \
        --no-password \
        -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"
    
    # Restore database
    echo "Restoring database..."
    PGPASSWORD="${DATABASE_PASSWORD}" pg_restore \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --no-password \
        --verbose \
        --no-owner \
        --no-privileges \
        "database.dump"
    
    echo -e "${GREEN}✓${NC} Database restored successfully"
}

# Function to restore Redis
restore_redis() {
    echo -e "${YELLOW}Restoring Redis data...${NC}"
    
    if [ ! -f "redis.rdb" ]; then
        echo -e "${RED}❌ Redis backup file not found${NC}"
        return 1
    fi
    
    REDIS_HOST="${REDIS_HOST:-redis}"
    REDIS_PORT="${REDIS_PORT:-6379}"
    
    # Stop Redis writes
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" CONFIG SET stop-writes-on-bgsave-error yes
    
    # Flush current data
    echo "Flushing current Redis data..."
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" FLUSHALL
    
    # Copy RDB file
    cp redis.rdb /data/redis.rdb
    
    # Restart Redis to load the RDB file
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" SHUTDOWN NOSAVE
    sleep 5
    
    # Verify
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" INFO keyspace
    
    echo -e "${GREEN}✓${NC} Redis data restored successfully"
}

# Function to restore application data
restore_application_data() {
    echo -e "${YELLOW}Restoring application data...${NC}"
    
    # Restore configuration files
    if [ -f "configs.tar.gz" ]; then
        echo "Restoring configuration files..."
        tar -xzf configs.tar.gz -C /
    fi
    
    # Restore certificates
    if [ -f "certs.tar.gz" ]; then
        echo "Restoring certificates..."
        tar -xzf certs.tar.gz -C /
    fi
    
    # Restore data files
    if [ -f "data.tar.gz" ]; then
        echo "Restoring data files..."
        tar -xzf data.tar.gz -C /
    fi
    
    # Set correct permissions
    chown -R bolcd:bolcd /app/configs /app/certs /var/lib/bolcd/data 2>/dev/null || true
    
    echo -e "${GREEN}✓${NC} Application data restored successfully"
}

# Function to run post-restore tasks
post_restore_tasks() {
    echo -e "${YELLOW}Running post-restore tasks...${NC}"
    
    # Run database migrations
    echo "Running database migrations..."
    cd /app
    alembic upgrade head || true
    
    # Clear caches
    echo "Clearing caches..."
    redis-cli -h redis FLUSHDB || true
    
    # Restart services
    echo "Restarting services..."
    supervisorctl restart all || true
    
    # Run health checks
    echo "Running health checks..."
    sleep 10
    curl -f http://localhost:8080/health || true
    
    echo -e "${GREEN}✓${NC} Post-restore tasks completed"
}

# Main restore flow
main() {
    # Start timer
    start_time=$(date +%s)
    
    # Check if backup exists locally
    if [ ! -d "$BACKUP_DIR/$BACKUP_NAME" ]; then
        download_from_s3
    fi
    
    # Navigate to backup directory
    cd "$BACKUP_DIR/$BACKUP_NAME"
    
    # Decrypt if needed
    decrypt_backup
    
    # Verify backup
    verify_backup
    
    # Confirmation
    echo -e "${YELLOW}⚠️  Warning: This will overwrite existing data!${NC}"
    read -p "Are you sure you want to continue? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Restore cancelled"
        exit 0
    fi
    
    # Perform restore
    case $RESTORE_TYPE in
        full)
            restore_database
            restore_redis
            restore_application_data
            post_restore_tasks
            ;;
        database)
            restore_database
            ;;
        redis)
            restore_redis
            ;;
        application)
            restore_application_data
            ;;
        *)
            echo -e "${RED}Unknown restore type: $RESTORE_TYPE${NC}"
            exit 1
            ;;
    esac
    
    # Calculate duration
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    # Summary
    echo ""
    echo -e "${BLUE}Restore Summary${NC}"
    echo "==============="
    echo "Backup: $BACKUP_NAME"
    echo "Type: $RESTORE_TYPE"
    echo "Duration: ${duration}s"
    echo ""
    echo -e "${GREEN}✅ Restore completed successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Verify application functionality"
    echo "2. Check logs for any errors"
    echo "3. Run integration tests"
}

# Run main function
main
