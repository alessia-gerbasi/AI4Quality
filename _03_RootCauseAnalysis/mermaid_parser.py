"""
Parse a simple Mermaid flowchart back into a schema YAML structure.

Supported syntax (subset of Mermaid graph TD):
  - Decision node:  A{"label"} or A{label}
  - Outcome node:   A["label"] or A[label]
  - Start node:     START([Start]) — ignored
  - YES branch:     A -->|YES| B
  - NO branch:      A -->|NO| B
  - Any edge label other than YES is treated as YES; absent = YES

Questions/conditions are stored as-is in the node label.
The user edits conditions directly in the label text using @var syntax.
"""
import re
import yaml
from typing import Dict, Any


def parse_mermaid_to_schema(mermaid_text: str, existing_schema: Dict = None) -> Dict:
    """Convert Mermaid flowchart text to schema dict.

    Preserves outcome cards from existing_schema when outcome labels match.
    """
    lines = [l.strip() for l in mermaid_text.splitlines() if l.strip()]

    decisions = {}   # node_id -> {question, condition, if_true, if_false}
    outcomes = {}    # node_id -> {label}
    edges = []       # (from, label, to)

    # Parse node definitions
    for line in lines:
        if line.startswith('graph') or line.startswith('START'):
            continue

        # Decision node: id{"text"} or id{text}
        m = re.match(r'^(\w+)\{"?([^"{}]+)"?\}$', line)
        if m:
            node_id, label = m.group(1), m.group(2).strip()
            # Extract condition from label: if it contains @, treat full label as condition
            # Otherwise treat as question (user can put condition in parentheses)
            question, condition = _split_question_condition(label)
            decisions[node_id] = {'question': question, 'condition': condition}
            continue

        # Outcome node: id["text"] or id[text]
        m = re.match(r'^(\w+)\[\"?([^"\[\]]+)\"?\]$', line)
        if m:
            node_id, label = m.group(1), m.group(2).strip()
            if node_id != 'START':
                outcomes[node_id] = {'label': label}
            continue

        # Edge: A -->|LABEL| B  or  A --> B
        m = re.match(r'^(\w+)\s*-->\|([^|]+)\|\s*(\w+)$', line)
        if m:
            edges.append((m.group(1), m.group(2).strip().upper(), m.group(3)))
            continue

        m = re.match(r'^(\w+)\s*-->\s*(\w+)$', line)
        if m:
            edges.append((m.group(1), 'YES', m.group(2)))

    # Wire up edges into decisions
    for (src, label, dst) in edges:
        if src in decisions:
            if label in ('YES', 'TRUE', '1'):
                decisions[src]['if_true'] = dst
            else:
                decisions[src]['if_false'] = dst

    # Build schema, preserving existing outcome cards where label matches
    existing_outcomes = (existing_schema or {}).get('outcomes', {})
    label_to_existing = {v.get('label'): v for v in existing_outcomes.values()}

    schema_outcomes = {}
    for node_id, info in outcomes.items():
        label = info['label']
        if node_id in existing_outcomes:
            # Keep card from same node id
            schema_outcomes[node_id] = existing_outcomes[node_id]
        elif label in label_to_existing:
            # Match by label
            schema_outcomes[node_id] = label_to_existing[label]
        else:
            # New outcome — create a blank card
            schema_outcomes[node_id] = {
                'label': label,
                'card': {
                    'title': f'🔲 {label}',
                    'explanation': 'Add explanation here',
                    'impact': 'Add impact description here',
                    'recommendations': []
                }
            }

    schema_decisions = {}
    for node_id, info in decisions.items():
        schema_decisions[node_id] = {
            'question': info.get('question', node_id),
            'condition': info.get('condition', 'True'),
            'if_true': info.get('if_true', ''),
            'if_false': info.get('if_false', ''),
        }

    schema = {
        'name': (existing_schema or {}).get('name', 'Untitled Schema'),
        'description': (existing_schema or {}).get('description', ''),
        'variables': (existing_schema or {}).get('variables', {}),
        'decisions': schema_decisions,
        'outcomes': schema_outcomes,
    }
    return schema


def _split_question_condition(label: str):
    """Split a Mermaid node label into (question, condition).

    Convention: write the condition in square brackets at the end:
      "Is timing OK? [@time_delta >= 30 AND @time_delta <= 45]"
    If no brackets, the full label is both question and condition.
    """
    m = re.match(r'^(.*?)\[(.+)\]\s*$', label)
    if m:
        question = m.group(1).strip()
        condition = m.group(2).strip()
        return question, condition
    # No brackets: label is question, condition defaults to True (user must set later)
    return label, label


def schema_to_yaml_string(schema: Dict) -> str:
    return yaml.dump(schema, allow_unicode=True, default_flow_style=False, sort_keys=False)
