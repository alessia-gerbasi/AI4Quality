import yaml
from typing import Dict, Set
from pathlib import Path

class SchemaMermaidConverter:
    def __init__(self, schema_path: str):
        with open(schema_path, 'r') as f:
            self.schema = yaml.safe_load(f)
    
    def to_mermaid(self) -> str:
        """Convert schema to Mermaid flowchart syntax"""
        lines = ['graph TD']
        
        # Collect all nodes
        decisions = self.schema.get('decisions', {})
        outcomes = self.schema.get('outcomes', {})
        
        # Add decision nodes
        for node_key, node_def in decisions.items():
            question = node_def.get('question', node_key)
            # Sanitize for Mermaid: remove special chars that break syntax
            safe_question = question[:50]  # Limit length
            # Remove problematic characters
            safe_question = safe_question.replace('"', "'")  # Replace quotes with single quotes
            safe_question = safe_question.replace('(', ' ')
            safe_question = safe_question.replace(')', ' ')
            safe_question = safe_question.replace('?', '')
            lines.append(f'  {node_key}{{"{node_key}<br/>{safe_question}"}}')
        
        # Add outcome nodes
        for outcome_key, outcome_def in outcomes.items():
            label = outcome_def.get('label', outcome_key)
            label = label.replace('"', "'")
            lines.append(f'  {outcome_key}["{label}"]')
        
        # Add edges
        if 'root' in decisions:
            lines.append('  START([Start]) --> root')
        
        for node_key, node_def in decisions.items():
            if_true = node_def.get('if_true')
            if_false = node_def.get('if_false')
            
            if if_true:
                lines.append(f'  {node_key} -->|YES| {if_true}')
            if if_false:
                lines.append(f'  {node_key} -->|NO| {if_false}')
        
        return '\n'.join(lines)
    
    def save_mermaid_md(self, output_path: str):
        """Save as Markdown with embedded Mermaid"""
        mermaid_code = self.to_mermaid()
        md_content = f'''# Schema: {self.schema.get('name', 'Unnamed')}

{self.schema.get('description', '')}

## Decision Tree

```mermaid
{mermaid_code}
```

## Schema Details

**Variables**: {len(self.schema.get('variables', {}))} derived variables
**Decisions**: {len(self.schema.get('decisions', {}))} decision nodes  
**Outcomes**: {len(self.schema.get('outcomes', {}))} possible outcomes
'''
        Path(output_path).write_text(md_content)
        print(f"Saved Mermaid diagram to {output_path}")
