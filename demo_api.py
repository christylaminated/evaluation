#!/usr/bin/env python3
"""
Demo script to show Llama API integration
This demonstrates how generated_schemas/ folder gets populated
"""

import json
import requests
import os
from datetime import datetime

def call_llama_api(prompt, output_file):
    """Call Llama API and save results to generated_schemas/"""
    
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
  "currencyCode": "USD" (only required for MONEY fields)
}

Rules:
- ALWAYS include "appsId" field in CamelCase
- Valid fieldType values: TEXT, NUMERIC, BOOLEAN, MONEY, DATE, REF_PICK_LIST, EMBED  
- For REF_PICK_LIST: include "refPickListId" as "FormName.fieldId"
- For MONEY: MUST include "fractionDigits" (typically 2) and "currencyCode"
- Return ONLY the JSON (object or array), with NO explanation or extra text."""
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 1024
    }
    
    print(f"📡 Calling Llama API for {output_file}...")
    start_time = datetime.now()
    
    try:
        response = requests.post(
            api_url,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json=payload,
            timeout=30
        )
        
        generation_time = (datetime.now() - start_time).total_seconds() * 1000
        
        if response.status_code != 200:
            print(f"❌ API Error {response.status_code}: {response.text}")
            return None, generation_time
            
        data = response.json()
        print(f"✅ API Response received in {generation_time:.1f}ms")
        
        # Extract content from response
        content = None
        if data.get('choices') and data['choices'][0].get('message'):
            content = data['choices'][0]['message']['content']
        elif data.get('completion_message', {}).get('content'):
            content = data['completion_message']['content']
            if isinstance(content, dict) and 'text' in content:
                content = content['text']
        elif data.get('content'):
            content = data['content']
            
        if not content:
            print(f"❌ No content in API response")
            return None, generation_time
            
        print(f"📝 Raw content received: {content[:200]}...")
        
        # Parse JSON response
        try:
            schemas = json.loads(content.strip())
            
            # Ensure it's a list
            if not isinstance(schemas, list):
                schemas = [schemas] if isinstance(schemas, dict) else []
            
            # Save to generated_schemas folder
            output_path = os.path.join('generated_schemas', output_file)
            with open(output_path, 'w') as f:
                json.dump(schemas, f, indent=2)
                
            print(f"💾 Saved {len(schemas)} schema(s) to {output_path}")
            return schemas, generation_time
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON: {e}")
            # Save raw content for debugging
            debug_path = os.path.join('generated_schemas', output_file.replace('.json', '_debug.txt'))
            with open(debug_path, 'w') as f:
                f.write(content)
            print(f"🐛 Saved raw content to {debug_path}")
            return None, generation_time
            
    except requests.exceptions.RequestException as e:
        generation_time = (datetime.now() - start_time).total_seconds() * 1000
        print(f"❌ Network error: {e}")
        return None, generation_time

def demo_evaluation():
    """Demonstrate the evaluation process with 2 test cases"""
    
    print("🚀 AI Schema Generation Evaluation Demo")
    print("=" * 60)
    
    # Load prompts
    with open('prompts.json') as f:
        prompts = json.load(f)
    
    # Test with first 2 prompts 
    test_cases = prompts[:2]
    
    results = []
    
    for i, prompt_data in enumerate(test_cases, 1):
        prompt_id = prompt_data['id']
        prompt_text = prompt_data['prompt']
        
        print(f"\n📋 Test Case {i}/2: {prompt_id}")
        print(f"💭 Prompt: {prompt_text}")
        print(f"🎯 Expected schemas: {prompt_data['expected_schemas_count']}")
        print("-" * 40)
        
        # Generate schemas using AI
        schemas, gen_time = call_llama_api(prompt_text, f"{prompt_id}.json")
        
        if schemas:
            print(f"✅ Generated {len(schemas)} schemas:")
            for j, schema in enumerate(schemas, 1):
                app_id = schema.get('appsId', 'N/A')
                form_id = schema.get('formId', 'N/A') 
                field_count = len(schema.get('fields', {}))
                print(f"   {j}. {app_id}.{form_id} ({field_count} fields)")
                
            # Load ground truth for comparison
            gt_file = f"ground_truth/{prompt_id}.json"
            if os.path.exists(gt_file):
                with open(gt_file) as f:
                    ground_truth = json.load(f)
                    
                print(f"📚 Ground truth has {len(ground_truth)} schemas")
                
                # Simple comparison
                schema_count_match = len(schemas) == len(ground_truth)
                print(f"📊 Schema count match: {'✅' if schema_count_match else '❌'}")
                
                results.append({
                    'prompt_id': prompt_id,
                    'generated_count': len(schemas),
                    'expected_count': len(ground_truth),
                    'schema_count_match': schema_count_match,
                    'generation_time_ms': gen_time
                })
            else:
                print(f"⚠️  Ground truth file not found: {gt_file}")
        else:
            print(f"❌ Failed to generate schemas")
            results.append({
                'prompt_id': prompt_id,
                'generated_count': 0,
                'expected_count': prompt_data['expected_schemas_count'],
                'schema_count_match': False,
                'generation_time_ms': gen_time
            })
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 DEMO RESULTS SUMMARY")
    print("=" * 60)
    
    for result in results:
        print(f"🔸 {result['prompt_id']}:")
        print(f"   Generated: {result['generated_count']}, Expected: {result['expected_count']}")
        print(f"   Count Match: {'✅' if result['schema_count_match'] else '❌'}")
        print(f"   Time: {result['generation_time_ms']:.1f}ms")
    
    avg_time = sum(r['generation_time_ms'] for r in results) / len(results)
    success_rate = sum(r['schema_count_match'] for r in results) / len(results) * 100
    
    print(f"\n🎯 Success Rate: {success_rate:.1f}%")
    print(f"⏱️  Average Generation Time: {avg_time:.1f}ms")
    
    print(f"\n💡 To run full evaluation on all 15 domains:")
    print(f"   python3 compare.py")
    print(f"\n📁 Generated schemas are saved in: generated_schemas/")
    print(f"📚 Compare against ground truth in: ground_truth/")

if __name__ == "__main__":
    # Make sure we have the required library
    try:
        import requests
    except ImportError:
        print("❌ Missing requests library. Install with: pip install requests")
        exit(1)
        
    demo_evaluation()
