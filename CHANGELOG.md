# Changelog

All notable changes to the Attendance Analyzer project will be documented in this file.

## [1.1.0] - 2025-10-08

### Added
- **Edge Case Handling**: Comprehensive support for various data formats
  - Percentage format strings (e.g., "85%", "90%")
  - Missing/empty data (NaN values)
  - Mixed data formats in the same file
  - Empty subjects with no data
  - Missing registration numbers
  
- **Empty Percentage Column Handling**
  - Automatic calculation of overall percentages from subject-wise attendance
  - Smart detection of empty or missing percentage columns
  - Console notifications when calculation occurs
  - PDF report annotations indicating calculated percentages
  
- **Robust Error Handling**
  - Graceful degradation on malformed data
  - NaN checks throughout the codebase
  - Type conversion safety with try-except blocks
  - Clear "N/A" indicators instead of crashes

- **Documentation**
  - EDGE_CASES.md - Detailed edge case documentation
  - EMPTY_PERCENTAGE_HANDLING.md - Empty percentage handling guide
  - Enhanced README with edge case information

### Fixed
- Bug where reports showed 0.0% for all attendance values
- Issue with format detection when max percentage was 0 or NaN
- Incorrect threshold comparison for mixed percentage formats
- Column mapping conflicts causing incorrect data reading

### Changed
- Enhanced `clean_numeric_value()` function for better data parsing
- Improved percentage format auto-detection (decimal vs percentage)
- Updated PDF generation to show "N/A" for missing values
- Refined statistics calculation to handle empty data gracefully

### Technical Details
- Added proper NaN filtering in threshold calculations
- Implemented automatic percentage calculation from subject data
- Enhanced individual student analysis with fallback calculations
- Improved subject-wise performance reporting

## [1.0.0] - 2025-10-08

### Initial Release
- Flask web application for attendance analysis
- Auto-detection of Excel file structure
- Dynamic subject detection
- Comprehensive PDF report generation
- Subject-wise performance analysis
- Individual student breakdowns
- Color-coded performance indicators
- Fun processing animations
- Real-time progress updates
- Drag & drop file upload interface

---

## Legend
- **Added**: New features
- **Changed**: Changes in existing functionality
- **Fixed**: Bug fixes
- **Removed**: Removed features
- **Security**: Security improvements
