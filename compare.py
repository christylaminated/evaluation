#!/usr/bin/env python3
"""
Schema Generation Evaluation Script

This script evaluates the quality of AI-generated database schemas by comparing
them against ground truth schemas using various metrics.
"""

import json
import csv
import os
import sys
import asyncio
import aiohttp
import ssl
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import argparse

# Add the parent directory to sys.path to import from the UI lib
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'UI', 'finalUI', 'lib'))

@dataclass
class EvaluationResult:
    prompt_id: str
    schema_count_match: bool
    field_coverage: float  # 0-1
    type_accuracy: float   # 0-1
    structure_score: float # 0-1
    semantic_score: float  # 0-1
    overall_score: float   # 0-1
    errors: List[str]
    generation_time_ms: float
    
class SchemaEvaluator:
    def __init__(self, mappings_dir: str):
        """Initialize evaluator with field name and type mappings"""
        with open(os.path.join(mappings_dir, 'field_name_aliases.json')) as f:
            self.field_aliases = json.load(f)
            
        with open(os.path.join(mappings_dir, 'type_aliases.json')) as f:
            self.type_aliases = json.load(f)
            
        # Create reverse mappings for lookups
        self.field_reverse_map = {}
        for canonical, aliases in self.field_aliases.items():
            self.field_reverse_map[canonical.lower()] = canonical
            for alias in aliases:
                self.field_reverse_map[alias.lower()] = canonical
                
        self.type_reverse_map = {}
        for canonical, aliases in self.type_aliases.items():
            self.type_reverse_map[canonical.upper()] = canonical
            for alias in aliases:
                self.type_reverse_map[alias.upper()] = canonical
    
    def normalize_field_name(self, field_name: str) -> str:
        """Normalize field name using aliases"""
        return self.field_reverse_map.get(field_name.lower(), field_name.lower())
    
    def normalize_field_type(self, field_type: str) -> str:
        """Normalize field type using aliases"""
        return self.type_reverse_map.get(field_type.upper(), field_type.upper())
    
    def extract_schema_fields(self, schema: Dict) -> Dict[str, str]:
        """Extract field names and types from a schema"""
        fields = {}
        if 'fields' in schema:
            for field_name, field_def in schema['fields'].items():
                normalized_name = self.normalize_field_name(field_name)
                normalized_type = self.normalize_field_type(field_def.get('fieldType', ''))
                fields[normalized_name] = normalized_type
        return fields
    
    def calculate_field_coverage(self, generated_schemas: List[Dict], ground_truth_schemas: List[Dict]) -> float:
        """Calculate what percentage of ground truth fields are present in generated schemas"""
        gt_fields = set()
        gen_fields = set()
        
        for schema in ground_truth_schemas:
            gt_fields.update(self.extract_schema_fields(schema).keys())
            
        for schema in generated_schemas:
            gen_fields.update(self.extract_schema_fields(schema).keys())
        
        if not gt_fields:
            return 1.0
            
        intersection = gt_fields.intersection(gen_fields)
        return len(intersection) / len(gt_fields)
    
    def calculate_type_accuracy(self, generated_schemas: List[Dict], ground_truth_schemas: List[Dict]) -> float:
        """Calculate accuracy of field types"""
        gt_field_types = {}
        gen_field_types = {}
        
        for schema in ground_truth_schemas:
            gt_field_types.update(self.extract_schema_fields(schema))
            
        for schema in generated_schemas:
            gen_field_types.update(self.extract_schema_fields(schema))
        
        if not gt_field_types:
            return 1.0
            
        correct_types = 0
        total_fields = 0
        
        for field_name, gt_type in gt_field_types.items():
            if field_name in gen_field_types:
                total_fields += 1
                if gen_field_types[field_name] == gt_type:
                    correct_types += 1
        
        return correct_types / total_fields if total_fields > 0 else 0.0
    
    def calculate_structure_score(self, generated_schemas: List[Dict], ground_truth_schemas: List[Dict]) -> float:
        """Evaluate schema structure (relationships, constraints, etc.)"""
        score = 0.0
        total_checks = 0
        
        # Check schema count
        total_checks += 1
        if len(generated_schemas) == len(ground_truth_schemas):
            score += 1.0
            
        # Check required fields
        for gt_schema in ground_truth_schemas:
            matching_gen_schema = None
            for gen_schema in generated_schemas:
                if (gt_schema.get('formId', '').lower() == gen_schema.get('formId', '').lower() or
                    gt_schema.get('description', '').lower() in gen_schema.get('description', '').lower()):
                    matching_gen_schema = gen_schema
                    break
            
            if matching_gen_schema:
                # Check required fields
                gt_required = {name for name, field in gt_schema.get('fields', {}).items() 
                             if field.get('required', False)}
                gen_required = {name for name, field in matching_gen_schema.get('fields', {}).items() 
                              if field.get('required', False)}
                
                total_checks += 1
                if gt_required == gen_required:
                    score += 1.0
                else:
                    # Partial credit for overlap
                    if gt_required:
                        overlap = len(gt_required.intersection(gen_required))
                        score += overlap / len(gt_required)
        
        return score / total_checks if total_checks > 0 else 0.0
    
    def calculate_semantic_score(self, prompt: str, generated_schemas: List[Dict], ground_truth_schemas: List[Dict]) -> float:
        """Evaluate semantic understanding of the prompt"""
        score = 0.0
        
        # Check if key entities from prompt are captured
        prompt_lower = prompt.lower()
        
        # Extract key entities mentioned in prompt
        entities = []
        common_entities = ['product', 'category', 'customer', 'order', 'user', 'student', 
                          'course', 'employee', 'department', 'event', 'booking', 'item']
        
        for entity in common_entities:
            if entity in prompt_lower:
                entities.append(entity)
        
        # Check if generated schemas have forms for these entities
        gen_form_ids = [schema.get('formId', '').lower() for schema in generated_schemas]
        
        entity_coverage = 0
        for entity in entities:
            if any(entity in form_id for form_id in gen_form_ids):
                entity_coverage += 1
        
        if entities:
            score = entity_coverage / len(entities)
        else:
            score = 0.8  # Default score if no specific entities detected
            
        return min(score, 1.0)
    
    def evaluate_schemas(self, prompt_id: str, prompt: str, generated_schemas: List[Dict], 
                        ground_truth_schemas: List[Dict], generation_time_ms: float) -> EvaluationResult:
        """Evaluate generated schemas against ground truth"""
        errors = []
        
        try:
            # Ensure we have valid schema lists
            if not isinstance(generated_schemas, list):
                if isinstance(generated_schemas, dict):
                    generated_schemas = [generated_schemas]
                else:
                    generated_schemas = []
                    errors.append("Generated schemas is not a valid list or dict")
            
            if not isinstance(ground_truth_schemas, list):
                ground_truth_schemas = []
                errors.append("Ground truth schemas is not a valid list")
            
            # Calculate metrics
            schema_count_match = len(generated_schemas) == len(ground_truth_schemas)
            field_coverage = self.calculate_field_coverage(generated_schemas, ground_truth_schemas)
            type_accuracy = self.calculate_type_accuracy(generated_schemas, ground_truth_schemas) 
            structure_score = self.calculate_structure_score(generated_schemas, ground_truth_schemas)
            semantic_score = self.calculate_semantic_score(prompt, generated_schemas, ground_truth_schemas)
            
            # Calculate overall score (weighted average)
            weights = {
                'field_coverage': 0.3,
                'type_accuracy': 0.25,
                'structure_score': 0.25,
                'semantic_score': 0.2
            }
            
            overall_score = (
                weights['field_coverage'] * field_coverage +
                weights['type_accuracy'] * type_accuracy + 
                weights['structure_score'] * structure_score +
                weights['semantic_score'] * semantic_score
            )
            
            return EvaluationResult(
                prompt_id=prompt_id,
                schema_count_match=schema_count_match,
                field_coverage=field_coverage,
                type_accuracy=type_accuracy,
                structure_score=structure_score,
                semantic_score=semantic_score,
                overall_score=overall_score,
                errors=errors,
                generation_time_ms=generation_time_ms
            )
            
        except Exception as e:
            errors.append(f"Evaluation error: {str(e)}")
            return EvaluationResult(
                prompt_id=prompt_id,
                schema_count_match=False,
                field_coverage=0.0,
                type_accuracy=0.0,
                structure_score=0.0,
                semantic_score=0.0,
                overall_score=0.0,
                errors=errors,
                generation_time_ms=generation_time_ms
            )

