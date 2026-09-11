"""Сверка ссылок в хранилище Obsidian.

    python3 tools/check_vault.py            (после build_vault.py)

Проверяет, что каждая вики-ссылка `[[заметка]]` ведёт в существующую
заметку, что имена заметок не повторяются и что YAML-шапка у каждой
заметки на месте. В хранилище двадцать четыре с половиной тысячи заметок и
за полмиллиона ссылок между ними — глазами это не проверить, а битая
ссылка в Obsidian выглядит так же, как рабочая, пока по ней не щёлкнешь.

Такая же сверка есть у хранилища Cummins (`_build/check_links.py`).
"""
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lgraw import ROOT                              # noqa: E402

VAULT = os.path.join(ROOT, "obsidian-vault")
LINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")


def main():
    if not os.path.isdir(VAULT):
        raise SystemExit("нет obsidian-vault — сначала tools/build_vault.py")

    notes = {}                      # имя заметки -> путь
    dupes = defaultdict(list)
    files = []
    for root, _dirs, names in os.walk(VAULT):
        for n in names:
            if not n.endswith(".md"):
                continue
            path = os.path.join(root, n)
            if n == "README.md" and root == VAULT:
                continue       # описание хранилища: ни шапки, ни ссылок ему не нужно
            files.append(path)
            name = n[:-3]
            if name in notes:
                dupes[name].append(path)
            else:
                notes[name] = path

    broken = Counter()
    examples = {}
    no_front = []
    links = 0
    for path in files:
        text = open(path, encoding="utf-8").read()
        if not text.startswith("---\n"):
            no_front.append(path)
        for m in LINK.finditer(text):
            target = m.group(1).strip()
            links += 1
            if target not in notes:
                broken[target] += 1
                examples.setdefault(target, os.path.relpath(path, VAULT))

    print("заметок %d, ссылок %d" % (len(files), links))
    print("битых ссылок: %d (на %d разных заметок)"
          % (sum(broken.values()), len(broken)))
    for target, n in broken.most_common(10):
        print("   %5d  [[%s]]  например в %s" % (n, target, examples[target]))
    print("повторяющихся имён заметок: %d" % len(dupes))
    for name in list(dupes)[:5]:
        print("   %s — %d экземпляра" % (name, len(dupes[name]) + 1))
    print("заметок без YAML-шапки: %d" % len(no_front))
    for path in no_front[:5]:
        print("   " + os.path.relpath(path, VAULT))

    if broken or dupes or no_front:
        sys.exit(1)
    print("всё сходится")


if __name__ == "__main__":
    main()
