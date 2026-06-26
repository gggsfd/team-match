#!/bin/bash
# Fix admin/users.php line 34 - PDO chaining bug
# execute() returns bool, cannot chain fetch() on it

cd /opt/teammatch/backend/api/admin

# Use python3 for reliable replacement
python3 << 'PYFIX'
with open('users.php', 'r', encoding='utf-8') as f:
    content = f.read()

old = "$total = (int)$db->prepare(\"SELECT COUNT(*) AS cnt FROM user u WHERE {$wsql}\")->execute($params)->fetch()['cnt'];"
new = """$countStmt = $db->prepare("SELECT COUNT(*) AS cnt FROM user u WHERE {$wsql}");
    $countStmt->execute($params);
    $total = (int)$countStmt->fetch()['cnt'];"""

if old in content:
    content = content.replace(old, new)
    with open('users.php', 'w', encoding='utf-8') as f:
        f.write(content)
    print("FIXED: line 34 replaced successfully")
else:
    print("WARNING: pattern not found, showing context:")
    for i, line in enumerate(content.split('\n')[32:38], start=33):
        print(f"  {i}: {line[:120]}")
PYFIX

# Verify
echo ""
echo "=== Fixed result ==="
sed -n '33,39p' users.php
