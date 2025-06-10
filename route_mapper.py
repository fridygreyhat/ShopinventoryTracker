#!/usr/bin/env python3
"""
Route Mapper - Comprehensive Flask Route Analysis Tool
Analyzes all routes in the business management application and displays their paths, methods, and blueprints.
"""

import os
import re
from collections import defaultdict
from typing import Dict, List, Tuple

class RouteMapper:
    def __init__(self):
        self.routes = defaultdict(list)
        self.blueprints = {}
        self.route_files = [
            'routes.py',
            'auth.py', 
            'admin_portal.py',
            'admin_routes.py',
            'routes_sms.py',
            'language_routes.py'
        ]
        
    def analyze_routes(self):
        """Analyze all route files and extract route information"""
        for file_path in self.route_files:
            if os.path.exists(file_path):
                self._analyze_file(file_path)
        
        return self._generate_route_mapping()
    
    def _analyze_file(self, file_path: str):
        """Analyze a single Python file for routes"""
        print(f"Analyzing {file_path}...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract blueprint definitions
        blueprint_pattern = r'(\w+_bp)\s*=\s*Blueprint\(["\'](\w+)["\'],.*?url_prefix=["\']([^"\']*)["\']'
        blueprint_matches = re.findall(blueprint_pattern, content)
        
        for bp_var, bp_name, url_prefix in blueprint_matches:
            self.blueprints[bp_var] = {
                'name': bp_name,
                'url_prefix': url_prefix,
                'file': file_path
            }
        
        # Extract route definitions
        route_pattern = r'@(app|[\w_]+_bp)\.route\(["\']([^"\']+)["\'](?:,\s*methods=\[([^\]]+)\])?\)'
        route_matches = re.finditer(route_pattern, content, re.MULTILINE)
        
        for match in route_matches:
            decorator_obj = match.group(1)
            route_path = match.group(2)
            methods_str = match.group(3)
            
            # Parse methods
            methods = ['GET']  # Default method
            if methods_str:
                methods = [m.strip().strip('"\'') for m in methods_str.split(',')]
            
            # Find function name following the decorator
            lines = content[match.end():].split('\n')
            func_name = None
            for line in lines:
                func_match = re.match(r'def\s+(\w+)\s*\(', line.strip())
                if func_match:
                    func_name = func_match.group(1)
                    break
                if line.strip() and not line.strip().startswith('@'):
                    break
            
            # Determine blueprint info
            if decorator_obj == 'app':
                blueprint_info = {
                    'name': 'main',
                    'url_prefix': '',
                    'file': file_path
                }
            else:
                blueprint_info = self.blueprints.get(decorator_obj, {
                    'name': decorator_obj,
                    'url_prefix': '',
                    'file': file_path
                })
            
            # Calculate full path
            full_path = blueprint_info.get('url_prefix', '') + route_path
            
            route_info = {
                'path': route_path,
                'full_path': full_path,
                'methods': methods,
                'function': func_name or 'unknown',
                'blueprint': blueprint_info.get('name', 'main'),
                'blueprint_prefix': blueprint_info.get('url_prefix', ''),
                'file': file_path,
                'decorator': decorator_obj
            }
            
            self.routes[file_path].append(route_info)
    
    def _generate_route_mapping(self) -> Dict:
        """Generate comprehensive route mapping"""
        all_routes = []
        blueprints_summary = {}
        
        for file_path, routes in self.routes.items():
            for route in routes:
                all_routes.append(route)
                
                blueprint_name = route['blueprint']
                if blueprint_name not in blueprints_summary:
                    blueprints_summary[blueprint_name] = {
                        'name': blueprint_name,
                        'prefix': route['blueprint_prefix'],
                        'file': file_path,
                        'route_count': 0,
                        'routes': []
                    }
                
                blueprints_summary[blueprint_name]['route_count'] += 1
                blueprints_summary[blueprint_name]['routes'].append(route)
        
        # Sort routes by full path
        all_routes.sort(key=lambda x: x['full_path'])
        
        return {
            'total_routes': len(all_routes),
            'all_routes': all_routes,
            'blueprints': blueprints_summary,
            'files_analyzed': len(self.route_files)
        }
    
    def print_route_table(self, mapping: Dict):
        """Print a formatted table of all routes"""
        print("\n" + "="*120)
        print("COMPLETE APPLICATION ROUTE MAPPING")
        print("="*120)
        print(f"Total Routes Found: {mapping['total_routes']}")
        print(f"Files Analyzed: {mapping['files_analyzed']}")
        print(f"Blueprints: {len(mapping['blueprints'])}")
        print("="*120)
        
        # Header
        print(f"{'FULL PATH':<40} {'METHODS':<15} {'BLUEPRINT':<15} {'FUNCTION':<20} {'FILE':<25}")
        print("-"*120)
        
        # Routes
        for route in mapping['all_routes']:
            methods_str = ', '.join(route['methods'])
            print(f"{route['full_path']:<40} {methods_str:<15} {route['blueprint']:<15} {route['function']:<20} {route['file']:<25}")
    
    def print_blueprint_summary(self, mapping: Dict):
        """Print blueprint summary"""
        print("\n" + "="*80)
        print("BLUEPRINT SUMMARY")
        print("="*80)
        
        for bp_name, bp_info in mapping['blueprints'].items():
            print(f"\nBlueprint: {bp_name}")
            print(f"  Prefix: '{bp_info['prefix']}'")
            print(f"  File: {bp_info['file']}")
            print(f"  Routes: {bp_info['route_count']}")
            
            for route in bp_info['routes']:
                methods_str = ', '.join(route['methods'])
                print(f"    {route['full_path']} [{methods_str}] -> {route['function']}")
    
    def export_to_file(self, mapping: Dict, filename: str = 'route_mapping.txt'):
        """Export route mapping to file"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("COMPLETE APPLICATION ROUTE MAPPING\n")
            f.write("="*80 + "\n")
            f.write(f"Generated: {os.popen('date').read().strip()}\n")
            f.write(f"Total Routes: {mapping['total_routes']}\n")
            f.write(f"Blueprints: {len(mapping['blueprints'])}\n\n")
            
            # All routes table
            f.write("ALL ROUTES\n")
            f.write("-"*80 + "\n")
            f.write(f"{'FULL PATH':<40} {'METHODS':<15} {'BLUEPRINT':<15} {'FUNCTION':<15}\n")
            f.write("-"*80 + "\n")
            
            for route in mapping['all_routes']:
                methods_str = ', '.join(route['methods'])
                f.write(f"{route['full_path']:<40} {methods_str:<15} {route['blueprint']:<15} {route['function']:<15}\n")
            
            # Blueprint details
            f.write("\n\nBLUEPRINT DETAILS\n")
            f.write("-"*80 + "\n")
            
            for bp_name, bp_info in mapping['blueprints'].items():
                f.write(f"\n[{bp_name.upper()}] Blueprint\n")
                f.write(f"Prefix: '{bp_info['prefix']}'\n")
                f.write(f"File: {bp_info['file']}\n")
                f.write(f"Routes: {bp_info['route_count']}\n\n")
                
                for route in bp_info['routes']:
                    methods_str = ', '.join(route['methods'])
                    f.write(f"  {route['full_path']} [{methods_str}] -> {route['function']}\n")
        
        print(f"\nRoute mapping exported to: {filename}")

def main():
    """Main function to run route analysis"""
    mapper = RouteMapper()
    mapping = mapper.analyze_routes()
    
    # Print results
    mapper.print_route_table(mapping)
    mapper.print_blueprint_summary(mapping)
    
    # Export to file
    mapper.export_to_file(mapping)
    
    return mapping

if __name__ == '__main__':
    main()