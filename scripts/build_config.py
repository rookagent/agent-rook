#!/usr/bin/env python3
"""
Build-time config generator.
Reads agent.yaml and writes engine/frontend/src/agentConfig.json.

Usage:
    python scripts/build_config.py
    python scripts/build_config.py --agent-yaml path/to/agent.yaml

Run this before `npm build` or `npm start` to sync agent config to the frontend.
"""
import json
import os
import sys
import yaml

def main():
    # Find agent.yaml
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    yaml_path = os.path.join(project_root, 'agent.yaml')
    if '--agent-yaml' in sys.argv:
        idx = sys.argv.index('--agent-yaml')
        if idx + 1 < len(sys.argv):
            yaml_path = sys.argv[idx + 1]

    if not os.path.exists(yaml_path):
        print(f"Error: {yaml_path} not found")
        sys.exit(1)

    with open(yaml_path) as f:
        config = yaml.safe_load(f)

    agent = config.get('agent', {})
    branding = config.get('branding', {})
    chat = config.get('chat', {})
    access = config.get('access', {})
    dashboard = config.get('dashboard', {})
    spokes = config.get('spokes', {})

    frontend_config = {
        'name': agent.get('name', 'Agent'),
        'tagline': agent.get('tagline', ''),
        'welcome_message': chat.get('welcome_message', f"Hey! I'm {agent.get('name', 'your agent')}. How can I help?"),
        'suggestions': chat.get('suggestions', []),
        'branding': {
            'primary_color': branding.get('primary_color', '#2D4A3E'),
            'secondary_color': branding.get('secondary_color', '#D4A843'),
            'background': branding.get('background', '#FBFDF9'),
            'logo': branding.get('logo', '/logo.png'),
            'fonts': branding.get('fonts', {'heading': 'Caveat', 'body': 'Quicksand'}),
        },
        'access': {
            'free_messages_per_day': access.get('free_messages_per_day', 3),
        },
        'api_url': '/api',
        'dashboard': dashboard,
        'spokes': spokes,
    }

    output_path = os.path.join(project_root, 'engine', 'frontend', 'src', 'agentConfig.json')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(frontend_config, f, indent=2, ensure_ascii=False)

    print(f"Generated {output_path} from {yaml_path}")
    print(f"  Agent: {frontend_config['name']}")
    print(f"  Cards: {len(dashboard.get('cards', []))}")
    print(f"  Spokes: {len([s for s in spokes.values() if s.get('enabled', True)])}")

if __name__ == '__main__':
    main()
