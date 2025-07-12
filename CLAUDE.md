# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Survey Route Grouping System** (台南市志工普查路線分組系統) - a Python application for intelligently grouping addresses for volunteer survey routes in Tainan City, Taiwan. The system combines geographic analysis, spatial clustering, and route optimization to create efficient surveying groups.

## Technology Stack

- **Language**: Python 3.11+
- **Package Manager**: `uv` (ultraviolet) - fast, modern Python package manager
- **Database**: Supabase + PostGIS (PostgreSQL with spatial extensions)
- **CLI Framework**: Typer with Rich for enhanced terminal output
- **Geographic Processing**: GeoPandas, PostGIS, Shapely, PyProj (WGS84/EPSG:4326)
- **Visualization**: Folium for interactive maps
- **Data Validation**: Pydantic v2 with pydantic-settings

## Common Development Commands

```bash
# Project setup
uv sync                                    # Install dependencies
uv sync --all-extras                       # Install with dev dependencies

# Code quality (run these before commits)
uv run black src tests                     # Format code
uv run ruff check src tests                # Lint code
uv run mypy src                            # Type checking

# Testing
uv run pytest                              # Run all tests
uv run pytest --cov=src/survey_grouping   # Run with coverage report
uv run pytest tests/test_clustering.py    # Run specific test file
uv run pytest -m "not slow"               # Skip slow tests

# Application commands
uv run survey-grouping test-connection     # Test database connection
uv run survey-grouping create-groups 新營區 三仙里              # Create groups
uv run survey-grouping visualize 七股區 西寮里                 # Generate maps
uv run survey-grouping batch-process 新營區 --output-dir output # Process district
```

## Architecture Overview

### Core Components

1. **Database Layer** (`database/`):
   - `connection.py`: Supabase client management
   - `queries.py`: PostGIS spatial queries and address operations

2. **Algorithms** (`algorithms/`):
   - `grouping_engine.py`: Main grouping orchestration
   - `clustering.py`: K-means and geographic clustering
   - `address_classifier.py`: Address type classification (street/area/neighborhood)
   - `route_optimizer.py`: Route optimization algorithms

3. **Models** (`models/`):
   - `address.py`: Address data model with coordinate validation
   - `group.py`: RouteGroup and GroupingResult models
   - `address_stats.py`: Statistics and analytics models

4. **Export/Visualization** (`exporters/`, `visualizers/`):
   - Multiple export formats (CSV, Excel, JSON, GeoJSON)
   - Interactive Folium maps with route visualization

### Key Patterns

- **Async/Await**: Database operations use async patterns with Supabase
- **Pydantic Validation**: Comprehensive data validation throughout
- **PostGIS Integration**: Leverages spatial database capabilities for distance calculations
- **Plugin Architecture**: Modular exporters and visualization renderers
- **CLI-First Design**: Typer-based command interface with programmatic API

## Configuration

### Environment Setup
The system uses `.env` file for configuration. Key variables:

```env
# Database (required)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# Grouping parameters
DEFAULT_GROUP_SIZE=35
MIN_GROUP_SIZE=25
MAX_GROUP_SIZE=45

# Geographic parameters
MAX_DISTANCE_THRESHOLD=500.0
CLUSTERING_ALGORITHM=kmeans
```

### Settings Management
- Configuration managed via `src/survey_grouping/config/settings.py`
- Uses Pydantic BaseSettings for type-safe configuration
- Supports validation and default values

## Database Schema

### Core Tables
- `addresses`: Address data with PostGIS GEOMETRY column (WGS84)
- `address_stats`: Cached statistics for performance

### Spatial Features
- Coordinate system: WGS84 (EPSG:4326)
- PostGIS extensions for distance calculations
- Spatial indexing with GIST indexes
- Automatic geometry column updates via database triggers

## Testing

### Test Structure
- **Unit Tests**: Algorithm and model validation
- **Integration Tests**: Database and API interactions
- **Fixtures**: Real CSV data samples in `tests/fixtures/`

### Test Markers
- `@pytest.mark.slow`: Time-intensive tests
- `@pytest.mark.integration`: Database-dependent tests
- `@pytest.mark.unit`: Pure unit tests

### Coverage
- Target: 80%
- Coverage reports: HTML, XML, and terminal output

## Development Guidelines

### Code Quality
- **Black**: Line length 88, Python 3.11+ target
- **Ruff**: Comprehensive linting with modern rules
- **MyPy**: Strict type checking enabled
- **Type Hints**: Required throughout codebase

### Async Patterns
- Database queries use async/await with Supabase client
- CLI commands wrap async functions with `asyncio.run()`
- Example pattern in `main.py` commands

### Geographic Data
- Always use WGS84 coordinates (longitude, latitude)
- PostGIS functions for distance calculations
- Validate coordinates before processing

### Error Handling
- Comprehensive exception handling with user-friendly messages
- Rich console output for better CLI experience
- Proper cleanup of resources

## Key Entry Points

1. **CLI Application**: `src/survey_grouping/main.py`
2. **Programmatic API**: Import `GroupingEngine` directly
3. **Examples**: `examples/basic_usage.py` and `examples/full_workflow.py`

## Important Notes

- The system processes real address data for Tainan City, Taiwan
- Uses Chinese language for user-facing messages and documentation
- Supports both interactive CLI and programmatic usage
- Generates offline-capable HTML maps for field use
- Designed for volunteer survey coordination and route optimization

## Work Scripts Directory

The `work_scripts/` directory contains processing and validation scripts used during development and data processing. This directory is ignored by git and should contain:
- One-off processing scripts for specific villages or districts
- Validation scripts for data quality checks
- Batch processing utilities
- Temporary scripts for testing new functionality

These scripts are not part of the main application but are useful for data preparation and validation tasks.