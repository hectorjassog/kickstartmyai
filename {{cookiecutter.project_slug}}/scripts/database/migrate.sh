#!/bin/bash

# Migration Helper Script for {{cookiecutter.project_name}}
# Provides convenient commands for database migration management

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

show_help() {
    echo -e "${YELLOW}Database Migration Helper${NC}"
    echo "=========================="
    echo ""
    echo "Usage: ./scripts/database/migrate.sh [command]"
    echo ""
    echo "Commands:"
    echo "  init                 Initialize Alembic (first time setup)"
    echo "  create-initial       Create initial migration for all tables"
    echo "  generate [message]   Generate new migration with optional message"
    echo "  upgrade [revision]   Upgrade to latest or specific revision"
    echo "  downgrade [revision] Downgrade to specific revision"
    echo "  current              Show current revision"
    echo "  history              Show migration history"
    echo "  reset                Reset database (drop all + upgrade)"
    echo "  fresh                Fresh start (drop all + generate + upgrade)"
    echo "  check                Check if migrations are up to date"
    echo "  validate-models      Validate model imports in __init__.py"
    echo "  fix-models           Fix model imports in __init__.py"
    echo "  help                 Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./scripts/database/migrate.sh init"
    echo "  ./scripts/database/migrate.sh create-initial"
    echo "  ./scripts/database/migrate.sh generate 'Add user table'"
    echo "  ./scripts/database/migrate.sh upgrade"
    echo "  ./scripts/database/migrate.sh downgrade -1"
    echo "  ./scripts/database/migrate.sh validate-models"
}

check_env() {
    if [ ! -f ".env" ]; then
        echo -e "${RED}Error: .env file not found. Please create one from .env.example${NC}"
        exit 1
    fi
    
    if ! command -v alembic &> /dev/null; then
        echo -e "${RED}Error: Alembic not installed. Run: pip install -r requirements.txt${NC}"
        exit 1
    fi
}

validate_models() {
    echo -e "${BLUE}Validating model imports...${NC}"
    python scripts/database/validate_models.py
    return $?
}

fix_models() {
    echo -e "${BLUE}Fixing model imports...${NC}"
    python scripts/database/validate_models.py --write-fix
    return $?
}

init_alembic() {
    echo -e "${YELLOW}Initializing Alembic...${NC}"
    
    if [ -d "alembic" ]; then
        echo -e "${RED}Error: Alembic already initialized (alembic/ directory exists)${NC}"
        exit 1
    fi
    
    alembic init alembic
    echo -e "${GREEN}✅ Alembic initialized successfully${NC}"
    echo -e "${YELLOW}Note: Configure alembic/env.py and alembic.ini before creating migrations${NC}"
}

create_initial_migration() {
    echo -e "${YELLOW}Creating initial migration...${NC}"
    python scripts/database/create_initial_migration.py
}

generate_migration() {
    local message="${1:-Auto-generated migration}"
    
    # Validate models before generating migration
    echo -e "${BLUE}Step 1: Validating model imports...${NC}"
    if ! validate_models; then
        echo -e "${RED}❌ Model validation failed!${NC}"
        echo -e "${YELLOW}Run './scripts/database/migrate.sh fix-models' to fix automatically${NC}"
        echo -e "${YELLOW}Or fix manually and try again${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Model imports validated${NC}"
    
    echo -e "${BLUE}Step 2: Generating migration: $message${NC}"
    
    alembic revision --autogenerate -m "$message"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Migration generated successfully${NC}"
        echo -e "${YELLOW}Review the migration file before upgrading${NC}"
    else
        echo -e "${RED}❌ Failed to generate migration${NC}"
        exit 1
    fi
}

upgrade_database() {
    local revision="${1:-head}"
    echo -e "${YELLOW}Upgrading database to: $revision${NC}"
    
    alembic upgrade "$revision"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Database upgraded successfully${NC}"
    else
        echo -e "${RED}❌ Failed to upgrade database${NC}"
        exit 1
    fi
}

downgrade_database() {
    local revision="$1"
    
    if [ -z "$revision" ]; then
        echo -e "${RED}Error: Revision required for downgrade${NC}"
        echo "Usage: ./migrate.sh downgrade <revision>"
        echo "Example: ./migrate.sh downgrade -1"
        exit 1
    fi
    
    echo -e "${YELLOW}Downgrading database to: $revision${NC}"
    
    alembic downgrade "$revision"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Database downgraded successfully${NC}"
    else
        echo -e "${RED}❌ Failed to downgrade database${NC}"
        exit 1
    fi
}

show_current() {
    echo -e "${YELLOW}Current database revision:${NC}"
    alembic current
}

show_history() {
    echo -e "${YELLOW}Migration history:${NC}"
    alembic history --verbose
}

reset_database() {
    echo -e "${YELLOW}Resetting database (drop all tables + upgrade)...${NC}"
    read -p "Are you sure? This will destroy all data! (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Drop all tables
        python scripts/database/init_db.py drop
        
        # Upgrade to latest
        upgrade_database
        
        echo -e "${GREEN}✅ Database reset completed${NC}"
    else
        echo -e "${YELLOW}Reset cancelled${NC}"
    fi
}

fresh_start() {
    echo -e "${YELLOW}Fresh start (drop + generate + upgrade)...${NC}"
    read -p "Are you sure? This will destroy all data! (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Drop all tables
        python scripts/database/init_db.py drop
        
        # Generate new migration (this will validate models first)
        generate_migration "Fresh start migration"
        
        # Upgrade to latest
        upgrade_database
        
        echo -e "${GREEN}✅ Fresh start completed${NC}"
    else
        echo -e "${YELLOW}Fresh start cancelled${NC}"
    fi
}

check_migrations() {
    echo -e "${YELLOW}Checking migration status...${NC}"
    
    # First validate models
    if ! validate_models; then
        echo -e "${YELLOW}⚠️  Model validation issues found${NC}"
    fi
    
    # Check if there are pending migrations
    current_rev=$(alembic current --verbose 2>/dev/null | grep "Rev:" | awk '{print $2}' || echo "")
    head_rev=$(alembic heads 2>/dev/null | awk '{print $1}' || echo "")
    
    if [ -z "$current_rev" ]; then
        echo -e "${YELLOW}⚠️  No migrations applied yet${NC}"
        echo "Run: ./migrate.sh create-initial"
    elif [ "$current_rev" = "$head_rev" ]; then
        echo -e "${GREEN}✅ Database is up to date${NC}"
    else
        echo -e "${YELLOW}⚠️  Database needs migration${NC}"
        echo "Current: $current_rev"
        echo "Latest:  $head_rev"
        echo "Run: ./migrate.sh upgrade"
    fi
}

# Main command handler
case "${1:-help}" in
    "init")
        check_env
        init_alembic
        ;;
    "create-initial")
        check_env
        create_initial_migration
        ;;
    "generate")
        check_env
        generate_migration "$2"
        ;;
    "upgrade")
        check_env
        upgrade_database "$2"
        ;;
    "downgrade")
        check_env
        downgrade_database "$2"
        ;;
    "current")
        check_env
        show_current
        ;;
    "history")
        check_env
        show_history
        ;;
    "reset")
        check_env
        reset_database
        ;;
    "fresh")
        check_env
        fresh_start
        ;;
    "check")
        check_env
        check_migrations
        ;;
    "validate-models")
        validate_models
        ;;
    "fix-models")
        fix_models
        ;;
    "help"|*)
        show_help
        ;;
esac
