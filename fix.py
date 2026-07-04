import os

with open('app/templates/guide.html', encoding='utf-8') as f:
    content = f.read()

content = content.replace('{% extends "base.html" %}', '{% extends "v2/base_v2.html" %}')

toc_old = """        <a href="#intro">1. Введение и базовые понятия</a>
        <a href="#catalogs">2. Справочники</a>
        <a href="#rent">3. Управление арендой</a>
        <a href="#bills">4. Коммунальные счета</a>
        <a href="#billing">5. Расчет начислений</a>
        <a href="#docs">6. Документооборот</a>
        <a href="#faq">7. Ошибки и их исправление</a>"""

toc_new = """        <a href="#intro">1. Введение и базовые понятия</a>
        <a href="#catalogs">2. Справочники</a>
        <a href="#rent">3. Управление арендой</a>
        <a href="#bills">4. Коммунальные счета</a>
        <a href="#billing">5. Расчет начислений</a>
        <a href="#payments">6. Управление оплатами и балансом</a>
        <a href="#docs">7. Формирование документов</a>
        <a href="#settings">8. Резервное копирование и импорт</a>
        <a href="#faq">9. Ошибки и их исправление (FAQ)</a>"""

content = content.replace(toc_old, toc_new)

with open('app/templates/v2/guide.html', 'w', encoding='utf-8') as f:
    f.write(content)
