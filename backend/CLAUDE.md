# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a dual-service AI application architecture consisting of:
- **Main AI Application Service** (`/app/`) - Comprehensive AI backend with document processing, search, research, and assistant capabilities
- **MCP (Model Context Protocol) Service** (`/mcp-app/`) - Dedicated tool management and execution service

## Development Commands

### Full Stack Development
```bash
# Start all services (PostgreSQL, Redis, Elasticsearch, Main App, MCP Service)
docker-compose up -d

# View logs
docker-compose logs -f [service_name]

# Stop all services
docker-compose down

# Rebuild specific service
docker-compose build [app|mcp-service]
```

### Individual Service Development
```bash
# Main Application (FastAPI)
cd app
pip install -r requirements.txt
uvicorn app_main:app --host 0.0.0.0 --port 8001 --reload

# MCP Service (FastAPI)
cd mcp-app
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Database Management
```bash
# PostgreSQL is initialized via /app/scripts/init.sql
# Database runs on port 5432 (internal) / 5432 (external if mapped)
# Default credentials in docker-compose.yml:
# DB: app_db, User: app_user, Password: app_password
```

### Service Health Checks
```bash
# Main App Health: http://localhost:8100/health
# MCP Service Health: http://localhost:8000/health
# API Docs: http://localhost:8100/docs (Main), http://localhost:8000/docs (MCP)
```

## Architecture & Key Components

### Main Application (`/app/`)
**Core Modules:**
- `app_main.py` - FastAPI application entry point with CORS and route registration
- `router/` - API route handlers for documents, search, research, users, assistants, chat, and MCP integration
- `models/` - SQLAlchemy models for users, documents, assistants, chat sessions/messages
- `services/` - Business logic for document processing, AI integration, search functionality
- `utils/` - Utility functions for file handling, AI processing, database operations

**Key Technologies:**
- FastAPI 0.115.0 with JWT authentication
- PostgreSQL 15 with SQLAlchemy ORM
- Redis 7 for caching
- Elasticsearch 8.11.3 for search
- OpenAI API, LlamaIndex, DashScope for AI capabilities
- Document processing: python-docx, pdfplumber, tika

### MCP Service (`/mcp-app/`)
**Core Modules:**
- `app/main.py` - FastAPI application with tool management lifecycle
- `app/api/` - RESTful endpoints for tools, execution, and servers
- `app/services/` - ToolManager, ToolExecutionService, ServerManager
- `app/models/` - Tool definitions and configurations
- `configs/` - JSON configuration files for tools and MCP servers

**Key Features:**
- Configuration-driven tool definitions
- Multi-protocol support (HTTP, STDIO, WebSocket, Function)
- Dynamic tool discovery from MCP servers
- Tool execution and monitoring

### Service Communication
- Main App communicates with MCP Service via HTTP
- MCP Service URL: `http://mcp-service:8000` (internal Docker network)
- External access: `http://localhost:8000`

## Database Schema

**Core Tables:**
- `users` - User authentication and profiles
- `documents` - Document metadata and processing status
- `assistants` - AI assistant configurations
- `assistant_knowledge_base` - Document-assistant associations
- `assistant_mcp_services` - MCP service-assistant associations
- `chat_sessions` - Chat conversation headers
- `chat_messages` - Individual chat messages

## Key Configuration Files

- `docker-compose.yml` - Full service orchestration with environment variables
- `app/.env` - Main application environment variables (database, API keys, JWT)
- `mcp-app/env.example` - MCP service configuration template
- `mcp-app/configs/tools.json` - Tool registry (currently empty)
- `mcp-app/configs/mcp_servers.json` - MCP server configurations
- `app/scripts/init.sql` - Database initialization script

## Development Notes

- **Hot Reload**: Both services support uvicorn hot reload for development
- **CORS**: Enabled for all origins in development (restrict in production)
- **Health Checks**: Built-in health endpoints for Docker orchestration
- **File Uploads**: Main app stores uploads in `/app/uploads` volume
- **Logs**: Both services output to stdout and have dedicated log directories
- **Security**: Services run as non-root users in containers
- **Chinese Support**: Extensive Chinese text processing with jieba, hanziconv

## API Integration Points

**Main Application APIs:**
- Document management: `/api/documents/*`
- Search functionality: `/api/search/*`
- Research tools: `/api/research/*`
- User management: `/api/users/*`
- AI assistants: `/api/assistants/*`
- Chat functionality: `/api/chat/*`
- MCP integration: `/api/mcp/*`

**MCP Service APIs:**
- Tool management: `/api/v1/tools/*`
- Tool execution: `/api/v1/execution/*`
- Server management: `/api/v1/servers/*`