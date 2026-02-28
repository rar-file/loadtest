# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Docker support with multi-stage Dockerfile
- Docker Compose configuration for easy deployment
- Pre-commit hooks configuration for code quality
- Quick start example (`examples/quickstart.py`)
- Enhanced CLI with better error messages and help
- `loadtest quickstart` command for getting started guide
- `loadtest info` command showing available components
- `.dockerignore` for efficient Docker builds

### Fixed
- Fixed HTML report to include test name in title
- Fixed phoney library integration (changed `random_int` to standard `random.randint`)
- Fixed HTTP response elapsed time access for mocked responses
- Fixed AsyncMock test assertions for HTTP scenario tests
- Fixed CI workflow caching and added additional checks
- Fixed nightly workflow benchmark comparison command

### Changed
- Improved CLI user experience with rich formatting
- Enhanced README with comprehensive quick start guide
- Updated CI workflow with Docker build verification
- Updated release workflow with better error handling

## [0.1.0] - 2024-02-28

### Added
- Initial release with core load testing functionality
- Async-first architecture for high concurrency
- HTTP scenario support with httpx
- Web scenario support with Playwright
- Multiple traffic patterns: constant, ramp, spike
- Real-time metrics collection and reporting
- HTML and console report generation
- Integration with Phoney for realistic test data
- CLI interface for running tests
- Comprehensive test suite with 90%+ coverage
- GitHub Actions CI/CD pipelines
- Documentation with MkDocs
- 24+ usage examples

---

## Release Template

### Added
- New features

### Changed
- Changes in existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Now removed features

### Fixed
- Bug fixes

### Security
- Security improvements
