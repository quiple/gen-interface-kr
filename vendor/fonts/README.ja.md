# 入力フォント

Gen Interface JP の生成に使う外部由来の入力フォントを置くディレクトリです。

## 配置

```text
vendor/fonts/
  Inter-4.1/
  Noto_Sans_JP/
```

`src/font/build.py` は Inter の static TTF を `Inter-4.1/extras/ttf/` から、Noto Sans JP の variable font を `Noto_Sans_JP/NotoSansJP-VariableFont_wght.ttf` から読み込みます。

## 使われ方

- Inter / Inter Display は Latin 側のベースとして使います。
- Noto Sans JP は日本語側のベースとして使い、`palt` 情報をもとにプロポーショナル化します。

このディレクトリは入力素材置き場です。ここから生成した TTF / WOFF2 は `dist/` 配下に出力します。
