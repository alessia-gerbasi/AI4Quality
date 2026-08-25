import yaml
from typing import Dict, Any, Tuple, List
from pathlib import Path
import math
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
                return {**phases, **{key: value for key, value in proc.items() if key != 'phases'}}

        # Legacy format where procedure is top-level
        proc_legacy = self.thresholds.get(procedure, {}) if isinstance(self.thresholds, dict) else {}
        return proc_legacy if isinstance(proc_legacy, dict) else {}
    
    def evaluate(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run schema against patient data, return diagnosis + path trace"""
        self.trace = []
        
        try:
            prepared_data = self._prepare_patient_data(patient_data)

            # 1. Calculate derived variables
            variables = self._calculate_variables(prepared_data)
            
            # 2. Traverse either an independent checklist or a decision tree.
            if self.schema.get('independent_checks'):
                return self._evaluate_independent_checks(prepared_data, variables)
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
            display_context = {**prepared_data, **variables}
            
            return {
                'diagnosis_label': outcome.get('label', 'unknown'),
                'card': self._render_card(outcome.get('card', {}), display_context),
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

    def _evaluate_independent_checks(self, prepared_data: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate every checklist item and combine all failed outcomes."""
        display_context = {**prepared_data, **variables}
        failures = []

        for check in self.schema.get('independent_checks', []):
            name = check.get('name', 'unnamed_check')
            condition = check.get('condition', 'False')
            available_condition = check.get('available_condition')
            available = True
            if available_condition:
                available = self._evaluate_condition(available_condition, variables)
                self.trace.append({
                    'node': name,
                    'question': check.get('question', name),
                    'condition': available_condition,
                    'substituted_condition': self._substitute_refs(available_condition, variables, {}),
                    'result': available,
                })

            if not available:
                if check.get('skip_if_unavailable'):
                    continue
                outcome_key = check.get('missing_outcome', 'outcome_missing_data')
                passed = False
            elif check.get('report_outcome'):
                if self._evaluate_condition(check.get('condition', 'False'), variables):
                    failures.append(check['report_outcome'])
                elif check.get('high_condition') and self._evaluate_condition(check['high_condition'], variables):
                    failures.append(check.get('high_outcome', check['report_outcome']))
                else:
                    failures.append(check.get('low_outcome', check['report_outcome']))
                continue
            else:
                substituted = self._substitute_refs(condition, variables, {})
                passed = self._evaluate_condition(condition, variables)
                self.trace.append({
                    'node': name,
                    'question': check.get('question', name),
                    'condition': condition,
                    'substituted_condition': substituted,
                    'result': passed,
                })
                if passed:
                    outcome_key = None
                elif check.get('high_condition') and self._evaluate_condition(check['high_condition'], variables):
                    outcome_key = check.get('high_outcome', check.get('outcome'))
                else:
                    outcome_key = check.get('low_outcome', check.get('outcome'))

            if not passed and outcome_key:
                failures.append(outcome_key)

        if not failures:
            outcome_keys = ['outcome_protocol_ok']
        else:
            outcome_keys = list(dict.fromkeys(failures))

        outcomes = self.schema.get('outcomes', {})
        cards = [self._render_card(outcomes[key].get('card', {}), display_context)
                 for key in outcome_keys if key in outcomes]
        if not cards:
            raise ValueError('Independent checks did not resolve to valid outcomes')

        labels = [outcomes[key].get('label', 'unknown') for key in outcome_keys if key in outcomes]
        recommendations = list(dict.fromkeys(
            recommendation
            for card in cards
            for recommendation in card.get('recommendations', [])
        ))
        combined_card = {
            'title': cards[0].get('title', 'Protocol analysis') if len(cards) == 1 else 'Protocol check results',
            'explanation': '\n'.join(card.get('explanation', '') for card in cards),
            'impact': '\n'.join(card.get('impact', '') for card in cards),
            'recommendations': recommendations,
        }
        return {
            'diagnosis_label': labels[0] if labels else 'unknown',
            'diagnoses': labels,
            'cards': cards,
            'card': combined_card,
            'decision_path': self.trace,
            'calculated_variables': variables,
            'success': True,
        }

    def _evaluate_condition(self, condition: str, variables: Dict[str, Any]) -> bool:
        try:
            return bool(eval(self._substitute_refs(condition, variables, {})))
        except Exception:
            return False
    
    def _calculate_variables(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate derived variables from patient data + thresholds"""
        variables = {}
        context = dict(patient_data or {})
        
        if 'variables' not in self.schema:
            return variables
        
        for var_name, var_def in self.schema['variables'].items():
            try:
                if 'calculation' in var_def:
                    expr = var_def['calculation']
                    expr = self._substitute_refs(expr, context, self.thresholds)
                    variables[var_name] = eval(expr)
                elif 'source' in var_def:
                    variables[var_name] = self._lookup_threshold(var_def, context)
            except Exception as e:
                variables[var_name] = f"ERROR: {str(e)}"
            context[var_name] = variables[var_name]
        
        return variables

    def _prepare_patient_data(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        prepared = dict(patient_data or {})

        phase_value = prepared.get('_phase') or prepared.get('phase_name') or ''
        prepared['_phase_norm'] = str(phase_value).strip().lower()

        prepared['_acquisition_time_seconds'] = self._parse_dicom_time_to_seconds(
            prepared.get('_current_acquisition_time')
            or prepared.get('acquisition_time')
            or prepared.get('AcquisitionTime')
        )
        prepared['_contrast_bolus_start_seconds'] = self._parse_dicom_time_to_seconds(
            prepared.get('_current_contrast_bolus_start')
            or prepared.get('contrast_bolus_start')
            or prepared.get('ContrastBolusStartTime')
        )
        prepared['_arterial_acquisition_time_seconds'] = self._parse_dicom_time_to_seconds(
            prepared.get('_arterial_acquisition_time')
        )
        prepared['_arterial_contrast_bolus_start_seconds'] = self._parse_dicom_time_to_seconds(
            prepared.get('_arterial_contrast_bolus_start')
        )

        phase_details = self._parse_actual_phase_details(prepared.get('Actual Phase Details'))
        prepared['_parsed_actual_phase_details'] = phase_details
        prepared['_contrast_duration_seconds'] = self._extract_contrast_duration_seconds(
            phase_details,
            prepared,
        )
        prepared['_needle_access_normalized'] = self._normalize_text(prepared.get('Needle Access'))
        prepared['_timing_access_offset_seconds'] = self._resolve_timing_adjustment_seconds(prepared)
        prepared['_contrast_flow_rate_from_data_points'] = self._extract_contrast_flow_rate(
            prepared.get('Actual Flow-Rate Data Points')
        )
        prepared['_protocol_mismatch_details'] = self._protocol_mismatch_details(prepared)

        return prepared

    def _extract_contrast_flow_rate(self, value: Any) -> Any:
        if self._is_missing_value(value):
            return None
        text = str(value)
        contrast_blocks = re.findall(
            r'PhaseType\s*:\s*Contrast.*?\[Time,\s*Value\]\s*:\s*(.*?);\s*\]',
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        samples = []
        for block in contrast_blocks:
            samples.extend(float(raw_value) for raw_value in re.findall(
                r'\[\s*[-+]?\d+(?:\.\d+)?\s*,\s*([-+]?\d+(?:\.\d+)?)\s*\]',
                block,
            ))
        return sum(samples) / len(samples) if samples else None

    def _protocol_mismatch_details(self, patient_data: Dict[str, Any]) -> str:
        comparisons = [
            ('Contrast volume', 'Programmed Total Contrast Volume (mL)', 'Actual Total Contrast Volume Injected (mL)'),
            ('Contrast dose', 'Programmed Total Contrast Dose (gI)', 'Actual Total Contrast Dose (gI)'),
            ('Saline volume', 'Programmed Total Saline Volume (mL)', 'Actual Total Saline Volume Injected (mL)'),
        ]
        mismatches = []
        for label, programmed_key, actual_key in comparisons:
            programmed = patient_data.get(programmed_key)
            actual = patient_data.get(actual_key)
            if self._is_missing_value(programmed) or self._is_missing_value(actual):
                mismatches.append(f'{label}: programmed={self._format_display_value(programmed)}, actual={self._format_display_value(actual)}')
                continue
            try:
                equal = abs(float(programmed) - float(actual)) <= 2
            except (TypeError, ValueError):
                equal = str(programmed).strip() == str(actual).strip()
            if not equal:
                mismatches.append(f'{label}: programmed={self._format_display_value(programmed)}, actual={self._format_display_value(actual)}')
        return '; '.join(mismatches) if mismatches else 'No mismatches'
    
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
            if not self._is_missing_value(val):
                replacement = repr(val) if isinstance(val, str) else str(val)
            else:
                replacement = 'None'
            expr = expr.replace(f'@{{{match}}}', replacement)

        # 2. @simple_name
        for ref in re.findall(r'@(\w+)', expr):
            val = patient_data.get(ref)
            if not self._is_missing_value(val):
                replacement = repr(val) if isinstance(val, str) else str(val)
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

    def _is_missing_value(self, value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip().lower() in {'', 'nan', 'none', 'null'}
        try:
            return bool(math.isnan(value))
        except (TypeError, ValueError):
            return False

    def _render_card(self, card: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        rendered = {}
        for key, value in (card or {}).items():
            if isinstance(value, str):
                rendered[key] = self._interpolate_text(value, context)
            elif isinstance(value, list):
                rendered[key] = [self._interpolate_text(item, context) if isinstance(item, str) else item for item in value]
            else:
                rendered[key] = value
        return rendered

    def _interpolate_text(self, template: str, context: Dict[str, Any]) -> str:
        if not isinstance(template, str):
            return template

        def replace_braced(match: re.Match[str]) -> str:
            return self._format_display_value(context.get(match.group(1)))

        def replace_simple(match: re.Match[str]) -> str:
            return self._format_display_value(context.get(match.group(1)))

        result = re.sub(r'@\{([^}]+)\}', replace_braced, template)
        result = re.sub(r'@(\w+)', replace_simple, result)
        return result

    def _format_display_value(self, value: Any) -> str:
        if value is None:
            return 'N/A'
        if isinstance(value, float):
            if value.is_integer():
                return str(int(value))
            return f"{value:.2f}".rstrip('0').rstrip('.')
        return str(value)

    def _parse_dicom_time_to_seconds(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, float) and str(value) == 'nan':
            return None

        text = str(value).strip()
        if not text or text.lower() == 'nan':
            return None

        try:
            raw = float(text)
        except ValueError:
            return None

        hhmmss = int(raw)
        frac = raw - hhmmss
        hh = hhmmss // 10000
        mm = (hhmmss % 10000) // 100
        ss = hhmmss % 100
        if not (0 <= hh < 24 and 0 <= mm < 60 and 0 <= ss < 60):
            return None
        return hh * 3600 + mm * 60 + ss + frac

    def _parse_actual_phase_details(self, value: Any) -> List[Dict[str, Any]]:
        if value is None:
            return []
        if isinstance(value, float) and str(value) == 'nan':
            return []

        text = str(value).strip()
        if not text or text.lower() == 'nan':
            return []

        entries: List[Dict[str, Any]] = []
        for block in re.findall(r'\[([^\]]+)\]', text):
            entry: Dict[str, Any] = {}
            for part in block.split(','):
                if ':' not in part:
                    continue
                raw_key, raw_val = part.split(':', 1)
                key = re.sub(r'[^A-Za-z0-9]+', '', raw_key.strip())
                val = raw_val.strip()
                if not key:
                    continue
                entry[key] = self._coerce_scalar(val)
            if entry:
                entries.append(entry)
        return entries

    def _coerce_scalar(self, value: str) -> Any:
        text = str(value).strip()
        if not text:
            return None
        try:
            numeric = float(text)
        except ValueError:
            return text
        return int(numeric) if numeric.is_integer() else numeric

    def _extract_contrast_duration_seconds(self, phase_details: List[Dict[str, Any]], patient_data: Dict[str, Any]) -> Any:
        duration = self._extract_duration_from_phase_bounds(phase_details)
        if duration is not None:
            return duration

        duration = self._extract_duration_from_volume_rate(phase_details)
        if duration is not None:
            return duration

        contrast_volume = self._as_float(
            patient_data.get('Actual Total Contrast Volume Injected (mL)')
            or patient_data.get('Total Contrast Injected (mL)')
        )
        flow_rate = self._as_float(patient_data.get('Actual Contrast Avg Rate (mL/s)'))
        if contrast_volume is not None and flow_rate not in (None, 0):
            return contrast_volume / flow_rate
        return None

    def _extract_duration_from_phase_bounds(self, phase_details: List[Dict[str, Any]]) -> Any:
        for entry in phase_details:
            if not self._is_contrast_phase(entry):
                continue
            start = self._first_numeric(entry, ['ContrastStartSecond', 'StartSecond'])
            stop = self._first_numeric(entry, ['NextPhaseStartSecond', 'EndSecond', 'StopSecond'])
            if start is not None and stop is not None and stop >= start:
                return stop - start
        return None

    def _extract_duration_from_volume_rate(self, phase_details: List[Dict[str, Any]]) -> Any:
        total_duration = 0.0
        found = False
        for entry in phase_details:
            if not self._is_contrast_phase(entry):
                continue
            volume = self._first_numeric(entry, ['ActualVolume', 'Volume'])
            rate = self._first_numeric(entry, ['ActualFlowRate', 'FlowRate'])
            if volume is None or rate in (None, 0):
                continue
            total_duration += volume / rate
            found = True
        return total_duration if found else None

    def _is_contrast_phase(self, entry: Dict[str, Any]) -> bool:
        phase_type = entry.get('PhaseType')
        if isinstance(phase_type, (int, float)):
            return int(phase_type) == 0
        if isinstance(phase_type, str):
            normalized = phase_type.strip().lower()
            return normalized in {'0', 'contrast'}
        return False

    def _first_numeric(self, entry: Dict[str, Any], keys: List[str]) -> Any:
        for key in keys:
            value = self._as_float(entry.get(key))
            if value is not None:
                return value
        return None

    def _as_float(self, value: Any) -> Any:
        if value is None:
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        if str(numeric) == 'nan':
            return None
        return numeric

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
        if field in proc_data:
            values = proc_data.get(field)
        else:
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
        delta = self._resolve_timing_adjustment_seconds(patient_data)

        if isinstance(value, list):
            return [v + delta for v in value]
        if isinstance(value, (int, float)):
            return value + delta
        return value

    def _resolve_timing_adjustment_seconds(self, patient_data: Dict[str, Any]) -> int | float:
        access_type = self._normalize_text(patient_data.get('Needle Access'))
        if not access_type:
            return 0

        adjustments = self.thresholds.get('timing_adjustments', {}).get('by_access', [])
        for rule in adjustments:
            match_values = self._rule_match_values(rule)
            if access_type in match_values:
                return rule.get('offset_seconds', 0)
        return 0

    def _rule_match_values(self, rule: Dict[str, Any]) -> set[str]:
        values = set()
        for key in ('access_type', 'label'):
            normalized = self._normalize_text(rule.get(key))
            if normalized:
                values.add(normalized)

        for list_key in ('access_types', 'match_values', 'aliases'):
            raw_values = rule.get(list_key, [])
            if isinstance(raw_values, list):
                for item in raw_values:
                    normalized = self._normalize_text(item)
                    if normalized:
                        values.add(normalized)
        return values

    def _normalize_text(self, value: Any) -> str:
        if value is None:
            return ''
        return str(value).strip().lower()
    
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
