# 入力フォント

Gen Interface KR の生成に使う外部由来の入力フォントを置くディレクトリです。

## 配置

```text
vendor/fonts/
  Inter-4.1/
  Noto_Sans_KR/
```

`src/font/build.py` は Inter の static TTF を `Inter-4.1/extras/ttf/` から、Noto Sans KR の variable font を `Noto_Sans_KR/NotoSansKR-VF.ttf` から読み込みます。

## 使われ方

- Inter / Inter Display は Latin 側のベースとして使います。
- Noto Sans KR は日本語側のベースとして使い、`palt` 情報をもとにプロポーショナル化します。

このディレクトリは入力素材置き場です。ここから生成した TTF / WOFF2 は `dist/` 配下に出力します。
