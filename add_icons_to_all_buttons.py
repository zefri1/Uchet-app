import os

edit_svg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>'
info_svg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>'
pay_svg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect><line x1="1" y1="10" x2="23" y2="10"></line></svg>'
undo_svg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>'
trash_svg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>'

# 1. Update directory.html
dir_path = 'app/templates/v2/directory.html'
with open(dir_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace Изменить buttons
content = content.replace(
    'class="btn btn-secondary btn-compact" onclick="openEditObjectModal',
    f'class="btn btn-secondary btn-compact" onclick="openEditObjectModal'
)
content = content.replace('>Изменить</button>', f'>{edit_svg} Изменить</button>')

with open(dir_path, 'w', encoding='utf-8') as f:
    f.write(content)

# 2. Update payments.html
pay_path = 'app/templates/v2/payments.html'
with open(pay_path, 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace('>Изменить</button>', f'>{edit_svg} Изменить</button>')
with open(pay_path, 'w', encoding='utf-8') as f:
    f.write(content)

# 3. Update settings.html
set_path = 'app/templates/v2/settings.html'
with open(set_path, 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace('>Изменить</button>', f'>{edit_svg} Изменить</button>')
content = content.replace('>Восстановить</button>', f'>{undo_svg} Восстановить</button>')
content = content.replace('>Навсегда</button>', f'>{trash_svg} Навсегда</button>')
with open(set_path, 'w', encoding='utf-8') as f:
    f.write(content)

# 4. Update billing.html
bill_path = 'app/templates/v2/billing.html'
with open(bill_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'style="height:28px; padding:0 8px; font-size:11px;">Правка</button>',
    f'class="btn btn-secondary btn-compact">{edit_svg} Правка</button>'
)
# Let's clean up any doubled class name just in case: class="btn btn-secondary btn-compact" class="btn btn-secondary btn-compact"
content = content.replace(
    'class="btn btn-secondary btn-compact" class="btn btn-secondary btn-compact"',
    'class="btn btn-secondary btn-compact"'
)

content = content.replace(
    'style="font-size:11px;" data-audit=\'{{ item.audit_payload }}\' onclick="showAudit(this)">Формула</button>',
    f'class="btn btn-secondary btn-compact" data-audit=\'{{ item.audit_payload }}\' onclick="showAudit(this)">{info_svg} Формула</button>'
)

content = content.replace(
    'style="background-color: #10b981; border: none; font-size: 12px; padding: 4px 10px;" onclick="openFastPayModal',
    f'class="btn btn-primary btn-compact" style="background-color: #10b981 !important; border: none !important;" onclick="openFastPayModal'
)
content = content.replace('>Оплатить</button>', f'>{pay_svg} Оплатить</button>')

with open(bill_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Icons added successfully.")
