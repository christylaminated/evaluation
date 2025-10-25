# AI Schema Generation Evaluation Framework

This evaluation framework tests the quality of AI-generated database schemas from natural language prompts using the Llama API.

## Overview

The framework compares AI-generated schemas against ground truth schemas using multiple evaluation metrics:

- **Field Coverage**: Percentage of expected fields present in generated schemas
- **Type Accuracy**: Correctness of field types (TEXT, NUMERIC, MONEY, etc.)
- **Structure Score**: Schema relationships, constraints, and organization
- **Semantic Score**: How well the AI understood the business domain
- **Overall Score**: Weighted combination of all metrics

## Directory Structure

```
evaluation/
├── prompts.json              # Test prompts with expected schema counts
├── ground_truth/             # Expected schemas for each prompt
│   ├── ecomm-001.json
│   ├── school-002.json
│   └── ...
├── generated_schemas/        # AI-generated schemas (created by script)
│   ├── ecomm-001.json
│   └── ...
├── mappings/                 # Field name and type normalization
│   ├── field_name_aliases.json
│   └── type_aliases.json
├── compare.py               # Main evaluation script
├── report.csv              # Evaluation results (generated)
└── README.md               # This file
```

## Setup

1. Ensure Python 3.7+ is installed
2. Install required dependencies:
   ```bash
   pip install aiohttp
   ```

## Running Evaluation

### Basic Usage
```bash
cd evaluation/
python compare.py
```

### Custom Options
```bash
python compare.py --eval-dir /path/to/evaluation --output custom_report.csv
```

## Configuration

### Model Configuration
- **Model**: Llama-4-Maverick-17B-128E-Instruct-FP8
- **API**: https://api.llama.com/v1/chat/completions
- **Max Tokens**: 1024
- **Temperature**: Default (not specified)

### Evaluation Metrics Weights
- Field Coverage: 30%
- Type Accuracy: 25%
- Structure Score: 25%  
- Semantic Score: 20%

## Adding Test Cases

### 1. Add Prompt
Edit `prompts.json`:
```json
{
  "id": "new-test-001",
  "prompt": "Your natural language description...",
  "expected_schemas_count": 2,
  "description": "Brief description of test case"
}
```

### 2. Create Ground Truth
Create `ground_truth/new-test-001.json`:
```json
[
  {
    "appsId": "YourApp",
    "formId": "Entity1",
    "description": "Description...",
    "fields": {
      "field1": {
        "fieldId": "field1",
        "fieldType": "TEXT",
        "required": true
      }
    }
  }
]
```

### 3. Update Mappings (if needed)
Add field name or type aliases to files in `mappings/` directory.

## Output Format

The script generates `report.csv` with columns:
- `prompt_id`: Test case identifier
- `schema_count_match`: Boolean, correct number of schemas generated
- `field_coverage`: 0-1, percentage of expected fields found
- `type_accuracy`: 0-1, percentage of correct field types
- `structure_score`: 0-1, schema organization quality
- `semantic_score`: 0-1, business domain understanding
- `overall_score`: 0-1, weighted overall quality
- `errors`: Any evaluation errors encountered
- `generation_time_ms`: API response time

## Interpreting Results

### Score Ranges
- **0.9-1.0**: Excellent - Production ready
- **0.7-0.89**: Good - Minor issues
- **0.5-0.69**: Fair - Needs improvement  
- **0.3-0.49**: Poor - Significant issues
- **0.0-0.29**: Very Poor - Major problems

### Common Issues
- **Low Field Coverage**: Missing important fields from requirements
- **Low Type Accuracy**: Wrong field types (TEXT vs NUMERIC, etc.)
- **Low Structure Score**: Missing relationships or constraints
- **Low Semantic Score**: Misunderstood business domain

## Extending the Framework

### Custom Metrics
Add new evaluation methods to `SchemaEvaluator` class in `compare.py`.

### Different APIs
Modify `call_llama_api()` function to use different models or endpoints.

### Batch Processing
The script already supports async processing for better performance.

## Troubleshooting

### API Errors
- Check API key validity
- Verify network connectivity
- Monitor rate limits

### JSON Parsing Errors
- Review generated schema format
- Check API response structure
- Validate ground truth files

### Missing Files
- Ensure all ground truth files exist
- Check file permissions
- Verify directory structure

## Version History
- v1.0: Initial framework with Llama API integration
- Schema format based on no-code database platform requirements
- Support for TEXT, NUMERIC, BOOLEAN, MONEY, DATE, REF_PICK_LIST, EMBED types

