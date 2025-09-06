#!/bin/bash
# BOL-CD Backup Script

set -e

# Configuration
BACKUP_TYPE="${1:-full}"
BACKUP_NAME="${2:-backup-$(date +%Y%m%d-%H%M%S)}"
BACKUP_DIR="/backups"
S3_BUCKET="${BACKUP_S3_BUCKET:-bolcd-backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔐 BOL-CD Backup Script${NC}"
echo "========================"
echo "Type: $BACKUP_TYPE"
echo "Name: $BACKUP_NAME"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR/$BACKUP_NAME"
cd "$BACKUP_DIR/$BACKUP_NAME"

# Function to backup database
backup_database() {
    echo -e "${YELLOW}Backing up PostgreSQL database...${NC}"
    
    # Get database credentials
    DB_HOST="${DATABASE_HOST:-postgres}"
    DB_PORT="${DATABASE_PORT:-5432}"
    DB_NAME="${DATABASE_NAME:-bolcd}"
    DB_USER="${DATABASE_USER:-bolcd_user}"
    
    # Perform backup
    PGPASSWORD="${DATABASE_PASSWORD}" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --no-password \
        --verbose \
        --format=custom \
        --blobs \
        --compress=9 \
        --file="database.dump"
    
    # Backup database schema separately
    PGPASSWORD="${DATABASE_PASSWORD}" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --no-password \
        --schema-only \
        --file="schema.sql"
    
    echo -e "${GREEN}✓${NC} Database backup completed ($(du -h database.dump | cut -f1))"
}

# Function to backup Redis
backup_redis() {
    echo -e "${YELLOW}Backing up Redis data...${NC}"
    
    REDIS_HOST="${REDIS_HOST:-redis}"
    REDIS_PORT="${REDIS_PORT:-6379}"
    
    # Trigger Redis backup
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" --rdb redis.rdb
    
    # Copy RDB file
    cp /data/redis.rdb ./redis.rdb
    
    echo -e "${GREEN}✓${NC} Redis backup completed ($(du -h redis.rdb | cut -f1))"
}

