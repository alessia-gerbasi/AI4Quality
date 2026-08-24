import yaml
from typing import Dict, Any, Tuple, List
from pathlib import Path
import re

class RuleEvaluator:
    def __init__(self, schema_path: str, threshold_yaml_path: str):
        self.schema = self._load_yaml(schema_path)
        self.thresholds = self._load_yaml(threshold_yaml_path)
        self.trace = []
    
    def _load_yaml(self, path: str) -> Dict:
        with open(path, 'r') as f:
            return yaml.safe_load(f)

    def _get_procedure_data(self, procedure: str) -> Dict[str, Any]:
        """Return per-procedure thresholds from unified or legacy config formats."""
        if not procedure:
            return {}

        # New unified format
        procedures = self.thresholds.get('procedures', {}) if isinstance(self.thresholds, dict) else {}
        proc = procedures.get(procedure)
        if isinstance(proc, dict):
            phases = proc.get('phases', {})
            if isinstance(phases, dict):
                return phases

        # Legacy format where procedure is top-level
        proc_legacy = self.thresholds.get(procedure, {}) if isinstance(self.thresholds, dict) else {}
        return proc_legacy if isinstance(proc_legacy, dict) else {}
    
    def evaluate(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run schema against patient data, return diagnosis + path trace"""
        self.trace = []
        
        try:
            # 1. Calculate derived variables
            variables = self._calculate_variables(patient_data)
            
            # 2. Traverse decision tree
            outcome_key = self._traverse_decisions(variables, 'root')
            
            # 3. Get outcome card
            if outcome_key not in self.schema.get('outcomes', {}):
                outcome_key = 'outcome_error'
            
            outcome = self.schema.get('outcomes', {}).get(outcome_key, {
                'label': 'error',
                'card': {
                    'title': '❌ Error in evaluation',
                    'explanation': f'Could not reach valid outcome. Last node: {outcome_key}',
                    'impact': 'Schema logic error',
                    'recommendations': ['Review schema decision paths']
                }
            })
            
            return {
                'diagnosis_label': outcome.get('label', 'unknown'),
                'card': outcome.get('card', {}),
                'decision_path': self.trace,
                'calculated_variables': variables,
                'success': True
            }
        except Exception as e:
            return {
                'diagnosis_label': 'error',
                'card': {
                    'title': '❌ Evaluation Error',
                    'explanation': str(e),
                    'impact': 'Rule evaluation failed',
                    'recommendations': ['Check patient data and schema format']
                },
                'decision_path': self.trace,
                'calculated_variables': {},
                'success': False
            }
    
    def _calculate_variables(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate derived variables from patient data + thresholds"""
        variables = {}
        
        if 'variables' not in self.schema:
            return variables
        
        for var_name, var_def in self.schema['variables'].items():
            try:
                if 'calculation' in var_def:
                    expr = var_def['calculation']
                    expr = self._substitute_refs(expr, patient_data, self.thresholds)
                    variables[var_name] = eval(expr)
                elif 'source' in var_def:
                    variables[var_name] = self._lookup_threshold(var_def, patient_data)
            except Exception as e:
                variables[var_name] = f"ERROR: {str(e)}"
        
        return variables
    
    def _substitute_refs(self, expr: str, patient_data: Dict, thresholds: Dict) -> str:
        """Substitute @{Column Name}, @simple_name, and $param references.

        Syntax:
          @{Column Name With Spaces}  → value from patient_data (Excel column)
          @simple_name                → value from patient_data or calculated variables
          $param.phase.field.index    → value from roi_hu_timing_table for current procedure
             e.g. $arteriosa.timing.0  → thresholds[procedure]['arteriosa']['timing'][0]
        """
        # 1. @{Column Name With Spaces}
        for match in re.findall(r'@\{([^}]+)\}', expr):
            val = patient_data.get(match)
            if val is not None:
                replacement = f"'{val}'" if isinstance(val, str) else str(val)
            else:
                replacement = 'None'
            expr = expr.replace(f'@{{{match}}}', replacement)

        # 2. @simple_name
        for ref in re.findall(r'@(\w+)', expr):
            val = patient_data.get(ref)
            if val is not None:
                replacement = f"'{val}'" if isinstance(val, str) else str(val)
                expr = expr.replace(f'@{ref}', replacement)
            else:
                # Substitute None so Python eval can handle it gracefully
                expr = expr.replace(f'@{ref}', 'None')

        # 3. $phase.field.index  — lookup from threshold table for current procedure
        procedure = patient_data.get('Order Procedure') or patient_data.get('procedure_code', '')
        for ref in re.findall(r'\$([\w.]+)', expr):
            val = self._resolve_param(ref, procedure)
            if val is not None:
                expr = expr.replace(f'${ref}', str(val))

        # Convert logical operators to Python syntax
        expr = expr.replace(' AND ', ' and ')
        expr = expr.replace(' OR ', ' or ')
        expr = expr.replace('NOT ', 'not ')

        return expr

    def _resolve_param(self, ref: str, procedure: str) -> Any:
        """Resolve $phase.field.index from roi_hu_timing_table.

        Examples:
          $arteriosa.timing.0   → thresholds[procedure]['arteriosa']['timing'][0]
          $arteriosa.HU.1       → thresholds[procedure]['arteriosa']['HU'][1]
          $venosa.HU_delta.0    → thresholds[procedure]['venosa']['HU_delta'][0]
        """
        parts = ref.split('.')
        if len(parts) < 2:
            return None
        proc_data = self._get_procedure_data(procedure)
        if not proc_data:
            return None
        phase = parts[0]
        field = parts[1] if len(parts) > 1 else None
        index = int(parts[2]) if len(parts) > 2 else None

        phase_data = proc_data.get(phase, {})
        if not isinstance(phase_data, dict) or not field:
            return None
        values = phase_data.get(field)
        if values is None:
            return None
        if index is not None and isinstance(values, list):
            base_value = values[index] if index < len(values) else None
            return self._apply_timing_adjustment(base_value, field)
        return self._apply_timing_adjustment(values, field)

    def _lookup_threshold(self, var_def: Dict, patient_data: Dict) -> Any:
        """Lookup threshold for source: roi_hu_timing_table variables."""
        procedure = (patient_data.get('Order Procedure')
                     or patient_data.get('procedure_code', 'TACPEC'))
        phase = var_def.get('phase', 'arteriosa')
        field = var_def.get('field', 'timing')
        index = var_def.get('index')

        proc_data = self._get_procedure_data(procedure)
        phase_data = proc_data.get(phase, {})
        if not isinstance(phase_data, dict):
            return None
        values = phase_data.get(field)
        if values is None:
            return None
        if index is not None and isinstance(values, list):
            base_value = values[index] if index < len(values) else None
            return self._apply_timing_adjustment(base_value, field, patient_data)
        return self._apply_timing_adjustment(values, field, patient_data)

    def _apply_timing_adjustment(self, value: Any, field: str, patient_data: Dict = None) -> Any:
        """Apply global timing adjustment by access type when field is timing."""
        if value is None:
            return None
        if field != 'timing':
            return value

        # Access value from injection history column.
        if patient_data is None:
            return value
        access_type = str(patient_data.get('Needle Access', '')).strip().lower()
        if not access_type:
            return value

        adjustments = self.thresholds.get('timing_adjustments', {}).get('by_access', [])
        delta = 0
        for rule in adjustments:
            rule_access = str(rule.get('access_type', '')).strip().lower()
            if rule_access and rule_access == access_type:
                delta = rule.get('offset_seconds', 0)
                break

        if isinstance(value, list):
            return [v + delta for v in value]
        if isinstance(value, (int, float)):
            return value + delta
        return value
    
    def _traverse_decisions(self, variables: Dict, node_key: str = 'root') -> str:
        """Recursively traverse decision tree"""
        if node_key in self.schema.get('outcomes', {}):
            return node_key
        
        decisions = self.schema.get('decisions', {})
        if node_key not in decisions:
            return 'outcome_error'
        
        node = decisions[node_key]
        question = node.get('question', 'unnamed decision')
        condition = node.get('condition', 'True')
        
        # Evaluate condition
        expr = self._substitute_refs(condition, variables, {})
        try:
            result = eval(expr)
        except Exception as e:
            result = False
        
        # Record in trace
        self.trace.append({
            'node': node_key,
            'question': question,
            'condition': condition,
            'substituted_condition': expr,
            'result': result
        })
        
        # Follow branch
        next_node = node.get('if_true') if result else node.get('if_false')
        if not next_node:
            return node_key
        
        return self._traverse_decisions(variables, next_node)
