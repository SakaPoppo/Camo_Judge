# 命名規則

## 基本方針

名前から変更の種類と対象Issueが分かる、短く一貫した形式を使います。軽微な変更では説明を簡潔にし、形式の維持そのものを目的にしません。

## ブランチ名

形式は `<種類>/<Issue番号>-<短い説明>` とし、説明は英小文字のkebab-caseを基本とします。

```text
feat/12-color-extraction
fix/15-image-loading
research/18-hsv-comparison
docs/20-update-specification
chore/22-setup-environment
```

種類の使い分け：

- `feat`：機能追加・改善
- `fix`：バグ修正
- `research`：分析・調査
- `docs`：文書のみの変更
- `chore`：環境設定や保守作業

## コミットメッセージ

Conventional Commitsの `<種類>: <要約>` を使用します。種類は英語、要約は日本語を基本とし、変更内容を短く表します。

```text
feat: 主要色の抽出機能を追加
fix: 不正な画像の読み込み処理を修正
research: HSVヒストグラムを比較
docs: 分析仕様書を更新
test: 画像処理のテストを追加
refactor: 前処理を簡略化
chore: 開発環境を設定
```

複数の種類を無理に一つへまとめず、作業の意味が変わる場合はコミットを分けます。作業途中の細かなコミットはSquash mergeで一つにまとめられます。

## PRタイトル

コミットと同じ `<種類>: <日本語の要約>` を使用し、Squash後に残る変更内容が分かる名前にします。

```text
feat: 主要色の抽出機能を実装
fix: 画像読み込み処理を修正
docs: データ仕様書を更新
```