# Function to backup application data
backup_application_data() {
    echo -e "${YELLOW}Backing up application data...${NC}"
    
    # Backup configuration files
    tar -czf configs.tar.gz \
        /app/configs/*.yaml \
        /app/configs/*.yml \
        /app/.env* \
        2>/dev/null || true
    
    # Backup certificates
    tar -czf certs.tar.gz \
        /app/certs/*.crt \
        /app/certs/*.key \
        /app/certs/*.pem \
        2>/dev/null || true
    
    # Backup uploaded files
    if [ -d "/var/lib/bolcd/data" ]; then
        tar -czf data.tar.gz /var/lib/bolcd/data/
    fi
    
    # Backup logs (last 7 days)
    find /var/log/bolcd -type f -mtime -7 -exec tar -czf logs.tar.gz {} \; 2>/dev/null || true
    
    echo -e "${GREEN}✓${NC} Application data backup completed"
}

# Function to create backup manifest
create_manifest() {
    echo -e "${YELLOW}Creating backup manifest...${NC}"
    
    cat > manifest.json <<EOF
{
  "backup_name": "$BACKUP_NAME",
  "backup_type": "$BACKUP_TYPE",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "version": "$(git describe --tags --always 2>/dev/null || echo 'unknown')",
  "files": [
$(find . -type f -exec sh -c 'echo "    {\"name\": \"$1\", \"size\": $(stat -c%s "$1"), \"checksum\": \"$(sha256sum "$1" | cut -d" " -f1)\"}," ' _ {} \; | sed '$ s/,$//')
  ],
  "metadata": {
    "hostname": "$(hostname)",
    "os": "$(uname -a)",
    "database_version": "$(psql --version | head -1)",
    "redis_version": "$(redis-cli --version)"
  }
}
EOF
    
    echo -e "${GREEN}✓${NC} Manifest created"
}

# Function to encrypt backup
encrypt_backup() {
    if [ -n "$ENCRYPTION_KEY" ]; then
        echo -e "${YELLOW}Encrypting backup...${NC}"
        
        # Create tar archive
        tar -cf backup.tar ./*
        
        # Encrypt with OpenSSL
        openssl enc -aes-256-cbc \
            -salt \
            -in backup.tar \
            -out backup.tar.enc \
            -pass pass:"$ENCRYPTION_KEY"
        
        # Remove unencrypted files
        rm -f backup.tar
        find . -type f ! -name "*.enc" ! -name "manifest.json" -delete
        
        echo -e "${GREEN}✓${NC} Backup encrypted"
    fi
}

# Function to upload to S3
upload_to_s3() {
    echo -e "${YELLOW}Uploading to S3...${NC}"
    
    if command -v aws &> /dev/null; then
        # Create archive
        tar -czf "../${BACKUP_NAME}.tar.gz" .
        
        # Upload to S3
        aws s3 cp "../${BACKUP_NAME}.tar.gz" \
            "s3://${S3_BUCKET}/backups/${BACKUP_TYPE}/${BACKUP_NAME}.tar.gz" \
            --storage-class STANDARD_IA \
            --server-side-encryption AES256 \
            --metadata "backup-type=${BACKUP_TYPE},timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        
        # Upload manifest separately for easy access
        aws s3 cp manifest.json \
            "s3://${S3_BUCKET}/backups/${BACKUP_TYPE}/${BACKUP_NAME}/manifest.json"
        
        echo -e "${GREEN}✓${NC} Backup uploaded to S3"
    else
        echo -e "${YELLOW}⚠${NC} AWS CLI not available, skipping S3 upload"
    fi
}

# Function to cleanup old backups
cleanup_old_backups() {
    echo -e "${YELLOW}Cleaning up old backups...${NC}"
    
    # Local cleanup
    find "$BACKUP_DIR" -type d -mtime +${RETENTION_DAYS} -exec rm -rf {} \; 2>/dev/null || true
    
    # S3 cleanup
    if command -v aws &> /dev/null; then
        # List and delete old backups
        aws s3 ls "s3://${S3_BUCKET}/backups/" --recursive | \
        while read -r line; do
            createDate=$(echo "$line" | awk '{print $1" "$2}')
            createDate=$(date -d "$createDate" +%s)
            olderThan=$(date -d "${RETENTION_DAYS} days ago" +%s)
            if [[ $createDate -lt $olderThan ]]; then
                fileName=$(echo "$line" | awk '{print $4}')
                echo "Deleting old backup: $fileName"
                aws s3 rm "s3://${S3_BUCKET}/$fileName"
            fi
        done
    fi
    
    echo -e "${GREEN}✓${NC} Cleanup completed"
}

# Function to verify backup
verify_backup() {
    echo -e "${YELLOW}Verifying backup...${NC}"
    
    # Check file integrity
    while IFS= read -r file; do
        if [ -f "$file" ]; then
            expected_checksum=$(grep "\"name\": \"$file\"" manifest.json | grep -oP '(?<="checksum": ")[^"]*')
            actual_checksum=$(sha256sum "$file" | cut -d' ' -f1)
            if [ "$expected_checksum" != "$actual_checksum" ]; then
                echo -e "${RED}❌ Checksum mismatch for $file${NC}"
                return 1
            fi
        fi
    done < <(find . -type f ! -name "manifest.json" -print)
    
    echo -e "${GREEN}✓${NC} Backup verified successfully"
}

# Main backup flow
main() {
    # Start timer
    start_time=$(date +%s)
    
    case $BACKUP_TYPE in
        full)
            backup_database
            backup_redis
            backup_application_data
            ;;
        database)
            backup_database
            ;;
        redis)
            backup_redis
            ;;
        application)
            backup_application_data
            ;;
        *)
            echo -e "${RED}Unknown backup type: $BACKUP_TYPE${NC}"
            echo "Valid types: full, database, redis, application"
            exit 1
            ;;
    esac
    
    # Create manifest
    create_manifest
    
    # Encrypt if key provided
    encrypt_backup
    
    # Verify backup
    verify_backup
    
    # Upload to S3
    upload_to_s3
    
    # Cleanup old backups
    cleanup_old_backups
    
    # Calculate duration
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    # Summary
    echo ""
    echo -e "${BLUE}Backup Summary${NC}"
    echo "=============="
    echo "Name: $BACKUP_NAME"
    echo "Type: $BACKUP_TYPE"
    echo "Location: $BACKUP_DIR/$BACKUP_NAME"
    echo "Size: $(du -sh . | cut -f1)"
    echo "Duration: ${duration}s"
    echo ""
    echo -e "${GREEN}✅ Backup completed successfully!${NC}"
}

# Run main function
main