async def call_llama_api(prompt: str) -> Tuple[List[Dict], float]:
    """Call the Llama API to generate schemas"""
    api_url = 'https://api.llama.com/v1/chat/completions'
    api_key = "LLM|1715966545708126|k13PL1i6ESgH3UAjuti9jGrVeCU"
    
    payload = {
        "model": "Llama-4-Maverick-17B-128E-Instruct-FP8",
        "messages": [
            {
                "role": "system",
                "content": """You are an expert database architect that designs schemas for a no-code platform. Generate ALL necessary form schemas for the user's project in one response.

CRITICAL: Always include "appsId" field. Never use "name" field.

If multiple schemas are needed, return them as a JSON array. If only one schema is needed, return a single JSON object. All schemas must use the same appsId.

Format for single schema:
{
  "appsId": "CamelCaseAppName",
  "formId": "FormName",
  "description": "Brief description of what this form represents",
  "fields": { ... }
}

Format for multiple schemas:
[
  {
    "appsId": "CamelCaseAppName",
    "formId": "FormName1",
    "description": "Brief description",
    "fields": { ... }
  },
  {
    "appsId": "CamelCaseAppName", 
    "formId": "FormName2",
    "description": "Brief description",
    "fields": { ... }
  }
]

Field structure:
"fieldName": {
  "fieldId": "fieldName",
  "fieldType": "one of: TEXT, NUMERIC, BOOLEAN, MONEY, DATE, REF_PICK_LIST, EMBED",
  "required": true or false (optional),
  "unique": true or false (optional),
  "default": "default value (optional)",
  "allowMultiple": true or false (optional, for arrays)",
  "refPickListId": "FormName.fieldId (only for REF_PICK_LIST)",
  "fractionDigits": 2 (only required for MONEY fields),
  "currencyCode": "USD" (only required for MONEY fields),
  "embeddedFormSchema": {
    "fields": {
      "nestedField": {
        "fieldId": "nestedField",
        "fieldType": "..."
      }
    }
  }
}

Rules:
- ALWAYS include "appsId" field in CamelCase (e.g., "SchoolManagement", "EcommercePlatform")
- NEVER use "name" field - use "appsId" instead
- Valid fieldType values: TEXT, NUMERIC, BOOLEAN, MONEY, DATE, REF_PICK_LIST, EMBED
- For REF_PICK_LIST: include "refPickListId" as "FormName.fieldId"
- For MONEY: MUST include "fractionDigits" (typically 2) and "currencyCode" (e.g., "USD")
- For EMBED: include "embeddedFormSchema" with nested fields
- Use "required" not "isRequired"
- ALL schemas in response must have the SAME appsId
- Each field key in fields must match its fieldId
- Return ONLY the JSON (object or array), with NO explanation or extra text."""
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 1024
    }
    
    start_time = datetime.now()
    
    # Create SSL context that doesn't verify certificates (matches working llamaApi.js behavior)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            async with session.post(
                api_url,
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                },
                json=payload
            ) as response:
                generation_time = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API Error {response.status}: {error_text}")
                
                data = await response.json()
                
                # Extract content from response (match working llamaApi.js format)
                content = None
                if data.get('choices') and data['choices'][0] and data['choices'][0].get('message'):
                    content = data['choices'][0]['message']['content']
                elif data.get('completion_message') and data['completion_message'].get('content'):
                    content_obj = data['completion_message']['content']
                    if isinstance(content_obj, dict) and 'text' in content_obj:
                        content = content_obj['text']
                    else:
                        content = content_obj
                elif data.get('content'):
                    content = data['content']
                
                if not content:
                    raise Exception('No content in API response')
                
                # Parse JSON response
                try:
                    schemas = json.loads(content.strip())
                    if not isinstance(schemas, list):
                        schemas = [schemas] if isinstance(schemas, dict) else []
                    return schemas, generation_time
                except json.JSONDecodeError as e:
                    raise Exception(f"Failed to parse JSON response: {e}")
                
        except Exception as e:
            generation_time = (datetime.now() - start_time).total_seconds() * 1000
            print(f"Error calling Llama API: {e}")
            return [], generation_time

