"""Exercise the handoff CLI with real local Git and stand-ins for remote services."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]


class HandoffTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        fixture = Path(directory.name).resolve()
        self.root = fixture / "workspace"
        self.root.mkdir()
        self.tool = fixture / "installed" / "handoff"
        shutil.copytree(ROOT / "skills" / "handoff", self.tool)
        self.repo = self.root / "sample-app"
        self.repo.mkdir()
        self.git("init", "-qb", "main")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("remote", "add", "origin", "git@github.com:fixture-org/upstream-app.git")
        self.base = self.commit("base")
        self.git("update-ref", "refs/remotes/origin/main", self.base)
        self.heads = [self.commit(f"change-{number}") for number in range(1, 7)]
        self.pr = self.root / "pr.json"
        self.call = self.root / "agent-call"
        self.latest = self.root / "handoff-requests/sample-app/pr-37/review.md"
        self.history = self.root / ".handoff-runs/review/sample-app/pr-37"
        self.stub("gh", '''
if [ "$5" != github.com/fixture-org/upstream-app ]; then exit 9; fi
cat "$PR_DATA"
''')
        for agent in ("codex", "claude"):
            self.stub(agent, f"""printf '%s\\n' '{agent}' >"$AGENT_CALL"
cat >>"$AGENT_CALL"
if [ "$IMPLEMENT" = yes ]; then echo implemented >implementation.txt; fi
if [ "$FAIL" = yes ]; then exit 7; fi
printf '%s\\n' "$REPLY"
""")

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.repo, text=True).strip()

    def commit(self, filename):
        (self.repo / filename).write_text(f"{filename}\n", encoding="utf-8")
        self.git("add", filename)
        self.git("commit", "-qm", filename)
        return self.git("rev-parse", "HEAD")

    def stub(self, name, code):
        path = self.root / name
        path.write_text("#!/bin/sh\n" + code + "\n", encoding="utf-8")
        path.chmod(0o755)

    def invoke(self, mode, *flags, to="codex", reply="結論：指摘なし", fail=False,
               use_root=False, explicit_workspace=False, codex_bin=None):
        sender = "claude" if to == "codex" else "codex"
        self.call.unlink(missing_ok=True)
        env = dict(
            os.environ, PATH=f"{self.root}:{os.environ['PATH']}", PR_DATA=str(self.pr),
            AGENT_CALL=str(self.call), REPLY=reply, FAIL="yes" if fail else "no",
            IMPLEMENT="yes" if mode == "implement" else "no",
        )
        env.pop("HANDOFF_CODEX_BIN", None)
        if codex_bin is not None:
            env["HANDOFF_CODEX_BIN"] = str(codex_bin)
        workspace = ["--workspace", self.root] if explicit_workspace else []
        return subprocess.run(
            [self.tool / "scripts/handoff", mode, *workspace, *([] if use_root else ["--repo", self.repo.name]),
             "--from", sender, "--to", to, *flags],
            cwd=self.tool if explicit_workspace else self.root,
            env=env, text=True, capture_output=True, timeout=15,
        )

    def review(self, head, *flags, expected=None, **options):
        self.pr.write_text(json.dumps({
            "url": "https://github.com/fixture-org/upstream-app/pull/37",
            "headRefOid": head, "baseRefOid": self.base,
        }), encoding="utf-8")
        return self.invoke("review", "--pr", "37", "--head", expected or head, *flags, **options)

    def result(self, process):
        self.assertEqual(process.returncode, 0, process.stderr)
        return Path(process.stdout.strip())

    def assert_blocked(self, process, reason):
        self.assertNotEqual(process.returncode, 0)
        self.assertIn(reason, process.stderr)
        self.assertFalse(self.call.exists(), "Agent started despite the block")

    def test_pinned_review_then_incremental_review_in_other_direction(self):
        first, second = self.heads[:2]
        result = self.result(self.review(first))
        self.assertTrue(self.call.read_text().startswith("codex\n"))
        self.assertIn("b/change-1", (result.parent / "review.diff").read_text())
        self.assertFalse((result.parent / self.repo.name).exists())
        updated = self.result(self.review(second, "--since", first[:8], to="claude"))
        self.assertTrue(self.call.read_text().startswith("claude\n"))
        diff = (updated.parent / "review.diff").read_text()
        self.assertIn("b/change-2", diff)
        self.assertNotIn("b/change-1", diff)
        latest = self.latest.read_text()
        self.assertIn(second, latest)
        self.assertIn("**結論：指摘なし**", latest)
        href = latest.split("[この回の実行履歴](", 1)[1].split(")", 1)[0]
        self.assertEqual((self.latest.parent / unquote(href)).resolve(), updated.parent)
        self.assertTrue(result.is_file())

    def test_explicit_codex_executable_overrides_path(self):
        binary = "custom codex"
        self.stub(binary, 'cat >"$AGENT_CALL"; echo "結論：指摘なし"; echo "custom executable"')
        result = self.result(self.review(self.heads[0], codex_bin=self.root / binary))
        self.assertIn("custom executable", result.read_text())

        self.assert_blocked(
            self.review(self.heads[1], codex_bin=self.root / "missing codex"),
            "HANDOFF_CODEX_BIN",
        )

    def test_review_preamble_and_ambiguous_conclusions(self):
        first, second = self.heads[:2]
        reply = (
            "差分を確認しました。\n\n結果をまとめます。\n"
            "結論：修正が必要\n\n## 未解決の指摘\n- 境界条件の確認"
        )
        process = self.review(first, to="claude", reply=reply)
        result = self.result(process)
        self.assertIn("起動中", process.stderr)
        self.assertIn("応答あり", process.stderr)
        self.assertIn("保存済み", process.stderr)
        self.assertIn("**結論：修正が必要**", result.read_text())
        self.assertIn("境界条件の確認", result.read_text())
        self.assertNotIn("結果をまとめます。", result.read_text())
        self.assertIn(reply, result.with_suffix(".stdout").read_text())

        before = self.latest.read_bytes()
        cases = [
            ("## 検証結果\n確認しました。", "結論欄がありません"),
            ("結論：指摘なし\n\n**結論：修正が必要**", "結論欄が複数あります"),
            ("結論：未定", "規定の選択肢"),
            ("## 検証結果\n結論：指摘なし", "短い前置き"),
            ("一行目\n二行目\n三行目\n結論：指摘なし", "短い前置き"),
        ]
        for malformed, reason in cases:
            with self.subTest(reason=reason, reply=malformed):
                failed = self.review(second, reply=malformed)
                self.assertNotEqual(failed.returncode, 0)
                self.assertIn("応答あり", failed.stderr)
                self.assertIn("解析失敗", failed.stderr)
                self.assertIn(reason, failed.stderr)
                self.assertNotIn("保存済み", failed.stderr)
                self.assertEqual(failed.stdout, "")
                self.assertEqual(self.latest.read_bytes(), before)
        self.assertEqual(list(self.history.glob(f"run-*/{self.repo.name}.md")), [result])

    def test_sha_mismatch_and_failed_review_preserve_latest(self):
        first, second = self.heads[:2]
        self.result(self.review(first))
        before = self.latest.read_bytes()
        self.assert_blocked(self.review(second, expected=first), "HEADが指定と異なります")
        failure = self.review(second, fail=True)
        self.assertNotEqual(failure.returncode, 0)
        self.assertIn("終了コード 7", failure.stderr)
        self.assertEqual(self.latest.read_bytes(), before)
        failed_workspace, = self.history.glob(f"run-*/{self.repo.name}/.git")
        self.assertTrue((failed_workspace.parent.parent / f"{self.repo.name}.stderr").is_file())
        invalid = self.review(second, reply="形式のない回答")
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn("結論欄", invalid.stderr)
        self.assertEqual(self.latest.read_bytes(), before)

    def test_incremental_review_carries_only_unresolved_findings_for_since_sha(self):
        first, second, third = self.heads[:3]
        previous = self.result(self.review(first, reply=(
            "結論：修正が必要\n\n"
            "## 未解決の指摘\n- 日付の境界条件を確認する。\n\n"
            "## 解消済みの指摘\n- 古い表示の指摘。\n\n"
            "## 検証結果\n- 前回のテスト結果。\n\n"
            "## 参考資料への追記候補\n- 汎用の確認点候補。"
        )))
        self.assertIn("汎用の確認点候補。", previous.read_text())
        self.result(self.review(second, reply=(
            "結論：修正が必要\n\n## 未解決の指摘\n- 別のSHAの指摘。"
        )))
        result = self.result(self.review(third, "--since", first[:8], to="claude"))
        sent = self.call.read_text()
        self.assertIn("日付の境界条件を確認する。", sent)
        for excluded in ("古い表示の指摘。", "前回のテスト結果。", "別のSHAの指摘。", "汎用の確認点候補。"):
            self.assertNotIn(excluded, sent)
        self.assertEqual((result.parent / "previous-findings.md").read_text(),
                         "- 日付の境界条件を確認する。\n")

    def test_pending_review_requires_answer_for_same_or_new_sha(self):
        first, second = self.heads[:2]
        self.result(self.review(first, reply="結論：ユーザー判断待ち"))
        for head in (first, second):
            with self.subTest(head=head):
                self.assert_blocked(self.review(head, "--approved-by-user"), "--user-answer")
        self.assert_blocked(self.review(second, "--user-answer", "  "), "--user-answer")
        answer = "前日の確定値を使う。"
        result = self.result(self.review(second, "--user-answer", answer))
        self.assertIn(answer, self.call.read_text())
        self.assertEqual((result.parent / "user-answer.md").read_text().strip(), answer)
        self.result(self.review(second))

    def test_fifth_distinct_head_requires_approval_even_after_changing_reviewer(self):
        for head in self.heads[:4]:
            self.result(self.review(head))
        self.result(self.review(self.heads[3], to="claude"))
        fifth, sixth = self.heads[4:]
        self.assert_blocked(self.review(fifth, to="claude"), "第5回")
        self.result(self.review(fifth, "--approved-by-user", to="claude"))
        self.assertIn("ユーザーの続行承認あり", self.latest.read_text())
        self.assert_blocked(self.review(sixth), "第6回")

    def test_review_resumes_with_saved_questions_and_user_answers(self):
        first, second = self.heads[:2]
        self.result(self.review(first, reply=(
            "結論：ユーザー判断待ち\n\n"
            "## ユーザー確認待ち\n1. 初回はどの日を表示しますか？\n"
            "2. 欠損日は表示しますか？\n\n## 検証結果\n旧テストの詳細"
        )))
        answer = "1. 前日。\n2. 表示しない。"
        result = self.result(self.review(second, "--user-answer", answer, to="claude"))
        context = (result.parent / "user-answer.md").read_text()
        self.assertIn("## 前回の質問", context)
        self.assertIn("2. 欠損日は表示しますか？", context)
        self.assertIn(f"## ユーザーの回答\n\n{answer}", context)
        self.assertNotIn("旧テストの詳細", context)
        self.assertIn(context.strip(), self.call.read_text())

    def test_implementation_keeps_changes_in_its_own_workspace(self):
        brief = self.root / "brief.md"
        brief.write_text("実装の依頼", encoding="utf-8")
        result = self.result(self.invoke("implement", "--brief", brief, reply="実装完了"))
        self.assertEqual(result.parent.parent, self.root / ".handoff-runs/implement")
        self.assertEqual((result.parent / self.repo.name / "implementation.txt").read_text(),
                         "implemented\n")
        self.assertFalse((self.repo / "implementation.txt").exists())

    def test_copied_package_reviews_project_root_without_repo_flag(self):
        shutil.move(self.repo / ".git", self.root / ".git")
        self.repo = self.root
        self.git("remote", "set-url", "origin", "https://github.com/fixture-org/upstream-app")
        result = self.result(self.review(self.heads[0], use_root=True, explicit_workspace=True))
        self.assertEqual(result.parent.parent,
                         self.root / ".handoff-runs/review" / self.root.name / "pr-37")


if __name__ == "__main__":
    unittest.main()
