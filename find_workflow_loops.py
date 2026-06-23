#!/usr/bin/env python3
import os
import re
import sys
import json
import argparse
import codecs
from collections import defaultdict

class UniversalTopologyEngine:
    def __init__(self, root_dir):
        self.root_dir = os.path.abspath(root_dir)
        self.graph = defaultdict(set)
        self.file_metadata = {}
        
        # Hardened boundaries to isolate true workflow components
        self.ignore_dirs = {
            '.git', 'node_modules', 'venv', '.venv', '__pycache__', 
            'dist', 'build', '.next', 'out', 'target', '.ideas',
            'ios', 'android', 'public', 'assets'
        }
        self.ignore_files = {
            'get-pip.py', 'db_dump.sql', 'dump.sql', 'local_schema_dump.sql', 
            'postcss.config.js', 'tailwind.config.js', 'vite.config.js'
        }
        self.noise_keywords = {'ui', 'shadcn', 'styles', 'footer', 'navbar', 'toast', 'button', 'vitest'}
        
        # Focus strictly on active execution layers
        self.supported_extensions = {'.ts', '.tsx', '.js', '.jsx', '.py'}
        
        self.import_patterns = [
            re.compile(r'(?:import|require|from)\s+[\'"]?([@\w\.\/\-]+)[\'"]?'),
            re.compile(r'(?:from)\s+([@\w\.\/\-]+)\s+(?:import)'),
        ]

    def normalize_path_key(self, rel_path):
        return os.path.splitext(rel_path.replace('\\', '/'))[0]

    def resolve_import_to_component(self, current_file_key, import_string, internal_components):
        clean_token = import_string.strip(" '\"();").replace('\\', '/')
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

    def scan_repository(self):
        raw_imports = defaultdict(list)

        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]
            
            if 'supabase' in root.split(os.sep) and 'migrations' in root.split(os.sep):
                continue

            for file in files:
                if file in self.ignore_files:
                    continue
                    
                ext = os.path.splitext(file)[1].lower()
                if ext not in self.supported_extensions:
                    continue
                    
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, self.root_dir)
                component_key = self.normalize_path_key(rel_path)
                
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        self.file_metadata[component_key] = {
                            "path": rel_path,
                            "loc": len(lines),
                            "ext": ext
                        }
                        
                        for line in lines:
                            for pattern in self.import_patterns:
                                for match in pattern.findall(line):
                                    raw_imports[component_key].append(match)
                except Exception:
                    continue

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

    def analyze_loop_opportunities(self):
        fan_in = defaultdict(int)
        fan_out = defaultdict(int)

        for source, targets in self.graph.items():
            fan_out[source] = len(targets)
            for t in targets:
                fan_in[t] += 1

        opportunities = {"orchestration_hubs": [], "linear_sinks": []}

        for comp, meta in self.file_metadata.items():
            if any(kw in comp.lower() for kw in self.noise_keywords):
                continue

            in_deg = fan_in[comp]
            out_deg = fan_out[comp]
            
            if in_deg >= 3:
                opportunities["orchestration_hubs"].append({
                    "component": "/".join(comp.split('/')[-2:]), "path": meta["path"], "fan_map": f"In: {in_deg} -> Out: {out_deg}"
                })
            if out_deg == 0 and in_deg > 0 and meta["loc"] > 100:
                opportunities["linear_sinks"].append({
                    "component": "/".join(comp.split('/')[-2:]), "path": meta["path"], "loc": meta["loc"]
                })

        return opportunities

    def generate_textual_tree(self):
        """Compiles a high-visibility execution path map, surviving deep cyclical loops."""
        in_degrees = defaultdict(int)
        for source, targets in self.graph.items():
            for t in targets:
                in_degrees[t] += 1
        
        # Isolate application root boundaries (nothing imports them)
        roots = [comp for comp in self.file_metadata if in_degrees[comp] == 0]
        
        # Fallback: if deeply chained in a loop infrastructure layout, locate lowest absolute weights
        if not roots:
            min_in = min(in_degrees.values()) if in_degrees else 0
            roots = [comp for comp in self.file_metadata if in_degrees[comp] == min_in]
            
        roots.sort()
        tree_output = []

        def recurse_tree(node, prefix="", is_last=True, trace_history=None):
            if trace_history is None:
                trace_history = set()
                
            short_name = "/".join(node.split("/")[-2:])
            branch_pointer = "└── " if is_last else "├── "
            
            if node in trace_history:
                tree_output.append(f"{prefix}{branch_pointer}🔄 {short_name} (Loop Trace Breakpoint)")
                return
                
            emoji = "📄 "
            if "page" in node.lower(): emoji = "🎨 "
            elif "context" in node.lower(): emoji = "🧬 "
            elif "lib" in node.lower(): emoji = "🛠️ "
            elif "worker" in node.lower(): emoji = "⚡ "
            
            tree_output.append(f"{prefix}{branch_pointer}{emoji}{short_name}")
            
            children = sorted(list(self.graph.get(node, [])))
            if children:
                nested_prefix = prefix + ("    " if is_last else "│   ")
                extended_history = trace_history | {node}
                for index, child in enumerate(children):
                    recurse_tree(child, nested_prefix, index == len(children) - 1, extended_history)

        for idx, root in enumerate(roots[:15]):
            recurse_tree(root, "", idx == len(roots[:15]) - 1)
            
        if len(roots) > 15:
            tree_output.append(f"\n... (Truncated {len(roots) - 15} auxiliary root boundaries)")
            
        return "\n".join(tree_output) if tree_output else "  ⚠️ No traceable textual tree execution vectors discovered."

    def generate_html_graph(self, output_html_path):
        """Generates a zero-dependency interactive HTML map with physics simulation."""
        print(f"\n🌐 Compiling interactive visual graph database...")
        nodes_js = []
        edges_js = []
        node_to_id = {}
        idx = 1
        
        for comp, meta in self.file_metadata.items():
            short_name = "/".join(comp.split("/")[-2:])
            node_to_id[comp] = idx
            
            color = "#38bdf8"
            if "page" in comp.lower(): color = "#f43f5e"
            elif "context" in comp.lower(): color = "#10b981"
            elif "lib" in comp.lower(): color = "#a855f7"
            elif "worker" in comp.lower(): color = "#eab308"
                
            nodes_js.append({
                "id": idx,
                "label": short_name,
                "title": f"Namespace: {comp}<br>Volume: {meta['loc']} LOC",
                "color": {"background": color, "border": "#1e293b", "highlight": {"background": "#ffffff", "border": "#0f172a"}},
                "font": {"color": "#ffffff", "size": 11, "face": "sans-serif"}
            })
            idx += 1
            
        for source, targets in self.graph.items():
            src_id = node_to_id.get(source)
            for t in targets:
                tgt_id = node_to_id.get(t)
                if src_id and tgt_id:
                    edges_js.append({
                        "from": src_id, 
                        "to": tgt_id, 
                        "arrows": "to", 
                        "color": {"color": "#64748b", "opacity": 0.3, "highlight": "#38bdf8"},
                        "width": 1
                    })

        html_template = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>K-DenceAI System Topology Map</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style type="text/css">
        html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; background-color: #0f172a; font-family: system-ui, -apple-system, sans-serif; overflow: hidden; }}
        #header {{ padding: 14px 24px; background-color: #1e293b; border-bottom: 1px solid #334155; display: flex; justify-content: space-between; align-items: center; box-sizing: border-box; height: 60px; }}
        #header h1 {{ margin: 0; font-size: 16px; color: #f8fafc; font-weight: 600; letter-spacing: -0.025em; }}
        #legend {{ display: flex; gap: 18px; font-size: 11px; color: #94a3b8; font-weight: 500; }}
        .legend-item {{ display: flex; align-items: center; gap: 6px; }}
        .dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}
        #network-container {{ width: 100%; height: calc(100% - 60px); position: absolute; top: 60px; bottom: 0; }}
    </style>
