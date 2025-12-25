# Integration Tests - Conecta Plus

Integration tests for the Conecta Plus platform, testing the interaction between different modules and services.

## Test Structure

```
tests/integration/
├── test_api_gateway_integration.py  # API Gateway integration tests
├── test_database_integration.py     # Database layer tests
├── requirements.txt                  # Python dependencies
└── README.md                         # This file
```

## Prerequisites

1. **Running Services**: All required services must be running:
   - API Gateway (port 3001)
   - PostgreSQL (port 5432)
   - MongoDB (port 27017)
   - Redis (port 6379)

2. **Python Dependencies**:
   ```bash
   cd /opt/conecta-plus/tests/integration
   pip install -r requirements.txt
   ```

## Running Tests

### Run All Integration Tests
```bash
cd /opt/conecta-plus/tests/integration
pytest -v
```

### Run Specific Test File
```bash
# API Gateway tests only
pytest test_api_gateway_integration.py -v

# Database tests only
pytest test_database_integration.py -v
```

### Run Specific Test Class
```bash
# Only authentication tests
pytest test_api_gateway_integration.py::TestAuthenticationIntegration -v

# Only PostgreSQL tests
pytest test_database_integration.py::TestPostgreSQLIntegration -v
```

### Run with Coverage
```bash
pytest --cov=. --cov-report=html -v
```

## Test Categories

### API Gateway Integration Tests (`test_api_gateway_integration.py`)

- **TestAuthenticationIntegration**: Tests login, token generation, and auth flow
- **TestFinanceiroIAIntegration**: Tests Financial IA endpoints (scores, tendências, feedback)
- **TestDashboardIntegration**: Tests dashboard statistics and alerts
- **TestCondominiosIntegration**: Tests condomínios CRUD operations
- **TestErrorHandling**: Tests error responses and validation

### Database Integration Tests (`test_database_integration.py`)

- **TestPostgreSQLIntegration**: PostgreSQL connection and query tests
- **TestMongoDBIntegration**: MongoDB connection and document operations
- **TestRedisIntegration**: Redis cache operations and expiration
- **TestCrossDatabaseIntegration**: Cross-database caching patterns

## Environment Variables

Override default connection strings using environment variables:

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/db"
export MONGODB_URL="mongodb://localhost:27017"
export REDIS_URL="redis://localhost:6379"
```

## Test Data

Tests use the following test credentials:
- Email: `admin@conectaplus.com.br`
- Password: `admin123`

**Note**: These should match the seeded test user in your development database.

## CI/CD Integration

These tests are designed to run in CI/CD pipelines. Example GitHub Actions workflow:

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: conecta_db
          POSTGRES_USER: conecta_user
          POSTGRES_PASSWORD: conecta_password
        ports:
          - 5432:5432

      mongodb:
        image: mongo:7
        ports:
          - 27017:27017

      redis:
        image: redis:7
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r tests/integration/requirements.txt

      - name: Run integration tests
        run: |
          cd tests/integration
          pytest -v --junitxml=junit.xml

      - name: Publish Test Results
        uses: EnricoMi/publish-unit-test-result-action@v2
        if: always()
        with:
          files: tests/integration/junit.xml
```

## Troubleshooting

### Tests Fail with Connection Errors

1. Verify all services are running:
   ```bash
   docker ps
   ```

2. Check service logs:
   ```bash
   docker logs conecta-api-gateway-dev
   docker logs conecta-postgres
   docker logs conecta-mongodb
   docker logs conecta-redis
   ```

3. Verify network connectivity:
   ```bash
   curl http://localhost:3001/health
   pg_isready -h localhost -p 5432
   ```

### Import Errors

Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### Authentication Fails

1. Verify test credentials exist in database
2. Check API Gateway logs for authentication errors
3. Ensure database has been seeded with test data

## Best Practices

1. **Isolation**: Each test should be independent and not rely on other tests
2. **Cleanup**: Tests should clean up any data they create
3. **Idempotency**: Tests should be able to run multiple times
4. **Fast Execution**: Keep tests focused and avoid unnecessary waits
5. **Clear Assertions**: Use descriptive assertion messages

## Adding New Tests

When adding new integration tests:

1. Follow existing naming conventions (`test_*.py`)
2. Use pytest fixtures for setup/teardown
3. Group related tests in classes
4. Add docstrings explaining what's being tested
5. Include both happy path and error cases
6. Update this README with new test categories

## Reporting Issues

If tests fail unexpectedly:
1. Check the test output for specific error messages
2. Verify all prerequisites are met
3. Review recent code changes that might affect the tested functionality
4. File an issue with: test name, error message, environment details
