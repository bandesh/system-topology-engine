#!/usr/bin/env python3
import os
import re
import sys
import json
import argparse
import codecs
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

class UniversalTopologyEngine:
    def __init__(self, root_dir, config_path=None):
        self.root_dir = os.path.abspath(root_dir)
        self.graph = defaultdict(set)
        self.file_metadata = {}
        self.lock = threading.Lock()
        
        # Default enterprise ignore boundaries
        self.ignore_dirs = {
            '.git', 'node_modules', 'venv', '.venv', '__pycache__', 
            'dist', 'build', '.next', 'out', 'target', '.ideas',
            'ios', 'android', 'public', 'assets', '.turbo', 'vendor'
        }
        self.ignore_files = {
            'get-pip.py', 'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
            'postcss.config.js', 'tailwind.config.js', 'vite.config.js', 'tsconfig.json'
        }
        self.noise_keywords = {'ui', 'styles', 'footer', 'navbar', 'toast', 'button', 'spec', 'test'}
        
        # 🌐 Extended Polyglot Language Registry Mapping
        self.lang_registry = {
            ".ts": {"regex": [re.compile(r'(?:import|require|from)\s+[\'"]?([@\w\.\/\-]+)[\'"]?')], "type": "typescript"},
            ".tsx": {"regex": [re.compile(r'(?:import|require|from)\s+[\'"]?([@\w\.\/\-]+)[\'"]?')], "type": "typescript"},
            ".js": {"regex": [re.compile(r'(?:import|require|from)\s+[\'"]?([@\w\.\/\-]+)[\'"]?')], "type": "javascript"},
            ".jsx": {"regex": [re.compile(r'(?:import|require|from)\s+[\'"]?([@\w\.\/\-]+)[\'"]?')], "type": "javascript"},
            ".py": {"regex": [re.compile(r'^\s*(?:import|from)\s+([\w\.\-]+)')], "type": "python"},
            ".go": {"regex": [re.compile(r'import\s+["\']([^"\']+)["\']'), re.compile(r'"([\w\.\/\-]+)"')], "type": "go"},
            ".rs": {"regex": [re.compile(r'^\s*(?:use)\s+([\w\.\:\-]+)')], "type": "rust"},
            ".java": {"regex": [re.compile(r'^\s*import\s+([\w\.\-\*]+);')], "type": "java"},
            ".cs": {"regex": [re.compile(r'^\s*using\s+([\w\.\-]+);')], "type": "csharp"}
        }

        # Global Intent Analyzer Definitions
        self.intent_patterns = {
            "generation": re.compile(r'(openai|anthropic|llm|generate|prompt|completion|ai|agent|predict|inference)', re.IGNORECASE),
            "critic_validation": re.compile(r'(validate|verify|check|schema|zod|yup|audit|validator|assert|guard)', re.IGNORECASE),
            "async_orchestration": re.compile(r'(queue|worker|bullmq|cron|job|process|async|events|pubsub|kafka|amqp|task)', re.IGNORECASE),
            "state_storage": re.compile(r'(supabase|prisma|db|database|client|storage|cache|redis|postgres|mongo|sql)', re.IGNORECASE)
        }

        if config_path:
            self._load_external_config(config_path)
        else:
            rc_fallback = os.path.join(self.root_dir, '.topologyrc.json')
            if os.path.exists(rc_fallback):
                self._load_external_config(rc_fallback)

    def _load_external_config(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                if "ignore_dirs" in cfg: self.ignore_dirs.update(cfg["ignore_dirs"])
                if "ignore_files" in cfg: self.ignore_files.update(cfg["ignore_files"])
                if "noise_keywords" in cfg: self.noise_keywords.update(cfg["noise_keywords"])
                print(f"⚙️  Configuration Profile Layer Loaded Successfully: {path}")
        except Exception as e:
            print(f"⚠️  Failed to ingest system config profile ({str(e)}). Defaulting to standard engine state.")

    def normalize_path_key(self, rel_path):
        return os.path.splitext(rel_path.replace('\\', '/'))[0]

    def resolve_import_to_component(self, current_file_key, import_string, internal_components):
        clean_token = import_string.strip(" '\"();;").replace('\\', '/').split('@')[-1]
        token_base = clean_token.split('/')[-1]
        
        if not token_base:
            return None

        if clean_token.startswith('.'):
            current_dir = os.path.dirname(current_file_key)
            parts = clean_token.split('/')
            dir_parts = current_dir.split('/') if current_dir else []
            for p in parts:
                if p == '..':
                    if dir_parts: dir_parts.pop()
                elif p != '.' and p:
                    dir_parts.append(p)
            resolved_rel = "/".join(dir_parts)
            if resolved_rel in internal_components:
                return resolved_rel

        for comp in internal_components:
            if comp.endswith('/' + clean_token) or comp == clean_token or comp.endswith('/' + token_base):
                if comp != current_file_key:
                    return comp
        return None

    def _process_single_file(self, filepath, raw_imports_dict):
        ext = os.path.splitext(filepath)[1].lower()
        if ext not in self.lang_registry:
            return

        rel_path = os.path.relpath(filepath, self.root_dir)
        component_key = self.normalize_path_key(rel_path)
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.splitlines()
                
                intents = []
                for intent_name, pattern in self.intent_patterns.items():
                    if pattern.search(content) or intent_name in component_key.lower():
                        intents.append(intent_name)

                with self.lock:
                    self.file_metadata[component_key] = {
                        "path": rel_path,
                        "loc": len(lines),
                        "ext": ext,
                        "type": self.lang_registry[ext]["type"],
                        "intents": intents
                    }
                
                local_imports = []
                for pattern in self.lang_registry[ext]["regex"]:
                    for match in pattern.findall(content):
                        if match:
                            local_imports.append(match)
                
                if local_imports:
                    with self.lock:
                        raw_imports_dict[component_key].extend(local_imports)
        except Exception:
            return

    def scan_repository(self):
        raw_imports = defaultdict(list)
        files_to_process = []

        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]
            for file in files:
                if file in self.ignore_files:
                    continue
                files_to_process.append(os.path.join(root, file))

        max_workers = min(32, (os.cpu_count() or 1) * 4)
        print(f"🚀 Initializing Concurrent Ingestion Pool using {max_workers} operational workers...")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self._process_single_file, fp, raw_imports) for fp in files_to_process]
            for future in as_completed(futures):
                pass 

        internal_components = set(self.file_metadata.keys())
        for source_key, imports in raw_imports.items():
            for imp in imports:
                resolved_target = self.resolve_import_to_component(source_key, imp, internal_components)
                if resolved_target:
                    self.graph[source_key].add(resolved_target)

    def detect_structural_loops(self):
        visited = set()
        stack = set()
        current_path = []
        cycles = []

        def dfs(node):
            if node in stack:
                idx = current_path.index(node)
                short_cycle = [ "/".join(n.split('/')[-2:]) for n in current_path[idx:] ] + ["/".join(node.split('/')[-2:])]
                cycles.append(" -> ".join(short_cycle))
                return
            if node in visited:
                return

            visited.add(node)
            stack.add(node)
            current_path.append(node)
            for neighbor in self.graph.get(node, []):
                dfs(neighbor)
            current_path.pop()
            stack.remove(node)

        for component in list(self.file_metadata.keys()):
            dfs(component)
        return list(set(cycles))

    def analyze_intelligent_loops(self):
        fan_in = defaultdict(int)
        fan_out = defaultdict(int)

        for source, targets in self.graph.items():
            fan_out[source] = len(targets)
            for t in targets:
                fan_in[t] += 1

        opportunities = {
            "actor_critic_pairs": [],
            "state_driven_workers": [],
            "governance_veto_gates": []
        }

        for comp, meta in self.file_metadata.items():
            if any(kw in comp.lower() for kw in self.noise_keywords):
                continue

            in_deg = fan_in[comp]
            out_deg = fan_out[comp]
            intents = meta["intents"]
            display_name = f"[{meta['type'].upper()}] " + "/".join(comp.split('/')[-2:])

            if "generation" in intents or (out_deg > 2 and "critic_validation" in intents):
                opportunities["actor_critic_pairs"].append({
                    "component": display_name, "path": meta["path"],
                    "reason": "Execution sequence processing raw data generation loops. Perfect self-correction vector."
                })

            if "async_orchestration" in intents or "worker" in comp.lower() or "job" in comp.lower():
                opportunities["state_driven_workers"].append({
                    "component": display_name, "path": meta["path"],
                    "reason": f"Background transaction processor structure ({meta['loc']} LOC). Ideal for decoupling state loops."
                })

            if in_deg >= 4 and ("state_storage" in intents or "context" in comp.lower() or "config" in comp.lower()):
                opportunities["governance_veto_gates"].append({
                    "component": display_name, "path": meta["path"],
                    "reason": f"High gravity operational node with {in_deg} inputs. Requires decoupled verification guardrails."
                })

        return opportunities

    def generate_textual_tree(self):
        in_degrees = defaultdict(int)
        for source, targets in self.graph.items():
            for t in targets:
                in_degrees[t] += 1
        
        roots = [comp for comp in self.file_metadata if in_degrees[comp] == 0]
        if not roots:
            min_in = min(in_degrees.values()) if in_degrees else 0
            roots = [comp for comp in self.file_metadata if in_degrees[comp] == min_in]
            
        roots.sort()
        tree_output = []

        def recurse_tree(node, prefix="", is_last=True, trace_history=None):
            if trace_history is None: trace_history = set()
            short_name = f"[{self.file_metadata[node]['type'].upper()}] " + "/".join(node.split("/")[-2:])
            branch_pointer = "└── " if is_last else "├── "
            
            if node in trace_history:
                tree_output.append(f"{prefix}{branch_pointer}🔄 {short_name} (Cycle Breakpoint)")
                return
                
            tree_output.append(f"{prefix}{branch_pointer}{short_name}")
            children = sorted(list(self.graph.get(node, [])))
            if children:
                nested_prefix = prefix + ("    " if is_last else "│   ")
                extended_history = trace_history | {node}
                for index, child in enumerate(children):
                    if index > 10:  
                        tree_output.append(f"{nested_prefix}└── ... (Truncated excessive lateral components)")
                        break
                    recurse_tree(child, nested_prefix, index == len(children) - 1, extended_history)

        for idx, root in enumerate(roots[:15]):
            recurse_tree(root, "", idx == len(roots[:15]) - 1)
        return "\n".join(tree_output) if tree_output else "  ⚠️ No traceable execution boundaries found."

    def generate_html_graph(self, output_html_path):
        print(f"\n🌐 Compiling global interactive visual database...")
        nodes_js = []
        edges_js = []
        node_to_id = {}
        idx = 1
        
        color_palette = {
            "typescript": "#3178c6", "javascript": "#f1e05a", "python": "#3572a5",
            "go": "#00add8", "rust": "#dea584", "java": "#b07219", "csharp": "#178600"
        }

        for comp, meta in self.file_metadata.items():
            short_name = "/".join(comp.split("/")[-2:])
            node_to_id[comp] = idx
            base_color = color_palette.get(meta["type"], "#64748b")
                
            nodes_js.append({
                "id": idx,
                "label": short_name,
                "title": f"Namespace: {comp}<br>Engine Stack: {meta['type'].upper()}<br>Volume: {meta['loc']} LOC",
                "color": {"background": base_color, "border": "#1e293b", "highlight": {"background": "#ffffff", "border": "#0f172a"}},
                "font": {"color": "#ffffff", "size": 11}
            })
            idx += 1
            
        for source, targets in self.graph.items():
            src_id = node_to_id.get(source)
            for t in targets:
                tgt_id = node_to_id.get(t)
                if src_id and tgt_id:
                    edges_js.append({
                        "from": src_id, "to": tgt_id, "arrows": "to", 
                        "color": {"color": "#475569", "opacity": 0.4, "highlight": "#f8fafc"},
                        "width": 1.2
                    })

        html_template = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Enterprise Topology Map</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style type="text/css">
        html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; background-color: #0f172a; font-family: system-ui, sans-serif; overflow: hidden; }}
        #header {{ padding: 14px 24px; background-color: #1e293b; border-bottom: 1px solid #334155; display: flex; justify-content: space-between; align-items: center; box-sizing: border-box; height: 60px; }}
        #header h1 {{ margin: 0; font-size: 15px; color: #f8fafc; font-weight: 600; }}
        #network-container {{ width: 100%; height: calc(100% - 60px); position: absolute; top: 60px; }}
    </style>