</head>
<body>
    <div id="header">
        <h1>System Topology Map ({len(self.file_metadata)} Connected Layers)</h1>
        <div id="legend">
            <div class="legend-item"><span class="dot" style="background: #f43f5e;"></span> Pages</div>
            <div class="legend-item"><span class="dot" style="background: #10b981;"></span> Contexts</div>
            <div class="legend-item"><span class="dot" style="background: #a855f7;"></span> Libs</div>
            <div class="legend-item"><span class="dot" style="background: #eab308;"></span> Workers</div>
            <div class="legend-item"><span class="dot" style="background: #38bdf8;"></span> Components</div>
        </div>
    </div>
    <div id="network-container"></div>
    <script type="text/javascript">
        var container = document.getElementById('network-container');
        var data = {{ nodes: new vis.DataSet({json.dumps(nodes_js)}), edges: new vis.DataSet({json.dumps(edges_js)}) }};
        var options = {{
            nodes: {{ shape: 'dot', size: 14, borderWidth: 2 }},
            edges: {{ smooth: {{ type: 'cubicBezier', roundness: 0.4 }}, width: 1.2 }},
            interaction: {{ hover: true, tooltipDelay: 100, navigationButtons: true }},
            physics: {{
                barnesHut: {{ gravitationalConstant: -12000, centralGravity: 0.2, springLength: 180, springConstant: 0.05, avoidOverlap: 1 }},
                stabilization: {{ iterations: 180 }}
            }}
        }};
        var network = new vis.Network(container, data, options);
    </script>
