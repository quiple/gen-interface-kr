# googlefonts/nam-files の vendored data

このディレクトリには、次のリポジトリから取得したデータを固定して置いています。

https://github.com/googlefonts/nam-files

含めているファイル:

- `slices/japanese_default.txt`

元プロジェクトのライセンスは Apache-2.0 です。このディレクトリ内の `LICENSE` を参照してください。このデータは Gen Interface KR の Web フォント subset 生成における、デフォルトの日本語分割 strategy として使います。

## 使われ方

`src/webfont/build.py` の `google-japanese` strategy が、`slices/japanese_default.txt` を読み込みます。各 slice に含まれるコードポイントと Gen Interface KR Regular の cmap を intersect し、実際にフォントが持つグリフだけを subset WOFF2 にします。

Google Fonts のライブ CSS を観測する処理は持たず、OSS として公開されているこのデータを固定して参照します。
