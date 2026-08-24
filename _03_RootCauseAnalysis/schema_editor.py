"""
Schema Editor — graphical tool to draw decision trees and save them as executable YAML schemas.

Run:  streamlit run schema_editor.py
"""
import streamlit as st
import yaml
from pathlib import Path
from streamlit_flow import streamlit_flow
from streamlit_flow.elements import StreamlitFlowNode, StreamlitFlowEdge
from streamlit_flow.state import StreamlitFlowState
from streamlit_flow.layouts import TreeLayout, ManualLayout

SCHEMA_DIR = Path(__file__).parent / 'schemas'

# ── Helpers ──────────────────────────────────────────────────────────────────

def load_schema(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


def save_schema(schema: dict, path: Path):
    with open(path, 'w') as f:
        yaml.dump(schema, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def schema_to_flow(schema: dict):
    """Convert a schema YAML dict to streamlit-flow nodes and edges."""
    nodes, edges = [], []
    x_step, y_step = 300, 180
    positions = {}

    # Assign positions with a simple BFS from root
    def _bfs_positions(node_id, x, y, visited):
        if node_id in visited:
            return
        visited.add(node_id)
        positions[node_id] = (x, y)
        d = schema.get('decisions', {}).get(node_id)
        if d:
            if d.get('if_true'):
                _bfs_positions(d['if_true'], x - x_step // 2, y + y_step, visited)
            if d.get('if_false'):
                _bfs_positions(d['if_false'], x + x_step // 2, y + y_step, visited)

    _bfs_positions('root', 400, 0, set())

    # Remaining nodes not reached from root
    all_ids = list(schema.get('decisions', {}).keys()) + list(schema.get('outcomes', {}).keys())
    orphan_x = 900
    for nid in all_ids:
        if nid not in positions:
            positions[nid] = (orphan_x, 0)
            orphan_x += 200

    # Decision nodes
    for node_id, d in schema.get('decisions', {}).items():
        question = d.get('question', node_id)
        condition = d.get('condition', '')
        label = f"{question}\n[{condition}]" if condition else question
        x, y = positions.get(node_id, (0, 0))
        nodes.append(StreamlitFlowNode(
            node_id, (x, y),
            {'label': label},
            node_type='default',
            source_position='bottom',
            target_position='top',
            style={'background': '#fff9c4', 'border': '2px solid #f0c040',
                   'borderRadius': '8px', 'padding': '8px', 'fontSize': '12px',
                   'whiteSpace': 'pre-wrap', 'maxWidth': '220px'}
        ))
        if d.get('if_true'):
            edges.append(StreamlitFlowEdge(
                f'{node_id}->yes->{d["if_true"]}', node_id, d['if_true'],
                label='YES', animated=False,
                style={'stroke': '#2e7d32'},
                label_style={'fill': '#2e7d32', 'fontWeight': 'bold'}
            ))
        if d.get('if_false'):
            edges.append(StreamlitFlowEdge(
                f'{node_id}->no->{d["if_false"]}', node_id, d['if_false'],
                label='NO', animated=False,
                style={'stroke': '#c62828'},
                label_style={'fill': '#c62828', 'fontWeight': 'bold'}
            ))

    # Outcome nodes
    for node_id, o in schema.get('outcomes', {}).items():
        label = o.get('label', node_id)
        card_title = o.get('card', {}).get('title', '')
        display = f"{label}\n{card_title}" if card_title else label
        x, y = positions.get(node_id, (0, 0))
        nodes.append(StreamlitFlowNode(
            node_id, (x, y),
            {'label': display},
            node_type='output',
            target_position='top',
            style={'background': '#e8f5e9', 'border': '2px solid #388e3c',
                   'borderRadius': '8px', 'padding': '8px', 'fontSize': '12px',
                   'whiteSpace': 'pre-wrap', 'maxWidth': '200px'}
        ))

    return nodes, edges


def flow_to_schema(state, existing_schema: dict) -> dict:
    """Convert streamlit-flow state back to a schema dict."""
    decisions = {}
    outcomes = {}

    existing_decisions = existing_schema.get('decisions', {})
    existing_outcomes  = existing_schema.get('outcomes', {})

    for node in state.nodes:
        nid = node.id
        label = node.data.get('label', nid)

        # Detect outcome nodes (node_type == 'output')
        if node.node_type == 'output':
            # Preserve existing outcome or create blank
            if nid in existing_outcomes:
                outcomes[nid] = existing_outcomes[nid]
            else:
                # Strip card title from label if present
                clean_label = label.split('\n')[0].strip()
                outcomes[nid] = {
                    'label': clean_label,
                    'card': {
                        'title': f'🔲 {clean_label}',
                        'explanation': 'Add explanation here',
                        'impact': 'Add impact description here',
                        'recommendations': []
                    }
                }
        else:
            # Decision node — extract question and condition from label
            question, condition = _parse_node_label(label)
            base = existing_decisions.get(nid, {})
            decisions[nid] = {
                'question': question,
                'condition': condition or base.get('condition', 'True'),
                'if_true': base.get('if_true', ''),
                'if_false': base.get('if_false', ''),
            }

    # Wire edges
    for edge in state.edges:
        src, dst = edge.source, edge.target
        lbl = (edge.label or 'YES').upper()
        if src in decisions:
            if lbl in ('YES', 'TRUE'):
                decisions[src]['if_true'] = dst
            else:
                decisions[src]['if_false'] = dst

    return {
        'name': existing_schema.get('name', 'Untitled'),
        'description': existing_schema.get('description', ''),
        'variables': existing_schema.get('variables', {}),
        'decisions': decisions,
        'outcomes': outcomes,
    }


def _parse_node_label(label: str):
    """Extract (question, condition) from 'Question text\n[condition]'."""
    import re
    lines = label.split('\n')
    question = lines[0].strip()
    condition = ''
    rest = '\n'.join(lines[1:])
    m = re.search(r'\[(.+)\]', rest)
    if m:
        condition = m.group(1).strip()
    return question, condition


# ── App ───────────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(layout="wide", page_title="Schema Editor")
    st.title("✏️ Schema Editor")

    SCHEMA_DIR.mkdir(exist_ok=True)
    schemas = sorted([f.stem for f in SCHEMA_DIR.glob('*.yaml')])

    # Sidebar
    with st.sidebar:
        st.header("Schema")
        if schemas:
            selected = st.selectbox("Load schema", schemas)
        else:
            selected = None
            st.info("No schemas yet. Create one below.")

        new_name = st.text_input("New schema name (no spaces)")
        if st.button("➕ Create new schema") and new_name.strip():
            name = new_name.strip().replace(' ', '_')
            new_path = SCHEMA_DIR / f'{name}.yaml'
            if not new_path.exists():
                save_schema({'name': name, 'description': '', 'variables': {},
                             'decisions': {
                                 'root': {'question': 'First decision?',
                                         'condition': 'True',
                                         'if_true': 'outcome_yes', 'if_false': 'outcome_no'}
                             },
                             'outcomes': {
                                 'outcome_yes': {'label': 'outcome_yes',
                                                 'card': {'title': '✓ Yes outcome', 'explanation': '',
                                                          'impact': '', 'recommendations': []}},
                                 'outcome_no':  {'label': 'outcome_no',
                                                 'card': {'title': '✗ No outcome', 'explanation': '',
                                                          'impact': '', 'recommendations': []}}
                             }}, new_path)
                st.rerun()

        st.divider()
        st.markdown("""
**How to use:**
1. **Yellow** nodes = decisions (question + condition)
2. **Green** nodes = outcomes (diagnosis labels)
3. Click a node to select it → edit in panel below
4. Drag to move, draw new connections
5. Press **Save** to write YAML

**Node label format:**
```
Your question text
[@variable >= 30 AND @variable <= 45]
```
The condition is in `[brackets]`.
""")

    if not selected:
        st.info("Create a schema using the sidebar.")
        return

    schema_path = SCHEMA_DIR / f'{selected}.yaml'
    schema = load_schema(schema_path)

    # Persist selected node across reruns
    state_key = f'selected_node_{selected}'
    if state_key not in st.session_state:
        st.session_state[state_key] = None

    # Fit view only on first render; afterwards keep current viewport to avoid jumping
    fit_key = f'fitted_{selected}'
    should_fit = not st.session_state.get(fit_key, False)
    if should_fit:
        st.session_state[fit_key] = True

    nodes, edges = schema_to_flow(schema)
    flow_state = StreamlitFlowState(nodes, edges)

    graph_col, props_col = st.columns([2, 1])

    with graph_col:
        st.subheader(f"Schema: {schema.get('name', selected)}")

        state = streamlit_flow(
            f'editor_{selected}',
            flow_state,
            layout=TreeLayout(direction='down') if should_fit else ManualLayout(),
            fit_view=should_fit,
            allow_new_edges=True,
            get_node_on_click=True,
            get_edge_on_click=False,
            pan_on_drag=True,
            show_minimap=True,
            height=550,
        )

        # Update persisted selection only when a node is actually clicked
        if state and state.selected_id:
            st.session_state[state_key] = state.selected_id

        # Re-fit button below graph
        if st.button("🔍 Re-fit view", help="Reset viewport to show all nodes"):
            st.session_state[fit_key] = False
            st.rerun()

        # Add-node controls below the graph
        st.divider()
        st.markdown("**Add a node**")
        ac1, ac2, ac3 = st.columns(3)
        new_node_id = ac1.text_input("Node ID (no spaces)", key="new_node_id", label_visibility="collapsed",
                                      placeholder="e.g. check_access")
        if ac2.button("➕ Decision", use_container_width=True) and new_node_id.strip():
            nid = new_node_id.strip()
            if nid not in schema.get('decisions', {}) and nid not in schema.get('outcomes', {}):
                schema.setdefault('decisions', {})[nid] = {
                    'question': nid, 'condition': 'True', 'if_true': '', 'if_false': ''
                }
                save_schema(schema, schema_path)
                st.session_state[state_key] = nid
                st.rerun()
        if ac3.button("➕ Outcome", use_container_width=True) and new_node_id.strip():
            nid = new_node_id.strip()
            if nid not in schema.get('decisions', {}) and nid not in schema.get('outcomes', {}):
                schema.setdefault('outcomes', {})[nid] = {
                    'label': nid,
                    'card': {'title': f'🔲 {nid}', 'explanation': '', 'impact': '', 'recommendations': []}
                }
                save_schema(schema, schema_path)
                st.session_state[state_key] = nid
                st.rerun()

    with props_col:
        clicked_id = st.session_state[state_key]

        if clicked_id:
            is_decision = clicked_id in schema.get('decisions', {})
            is_outcome  = clicked_id in schema.get('outcomes', {})

            # Deselect / delete header
            hc1, hc2 = st.columns([3, 1])
            hc1.subheader(f"`{clicked_id}`")
            if hc2.button("✖ Deselect"):
                st.session_state[state_key] = None
                st.rerun()

            if is_decision:
                d = schema['decisions'][clicked_id]
                st.caption("Decision node")
                new_q   = st.text_input("Question", value=d.get('question', ''))
                new_c   = st.text_input("Condition", value=d.get('condition', ''),
                                        help="Example: @time_delta >= 30 AND @time_delta <= 45")
                new_yes = st.text_input("→ YES branch (node id)", value=d.get('if_true', ''))
                new_no  = st.text_input("→ NO branch (node id)", value=d.get('if_false', ''))

                bc1, bc2 = st.columns(2)
                if bc1.button("💾 Save", type="primary", use_container_width=True):
                    schema['decisions'][clicked_id] = {
                        'question': new_q, 'condition': new_c,
                        'if_true': new_yes, 'if_false': new_no
                    }
                    save_schema(schema, schema_path)
                    st.rerun()
                if bc2.button("🗑 Delete node", use_container_width=True):
                    schema['decisions'].pop(clicked_id, None)
                    # Remove dangling references
                    for d2 in schema.get('decisions', {}).values():
                        if d2.get('if_true') == clicked_id:  d2['if_true'] = ''
                        if d2.get('if_false') == clicked_id: d2['if_false'] = ''
                    save_schema(schema, schema_path)
                    st.session_state[state_key] = None
                    st.rerun()

            elif is_outcome:
                o    = schema['outcomes'][clicked_id]
                card = o.get('card', {})
                st.caption("Outcome node")
                new_label  = st.text_input("Database label", value=o.get('label', clicked_id))
                new_title  = st.text_input("Card title", value=card.get('title', ''))
                new_expl   = st.text_area("Explanation", value=card.get('explanation', ''), height=80)
                new_impact = st.text_input("Impact", value=card.get('impact', ''))
                recs_text  = '\n'.join(card.get('recommendations', []))
                new_recs   = st.text_area("Recommendations (one per line)", value=recs_text, height=80)

                bc1, bc2 = st.columns(2)
                if bc1.button("💾 Save", type="primary", use_container_width=True):
                    schema['outcomes'][clicked_id] = {
                        'label': new_label,
                        'card': {
                            'title': new_title, 'explanation': new_expl,
                            'impact': new_impact,
                            'recommendations': [r.strip() for r in new_recs.splitlines() if r.strip()]
                        }
                    }
                    save_schema(schema, schema_path)
                    st.rerun()
                if bc2.button("🗑 Delete node", use_container_width=True):
                    schema['outcomes'].pop(clicked_id, None)
                    for d2 in schema.get('decisions', {}).values():
                        if d2.get('if_true') == clicked_id:  d2['if_true'] = ''
                        if d2.get('if_false') == clicked_id: d2['if_false'] = ''
                    save_schema(schema, schema_path)
                    st.session_state[state_key] = None
                    st.rerun()
            else:
                st.info(f"Node `{clicked_id}` not found — it may have been added via the graph canvas. Save the full schema first.")
        else:
            st.subheader("Properties")
            st.info("Click a node in the graph to edit it.")

        st.divider()

        with st.expander("⚙️ Variables (calculations)"):
            vars_yaml = st.text_area(
                "vars", label_visibility="collapsed",
                value=yaml.dump(schema.get('variables', {}), allow_unicode=True, default_flow_style=False),
                height=150
            )

        with st.expander("📝 Name & description"):
            new_name_val = st.text_input("Name", value=schema.get('name', selected))
            new_desc = st.text_area("Description", value=schema.get('description', ''), height=60)

        if st.button("💾 Save full schema (sync graph → YAML)", use_container_width=True):
            try:
                new_schema = flow_to_schema(state, schema)
                try:
                    new_schema['variables'] = yaml.safe_load(vars_yaml) or {}
                except Exception:
                    new_schema['variables'] = schema.get('variables', {})
                new_schema['name'] = new_name_val
                new_schema['description'] = new_desc
                save_schema(new_schema, schema_path)
                st.success("✅ Schema saved as YAML.")
                st.rerun()
            except Exception as e:
                st.error(f"Save failed: {e}")


if __name__ == '__main__':
    main()