</body>
</html>"""
        try:
            with open(output_html_path, 'w', encoding='utf-8') as f:
                f.write(html_template)
            print(f"✅ INTERACTIVE HTML GENERATED: Explore here -> {os.path.abspath(output_html_path)}")
        except Exception as e:
            print(f"🚨 HTML Export Exception: {str(e)}", file=sys.stderr)

    def generate_visual_graph(self, output_img_path):
        """Generates a visual diagram directly from the evaluated internal dependency state."""
        if output_img_path.lower().endswith('.html'):
            self.generate_html_graph(output_img_path)
            return

        try:
            import networkx as nx
            import matplotlib.pyplot as plt
        except ImportError:
            print("\n🚨 VISUALIZATION SKIPPED: Missing networkx or matplotlib graphic packages.")
            return

        print(f"\n🎨 Rendering noise-pruned structural matrix into static PNG layout...")
        G = nx.DiGraph()
        
        for source, targets in self.graph.items():
            if any(kw in source.lower() for kw in self.noise_keywords):
                continue
            short_src = "/".join(source.split("/")[-2:])
            for target in targets:
                if any(kw in target.lower() for kw in self.noise_keywords):
                    continue
                short_tgt = "/".join(target.split("/")[-2:])
                G.add_edge(short_src, short_tgt)

        if len(G.nodes) == 0:
            return

        plt.figure(figsize=(26, 18))
        pos = nx.spring_layout(G, k=1.8, iterations=100, seed=42)
        pos_labels = {node: (coords[0], coords[1] + 0.03) for node, coords in pos.items()}

        nx.draw_networkx_nodes(G, pos, node_size=180, node_color="#0f172a", alpha=0.9)
        nx.draw_networkx_edges(G, pos, arrowstyle="->", arrowsize=12, edge_color="#94a3b8", alpha=0.35, width=1.0)
        
        nx.draw_networkx_labels(
            G, pos_labels, font_size=7, font_color="#1e293b", font_family="sans-serif", font_weight="bold",
            bbox=dict(facecolor="#ffffff", edgecolor="#e2e8f0", alpha=0.9, boxstyle="round,pad=0.2")
        )
        
        plt.title(f"Engine Core Topology Map ({len(G.nodes)} Core Execution Layers)", fontsize=16, color="#0f172a", loc="left", pad=15)
        plt.axis("off")
        
        try:
            plt.savefig(output_img_path, dpi=300, bbox_inches='tight')
            print(f"✅ VISUAL GRAPH CAPTURED: Saved to {os.path.abspath(output_img_path)}")
        except Exception as e:
            print(f"🚨 Graph rendering write error: {str(e)}", file=sys.stderr)
        finally:
            plt.close()

    def export_json(self, output_path):
        cycles = self.detect_structural_loops()
        opportunities = self.analyze_loop_opportunities()
        serializable_graph = { k: list(v) for k, v in self.graph.items() }
        
        payload = {
            "metadata": {"target_directory": self.root_dir, "total_components_mapped": len(self.file_metadata)},
            "components": self.file_metadata,
            "adjacency_matrix": serializable_graph,
            "structural_anomalies": {"circular_dependency_count": len(cycles), "detected_cycles": cycles},
            "architectural_opportunities": opportunities
        }
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2)
            print(f"💾 DATA EXPORT SUCCESS: Matrix captured at: {os.path.abspath(output_path)}")
        except Exception as e:
            print(f"🚨 EXPORT ERROR: {str(e)}", file=sys.stderr)

    def print_report(self):
        print("=" * 90)
        print("                 UNIVERSAL SYSTEM TOPOLOGY & LOOP OPTIMIZATION ENGINE")
        print("=" * 90)
        print(f"Target Core Directory: {self.root_dir}")
        print(f"Mapped Components:    {len(self.file_metadata)} namespaced files\n")

        print("🌲 LAYER: Hierarchical Dependency Tree (Traced Execution Paths)")
        print("-" * 90)
        print(self.generate_textual_tree())
        print("\n")

        cycles = self.detect_structural_loops()
        print("🔄 LAYER: Structural Dependency Cycles (Code Integrity Risks)")
        print("-" * 90)
        if not cycles:
            print("  ✅ Clean Graph Topology: No compile-time circular loops found.")
        else:
            print(f"  ⚠️  Identified {len(cycles)} path-isolated structural loops:")
            for cycle in cycles[:15]:
                print(f"    ↳ {cycle}")
        print("\n")

        opps = self.analyze_loop_opportunities()
        print("🏭 LAYER: Automated Loop Opportunities (Architectural Recommendations)")
        print("-" * 90)
        print("  💡 Pattern [A]: Feedback Orchestration Rings (High-Frequency Hubs)")
        for hub in opps["orchestration_hubs"][:5]:
            print(f"    ↳ 🧱 {hub['component']:<30} [{hub['fan_map']}] at {hub['path']}")
        
        print("\n  💡 Pattern [B]: Evaluator/Critic Gates (Linear Dead-Ends)")
        for sink in opps["linear_sinks"][:5]:
            print(f"    ↳ 🧱 {sink['component']:<30} [{sink['loc']} LOC] at {sink['path']}")
        print("=" * 90)

if __name__ == "__main__":
    # Force full UTF-8 encoding support to prevent standard Windows PowerShell from swallowing lines
    if sys.platform.startswith("win"):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

    print("\n🚀 CURRENT VERSION: V2 (WITH TEXT TREE) ACTIVE\n")

    parser = argparse.ArgumentParser(description="Universal System Topology Engine")
    parser.add_argument("target", nargs="?", default=".", help="Target root directory to scan")
    parser.add_argument("-e", "--export", help="Output file path for JSON export")
    parser.add_argument("-v", "--visualize", help="Output file path for structural graph image or interactive HTML map")
    
    args = parser.parse_args()
    
    engine = UniversalTopologyEngine(args.target)
    engine.scan_repository()
    engine.print_report()
    
    if args.export:
        engine.export_json(args.export)
        
    if args.visualize:
        engine.generate_visual_graph(args.visualize)