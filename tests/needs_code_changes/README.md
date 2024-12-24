# Tests Needing Code Changes

## conftest.py
- Missing LoggingConfig in nova.core.models
- Missing PathsConfig in nova.core.models
- Missing various config classes referenced

## test_logging.py
- Depends on LoggingConfig implementation

## Processor Tests
The following tests need processor implementations:
- test_markdown_processor.py
- test_markdown_aggregate.py
- test_markdown_consolidate.py
- test_three_file_split_processor.py
- test_split_processor.py
- test_aggregate_processor.py
- test_consolidate_processor.py

## Pipeline Tests
The following tests need pipeline implementations:
- test_pipeline.py (depends on PipelineManager and PipelinePhase)
- test_cross_references.py (depends on reference handling implementation)
- test_content_converters.py (depends on content conversion implementation)
- test_reference_manager.py (depends on reference management implementation)

## Error and Performance Tests
The following tests need error handling and performance implementations:
- test_error_cases.py (depends on processor and error handling implementations)
- test_performance.py (depends on processor and performance monitoring)
- test_state.py (depends on state management implementation)

## Attachment and Utility Tests
The following tests need attachment and utility implementations:
- test_attachments.py (depends on attachment processor implementation)
- test_directory.py (depends on directory handling implementation)
- test_input.py (depends on input validation implementation)
- test_validation.py (depends on validation implementation)
- test_paths.py (depends on path handling implementation)

## Test Data and Fixtures
The following test data and fixtures have been moved:
- markdown_split_test/ -> test_data/ (for markdown split processor tests)
- attachments/ -> fixtures/ (for attachment processor tests)

These tests depend on the core implementations that need to be completed first.
EOF 
