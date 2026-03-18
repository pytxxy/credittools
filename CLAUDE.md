# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based collection of utility tools for Android app development, build automation, and deployment processes. The codebase focuses on mobile app lifecycle management including APK building, signing, compression, and various integration utilities.

## Key Architecture Components

### Client-Server Architecture
The core architecture uses RPyC (Remote Python Call) for distributed processing:
- **app_server.py**: Main server that manages build tasks and coordinates with remote clients
- **app_client.py**: Client that connects to the server to submit build requests
- **app_controller.py**: Controller that maintains task queues and schedules execution across distributed workers

### Common Patterns
1. **ProcessManager Class**: Most tools use this pattern for argument parsing and initialization
2. **XML Configuration**: Extensive use of XML-based configuration through `config_parser.py`
3. **creditutils Integration**: Heavy reliance on the `creditutils` library for common utilities
4. **Command-Line Interface**: All tools implement argparse with consistent parameter validation

### Core Modules

#### Android Build Tools
- `build_base_android.py`: Base Android build automation
- `build_h5bridge_android.py`: H5 bridge Android builds
- `sign_apk.py`: APK signing utilities
- `apk_info.py`: APK information extraction
- `protect_android_app.py`: Android app protection utilities
- `release_android_client.py`: Android client release automation

#### Compression & Optimization
- `smart_compress.py`: PNG/JPG compression using TinyPNG API
- `get_repeat_resource.py`: Duplicate resource detection

#### Version Control & Integration
- `svn_client.py`, `svn_service.py`: Subversion integration
- `sync_git.py`, `sync_gitlab.py`: Git/GitLab synchronization
- `push_tag.py`: Git tag management
- `clean_gitlab_history.py`: GitLab history cleanup

#### Deployment & Publishing
- `release_apk.py`: APK publishing workflow
- `update_apk_channel.py`: APK channel configuration
- `update_apk_config.py`: APK metadata updates
- `ftp_upload.py`, `ftp_download.py`: FTP operations

#### Utility Tools
- `format_json_file.py`: JSON file formatting
- `format_xml_file.py`: XML file formatting
- `md5.py`: MD5 calculation utilities
- `url_validator.py`: URL validation utilities

## Testing

Tests are located in the `tests/` directory and follow standard unittest patterns. Key test files:
- `test_smart_compress.py`: Image compression tests
- `test_apk_*.py`: APK-related functionality tests
- `test_svn_service.py`: SVN integration tests

To run tests:
```bash
python -m unittest discover tests
```

Or run specific test files:
```bash
python tests/test_smart_compress.py
python tests/test_apk_info.py
```

## Dependencies

Key dependencies from requirements.txt:
- `rpyc==5.1.0`: Remote Python Call for distributed processing
- `xmltodict==0.12.0`: XML to dictionary conversion
- `requests==2.31.0`: HTTP requests
- `paramiko==3.4.0`: SSH/SFTP operations
- `creditutils>=0.3.0`: Custom utility library

## Development Notes

1. **RPyC Service Discovery**: The system uses UDP registry for service discovery. Start the registry server before running distributed services.

2. **Configuration Files**: Most tools expect XML configuration files with a root 'config' tag.

3. **Error Handling**: Tools consistently use traceback for error logging and include descriptive exception messages.

4. **Path Handling**: All paths are converted to absolute paths using `os.path.abspath()` for consistency.

5. **Chinese Comments**: Many files contain Chinese comments and documentation, indicating the primary development language is Chinese.

## Common Commands

Since this is a collection of individual scripts rather than a single application, commands are script-specific:

```bash
# Get APK information
python apk_info.py path/to/app.apk

# Compress images
python smart_compress.py -k YOUR_TINYPNG_KEY -s /path/to/images -d /path/to/output

# Sign APK
python sign_apk.py -s /path/to/app.apk -k /path/to/keystore -p password -a alias

# Build Android app
python build_base_android.py -c config.xml

# Run tests
python -m unittest tests.test_smart_compress
```