</head>
<body>
    <div id="header">
        <h1>Enterprise Architecture Topology ({len(self.file_metadata)} Polyglot Modules)</h1>
    </div>
    <div id="network-container"></div>
    <script type="text/javascript">
        var container = document.getElementById('network-container');
        var data = {{ nodes: new vis.DataSet({json.dumps(nodes_js)}), edges: new vis.DataSet({json.dumps(edges_js)}) }};
        var options = {{
            nodes: {{ shape: 'dot', size: 14, borderWidth: 1.5 }},
            edges: {{ smooth: {{ type: 'cubicBezier', roundness: 0.3 }} }},
            physics: {{ barnesHut: {{ gravitationalConstant: -10000, centralGravity: 0.15, springLength: 160 }}, stabilization: {{ iterations: 150 }} }}
        }};
        var network = new vis.Network(container, data, options);
    </script>
</body>
</html>"""
        with open(output_html_path, 'w', encoding='utf-8') as f:
            f.write(html_template)
        print(f"✅ INTERACTIVE HTML GENERATED: Open target browser matrix -> {os.path.abspath(output_html_path)}")

    def generate_visual_graph(self, output_img_path):
        if output_img_path.lower().endswith('.html'):
            self.generate_html_graph(output_img_path)
            return

        try:
            import networkx as nx
            import matplotlib.pyplot as plt
        except ImportError:
            print("\n🚨 VISUALIZATION SKIPPED: Missing networkx or matplotlib runtime dependencies.")
            return

        print(f"\n🎨 Rendering structural engine architecture layout into high-definition PNG matrix...")
        G = nx.DiGraph()
        
        for source, targets in self.graph.items():
            if any(kw in source.lower() for kw in self.noise_keywords): continue
            short_src = "/".join(source.split("/")[-2:])
            for target in targets:
                if any(kw in target.lower() for kw in self.noise_keywords): continue
                short_tgt = "/".join(target.split("/")[-2:])
                G.add_edge(short_src, short_tgt)

        if len(G.nodes) == 0: return

        plt.figure(figsize=(24, 16))
        pos = nx.spring_layout(G, k=1.5, iterations=80, seed=42)
        pos_labels = {node: (coords[0], coords[1] + 0.025) for node, coords in pos.items()}

        nx.draw_networkx_nodes(G, pos, node_size=140, node_color="#1e293b", alpha=0.85)
        nx.draw_networkx_edges(G, pos, arrowstyle="->", arrowsize=10, edge_color="#64748b", alpha=0.3, width=0.9)
        nx.draw_networkx_labels(
            G, pos_labels, font_size=7, font_color="#0f172a", font_weight="bold",
            bbox=dict(facecolor="#ffffff", edgecolor="#cbd5e1", alpha=0.9, boxstyle="round,pad=0.2")
        )
        
        plt.axis("off")
        try:
            plt.savefig(output_img_path, dpi=300, bbox_inches='tight')
            print(f"✅ VISUAL GRAPH CAPTURED: Structural image saved at -> {os.path.abspath(output_img_path)}")
        except Exception as e:
            print(f"🚨 Graph rendering save error: {str(e)}", file=sys.stderr)
        finally:
            plt.close()

    def export_json(self, output_path):
        cycles = self.detect_structural_loops()
        opportunities = self.analyze_intelligent_loops()
        serializable_graph = { k: list(v) for k, v in self.graph.items() }
        
        payload = {
            "metadata": {"target_directory": self.root_dir, "total_components_mapped": len(self.file_metadata)},
            "components": self.file_metadata,
            "adjacency_matrix": serializable_graph,
            "structural_anomalies": {"circular_dependency_count": len(cycles), "detected_cycles": cycles},
            "intelligent_loop_opportunities": opportunities
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2)
        print(f"💾 DATA EXPORT SUCCESS: Global matrix captured at: {os.path.abspath(output_path)}")

    def print_report(self):
        print("=" * 100)
        print("                 GLOBAL CODESPACE TOPOLOGY & INTELLIGENT WORKFLOW MATRIX")
        print("=" * 100)
        print(f"Target Directory:      {self.root_dir}")
        print(f"Total Polyglot Nodes: {len(self.file_metadata)} source files mapped\n")

        print("🌲 LAYER: Hierarchical Dependency Tree (Cross-Language Scopes)")
        print("-" * 100)
        print(self.generate_textual_tree())
        print("\n")

        opps = self.analyze_intelligent_loops()
        print("🤖 LAYER: Intelligent Loop Injections (Autonomous Candidate Blueprints)")
        print("-" * 100)
        
        print("  🎭 [Blueprint A] Actor-Critic Self-Correction Rings")
        for ac in opps["actor_critic_pairs"][:5]:
            print(f"    ↳ {ac['component']:<40} -> {ac['reason']}\n       Path: {ac['path']}")
        
        print("\n  ⚙️  [Blueprint B] Async State-Driven Task Orchestrators")
        for sd in opps["state_driven_workers"][:5]:
            print(f"    ↳ {sd['component']:<40} -> {sd['reason']}\n       Path: {sd['path']}")
            
        print("\n  🛡️  [Blueprint C] Enterprise Governance Guardrails & Veto Gates")
        for gv in opps["governance_veto_gates"][:5]:
            print(f"    ↳ {gv['component']:<40} -> {gv['reason']}\n       Path: {gv['path']}")
        print("=" * 100)

if __name__ == "__main__":
    if sys.platform.startswith("win"):
        try: sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError: sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

    print("\n🚀 ENTERPRISE CODESPACE TOPOLOGY ENGINE ACTIVE\n")

    parser = argparse.ArgumentParser(description="Universal Global Topology Engine")
    parser.add_argument("target", nargs="?", default=".", help="Target directory to scan")
    parser.add_argument("-c", "--config", help="Optional path to a custom configuration file (.json)")
    parser.add_argument("-e", "--export", help="Output JSON metrics export path")
    parser.add_argument("-v", "--visualize", help="Output file path for structural graph image or interactive HTML map")
    
    args = parser.parse_args()
    
    engine = UniversalTopologyEngine(args.target, config_path=args.config)
    engine.scan_repository()
    engine.print_report()
    
    if args.export:
        engine.export_json(args.export)
        
    if args.visualize:
        engine.generate_visual_graph(args.visualize)