async def run_evaluation(evaluation_dir: str, output_file: str = "report.csv"):
    """Run the full evaluation process"""
    
    # Load prompts
    prompts_file = os.path.join(evaluation_dir, 'prompts.json')
    with open(prompts_file) as f:
        prompts = json.load(f)
    
    # Initialize evaluator
    mappings_dir = os.path.join(evaluation_dir, 'mappings')
    evaluator = SchemaEvaluator(mappings_dir)
    
    # Prepare directories
    ground_truth_dir = os.path.join(evaluation_dir, 'ground_truth')
    generated_dir = os.path.join(evaluation_dir, 'generated_schemas')
    os.makedirs(generated_dir, exist_ok=True)
    
    results = []
    
    print(f"Running evaluation on {len(prompts)} prompts...")
    
    for i, prompt_data in enumerate(prompts, 1):
        prompt_id = prompt_data['id']
        prompt_text = prompt_data['prompt']
        
        print(f"[{i}/{len(prompts)}] Processing {prompt_id}...")
        
        # Load ground truth
        gt_file = os.path.join(ground_truth_dir, f'{prompt_id}.json')
        try:
            with open(gt_file) as f:
                ground_truth = json.load(f)
        except Exception as e:
            print(f"  Error loading ground truth for {prompt_id}: {e}")
            continue
        
        # Generate schemas
        try:
            generated_schemas, generation_time = await call_llama_api(prompt_text)
            
            # Save generated schemas
            output_file_path = os.path.join(generated_dir, f'{prompt_id}.json')
            with open(output_file_path, 'w') as f:
                json.dump(generated_schemas, f, indent=2)
            
            print(f"  Generated {len(generated_schemas)} schemas in {generation_time:.1f}ms")
            
        except Exception as e:
            print(f"  Error generating schemas for {prompt_id}: {e}")
            generated_schemas = []
            generation_time = 0
        
        # Evaluate
        result = evaluator.evaluate_schemas(
            prompt_id, prompt_text, generated_schemas, ground_truth, generation_time
        )
        results.append(result)
        
        print(f"  Overall score: {result.overall_score:.3f}")
        if result.errors:
            print(f"  Errors: {', '.join(result.errors)}")
    
    # Write results to CSV
    output_path = os.path.join(evaluation_dir, output_file)
    with open(output_path, 'w', newline='') as csvfile:
        if results:
            fieldnames = list(asdict(results[0]).keys())
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results:
                row = asdict(result)
                # Convert list to string for CSV
                row['errors'] = '; '.join(row['errors'])
                writer.writerow(row)
    
    # Print summary
    if results:
        avg_score = sum(r.overall_score for r in results) / len(results)
        avg_time = sum(r.generation_time_ms for r in results) / len(results)
        print(f"\n--- Evaluation Summary ---")
        print(f"Total prompts: {len(results)}")
        print(f"Average overall score: {avg_score:.3f}")
        print(f"Average generation time: {avg_time:.1f}ms")
        print(f"Results saved to: {output_path}")
    
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Evaluate AI-generated database schemas')
    parser.add_argument('--eval-dir', default='.', help='Evaluation directory path')
    parser.add_argument('--output', default='report.csv', help='Output CSV file name')
    
    args = parser.parse_args()
    
    asyncio.run(run_evaluation(args.eval_dir, args.output))
