import os
import re

V2_ROUTES = {
    'directory.html': '/v2/directory',
    'billing.html': '/v2/billing',
    'payments.html': '/v2/payments',
    'settings.html': '/v2/settings'
}

def process_file(filepath, redirect_path):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex to find <form ... action="/path"...>
    # We want to insert ?redirect_to=redirect_path or &redirect_to=redirect_path
    def form_replacer(match):
        full_tag = match.group(0)
        action_url = match.group(2)
        if 'redirect_to=' in action_url:
            return full_tag
            
        joiner = '&' if '?' in action_url else '?'
        new_action = f'{action_url}{joiner}redirect_to={redirect_path}'
        return full_tag.replace(action_url, new_action)
        
    content = re.sub(r'(<form[^>]+action=[\"\'])(/[^\"\']+)([\"\'][^>]*>)', form_replacer, content)

    # Regex to find JS form assignments: form.action = '/something/' + id + '/edit';
    # Example: form.action = '/objects/' + id + '/edit';
    def js_replacer(match):
        prefix = match.group(1)
        suffix = match.group(2)
        if 'redirect_to=' in suffix:
            return match.group(0)
            
        # The suffix usually looks like: '/edit';
        # We replace it with: '/edit?redirect_to=...';
        new_suffix = suffix.replace("';", f"?redirect_to={redirect_path}';").replace('";', f'?redirect_to={redirect_path}";')
        return prefix + new_suffix

    content = re.sub(r'(form\.action\s*=\s*.*?)([^\'\"]+[\'\"];)', js_replacer, content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

base_dir = 'app/templates/v2'
for filename, route in V2_ROUTES.items():
    path = os.path.join(base_dir, filename)
    if os.path.exists(path):
        process_file(path, route)
        print(f"Fixed redirects in {filename}")

