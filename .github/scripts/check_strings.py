import sys
import glob
import xml.etree.ElementTree as ET
from collections import defaultdict
import os

# Usage: python check_strings.py changed1.xml base1.xml changed2.xml base2.xml ...

if (len(sys.argv) - 1) % 2 != 0 or len(sys.argv) == 1:
    print("Usage: python check_strings.py changed1.xml base1.xml [changed2.xml base2.xml ...]")
    sys.exit(1)

# Collect all strings.xml files by language
all_strings = {}
for path in glob.glob('**/values*/strings.xml', recursive=True):
    lang = os.path.dirname(path)
    all_strings.setdefault(lang, {})
    tree = ET.parse(path)
    for elem in tree.getroot().findall('string'):
        all_strings[lang][elem.attrib['name']] = elem.text or ''

issues = []

# For each pair: changed file and its base version
for i in range(1, len(sys.argv), 2):
    changed_file = sys.argv[i]
    base_file = sys.argv[i+1]
    print(f'Checking {changed_file} (base: {base_file})...')
    # Parse base and current
    base_keys = {}
    if os.path.exists(base_file) and os.path.getsize(base_file) > 0:
        try:
            base_tree = ET.parse(base_file)
            for elem in base_tree.getroot().findall('string'):
                base_keys[elem.attrib['name']] = elem.text or ''
        except Exception:
            pass
    tree = ET.parse(changed_file)
    current_keys = {elem.attrib['name']: elem.text or '' for elem in tree.getroot().findall('string')}
    # Find added or changed keys
    changed_keys = [k for k in current_keys if k not in base_keys or current_keys[k] != base_keys[k]]
    for key in changed_keys:
        value = current_keys[key]
        # No Content
        if value.strip() == '':
            issues.append({
                'type': 'No Content',
                'emoji': '❌',
                'key': key,
                'file': changed_file,
                'details': 'No value provided.'
            })
        # Not Translated
        translations = [all_strings[lang].get(key, None) for lang in all_strings if key in all_strings[lang]]
        if len(set(translations)) == 1 and len(translations) > 1:
            issues.append({
                'type': 'Not Translated',
                'emoji': '⚠️',
                'key': key,
                'file': changed_file,
                'details': 'Same value in all languages.'
            })
        # String Duplicated
        values_in_file = [v for k2, v in current_keys.items() if k2 != key]
        if value in values_in_file:
            issues.append({
                'type': 'String Duplicated',
                'emoji': '🔁',
                'key': key,
                'file': changed_file,
                'details': 'Value is duplicated in file.'
            })

# Group issues by (type, key, details)
grouped = defaultdict(lambda: {'files': set(), 'emoji': '', 'type': '', 'details': ''})
for issue in issues:
    group_key = (issue['type'], issue['key'], issue['details'])
    grouped[group_key]['files'].add(issue['file'])
    grouped[group_key]['emoji'] = issue['emoji']
    grouped[group_key]['type'] = issue['type']
    grouped[group_key]['details'] = issue['details']

# Write grouped issues to a file for the workflow to pick up
with open('.github/scripts/strings_issues.txt', 'w') as f:
    if grouped:
        f.write('| Issue Type | String Key | Files | Details |\n')
        f.write('|------------|-----------|-------|---------|\n')
        for (itype, key, details), group in grouped.items():
            issue_type = f"{group['emoji']} {group['type']}"
            file_list = ', '.join(sorted(group['files']))
            f.write(f"| {issue_type} | {key} | {file_list} | {group['details']} |\n")
    else:
        f.write('All good! No issues found in changed strings.xml files.')
