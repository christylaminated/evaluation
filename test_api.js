// Quick test script to demonstrate Llama API integration
// This shows how generated_schemas/ gets populated

const fs = require('fs');
const path = require('path');

async function testLlamaAPI(prompt, outputFile) {
  const apiUrl = 'https://api.llama.com/v1/chat/completions';
  const apiKey = "LLM|1715966545708126|k13PL1i6ESgH3UAjuti9jGrVeCU";

  const payload = {
    model: "Llama-4-Maverick-17B-128E-Instruct-FP8", 
    messages: [
      {
        role: "system",
        content: `You are an expert database architect that designs schemas for a no-code platform. Generate ALL necessary form schemas for the user's project in one response.

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
- Return ONLY the JSON (object or array), with NO explanation or extra text.`
      },
      {
        role: "user",
        content: prompt
      }
    ],
    max_tokens: 1024
  };

  try {
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API Error ${response.status}: ${errorText}`);
    }

    const data = await response.json();
    console.log(`✅ API Response for ${outputFile}:`, data);
    
    // Extract content from response
    let content;
    if (data.choices && data.choices[0] && data.choices[0].message) {
      content = data.choices[0].message.content;
    } else if (data.completion_message && data.completion_message.content) {
      content = data.completion_message.content.text || data.completion_message.content;
    } else if (data.content) {
      content = data.content;
    } else {
      throw new Error('No content in API response');
    }

    console.log(`📝 Raw content: ${content}`);
    
    // Parse and save JSON
    try {
      const schemas = JSON.parse(content.trim());
      const outputPath = path.join(__dirname, 'generated_schemas', outputFile);
      fs.writeFileSync(outputPath, JSON.stringify(schemas, null, 2));
      console.log(`💾 Saved generated schemas to: ${outputPath}`);
      return schemas;
    } catch (parseError) {
      console.error(`❌ Failed to parse JSON: ${parseError}`);
      // Save raw content for debugging
      const outputPath = path.join(__dirname, 'generated_schemas', outputFile.replace('.json', '_raw.txt'));
      fs.writeFileSync(outputPath, content);
      console.log(`🐛 Saved raw content to: ${outputPath}`);
      return null;
    }
    
  } catch (error) {
    console.error(`❌ Error calling API for ${outputFile}:`, error);
    return null;
  }
}

async function runTests() {
  console.log('🚀 Testing Llama API integration...\n');
  
  // Load test prompts
  const promptsData = JSON.parse(fs.readFileSync('prompts.json', 'utf8'));
  
  // Test with first 2 prompts to demonstrate
  const testPrompts = promptsData.slice(0, 2);
  
  for (const promptData of testPrompts) {
    console.log(`📋 Testing prompt: ${promptData.id}`);
    console.log(`💭 Prompt: ${promptData.prompt}`);
    
    const schemas = await testLlamaAPI(promptData.prompt, `${promptData.id}.json`);
    
    if (schemas) {
      console.log(`✅ Generated ${Array.isArray(schemas) ? schemas.length : 1} schema(s)`);
    } else {
      console.log(`❌ Failed to generate schemas`);
    }
    console.log('─'.repeat(80));
  }
  
  console.log('\n🎯 Test complete! Check generated_schemas/ for AI-generated output.');
}

// Make sure we have the global fetch available
if (typeof fetch === 'undefined') {
  console.log('Installing node-fetch...');
  const { exec } = require('child_process');
  exec('npm install node-fetch@2', (error, stdout, stderr) => {
    if (error) {
      console.error('❌ Failed to install node-fetch:', error);
      console.log('💡 Please install manually: npm install node-fetch@2');
      return;
    }
    console.log('✅ node-fetch installed');
    
    // Import fetch and run tests
    global.fetch = require('node-fetch');
    runTests();
  });
} else {
  runTests();
}
