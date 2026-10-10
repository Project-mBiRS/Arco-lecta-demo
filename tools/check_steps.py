#!/usr/bin/env python3
"""index.html の STEPS 定義の整合性チェック。

使い方: python3 tools/check_steps.py index.html
終了コード: 問題なし=0 / エラーあり=1（警告のみは0）
"""
import re
import sys


def extract_steps(src):
    m = re.search(r"const STEPS = \{(.*?)\n\};", src, re.DOTALL)
    if not m:
        sys.exit("ERROR: const STEPS = { ... }; が見つかりません")
    return m.group(1)


def split_nodes(body):
    """2スペースインデントのトップレベルキーでノードを分割する。"""
    starts = [(mm.group(1), mm.start()) for mm in re.finditer(r"^  ([A-Z0-9_]+)\s*:\s*\{", body, re.M)]
    nodes = {}
    for i, (key, pos) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else len(body)
        nodes[key] = body[pos:end]
    return nodes


def main(path):
    src = open(path, encoding="utf-8").read()
    errors, warnings = [], []

    nodes = split_nodes(extract_steps(src))
    keys = set(nodes)
    edges = {k: re.findall(r'next:\s*"([A-Z0-9_]+)"', v) for k, v in nodes.items()}

    # 1. 未定義参照
    for k, targets in edges.items():
        for t in targets:
            if t not in keys:
                errors.append(f"未定義の参照: {k} -> {t}")

    # 2. 法的根拠のないノード（lawTag / law / provision のいずれもない）
    no_law = [k for k, v in nodes.items() if not re.search(r"\b(lawTag|law|provision)\s*:", v)]
    for k in no_law:
        warnings.append(f"法的根拠フィールドなし: {k}")

    # 3. 到達不能ノード（どこからも参照されない。開始ノードは除く）
    referenced = {t for ts in edges.values() for t in ts}
    unreferenced = sorted(keys - referenced)

    # 4. ダブルクォートが奇数個の行（文字列リテラル破損の簡易検出）
    m = re.search(r'<script type="text/babel">(.*?)</script>', src, re.DOTALL)
    script_start = src[: m.start(1)].count("\n") + 1 if m else 1
    script = m.group(1) if m else src
    for i, line in enumerate(script.split("\n")):
        stripped = re.sub(r"`[^`]*`", "", line)  # テンプレートリテラル内は除外
        if stripped.count('"') % 2 == 1:
            warnings.append(f"ダブルクォート奇数: {path}:{script_start + i}")

    # 5. ルート長（開始ノード=参照されないノードから結果ノードまで、循環は除外）
    def longest(node, seen):
        if node not in nodes or not edges.get(node):
            return 1, [node]
        best = (1, [node])
        for t in edges[node]:
            if t in seen:
                continue
            n, p = longest(t, seen | {t})
            if n + 1 > best[0]:
                best = (n + 1, [node] + p)
        return best

    print(f"ノード数: {len(keys)}")
    print(f"開始候補（被参照なし）: {', '.join(unreferenced) or 'なし'}")
    for s in unreferenced:
        n, p = longest(s, {s})
        print(f"最長ルート（{s}起点、ノード数）: {n}")
        print("  " + " -> ".join(p))
    for w in warnings:
        print("WARN  " + w)
    for e in errors:
        print("ERROR " + e)
    print(f"結果: エラー {len(errors)} / 警告 {len(warnings)}")
    return 1 if errors else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))
