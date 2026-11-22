# Core Nexus Codebase Documentation

## Project Overview
**Core Nexus** is a core infrastructure/service layer providing centralized functionality for the broader system. It handles fundamental operations, shared utilities, and cross-cutting concerns that other modules depend upon.

## Architecture & Structure
The project uses a modular, layered architecture with clear separation of concerns:
- **Entry points**: API routers, CLI commands, web controllers
- **Service layer**: Business logic implementations
- **Repository layer**: Data access abstractions (database, cache, file storage)
- **Model layer**: Domain entities and value objects
- **Utility layer**: Shared helpers, formatters, validators

## Conventions & Patterns
### File Naming
- **Models**: PascalCase with `.ts`/`.js` extension
- **Services**: `kebab-case-name.service.ts` pattern
- **Repositories**: `database-type.repository.ts` (e.g., `users.repository.ts`)
- **Utilities**: `utility-name.util.ts` (e.g., `date.util.ts`)
- **Configuration**: Environment-specific configs in `.env.*` or config files

### Code Style
- Type-safe, strongly-typed codebase with comprehensive interfaces
- Dependency injection via constructor injection
- Asynchronous operations using Promises/async-await
- Error handling through custom errors thrown and caught at appropriate boundaries

## Key Directories
- **src/**: Main source code
  - `models/`: Domain entities
  - `services/`: Business logic
  - `repositories/`: Data access layer
  - `utils/`: Shared utilities
- **config/**: Configuration files (environment, database, caching)
- **tests/**: Unit and integration tests
- **scripts/**: Automation scripts (CI/CD hooks, migrations)

## Technology Stack
- Language/Framework: Modern TypeScript/JavaScript with async/await patterns
- Data Persistence: Relational DB + optional cache layer
- External Services: HTTP clients for third-party integrations
- Testing: Unit tests for critical paths, integration tests for API endpoints

## Important Notes
1. **Environment variables**: Loaded at startup from `.env` or framework-specific config
2. **Database migrations**: Located in `scripts/migrations/` directory
3. **API documentation**: Generated OpenAPI/Swagger spec if available
4. **Logging**: Structured logging with correlation IDs for traceability

## Quick Start
1. Set up environment variables (`.env.example` → `.env`)
2. Run database migrations (`npm run migrate` or equivalent)
3. Start the application (`npm start` or `npm run dev`)
4. Access API at configured host:port

## Common Tasks
- Adding a new service: Create in `src/services/` with corresponding interface in `src/models/`
- Adding data access: Extend repository in `src/repositories/`
- CLI commands: Add to `scripts/` or framework command definitions